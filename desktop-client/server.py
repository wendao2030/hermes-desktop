#!/usr/bin/env python3
"""
Hermes Desktop Client - FastAPI Server
Thin glue layer between Vue frontend and AIAgent backend.
"""

import sys
import os
import json
import uuid
import threading
import asyncio
import time
import traceback
import socket
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# --- Path setup: import AIAgent from hermes-agent ---
HERMES_HOME = Path(__file__).resolve().parent.parent
HERMES_AGENT = HERMES_HOME / "hermes-agent"
os.environ["HERMES_HOME"] = str(HERMES_HOME)
sys.path.insert(0, str(HERMES_AGENT))

try:
    import hermes_bootstrap  # noqa: F401
except ModuleNotFoundError:
    pass

from run_agent import AIAgent
from hermes_constants import parse_reasoning_effort
from hermes_state import SessionDB
from utils import is_truthy_value, normalize_proxy_env_vars

# --- FastAPI ---
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# --- Config / environment ---
from hermes_cli.config import load_config as load_hermes_config
from hermes_cli.env_loader import load_hermes_dotenv

PROJECT_ENV = HERMES_AGENT / ".env"
load_hermes_dotenv(hermes_home=HERMES_HOME, project_env=PROJECT_ENV)
normalize_proxy_env_vars()

SESSION_SOURCE = "desktop"

def load_config():
    return load_hermes_config()

app = FastAPI(title="Hermes Desktop Client")

# --- In-memory server log ---
server_logs = []
MAX_LOG_LINES = 500
LOG_FILE = Path(__file__).resolve().parent / "desktop_server.log"

def log_msg(level: str, msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = {"time": ts, "level": level, "msg": msg}
    server_logs.append(entry)
    if len(server_logs) > MAX_LOG_LINES:
        del server_logs[:len(server_logs) - MAX_LOG_LINES]
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {level}: {msg}\n")
    except Exception:
        pass

log_msg("INFO", "Server starting up...")

# --- Session management ---
sessions = {}  # {session_id: {"agent": AIAgent, "history": [], "created_at": datetime, "title": str}}
session_lock = threading.Lock()
session_db = SessionDB(HERMES_HOME / "state.db")

# --- Auto-shutdown when browser closes ---
active_connections = 0
shutdown_timer = None
shutdown_lock = threading.Lock()

def cancel_shutdown():
    global shutdown_timer
    with shutdown_lock:
        if shutdown_timer:
            shutdown_timer.cancel()
            shutdown_timer = None

def schedule_shutdown():
    global shutdown_timer
    with shutdown_lock:
        if shutdown_timer:
            return
        shutdown_timer = threading.Timer(8.0, do_shutdown)
        shutdown_timer.daemon = True
        shutdown_timer.start()
        log_msg("INFO", "Browser disconnected, server will exit in 8s if no reconnect...")

def do_shutdown():
    global shutdown_timer
    with shutdown_lock:
        if active_connections > 0:
            shutdown_timer = None
            return
        shutdown_timer = None
    log_msg("INFO", "Shutting down (no active clients)...")
    os._exit(0)

def generate_session_id():
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

def _ts_to_iso(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value)).isoformat()
    except (TypeError, ValueError, OSError):
        return datetime.now().isoformat()

def _message_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") in {"text", "input_text"}:
                    parts.append(str(item.get("text") or ""))
                elif "text" in item:
                    parts.append(str(item.get("text") or ""))
                elif item.get("type") in {"image", "image_url", "input_image"}:
                    parts.append("[图片]")
        return "\n".join(p for p in parts if p)
    return str(content)

def _history_for_frontend(history: list[dict]) -> list[dict]:
    visible = []
    for msg in history or []:
        role = msg.get("role")
        if role not in {"user", "assistant", "tool", "system"}:
            continue
        # Hide tool messages from frontend — they are technical internals
        if role == "tool":
            continue
        content = _message_text(msg.get("content"))
        if not content and role != "assistant":
            continue
        item = {"role": role, "content": content}
        visible.append(item)
    return visible

def _load_history_from_db(session_id: str) -> list[dict]:
    try:
        return session_db.get_messages_as_conversation(session_id, include_ancestors=True)
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Failed to load DB history: {e}")
        return []

def _default_title_from_history(history: list[dict], fallback: str = "") -> str:
    for msg in history or []:
        if msg.get("role") != "user":
            continue
        text = _message_text(msg.get("content")).strip().replace("\n", " ")
        if text:
            return text[:30] + ("..." if len(text) > 30 else "")
    return fallback

def _get_model_name(cfg: dict | None = None) -> str:
    cfg = cfg or load_config()
    model_cfg = cfg.get("model", "")
    if isinstance(model_cfg, dict):
        return str(model_cfg.get("default") or "").strip()
    return str(model_cfg or "").strip()

def _cfg_max_turns(cfg: dict, default: int = 90) -> int:
    agent_cfg = cfg.get("agent") or {}
    try:
        return int(agent_cfg.get("max_turns") or cfg.get("max_turns") or default)
    except (TypeError, ValueError):
        return default

def _load_reasoning_config(cfg: dict) -> dict | None:
    effort = str((cfg.get("agent") or {}).get("reasoning_effort", "") or "").strip()
    return parse_reasoning_effort(effort)

def _load_service_tier(cfg: dict) -> str | None:
    raw = str((cfg.get("agent") or {}).get("service_tier", "") or "").strip().lower()
    if not raw or raw in {"normal", "default", "standard", "off", "none"}:
        return None
    if raw in {"fast", "priority", "on"}:
        return "priority"
    return None

def _load_enabled_toolsets(cfg: dict) -> list[str] | None:
    try:
        from hermes_cli.tools_config import _get_platform_tools

        return sorted(_get_platform_tools(cfg, "cli", include_default_mcp_servers=True)) or None
    except Exception as e:
        log_msg("WARN", f"Could not resolve configured toolsets: {e}")
        return None

def _load_fallback_chain(cfg: dict) -> list[dict] | None:
    try:
        from hermes_cli.fallback_config import get_fallback_chain

        chain = get_fallback_chain(cfg)
        return chain or None
    except Exception as e:
        log_msg("WARN", f"Could not resolve fallback providers: {e}")
        return None

def _runtime_has_key(runtime: dict) -> bool:
    api_key = (runtime or {}).get("api_key")
    if callable(api_key) and not isinstance(api_key, str):
        return True
    return bool(isinstance(api_key, str) and api_key.strip())

def _proxy_env_keys() -> list[str]:
    keys = []
    for key in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY"):
        if os.environ.get(key) or os.environ.get(key.lower()):
            keys.append(key)
    return keys

def _resolve_desktop_runtime(cfg: dict) -> tuple[str, dict]:
    model = _get_model_name(cfg)
    try:
        from hermes_cli.runtime_provider import resolve_runtime_provider

        runtime = resolve_runtime_provider(target_model=model or None)
    except Exception as e:
        log_msg("WARN", f"Runtime provider resolution failed, falling back to config.yaml: {e}")
        model_cfg = cfg.get("model", {}) if isinstance(cfg.get("model"), dict) else {}
        runtime = {
            "provider": model_cfg.get("provider"),
            "base_url": model_cfg.get("base_url"),
            "api_key": model_cfg.get("api_key"),
            "api_mode": model_cfg.get("api_mode"),
        }

    runtime_model = runtime.get("model")
    if isinstance(runtime_model, str) and runtime_model.strip():
        provider_name = str(runtime.get("name") or "").strip()
        provider = str(runtime.get("provider") or "").strip()
        if not model or model == provider or (provider_name and model == provider_name):
            model = runtime_model.strip()

    base_url = str(runtime.get("base_url") or "")
    log_msg(
        "INFO",
        "Runtime resolved: "
        f"provider={runtime.get('provider') or 'unknown'} "
        f"requested={runtime.get('requested_provider') or 'unknown'} "
        f"model={model or 'unknown'} "
        f"api_mode={runtime.get('api_mode') or 'unknown'} "
        f"base_url={base_url or 'unknown'} "
        f"has_key={_runtime_has_key(runtime)} "
        f"request_overrides={bool(runtime.get('request_overrides'))} "
        f"proxy_env={','.join(_proxy_env_keys()) or 'none'}",
    )
    return model, runtime

def _session_summary_from_row(row: dict) -> dict:
    session_id = row.get("id") or row.get("session_id") or ""
    title = (row.get("title") or row.get("preview") or "").strip()
    if not title:
        title = session_id[-12:]
    started = row.get("last_active") or row.get("started_at")
    return {
        "session_id": session_id,
        "created_at": _ts_to_iso(started),
        "title": title,
        "message_count": int(row.get("message_count") or 0),
    }

def _ensure_session_record(session_id: str) -> None:
    try:
        session_db.ensure_session(session_id, source=SESSION_SOURCE, model=_get_model_name())
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Failed to ensure DB session: {e}")

def get_session_dir(session_id: str) -> Path:
    d = HERMES_HOME / "desktop-client" / "sessions" / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _empty_session():
    return {
        "agent": None,
        "history": [],
        "created_at": datetime.now(),
        "title": "",
        "callbacks": {},
        "running": False,
        "agent_thread": None,
    }

def _emit_session_event(session_id: str, event: dict):
    """Send an agent event through the current WebSocket bridge, if present."""
    with session_lock:
        session = sessions.get(session_id)
        callbacks = dict((session or {}).get("callbacks") or {})
    emit = callbacks.get("emit")
    if emit:
        try:
            emit(event)
        except Exception as e:
            log_msg("WARN", f"[{session_id[:12]}] event callback failed: {e}")

def create_agent(session_id: str) -> AIAgent:
    cfg = load_config()
    agent_cfg = cfg.get("agent", {})
    system_prompt = (agent_cfg.get("system_prompt", "") or "").strip()
    model, runtime = _resolve_desktop_runtime(cfg)

    agent = AIAgent(
        model=model,
        api_key=runtime.get("api_key"),
        base_url=runtime.get("base_url"),
        provider=runtime.get("provider"),
        api_mode=runtime.get("api_mode"),
        acp_command=runtime.get("command"),
        acp_args=runtime.get("args"),
        credential_pool=runtime.get("credential_pool"),
        max_iterations=_cfg_max_turns(cfg, 90),
        quiet_mode=True,
        verbose_logging=False,
        session_id=session_id,
        session_db=session_db,
        platform=SESSION_SOURCE,
        ephemeral_system_prompt=system_prompt or None,
        reasoning_config=_load_reasoning_config(cfg),
        service_tier=_load_service_tier(cfg),
        request_overrides=runtime.get("request_overrides"),
        enabled_toolsets=_load_enabled_toolsets(cfg),
        fallback_model=_load_fallback_chain(cfg),
        checkpoints_enabled=is_truthy_value(os.environ.get("HERMES_DESKTOP_CHECKPOINTS")),
        pass_session_id=is_truthy_value(os.environ.get("HERMES_DESKTOP_PASS_SESSION_ID")),
        stream_delta_callback=lambda delta: _emit_session_event(
            session_id, {"type": "delta", "text": delta}
        ) if delta else None,
        tool_progress_callback=lambda event_type, name=None, preview=None, args=None, **kwargs: _emit_session_event(
            session_id,
            {
                "type": "tool",
                "event": str(event_type),
                "name": str(name or ""),
                "status": str(kwargs.get("status") or event_type),
                "detail": str(preview or kwargs.get("summary") or ""),
            },
        ),
        tool_start_callback=lambda _tc_id, name, _args: _emit_session_event(
            session_id, {"type": "tool", "event": "tool.start", "name": str(name), "status": "started"}
        ),
        tool_complete_callback=lambda _tc_id, name, _args, _result: _emit_session_event(
            session_id, {"type": "tool", "event": "tool.complete", "name": str(name), "status": "complete"}
        ),
        thinking_callback=lambda text: _emit_session_event(
            session_id, {"type": "status", "text": str(text or "thinking")}
        ),
        reasoning_callback=lambda text: _emit_session_event(
            session_id, {"type": "reasoning", "text": str(text or "")}
        ) if text else None,
        status_callback=lambda kind, text=None: _emit_session_event(
            session_id, {"type": "status", "kind": str(kind), "text": str(text or kind)}
        ),
    )
    return agent

def get_or_create_session(session_id: str):
    with session_lock:
        if session_id not in sessions:
            sessions[session_id] = _empty_session()
        if not sessions[session_id]["history"]:
            sessions[session_id]["history"] = _load_history_from_db(session_id)
        s = sessions[session_id]
        if not s["history"]:
            s["history"] = _load_history_from_db(session_id)
        if s["agent"] is None:
            s["agent"] = create_agent(session_id)
        return s

# --- Static files (frontend) ---
STATIC_DIR = Path(__file__).resolve().parent / "static"

@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

# Serve static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- API ---

@app.get("/api/logs")
async def api_logs():
    """Return recent server logs for the frontend."""
    return {"logs": server_logs[-200:]}

@app.get("/api/config")
async def api_config():
    """Return non-sensitive config info for the frontend."""
    cfg = load_config()
    model, runtime = _resolve_desktop_runtime(cfg)
    provider = runtime.get("requested_provider") or runtime.get("provider") or "unknown"
    base_url = runtime.get("base_url") or "unknown"
    return {
        "model": model or "unknown",
        "provider": provider,
        "base_url": base_url,
        "max_turns": _cfg_max_turns(cfg, 90),
    }

@app.get("/api/diagnostics/runtime")
async def api_runtime_diagnostics():
    """Return redacted runtime/network diagnostics for desktop troubleshooting."""
    cfg = load_config()
    model, runtime = _resolve_desktop_runtime(cfg)
    base_url = str(runtime.get("base_url") or "")
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    tcp_probe = {"host": host, "port": port, "ok": False, "error": ""}
    if host:
        try:
            with socket.create_connection((host, port), timeout=8):
                tcp_probe["ok"] = True
        except Exception as e:
            tcp_probe["error"] = f"{type(e).__name__}: {e}"
    return {
        "python": sys.executable,
        "cwd": os.getcwd(),
        "hermes_home": str(HERMES_HOME),
        "model": model or "unknown",
        "provider": runtime.get("provider") or "unknown",
        "requested_provider": runtime.get("requested_provider") or "unknown",
        "api_mode": runtime.get("api_mode") or "unknown",
        "base_url": base_url or "unknown",
        "has_key": _runtime_has_key(runtime),
        "request_overrides": bool(runtime.get("request_overrides")),
        "proxy_env": _proxy_env_keys(),
        "tcp_probe": tcp_probe,
    }

@app.post("/api/session/new")
async def new_session():
    session_id = generate_session_id()
    _ensure_session_record(session_id)
    # Defer agent creation — only pre-register the session
    with session_lock:
        if session_id not in sessions:
            sessions[session_id] = _empty_session()
    return {"session_id": session_id}

@app.get("/api/sessions")
async def list_sessions():
    result = []
    try:
        rows = session_db.list_sessions_rich(
            source=SESSION_SOURCE,
            limit=200,
            order_by_last_active=True,
        )
        result = [_session_summary_from_row(row) for row in rows]
    except Exception as e:
        log_msg("WARN", f"Failed to list sessions from DB: {e}")

    with session_lock:
        known_ids = {item["session_id"] for item in result}
        for sid, s in sessions.items():
            if sid in known_ids:
                continue
            msg_count = len([m for m in s["history"] if m.get("role") == "user"])
            result.append({
                "session_id": sid,
                "created_at": s["created_at"].isoformat(),
                "title": s.get("title", "") or _default_title_from_history(s.get("history") or [], sid[-12:]),
                "message_count": msg_count,
            })
    result.sort(key=lambda x: x["created_at"], reverse=True)
    return result

@app.get("/api/session/{session_id}/history")
async def get_history(session_id: str):
    db_row = None
    try:
        db_row = session_db.get_session(session_id)
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Failed to inspect DB session: {e}")

    with session_lock:
        s = sessions.get(session_id)

    if not s and not db_row:
        raise HTTPException(status_code=404, detail="Session not found")

    history = _load_history_from_db(session_id)
    if not history and s:
        history = s.get("history") or []

    with session_lock:
        if session_id not in sessions:
            sessions[session_id] = _empty_session()
        sessions[session_id]["history"] = history
        if db_row:
            sessions[session_id]["created_at"] = datetime.fromtimestamp(float(db_row.get("started_at") or time.time()))
            sessions[session_id]["title"] = db_row.get("title") or _default_title_from_history(history)

    return {"history": _history_for_frontend(history)}

@app.post("/api/session/{session_id}/interrupt")
async def interrupt_session(session_id: str):
    with session_lock:
        session = sessions.get(session_id)
        agent = (session or {}).get("agent")
        running = bool((session or {}).get("running"))

    if not session or not agent:
        return {"ok": False, "status": "idle"}
    if hasattr(agent, "interrupt"):
        try:
            agent.interrupt()
            log_msg("INFO", f"[{session_id[:12]}] Interrupt requested")
            _emit_session_event(session_id, {"type": "status", "text": "interrupting"})
            return {"ok": True, "status": "interrupted" if running else "idle"}
        except Exception as e:
            log_msg("ERROR", f"[{session_id[:12]}] Interrupt failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return {"ok": False, "status": "unsupported"}

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    with session_lock:
        if session_id in sessions:
            del sessions[session_id]
    try:
        session_db.delete_session(session_id)
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] DB delete failed: {e}")
    return {"ok": True}

@app.post("/api/upload/{session_id}")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    session_dir = get_session_dir(session_id) / "uploads"
    session_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_name = Path(file.filename).name
    filepath = session_dir / safe_name

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return {
        "filename": safe_name,
        "path": str(filepath),
        "size": len(content),
    }

@app.get("/api/files/{session_id}")
async def list_files(session_id: str):
    session_dir = get_session_dir(session_id)
    files = []
    if session_dir.exists():
        for f in session_dir.rglob("*"):
            if f.is_file():
                rel = f.relative_to(session_dir)
                files.append({
                    "name": str(rel).replace("\\", "/"),
                    "size": f.stat().st_size,
                })
    return {"files": files}

@app.get("/api/file/{session_id}/{filename:path}")
async def download_file(session_id: str, filename: str):
    filepath = get_session_dir(session_id) / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath)

@app.get("/api/skills")
async def list_skills():
    """List installed skills using native hermes-agent."""
    try:
        from tools.skills_tool import _find_all_skills
        from agent.skill_utils import get_disabled_skill_names
        from hermes_constants import get_hermes_home

        all_skills = _find_all_skills(skip_disabled=False)
        disabled = get_disabled_skill_names()

        # Determine skill source: bundled, hub, or local
        skills_dir = get_hermes_home() / "skills"
        bundled_names = set()
        hub_names = set()

        bundled_manifest = skills_dir / ".bundled_manifest"
        if bundled_manifest.exists():
            try:
                for line in bundled_manifest.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        bundled_names.add(line.split(":", 1)[0].strip())
            except Exception:
                pass

        hub_lock = skills_dir / ".hub" / "lock.json"
        if hub_lock.exists():
            try:
                import json
                data = json.loads(hub_lock.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for name in (data.get("installed") or {}).keys():
                        hub_names.add(str(name))
            except Exception:
                pass

        def _skill_source(name):
            if name in bundled_names:
                return "builtin"
            if name in hub_names:
                return "hub"
            return "local"

        result = []
        for s in all_skills:
            name = s.get("name", "")
            result.append({
                "name": name,
                "description": s.get("description", ""),
                "category": s.get("category", ""),
                "enabled": name not in disabled,
                "source": _skill_source(name),
            })
        return {"skills": result, "count": len(result)}
    except Exception as e:
        log_msg("WARN", f"Skills list failed: {e}")
        return {"skills": [], "count": 0, "error": str(e)}

@app.get("/api/skills/featured")
async def get_featured_skills():
    """Get featured/popular skills. Tries uskill.cn first (domestic CDN, fast),
    falls back to built-in Chinese recommendations if network fails."""
    try:
        import httpx
        resp = httpx.get("https://www.uskill.cn/api/skills?pageSize=20", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            skills = []
            for sk in (data.get("skills") or [])[:20]:
                meta = sk.get("metadata", {})
                tags = meta.get("tags", [])
                # Map English tags to Chinese
                tag_map = {
                    "API": "接口", "React": "前端", "Vue": "前端", "Next.js": "前端",
                    "GitHub": "代码托管", "CI/CD": "自动化部署", "DevOps": "运维",
                    "Claude": "AI助手", "Excel": "电子表格", "Word": "文档",
                    "PDF": "文档处理", "PPT": "演示文稿", "Notion": "笔记",
                    "Database": "数据库", "Agent": "智能体", "Workflow": "工作流",
                    "框架": "开发", "文档": "文档工具", "编辑": "文本处理",
                    "分析": "数据分析", "设计": "UI设计", "集成": "系统集成",
                    "测试": "软件测试", "自动化": "自动执行", "智能体": "AI智能体",
                    "任务": "效率工具", "模板": "模板生成", "技能": "扩展能力",
                    "网页": "Web开发", "代码": "编程", "安全": "安全审计",
                    "协作": "团队协作", "部署": "运维发布",
                }
                cn_tags = [tag_map.get(t, t) for t in tags[:3]]
                
                # Get the best description: use enriched Chinese desc if available
                title = meta.get("title", sk.get("name", ""))
                short_zh = meta.get("shortDescZh", "") or ""
                en_desc = meta.get("description", "") or ""
                md_content = sk.get("markdown", "") or ""
                
                # Try enrichment map first, then fallback strategies
                desc = _enrich_skill_description(title, short_zh, en_desc, md_content)
                skills.append({
                    "name": title,
                    "description": desc[:180],
                    "source": "uskill.cn",
                    "identifier": meta.get("url", ""),
                    "trust_level": "community",
                    "tags": cn_tags,
                    "install_cmd": f"skills install {title}",
                })
            if skills:
                return {"skills": skills, "count": len(skills), "source": "uskill.cn"}
    except Exception:
        pass

    # Fallback to built-in Chinese recommendations
    skills = _builtin_recommended_skills()
    return {"skills": skills, "count": len(skills), "source": "builtin"}

def _enrich_skill_description(title: str, short_zh: str, en_desc: str, md_content: str) -> str:
    """Pick the best description for a skill. Prefers Chinese enrichment,
    falls back to English description if short_zh is too brief."""
    # If short_zh is a keyword list (like "文档、编辑、分析、Claude 相关"), it's too brief
    if short_zh and not short_zh.endswith("相关") and len(short_zh) > 20:
        return short_zh

    # Common skills with Chinese descriptions
    cn_map = {
        "docx": "创建和编辑 Word 文档，支持修订追踪、批注、格式保留和文字提取，适合写报告、合同、论文等专业文档",
        "xlsx": "创建和编辑 Excel 电子表格，支持公式计算、数据分析和图表可视化，处理 .xlsx/.csv 格式文件",
        "pptx": "创建和编辑 PowerPoint 演示文稿，支持完整幻灯片操作、排版设计和动画效果",
        "pdf": "全能 PDF 处理工具：提取文字、创建表单、合并拆分文档、加水印和签名",
        "skill-creator": "创建自定义技能的指南，零基础也能上手，用自然语言描述需求即可生成专属技能",
        "mcp-builder": "创建 MCP 服务器，让 AI 连接外部 API 和工具，打通各种软件平台",
        "theme-factory": "一键套用预设主题到幻灯片、文档、网页，10 套精美主题可选",
        "web-artifacts-builder": "用 React 和 HTML/CSS 快速搭建可交互网页小组件，做工具页面和数据看板",
        "algorithmic-art": "用 p5.js 创作算法生成艺术作品，输入创意即可生成独一无二的视觉图案",
        "canvas-design": "用 Canvas 设计精美视觉图形和海报，适合宣传图、活动物料和社交媒体配图",
        "frontend-design": "快速生成漂亮的前端页面，支持 React/HTML/CSS，做网站和落地页非常方便",
        "slack-gif-creator": "制作动画 GIF，支持聊天斗图、产品演示和教学示范",
        "internal-comms": "撰写专业内部通讯：周报、新闻稿、FAQ、通知公告，一键生成规范格式",
        "webapp-testing": "用 Playwright 自动测试网站功能和性能，检测无障碍性，帮你发现 Bug",
        "brand-guidelines": "自动应用品牌配色和字体规范，确保所有设计输出风格统一",
        "notion": "Notion API 集成工具，可创建和管理页面、数据库、块，自动化你的笔记工作流",
        "prompting": "智能提示词生成系统，用模板和最佳实践优化你的 AI 对话效果",
        "n8n-workflow-patterns": "n8n 工作流自动化模板，包含 Webhook、API 集成、数据库操作和 AI 智能体模式",
    }
    if title in cn_map:
        return cn_map[title]

    # Fallback: use English description (first 180 chars, cut at sentence boundary)
    if en_desc:
        # Find a good sentence break within 180 chars
        cut = en_desc[:180]
        if len(en_desc) > 180:
            last_dot = cut.rfind(". ")
            if last_dot > 60:
                cut = cut[:last_dot + 1]
        return cut

    # Last resort: use short_zh even if brief
    return short_zh or "暂无描述"

@app.get("/api/skills/{name}")
async def get_skill_detail(name: str):
    """View skill content using native hermes-agent."""
    try:
        from tools.skills_tool import skill_view
        return json.loads(skill_view(name))
    except Exception as e:
        log_msg("WARN", f"Skill view failed for '{name}': {e}")
        return {"success": False, "error": str(e)}

@app.post("/api/skills/{name}/toggle")
async def toggle_skill(name: str):
    """Enable/disable a skill via config."""
    try:
        from hermes_cli.skills_config import get_disabled_skills, save_disabled_skills
        cfg = load_config()
        disabled = get_disabled_skills(cfg)
        if name in disabled:
            disabled.remove(name)
            enabled = True
        else:
            disabled.add(name)
            enabled = False
        save_disabled_skills(cfg, disabled)
        return {"ok": True, "name": name, "enabled": enabled}
    except Exception as e:
        log_msg("WARN", f"Toggle skill failed for '{name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/skills/search/market")
async def search_skills_market(q: str = "", source: str = "all", limit: int = 20):
    """Search skills hub using native hermes-agent."""
    try:
        from tools.skills_hub import unified_search, create_source_router, GitHubAuth
        auth = GitHubAuth()
        sources = create_source_router(auth)
        results = unified_search(q, sources, source_filter=source, limit=limit)
        return {
            "skills": [
                {
                    "name": r.name,
                    "description": r.description,
                    "source": r.source,
                    "identifier": r.identifier,
                    "trust_level": r.trust_level,
                    "tags": r.tags,
                }
                for r in results
            ],
            "count": len(results),
        }
    except Exception as e:
        log_msg("WARN", f"Market search failed: {e}")
        return {"skills": [], "count": 0, "error": str(e)}

def _builtin_recommended_skills():
    """精选推荐技能列表（中文描述，面向普通用户）"""
    return [
        {"name": "PPT 制作", "description": "创建、编辑和分析 PowerPoint 演示文稿，支持完整幻灯片操作，做汇报、课件、方案演示必备", "source": "推荐", "identifier": "skills-sh/anthropics/skills/pptx", "trust_level": "trusted", "tags": ["办公", "演示"]},
        {"name": "PDF 处理", "description": "全能 PDF 工具：提取文字、创建表单、合并拆分文档、加水印签名，轻松处理各类 PDF 文件", "source": "推荐", "identifier": "skills-sh/anthropics/skills/pdf", "trust_level": "trusted", "tags": ["办公", "文档"]},
        {"name": "Word 文档", "description": "创建和编辑 Word 文档，支持修订追踪、批注、格式保留、文字提取，写报告合同不用愁", "source": "推荐", "identifier": "skills-sh/anthropics/skills/docx", "trust_level": "trusted", "tags": ["办公", "文档"]},
        {"name": "Excel 表格", "description": "创建和编辑 Excel 电子表格，支持公式计算、格式化、数据分析和图表可视化", "source": "推荐", "identifier": "skills-sh/anthropics/skills/xlsx", "trust_level": "trusted", "tags": ["办公", "表格"]},
        {"name": "网页设计", "description": "快速生成漂亮的前端页面，支持 React、HTML/CSS，做网站、落地页、H5 活动页非常方便", "source": "推荐", "identifier": "skills-sh/anthropics/skills/frontend-design", "trust_level": "trusted", "tags": ["设计", "网页"]},
        {"name": "主题美化", "description": "一键套用预设主题到幻灯片、文档、网页，10 套精美主题可选，让你的作品瞬间好看", "source": "推荐", "identifier": "skills-sh/anthropics/skills/theme-factory", "trust_level": "trusted", "tags": ["设计", "美化"]},
        {"name": "算法艺术", "description": "用 p5.js 创作算法生成的艺术作品，输入创意就能生成独一无二的视觉图案", "source": "推荐", "identifier": "skills-sh/anthropics/skills/algorithmic-art", "trust_level": "trusted", "tags": ["创意", "艺术"]},
        {"name": "画布设计", "description": "用 Canvas 设计精美的视觉图形和海报，适合做宣传图、活动物料、社交媒体配图", "source": "推荐", "identifier": "skills-sh/anthropics/skills/canvas-design", "trust_level": "trusted", "tags": ["创意", "设计"]},
        {"name": "动图制作", "description": "制作 Slack 等平台适用的动画 GIF，聊天斗图、产品演示、教学示范都能用", "source": "推荐", "identifier": "skills-sh/anthropics/skills/slack-gif-creator", "trust_level": "trusted", "tags": ["创意", "动图"]},
        {"name": "公司文案", "description": "撰写专业内部通讯：周报月报、新闻稿、FAQ、通知公告，一键生成规范格式", "source": "推荐", "identifier": "skills-sh/anthropics/skills/internal-comms", "trust_level": "trusted", "tags": ["写作", "商务"]},
        {"name": "网页测试", "description": "用 Playwright 自动测试网站功能，检测无障碍性、页面性能，帮你发现 Bug", "source": "推荐", "identifier": "skills-sh/anthropics/skills/webapp-testing", "trust_level": "trusted", "tags": ["开发", "测试"]},
        {"name": "制作技能", "description": "教你如何自己创建新技能，零基础也能上手，用自然语言描述你需要的功能即可", "source": "推荐", "identifier": "skills-sh/openai/skills/skill-creator", "trust_level": "trusted", "tags": ["入门", "自定义"]},
        {"name": "MCP 对接", "description": "教你创建 MCP 服务器，让 AI 连接外部 API 和工具，打通各种软件和平台", "source": "推荐", "identifier": "skills-sh/anthropics/skills/mcp-builder", "trust_level": "trusted", "tags": ["开发", "集成"]},
        {"name": "网页小组件", "description": "用 React 和 HTML/CSS 快速搭建可交互的网页小组件，做工具页面、数据看板很方便", "source": "推荐", "identifier": "skills-sh/anthropics/skills/web-artifacts-builder", "trust_level": "trusted", "tags": ["开发", "网页"]},
        {"name": "品牌规范", "description": "自动应用品牌配色和字体规范，确保所有设计输出风格统一，企业品牌管理必备", "source": "推荐", "identifier": "skills-sh/anthropics/skills/brand-guidelines", "trust_level": "trusted", "tags": ["设计", "品牌"]},
    ]

@app.post("/api/skills/install")
async def install_skill(request: dict):
    """Install a skill from hub. Body: {"identifier": "...", "name": "..."} """
    identifier = request.get("identifier", "")
    name = request.get("name", "")
    if not identifier and not name:
        raise HTTPException(status_code=400, detail="identifier or name required")
    try:
        from tools.skills_hub import (
            GitHubAuth, create_source_router, ensure_hub_dirs,
            quarantine_bundle, install_from_quarantine,
        )
        from tools.skills_guard import scan_skill, should_allow_install
        auth = GitHubAuth()
        sources = create_source_router(auth)
        ensure_hub_dirs()

        bundle = None

        # Strategy 1: try identifier directly (works for skills-sh/owner/repo/skill format)
        if identifier:
            for src in sources:
                try:
                    bundle = src.fetch(identifier)
                except Exception:
                    pass
                if bundle:
                    break

        # Strategy 2: if identifier is a URL, try as direct URL fetch
        if not bundle and identifier and identifier.startswith("http"):
            from tools.skills_hub import UrlSource
            url_src = UrlSource()
            try:
                bundle = url_src.fetch(identifier)
            except Exception:
                pass

        # Strategy 3: search by name across all sources
        if not bundle and name:
            from tools.skills_hub import unified_search
            results = unified_search(name, sources, limit=5)
            for r in results:
                try:
                    for src in sources:
                        if src.source_id() == r.source:
                            bundle = src.fetch(r.identifier)
                            if bundle:
                                break
                    if bundle:
                        break
                except Exception:
                    pass

        if not bundle:
            return {"ok": False, "error": f"No source found for: {name or identifier}"}

        # Scan and install
        result = scan_skill(bundle)
        if not should_allow_install(result):
            return {"ok": False, "error": f"Security scan blocked: {result.summary}"}

        quarantine_bundle(bundle)
        install_from_quarantine(bundle, force=False)
        return {"ok": True, "name": bundle.meta.name if bundle.meta else (name or identifier)}
    except Exception as e:
        log_msg("WARN", f"Install skill failed: {e}")
        return {"ok": False, "error": str(e)}

@app.delete("/api/skills/{name}")
async def delete_skill(name: str):
    """Uninstall a skill."""
    try:
        from tools.skills_hub import uninstall_skill
        ok, msg = uninstall_skill(name)
        return {"ok": ok, "message": msg}
    except Exception as e:
        log_msg("WARN", f"Uninstall skill failed: {e}")
        return {"ok": False, "error": str(e)}

# ---------------------------------------------------------------------------
# Cron / Scheduled Tasks API (delegates to hermes-agent cron.jobs)
# ---------------------------------------------------------------------------

@app.get("/api/cron/jobs")
async def list_cron_jobs():
    """List all scheduled cron jobs."""
    try:
        from cron.jobs import list_jobs
        jobs = list_jobs(include_disabled=False)
        return jobs
    except Exception as e:
        log_msg("WARN", f"List cron jobs failed: {e}")
        return []

@app.post("/api/cron/jobs/{job_id}/trigger")
async def trigger_cron_job(job_id: str):
    """Trigger a cron job immediately."""
    try:
        from cron.jobs import trigger_job
        job = trigger_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"ok": True, "job": job}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Trigger cron job failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/cron/jobs/{job_id}/pause")
async def pause_cron_job(job_id: str):
    """Pause a cron job."""
    try:
        from cron.jobs import pause_job
        job = pause_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"ok": True, "job": job}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Pause cron job failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/cron/jobs/{job_id}/resume")
async def resume_cron_job(job_id: str):
    """Resume a paused cron job."""
    try:
        from cron.jobs import resume_job
        job = resume_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"ok": True, "job": job}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Resume cron job failed: {e}")
        return {"ok": False, "error": str(e)}

@app.delete("/api/cron/jobs/{job_id}")
async def delete_cron_job(job_id: str):
    """Delete a cron job."""
    try:
        from cron.jobs import remove_job
        ok = remove_job(job_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Job not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Delete cron job failed: {e}")
        return {"ok": False, "error": str(e)}

def register_browser_bubble_fallbacks():
    """Install no-op bubble endpoints for browser/uvicorn development mode."""

    @app.post("/api/bubble/update")
    async def api_bubble_update_fallback(payload: dict):
        return {"ok": True, "visible": False, "mode": "browser"}

    @app.get("/api/bubble/status")
    async def api_bubble_status_fallback():
        return {"visible": False, "text": "", "mode": "browser"}

# --- WebSocket: streaming chat ---

@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # Track connection for auto-shutdown
    global active_connections
    active_connections += 1
    cancel_shutdown()
    log_msg("INFO", f"Client connected (active: {active_connections})")

    # Ensure session exists (but DON'T create agent yet — defer to first message)
    with session_lock:
        if session_id not in sessions:
            sessions[session_id] = _empty_session()

    # Queue for cross-thread streaming
    msg_queue: asyncio.Queue = asyncio.Queue()
    main_loop = asyncio.get_running_loop()

    def emit_event(event: dict):
        """Called from agent thread; schedule push to WS."""
        main_loop.call_soon_threadsafe(
            msg_queue.put_nowait, event,
        )

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()

            if not message:
                await websocket.send_json({"type": "error", "text": "Empty message"})
                continue

            if message == "__ping__":
                await websocket.send_json({"type": "info", "text": "pong"})
                continue

            # Get session and lazily create agent on first message
            with session_lock:
                if session_id not in sessions:
                    sessions[session_id] = _empty_session()
                s = sessions[session_id]
                s["callbacks"] = {"emit": emit_event}
                already_running = bool(s.get("running"))
            if already_running:
                await websocket.send_json({"type": "error", "text": "Session is already running"})
                continue
            if s["agent"] is None:
                try:
                    await websocket.send_json({"type": "status", "text": "Initializing agent..."})
                    log_msg("INFO", f"Creating agent for session {session_id[:12]}...")
                    _ensure_session_record(session_id)
                    s["agent"] = create_agent(session_id)
                    log_msg("INFO", f"Agent created for {session_id[:12]}")
                except Exception as e:
                    log_msg("ERROR", f"Agent creation failed: {e}")
                    await websocket.send_json({"type": "error", "text": f"Failed to initialize agent: {e}"})
                    continue
            session = s

            # Check for session switch
            if message.startswith("/switch "):
                new_sid = message.split(" ", 1)[1].strip()
                await websocket.send_json({"type": "info", "text": "Switched to session " + new_sid})
                session_id = new_sid
                with session_lock:
                    if session_id not in sessions:
                        sessions[session_id] = _empty_session()
                    session = sessions[session_id]
                    if not session["history"]:
                        session["history"] = _load_history_from_db(session_id)
                    session["callbacks"] = {"emit": emit_event}
                continue

            # Add user message to history
            with session_lock:
                if not session.get("history"):
                    session["history"] = _load_history_from_db(session_id)
                conversation_history = list(session.get("history") or [])
                session["history"] = conversation_history + [{"role": "user", "content": message}]
            log_msg("INFO", f"[{session_id[:12]}] User: {message[:60]}")

            # Auto-title on first exchange
            user_count = len([m for m in session["history"] if m.get("role") == "user"])
            if not session.get("title") and user_count == 1:
                title = message[:30] + ("..." if len(message) > 30 else "")
                session["title"] = title

            # Signal frontend that agent is thinking
            await websocket.send_json({"type": "status", "text": "thinking"})

            # Run agent in background thread
            result_holder = {}
            error_holder = {}

            def run_agent():
                try:
                    r = session["agent"].run_conversation(
                        user_message=message,
                        conversation_history=conversation_history,
                        task_id=session_id,
                    )
                    result_holder["result"] = r
                except Exception as e:
                    tb = traceback.format_exc()
                    cause = getattr(e, "__cause__", None)
                    context = getattr(e, "__context__", None)
                    log_msg("ERROR", f"[{session_id[:12]}] Agent exception type={type(e).__name__}: {e}")
                    if cause:
                        log_msg("ERROR", f"[{session_id[:12]}] Agent exception cause={type(cause).__name__}: {cause}")
                    if context:
                        log_msg("ERROR", f"[{session_id[:12]}] Agent exception context={type(context).__name__}: {context}")
                    for line in tb.rstrip().splitlines():
                        log_msg("TRACE", f"[{session_id[:12]}] {line}")
                    error_holder["error"] = str(e)
                finally:
                    main_loop.call_soon_threadsafe(msg_queue.put_nowait, None)

            agent_thread = threading.Thread(target=run_agent, daemon=True)
            with session_lock:
                session["running"] = True
                session["agent_thread"] = agent_thread
            agent_thread.start()

            # Drain queue while agent runs (streaming output)
            while agent_thread.is_alive() or not msg_queue.empty():
                try:
                    msg = await asyncio.wait_for(msg_queue.get(), timeout=0.05)
                    if msg is None:  # Sentinel — agent finished
                        break
                    await websocket.send_json(msg)
                except asyncio.TimeoutError:
                    continue

            agent_thread.join(timeout=30)
            with session_lock:
                session["running"] = False
                session["agent_thread"] = None

            # Process result
            if "result" in result_holder:
                result = result_holder["result"]
                full_messages = result.get("messages", [])
                if full_messages:
                    with session_lock:
                        session["history"] = full_messages

                final_text = result.get("final_response", "")
                log_msg("INFO", f"[{session_id[:12]}] Agent response complete, {len(final_text)} chars")
                if not final_text and full_messages:
                    last = full_messages[-1]
                    if last.get("role") == "assistant":
                        final_text = last.get("content", "")
                if result.get("interrupted"):
                    await websocket.send_json({"type": "info", "text": "Interrupted"})

                await websocket.send_json({
                    "type": "done",
                    "text": final_text or "(no response)",
                    "interrupted": bool(result.get("interrupted")),
                })
                try:
                    if not session_db.get_session_title(session_id):
                        title = _default_title_from_history(full_messages, message[:30])
                        if title:
                            session_db.set_session_title(session_id, title)
                            with session_lock:
                                session["title"] = title
                except Exception:
                    pass
            elif "error" in error_holder:
                # Restore history (remove the failed user message)
                with session_lock:
                    session["history"] = conversation_history
                log_msg("ERROR", f"[{session_id[:12]}] Agent error: {error_holder['error']}")
                await websocket.send_json({
                    "type": "error",
                    "text": f"Agent error: {error_holder['error']}",
                })
            try:
                latest_history = _load_history_from_db(session_id)
                if latest_history:
                    with session_lock:
                        session["history"] = latest_history
                await websocket.send_json({"type": "session.updated", "session_id": session_id})
            except Exception:
                pass

    except WebSocketDisconnect:
        pass  # Client disconnected
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "text": f"Server error: {e}"})
        except Exception:
            pass
    finally:
        with session_lock:
            session = sessions.get(session_id)
            if session and session.get("callbacks", {}).get("emit") is emit_event:
                session["callbacks"] = {}
            if session:
                session["running"] = False
                session["agent_thread"] = None
        active_connections = max(0, active_connections - 1)
        log_msg("INFO", f"Client disconnected (active: {active_connections})")
        if active_connections == 0:
            schedule_shutdown()

# --- Startup ---

if __name__ == "__main__":
    import argparse
    _ap = argparse.ArgumentParser()
    _ap.add_argument("--bubble-only", action="store_true", help="Start with floating bubble only (no main window)")
    _args, _unknown = _ap.parse_known_args()

    try:
        import time as _time
        NATIVE_BUBBLE_ENABLED = True
    except Exception as e:
        log_msg("ERROR", f"Native startup preflight failed: {type(e).__name__}: {e}")
        log_msg("ERROR", traceback.format_exc())
        raise
    host = "127.0.0.1"
    port = 8765
    url = f"http://{host}:{port}"

    BUBBLE_ONLY = _args.bubble_only

    # Start uvicorn in a background daemon thread
    server_config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server_instance = uvicorn.Server(server_config)
    _svr_thread = threading.Thread(target=server_instance.run, daemon=True)
    _svr_thread.start()

    # Wait for server to be ready
    import urllib.request
    for i in range(20):
        _time.sleep(0.3)
        try:
            urllib.request.urlopen(f"{url}/api/config", timeout=2)
            break
        except Exception:
            pass
    log_msg("INFO", f"Server ready on port {port}")

    # --- Win32: set custom icon + floating bubble widget ---
    icon_path = str(STATIC_DIR / "hermes.ico")
    logo_path = str(STATIC_DIR / "hermes_logo.png")

    import ctypes as _ct
    from ctypes import wintypes as _wt
    _kernel32 = _ct.windll.kernel32
    _user32 = _ct.windll.user32
    _gdi32 = _ct.windll.gdi32
    _LRESULT = getattr(_wt, "LRESULT", _wt.LPARAM)
    _HCURSOR = getattr(_wt, "HCURSOR", _wt.HANDLE)

    class _PAINTSTRUCT(_ct.Structure):
        _fields_ = [
            ("hdc", _wt.HDC),
            ("fErase", _wt.BOOL),
            ("rcPaint", _wt.RECT),
            ("fRestore", _wt.BOOL),
            ("fIncUpdate", _wt.BOOL),
            ("rgbReserved", _ct.c_byte * 32),
        ]

    def _configure_win32_signatures():
        """Declare Win32 signatures so 64-bit handles are not truncated.

        ctypes assumes C ``int`` for undeclared parameters.  That breaks on
        64-bit Windows when HWND/HINSTANCE/HMENU values exceed 32 bits, which
        is exactly what the floating bubble hit during CreateWindowExW.
        """
        _kernel32.GetModuleHandleW.argtypes = [_wt.LPCWSTR]
        _kernel32.GetModuleHandleW.restype = _wt.HMODULE
        _kernel32.GetLastError.argtypes = []
        _kernel32.GetLastError.restype = _wt.DWORD

        _user32.RegisterClassW.argtypes = [_ct.c_void_p]
        _user32.RegisterClassW.restype = _wt.ATOM
        _user32.CreateWindowExW.argtypes = [
            _wt.DWORD, _wt.LPCWSTR, _wt.LPCWSTR, _wt.DWORD,
            _ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int,
            _wt.HWND, _wt.HMENU, _wt.HINSTANCE, _wt.LPVOID,
        ]
        _user32.CreateWindowExW.restype = _wt.HWND
        _user32.DefWindowProcW.argtypes = [_wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM]
        _user32.DefWindowProcW.restype = _LRESULT
        _user32.PostMessageW.argtypes = [_wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM]
        _user32.PostMessageW.restype = _wt.BOOL
        _user32.SendMessageW.argtypes = [_wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM]
        _user32.SendMessageW.restype = _LRESULT
        _user32.ShowWindow.argtypes = [_wt.HWND, _ct.c_int]
        _user32.ShowWindow.restype = _wt.BOOL
        _user32.SetForegroundWindow.argtypes = [_wt.HWND]
        _user32.SetForegroundWindow.restype = _wt.BOOL
        _user32.SetWindowPos.argtypes = [
            _wt.HWND, _wt.HWND,
            _ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int,
            _wt.UINT,
        ]
        _user32.SetWindowPos.restype = _wt.BOOL
        _user32.SetLayeredWindowAttributes.argtypes = [
            _wt.HWND, _wt.COLORREF, _wt.BYTE, _wt.DWORD,
        ]
        _user32.SetLayeredWindowAttributes.restype = _wt.BOOL
        _user32.UpdateLayeredWindow.argtypes = [
            _wt.HWND, _wt.HDC, _ct.POINTER(_wt.POINT), _ct.POINTER(_wt.SIZE),
            _wt.HDC, _ct.POINTER(_wt.POINT), _wt.COLORREF,
            _ct.c_void_p, _wt.DWORD,
        ]
        _user32.UpdateLayeredWindow.restype = _wt.BOOL
        _user32.SetWindowRgn.argtypes = [_wt.HWND, _wt.HRGN, _wt.BOOL]
        _user32.SetWindowRgn.restype = _ct.c_int
        _user32.InvalidateRect.argtypes = [_wt.HWND, _ct.POINTER(_wt.RECT), _wt.BOOL]
        _user32.InvalidateRect.restype = _wt.BOOL
        _user32.UpdateWindow.argtypes = [_wt.HWND]
        _user32.UpdateWindow.restype = _wt.BOOL
        _user32.BeginPaint.argtypes = [_wt.HWND, _ct.POINTER(_PAINTSTRUCT)]
        _user32.BeginPaint.restype = _wt.HDC
        _user32.EndPaint.argtypes = [_wt.HWND, _ct.POINTER(_PAINTSTRUCT)]
        _user32.EndPaint.restype = _wt.BOOL
        _user32.GetClientRect.argtypes = [_wt.HWND, _ct.POINTER(_wt.RECT)]
        _user32.GetClientRect.restype = _wt.BOOL
        _user32.FillRect.argtypes = [_wt.HDC, _ct.POINTER(_wt.RECT), _wt.HBRUSH]
        _user32.FillRect.restype = _ct.c_int
        _user32.FindWindowW.argtypes = [_wt.LPCWSTR, _wt.LPCWSTR]
        _user32.FindWindowW.restype = _wt.HWND
        _user32.LoadCursorW.argtypes = [_wt.HINSTANCE, _ct.c_void_p]
        _user32.LoadCursorW.restype = _HCURSOR
        _user32.LoadImageW.argtypes = [
            _wt.HINSTANCE, _wt.LPCWSTR, _wt.UINT,
            _ct.c_int, _ct.c_int, _wt.UINT,
        ]
        _user32.LoadImageW.restype = _wt.HANDLE
        _user32.GetMessageW.argtypes = [_ct.POINTER(_wt.MSG), _wt.HWND, _wt.UINT, _wt.UINT]
        _user32.GetMessageW.restype = _wt.BOOL
        _user32.TranslateMessage.argtypes = [_ct.POINTER(_wt.MSG)]
        _user32.TranslateMessage.restype = _wt.BOOL
        _user32.DispatchMessageW.argtypes = [_ct.POINTER(_wt.MSG)]
        _user32.DispatchMessageW.restype = _LRESULT
        _user32.PostQuitMessage.argtypes = [_ct.c_int]
        _user32.PostQuitMessage.restype = None
        _user32.SetWindowTextW.argtypes = [_wt.HWND, _wt.LPCWSTR]
        _user32.SetWindowTextW.restype = _wt.BOOL

        _gdi32.CreateEllipticRgn.argtypes = [_ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int]
        _gdi32.CreateEllipticRgn.restype = _wt.HRGN
        _gdi32.Ellipse.argtypes = [_wt.HDC, _ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int]
        _gdi32.Ellipse.restype = _wt.BOOL
        _gdi32.CreateCompatibleDC.argtypes = [_wt.HDC]
        _gdi32.CreateCompatibleDC.restype = _wt.HDC
        _gdi32.CreateCompatibleBitmap.argtypes = [_wt.HDC, _ct.c_int, _ct.c_int]
        _gdi32.CreateCompatibleBitmap.restype = _wt.HBITMAP
        _gdi32.SelectObject.argtypes = [_wt.HDC, _wt.HGDIOBJ]
        _gdi32.SelectObject.restype = _wt.HGDIOBJ
        _gdi32.CreateSolidBrush.argtypes = [_wt.COLORREF]
        _gdi32.CreateSolidBrush.restype = _wt.HBRUSH
        _gdi32.DeleteObject.argtypes = [_wt.HGDIOBJ]
        _gdi32.DeleteObject.restype = _wt.BOOL
        _gdi32.DeleteDC.argtypes = [_wt.HDC]
        _gdi32.DeleteDC.restype = _wt.BOOL
        _gdi32.BitBlt.argtypes = [
            _wt.HDC, _ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int,
            _wt.HDC, _ct.c_int, _ct.c_int, _wt.DWORD,
        ]
        _gdi32.BitBlt.restype = _wt.BOOL
        _gdi32.StretchBlt.argtypes = [
            _wt.HDC, _ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int,
            _wt.HDC, _ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int,
            _wt.DWORD,
        ]
        _gdi32.StretchBlt.restype = _wt.BOOL
        _gdi32.GetObjectW.argtypes = [_wt.HANDLE, _ct.c_int, _ct.c_void_p]
        _gdi32.GetObjectW.restype = _ct.c_int

    _configure_win32_signatures()

    # WNDCLASSW is not in wintypes, define it manually
    class WNDCLASSW(_ct.Structure):
        _fields_ = [
            ("style", _ct.c_uint),
            ("lpfnWndProc", _ct.c_void_p),
            ("cbClsExtra", _ct.c_int),
            ("cbWndExtra", _ct.c_int),
            ("hInstance", _wt.HINSTANCE),
            ("hIcon", _wt.HICON),
            ("hCursor", _wt.HANDLE),
            ("hbrBackground", _wt.HBRUSH),
            ("lpszMenuName", _wt.LPCWSTR),
            ("lpszClassName", _wt.LPCWSTR),
        ]

    WM_SETICON = 0x80
    GCL_HICON = -14
    GCL_HICONSM = -34

    # --- Floating Bubble Widget ---
    WS_POPUP = 0x80000000
    WS_VISIBLE = 0x10000000
    WS_EX_LAYERED = 0x00080000
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_TOPMOST = 0x00000008
    CW_USEDEFAULT = -2147483648
    GWL_EXSTYLE = -20
    LWA_ALPHA = 0x02
    LWA_COLORKEY = 0x01
    WM_CLOSE = 0x0010

    WM_NCHITTEST = 0x84
    WM_NCLBUTTONDBLCLK = 0x00A3
    HTCAPTION = 2
    WM_LBUTTONDBLCLK = 0x203
    WM_RBUTTONDOWN = 0x204
    WM_PAINT = 0x000F
    WM_DESTROY = 0x0002

    # GDI objects
    TRANSPARENT = 1
    SRCCOPY = 0x00CC0020
    RGB_FORMAT = lambda r, g, b: (r) | (g << 8) | (b << 16)
    COLOR_KEY = RGB_FORMAT(255, 0, 255)  # magenta as transparent

    BUBBLE_SIZE = 80

    # Shared state for the floating bubble
    _bubble_state = {
        "hwnd": None,
        "visible": False,
        "text": "",
        "main_hwnd": None,
        "ready_event": threading.Event(),
        "logo_hbitmap": None,  # HBITMAP of the bubble icon
    }

    def _load_bubble_png(png_path):
        """Convert PNG to BMP with magenta background, then load as HBITMAP via LoadImageW."""
        try:
            from PIL import Image as _PILImage
            import io as _io

            if not os.path.exists(png_path):
                return False

            # Open PNG, resize with high-quality scaling
            pil_img = _PILImage.open(png_path).convert("RGBA")
            pil_img = pil_img.resize((BUBBLE_SIZE, BUBBLE_SIZE), _PILImage.LANCZOS)

            # Create a magenta background image
            bg = _PILImage.new("RGBA", pil_img.size, (255, 0, 255, 255))
            # Composite PNG onto magenta background
            composite = _PILImage.alpha_composite(bg, pil_img)

            # Save as BMP to memory
            bmp_bytes = _io.BytesIO()
            composite.save(bmp_bytes, format="BMP")
            bmp_data = bmp_bytes.getvalue()

            # Write BMP to temp file for LoadImageW
            temp_bmp = str(STATIC_DIR / "_bubble_temp.bmp")
            with open(temp_bmp, "wb") as f:
                f.write(bmp_data)

            # Load BMP via Win32 LoadImageW
            IMAGE_BITMAP = 0
            LR_LOADFROMFILE = 0x0010
            hbitmap = _user32.LoadImageW(None, temp_bmp, IMAGE_BITMAP, 0, 0, LR_LOADFROMFILE)
            if hbitmap:
                _bubble_state["logo_hbitmap"] = hbitmap
                return True
            return False
        except Exception:
            return False

    def _draw_bubble(hwnd):
        """Paint the circular floating bubble - icon + status text."""
        ps = _PAINTSTRUCT()
        hdc = _user32.BeginPaint(hwnd, _ct.byref(ps))
        if not hdc:
            return

        rect = _wt.RECT()
        _user32.GetClientRect(hwnd, _ct.byref(rect))
        w, h = rect.right, rect.bottom

        # Create memory DC for double buffering
        mem_dc = _gdi32.CreateCompatibleDC(hdc)
        bmp = _gdi32.CreateCompatibleBitmap(hdc, w, h)
        old_bmp = _gdi32.SelectObject(mem_dc, bmp)

        # Fill with transparent color key (magenta)
        magenta_brush = _gdi32.CreateSolidBrush(COLOR_KEY)
        _user32.FillRect(mem_dc, _ct.byref(rect), magenta_brush)
        _gdi32.DeleteObject(magenta_brush)

        cx, cy = w // 2, h // 2

        # Draw icon HBITMAP (if loaded)
        logo_bmp = _bubble_state.get("logo_hbitmap")
        if logo_bmp:
            # BMP is already BUBBLE_SIZE x BUBBLE_SIZE, just copy 1:1
            logo_dc = _gdi32.CreateCompatibleDC(mem_dc)
            old_logo = _gdi32.SelectObject(logo_dc, logo_bmp)
            _gdi32.BitBlt(mem_dc, 0, 0, w, h, logo_dc, 0, 0, SRCCOPY)
            _gdi32.SelectObject(logo_dc, old_logo)
            _gdi32.DeleteDC(logo_dc)
        else:
            # Fallback: "H" letter
            _gdi32.SetBkMode(mem_dc, TRANSPARENT)
            _gdi32.SetTextAlign(mem_dc, 1)
            font = _gdi32.CreateFontW(-32, 0, 0, 0, 700, False, False, False,
                                       0x86, 0, 0, 0, 0, "Segoe UI")
            old_font = _gdi32.SelectObject(mem_dc, font)
            _gdi32.SetTextColor(mem_dc, RGB_FORMAT(255, 255, 255))
            _user32.TextOutW(mem_dc, cx, cy - 10, "H", 1)
            _gdi32.SelectObject(mem_dc, old_font)
            _gdi32.DeleteObject(font)

        # Draw status text at bottom (on top of icon)
        text = _bubble_state.get("text", "")
        if text:
            _gdi32.SetBkMode(mem_dc, TRANSPARENT)
            _gdi32.SetTextAlign(mem_dc, 1)
            font = _gdi32.CreateFontW(-11, 0, 0, 0, 400, False, False, False,
                                       0x86, 0, 0, 0, 0, "Microsoft YaHei UI")
            old_font = _gdi32.SelectObject(mem_dc, font)
            _gdi32.SetTextColor(mem_dc, RGB_FORMAT(255, 255, 240))
            display_text = text[:8] + ("..." if len(text) > 8 else "")
            _user32.TextOutW(mem_dc, cx, h - 10, display_text, len(display_text))
            _gdi32.SelectObject(mem_dc, old_font)
            _gdi32.DeleteObject(font)

        # Blit to screen
        _gdi32.BitBlt(hdc, 0, 0, w, h, mem_dc, 0, 0, SRCCOPY)

        # Cleanup
        _gdi32.SelectObject(mem_dc, old_bmp)
        _gdi32.DeleteObject(bmp)
        _gdi32.DeleteDC(mem_dc)
        _user32.EndPaint(hwnd, _ct.byref(ps))


    # WndProc for bubble window
    _BubbleWndProcType = _ct.WINFUNCTYPE(
        _LRESULT, _wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM,
    )

    def _make_bubble_wndproc():
        """Create a proper WndProc that captures itself for subclassing."""

        @_BubbleWndProcType
        def bubble_wndproc(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_NCHITTEST:
                    return HTCAPTION  # allow dragging anywhere
                elif msg == WM_PAINT:
                    _draw_bubble(hwnd)
                    return 0
                elif msg == WM_LBUTTONDBLCLK:
                    # Double-click to restore main window
                    _restore_from_bubble()
                    return 0
                elif msg == WM_NCLBUTTONDBLCLK:
                    # HTCAPTION makes Windows send non-client double-click too
                    _restore_from_bubble()
                    return 0
                elif msg == WM_RBUTTONDOWN:
                    # Right-click menu
                    x = lparam & 0xFFFF
                    y = (lparam >> 16) & 0xFFFF
                    _show_context_menu(x, y)
                    return 0
                elif msg == WM_DESTROY:
                    if _bubble_state.get("logo_hbitmap"):
                        _gdi32.DeleteObject(_bubble_state["logo_hbitmap"])
                        _bubble_state["logo_hbitmap"] = None
                    _user32.PostQuitMessage(0)
                    return 0
                else:
                    return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)
            except Exception:
                return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        return bubble_wndproc

    _bubble_wndproc_fn = _make_bubble_wndproc()

    def _show_context_menu(x, y):
        """Show right-click context menu for bubble."""
        hmenu = _user32.CreatePopupMenu()
        _user32.AppendMenuW(hmenu, 0, 1001, "\u6062\u590d\u7a97\u53e3")     # Restore Window
        _user32.AppendMenuW(hmenu, 0x800, 0, "")                            # Separator
        _user32.AppendMenuW(hmenu, 0, 1002, "\u9000\u51fa\u7a0b\u5e8f")     # Exit Program

        ret = _user32.TrackPopupMenu(hmenu, 0x108, x, y, 0, _bubble_state["hwnd"], None)
        # 0x108 = TPM_RETURNCMD | TPM_RIGHTBUTTON

        if ret == 1001:
            _restore_from_bubble()
        elif ret == 1002:
            _user32.PostMessageW(_bubble_state["hwnd"], WM_CLOSE, 0, 0)
            if _bubble_state.get("main_hwnd"):
                _user32.PostMessageW(_bubble_state["main_hwnd"], 0x0010, 0, 0)

        _user32.DestroyMenu(hmenu)

    def _restore_from_bubble():
        """Hide bubble and show main window, or launch it if not running."""
        mhwnd = _bubble_state.get("main_hwnd")
        if mhwnd and _user32.IsWindow(mhwnd):
            _user32.ShowWindow(mhwnd, 5)   # SW_SHOW - restores window and taskbar icon
            _user32.SetForegroundWindow(mhwnd)
            # Hide the bubble
            bwnd = _bubble_state.get("hwnd")
            if bwnd:
                _user32.ShowWindow(bwnd, 0)  # SW_HIDE
                _bubble_state["visible"] = False
        elif BUBBLE_ONLY:
            # No main window yet (bubble-only startup): launch the main window
            import subprocess
            _script = os.path.abspath(__file__)
            _cwd = str(HERMES_HOME / "desktop-client")
            subprocess.Popen(
                [sys.executable, _script],
                cwd=_cwd,
                creationflags=0x00000008 if sys.platform == "win32" else 0
            )
            # Destroy this bubble-only process's bubble so the keep-alive loop exits
            bwnd = _bubble_state.get("hwnd")
            if bwnd:
                _user32.DestroyWindow(bwnd)
                _bubble_state["hwnd"] = None

    def _create_floating_bubble():
        """Create the floating bubble widget window and run its message pump."""
        try:
            # Use a unique class name to avoid conflicts with stale registrations
            import random
            wcname = f"HermesFloatBubble{random.randint(1000, 9999)}"

            # Register window class
            wndcls = WNDCLASSW()
            wndcls.lpfnWndProc = _ct.cast(_bubble_wndproc_fn, _ct.c_void_p)
            wndcls.hInstance = _kernel32.GetModuleHandleW(None)
            wndcls.lpszClassName = wcname
            wndcls.hbrBackground = _gdi32.GetStockObject(5)  # HOLLOW_BRUSH
            wndcls.hCursor = _user32.LoadCursorW(None, 32649)  # IDC_HAND

            reg_ok = _user32.RegisterClassW(_ct.byref(wndcls))
            reg_err = _kernel32.GetLastError()

            if not reg_ok and reg_err != 1410:  # Class already registered
                log_msg("ERROR", f"Failed to register bubble class: {reg_err}")
                return

            # Get screen size for initial position (bottom-right area)
            screen_w = _user32.GetSystemMetrics(0)
            screen_h = _user32.GetSystemMetrics(1)

            hwnd = _user32.CreateWindowExW(
                WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
                wcname,
                "Hermes",
                WS_POPUP,
                screen_w - BUBBLE_SIZE - 40,
                screen_h - BUBBLE_SIZE - 60,
                BUBBLE_SIZE,
                BUBBLE_SIZE,
                None, None, wndcls.hInstance, None
            )

            if not hwnd:
                log_msg("ERROR", "Could not create floating bubble")
                return

            _bubble_state["hwnd"] = hwnd
            _bubble_state["ready_event"].set()

            # Make it circular (clip region)
            rgn = _gdi32.CreateEllipticRgn(0, 0, BUBBLE_SIZE + 1, BUBBLE_SIZE + 1)
            _user32.SetWindowRgn(hwnd, rgn, True)

            # Set layered window alpha/color key
            _user32.SetLayeredWindowAttributes(hwnd, COLOR_KEY, 255, LWA_ALPHA | LWA_COLORKEY)

            # Load PNG icon
            bubble_png_path = str(STATIC_DIR / "bubble_icon.png")
            _load_bubble_png(bubble_png_path)

            log_msg("INFO", f"Floating bubble created (hwnd={hwnd})")

        except Exception as e:
            log_msg("ERROR", f"Bubble create exception: {e}")
            _bubble_state["ready_event"].set()
            return

        msg = _wt.MSG()
        while _user32.GetMessageW(_ct.byref(msg), None, 0, 0):
            _user32.TranslateMessage(_ct.byref(msg))
            _user32.DispatchMessageW(_ct.byref(msg))

    # API endpoint to update bubble text/status
    from pydantic import BaseModel as _BaseModel
    class _BubbleUpdate(_BaseModel):
        action: str = ""
        text: str = ""
    @app.post("/api/bubble/update")
    async def api_bubble_update(req: _BubbleUpdate):
        new_text = req.text
        action = req.action  # show, hide, restore, update

        if action == "show" or action == "":
            log_msg("INFO", f"Bubble show: visible={_bubble_state.get('visible')} hwnd={_bubble_state.get('hwnd')}")
            if _bubble_state.get("hwnd"):
                bwnd = _bubble_state["hwnd"]
                screen_w = _user32.GetSystemMetrics(0)
                screen_h = _user32.GetSystemMetrics(1)
                # Re-apply round region and layered attributes
                rgn = _gdi32.CreateEllipticRgn(0, 0, BUBBLE_SIZE + 1, BUBBLE_SIZE + 1)
                _user32.SetWindowRgn(bwnd, rgn, True)
                _user32.SetLayeredWindowAttributes(bwnd, COLOR_KEY, 255, LWA_ALPHA | LWA_COLORKEY)
                _user32.ShowWindow(bwnd, 5)  # SW_SHOW
                _user32.SetWindowPos(
                    bwnd, -1,  # HWND_TOPMOST
                    screen_w - BUBBLE_SIZE - 40, screen_h - BUBBLE_SIZE - 60,
                    BUBBLE_SIZE, BUBBLE_SIZE,
                    0x0040 | 0x0010  # SWP_SHOWWINDOW | SWP_NOACTIVATE
                )
                _user32.InvalidateRect(bwnd, None, True)
                _user32.UpdateWindow(bwnd)
                _bubble_state["visible"] = True
            else:
                log_msg("WARN", "Bubble hwnd is None, cannot show")
            # Hide main window (and its taskbar icon) when bubble is shown
            if _bubble_state.get("main_hwnd"):
                mhwnd = _bubble_state["main_hwnd"]
                _user32.ShowWindow(mhwnd, 0)  # SW_HIDE - hides window AND removes taskbar icon

        if action == "hide":
            if _bubble_state.get("visible") and _bubble_state.get("hwnd"):
                _user32.ShowWindow(_bubble_state["hwnd"], 0)
                _bubble_state["visible"] = False

        if action == "restore":
            _restore_from_bubble()
            if _bubble_state.get("visible"):
                _user32.ShowWindow(_bubble_state["hwnd"], 0)
                _bubble_state["visible"] = False

        if new_text:
            _bubble_state["text"] = new_text
            if _bubble_state.get("hwnd"):
                _user32.InvalidateRect(_bubble_state["hwnd"], None, True)

        return {"ok": True}

    @app.get("/api/bubble/status")
    async def api_bubble_status():
        return {"visible": _bubble_state.get("visible", False), "text": _bubble_state.get("text", "")}


    def _win_thread():
        """Set icons after window is ready + create bubble widget."""
        hicon_small = _user32.LoadImageW(None, icon_path, 1, 48, 48, 0x10)
        hicon_big = _user32.LoadImageW(None, icon_path, 1, 256, 256, 0x10)

        if BUBBLE_ONLY:
            # Bubble-only mode: no main window, just create the floating bubble
            log_msg("INFO", "Bubble-only mode: creating floating bubble...")
            try:
                bubble_thread = threading.Thread(target=_create_floating_bubble, daemon=True)
                bubble_thread.start()
                _bubble_state["ready_event"].wait(timeout=3.0)
                log_msg("INFO", f"Bubble init done: hwnd={_bubble_state.get('hwnd')}")
            except Exception as e:
                log_msg("ERROR", f"Failed to create floating bubble: {e}")
            return

        main_hwnd_val = None

        for i in range(50):
            _time.sleep(0.2)
            hwnd = _user32.FindWindowW(None, "Hermes Desktop")
            if not hwnd:
                continue

            main_hwnd_val = hwnd
            _bubble_state["main_hwnd"] = hwnd

            if hicon_small:
                _user32.SendMessageW(hwnd, WM_SETICON, 0, hicon_small)
                _user32.SetClassLongW(hwnd, GCL_HICONSM, hicon_small)
            if hicon_big:
                _user32.SendMessageW(hwnd, WM_SETICON, 1, hicon_big)
                _user32.SetClassLongW(hwnd, GCL_HICON, hicon_big)

            log_msg("INFO", "Icons set & bubble initialized")
            break
        else:
            log_msg("WARN", "Could not find Hermes Desktop window")

        # Create the floating bubble on its own UI thread. Win32 windows need
        # their message pump on the same thread that created the HWND.
        if main_hwnd_val:
            _time.sleep(0.5)
            try:
                bubble_thread = threading.Thread(target=_create_floating_bubble, daemon=True)
                bubble_thread.start()
                _bubble_state["ready_event"].wait(timeout=3.0)
                log_msg("INFO", f"Bubble init done: hwnd={_bubble_state.get('hwnd')}")
            except Exception as e:
                log_msg("ERROR", f"Failed to create floating bubble: {e}")

    threading.Thread(target=_win_thread, daemon=True).start()

    if BUBBLE_ONLY:
        # Bubble-only mode: keep process alive as long as the bubble exists
        log_msg("INFO", "Bubble-only mode active. Double-click bubble to open main window.")
        while _bubble_state.get("hwnd") and _user32.IsWindow(_bubble_state["hwnd"]):
            _time.sleep(1)
        log_msg("INFO", "Bubble closed, exiting...")
        os._exit(0)
    else:
        # Normal mode: open pywebview window
        import webview
        log_msg("INFO", "Opening native desktop window...")

        window_args = {
            "title": "Hermes Desktop",
            "url": url,
            "width": 1100,
            "height": 750,
            "min_size": (700, 500),
            "resizable": True,
            "background_color": "#faf3e8",
        }
        try:
            window = webview.create_window(**window_args, icon=icon_path)
        except TypeError:
            window = webview.create_window(**window_args)

        webview.start()
        log_msg("INFO", "Window closed, exiting...")
        os._exit(0)
