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
import re
import zipfile
from io import BytesIO
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# --- Path setup: import AIAgent from hermes-agent ---
HERMES_HOME = Path(__file__).resolve().parent.parent
SKILLS_DIR = HERMES_HOME / "skills"
HERMES_AGENT = HERMES_HOME / "hermes-agent"
HERMES_VENV_SITE = HERMES_HOME / "venv" / "Lib" / "site-packages"
os.environ["HERMES_HOME"] = str(HERMES_HOME)
if HERMES_VENV_SITE.exists():
    sys.path.insert(0, str(HERMES_VENV_SITE))
sys.path.insert(0, str(HERMES_AGENT))

def _prepend_process_path(*paths: Path) -> None:
    existing = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    normalized = {os.path.normcase(os.path.abspath(p)) for p in existing}
    additions: list[str] = []
    for path in paths:
        try:
            if not path.exists():
                continue
            value = str(path)
            key = os.path.normcase(os.path.abspath(value))
            if key not in normalized:
                additions.append(value)
                normalized.add(key)
        except Exception:
            continue
    if additions:
        os.environ["PATH"] = os.pathsep.join(additions + existing)

_prepend_process_path(
    HERMES_HOME / "tools" / "bin",
    HERMES_HOME / "venv" / "Scripts",
    HERMES_AGENT / "venv" / "Scripts",
    Path.home() / ".local" / "bin",
)

try:
    import hermes_bootstrap  # noqa: F401
except ModuleNotFoundError:
    pass

from run_agent import AIAgent
from hermes_constants import parse_reasoning_effort
from hermes_state import SessionDB
from utils import is_truthy_value, normalize_proxy_env_vars

# --- FastAPI ---
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
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

DESKTOP_HOST_VALUES = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}
SESSION_ID_RE = re.compile(r"^(?:\d{8}_\d{6}_[a-f0-9]{6,8}|emp-[a-f0-9]{8})$")
bubble_notify_callback = None
bubble_pending_lock = threading.Lock()
bubble_pending_target = {"session_id": "", "employee_id": ""}


def _set_bubble_pending_session(session_id: str, employee_id: str = ""):
    global bubble_pending_target
    sid = str(session_id or "").strip()
    eid = str(employee_id or "").strip()
    if not sid and not eid:
        return
    with bubble_pending_lock:
        bubble_pending_target = {"session_id": sid, "employee_id": eid}


def _emit_bubble_notification(payload: dict) -> bool:
    cb = bubble_notify_callback
    if not cb:
        return False
    try:
        cb(dict(payload or {}))
        return True
    except Exception as e:
        log_msg("WARN", f"Bubble notification failed: {e}")
        return False


def _host_without_port(value: str) -> str:
    h = (value or "").strip()
    if h.startswith("["):
        close = h.find("]")
        return h[1:close].lower() if close >= 0 else h.strip("[]").lower()
    return (h.rsplit(":", 1)[0] if ":" in h else h).lower()


def _is_desktop_host(value: str) -> bool:
    """Check if host is a local/desktop address."""
    host = _host_without_port(value)
    if host in DESKTOP_HOST_VALUES:
        return True
    # Also allow any 127.x.x.x loopback addresses
    if host.startswith("127."):
        return True
    return False


def _origin_is_allowed(value: str) -> bool:
    """Allow if origin is missing or from localhost. Blocks external origins."""
    if not value:
        return True
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    return _is_desktop_host(parsed.netloc)


@app.middleware("http")
async def desktop_boundary_middleware(request: Request, call_next):
    host = request.headers.get("host", "")
    origin = request.headers.get("origin", "")
    # Only block if BOTH host AND origin are clearly external
    if host and not _is_desktop_host(host) and origin and not _origin_is_allowed(origin):
        log_msg("WARN", f"Blocked external request: Host={host} Origin={origin}")
        return JSONResponse({"detail": "External access not allowed"}, status_code=403)
    return await call_next(request)


def _ws_request_is_allowed(websocket: WebSocket) -> bool:
    host = websocket.headers.get("host", "")
    origin = websocket.headers.get("origin", "")
    # Block only if clearly external
    if host and not _is_desktop_host(host) and origin and not _origin_is_allowed(origin):
        log_msg("WARN", f"Blocked external WS: Host={host} Origin={origin}")
        return False
    return True

# --- In-memory server log ---
server_logs = []
MAX_LOG_LINES = 500
DISPLAY_HISTORY_LIMIT = int(os.environ.get("HERMES_DESKTOP_DISPLAY_HISTORY_LIMIT", "80"))
AGENT_REPLAY_HISTORY_LIMIT = int(os.environ.get("HERMES_DESKTOP_AGENT_HISTORY_LIMIT", "80"))
MAX_PERSISTED_SESSION_MESSAGES = int(os.environ.get("HERMES_DESKTOP_MAX_PERSISTED_MESSAGES", "400"))
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

# --- Employee system ---
EMPLOYEES_DIR = HERMES_HOME / "employees"
MAX_EMPLOYEES = 5

def _employees_index_path() -> Path:
    return EMPLOYEES_DIR / "index.json"

def _load_employees_index() -> dict:
    p = _employees_index_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"employees": []}

def _save_employees_index(data: dict):
    p = _employees_index_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _employee_dir(emp_id: str) -> Path:
    return EMPLOYEES_DIR / emp_id

def _employee_profile_path(emp_id: str) -> Path:
    return _employee_dir(emp_id) / "profile.md"

def _now_iso() -> str:
    return datetime.now().isoformat()

def _new_workflow_id() -> str:
    return "wf-" + uuid.uuid4().hex[:8]

def _normalize_workflow(workflow: dict, *, fallback_name: str = "") -> dict:
    now = _now_iso()
    wf = dict(workflow or {})
    wf["id"] = (wf.get("id") or _new_workflow_id()).strip()
    wf["name"] = (wf.get("name") or fallback_name or "\u5e38\u7528\u4efb\u52a1").strip()
    wf["description"] = (wf.get("description") or "").strip()
    wf["steps"] = (wf.get("steps") or "").strip()
    wf["questions"] = (wf.get("questions") or "").strip()
    wf["default_inputs"] = wf.get("default_inputs") if isinstance(wf.get("default_inputs"), dict) else {}
    wf["enabled"] = bool(wf.get("enabled", True))
    wf["is_default"] = bool(wf.get("is_default", False))
    wf["created_at"] = wf.get("created_at") or now
    wf["updated_at"] = wf.get("updated_at") or now
    return wf

def _default_workflow_from_employee(emp: dict) -> dict:
    role = (emp.get("role") or "").strip()
    work_content = (emp.get("work_content") or "").strip()
    work_steps = (emp.get("work_steps") or emp.get("steps") or "").strip()
    description = work_content or role or "\u9002\u5408\u8fd9\u4f4d\u5458\u5de5\u7684\u65e5\u5e38\u5de5\u4f5c\u3002"
    questions = (
        "\u5f00\u59cb\u524d\u5148\u95ee\u6e05\u695a\u76ee\u6807\u3001\u7d20\u6750\u3001\u98ce\u683c/\u6807\u51c6\u3001"
        "\u8f93\u51fa\u5f62\u5f0f\u548c\u662f\u5426\u9700\u8981\u7528\u6237\u4e2d\u9014\u786e\u8ba4\u3002"
    )
    return _normalize_workflow({
        "id": "wf-default",
        "name": "\u65e5\u5e38\u5de5\u4f5c",
        "description": description,
        "steps": work_steps,
        "questions": questions,
        "enabled": True,
        "is_default": True,
    })

def _preset_workflows_for_employee(emp: dict) -> list[dict]:
    role_text = " ".join([
        emp.get("name", ""),
        emp.get("role", ""),
        emp.get("work_content", ""),
        emp.get("goal", ""),
    ]).lower()
    presets = [_default_workflow_from_employee(emp)]
    if any(word in role_text for word in ["\u8bbe\u8ba1", "\u4f5c\u56fe", "\u56fe\u7247", "\u6d77\u62a5", "design", "image", "poster"]):
        presets.extend([
            _normalize_workflow({
                "id": "wf-poster",
                "name": "\u5236\u4f5c\u6d77\u62a5/\u5c01\u9762",
                "description": "\u9700\u8981\u8f93\u51fa\u6d77\u62a5\u3001\u5c01\u9762\u3001\u5ba3\u4f20\u56fe\u6216\u793e\u5a92\u4f53\u914d\u56fe\u65f6\u4f7f\u7528\u3002",
                "questions": "\u5f00\u5de5\u524d\u95ee\u6e05\u695a\u5e73\u53f0\u3001\u5c3a\u5bf8\u3001\u4e3b\u9898\u3001\u6587\u6848\u3001\u98ce\u683c\u3001\u7d20\u6750\u548c\u8f93\u51fa\u7248\u672c\u6570\u3002",
                "steps": "1. \u7406\u89e3\u7528\u9014\u548c\u53d7\u4f17\n2. \u8865\u9f50\u5173\u952e\u6587\u6848\u548c\u7d20\u6750\n3. \u5982\u9700\u5148\u627e\u53c2\u8003\u56fe\n4. \u751f\u6210 2-3 \u4e2a\u8bbe\u8ba1\u65b9\u5411\n5. \u7ed9\u51fa\u786e\u8ba4\u70b9\n6. \u786e\u8ba4\u540e\u8f93\u51fa\u6210\u54c1\n7. \u603b\u7ed3\u7528\u6237\u559c\u6b22\u7684\u98ce\u683c",
            }),
            _normalize_workflow({
                "id": "wf-image-edit",
                "name": "\u5904\u7406\u56fe\u7247",
                "description": "\u9700\u8981\u4fee\u56fe\u3001\u6539\u5c3a\u5bf8\u3001\u53bb\u80cc\u666f\u3001\u589e\u5f3a\u753b\u8d28\u6216\u6279\u91cf\u5904\u7406\u65f6\u4f7f\u7528\u3002",
                "questions": "\u5f00\u5de5\u524d\u95ee\u6e05\u695a\u8981\u5904\u7406\u54ea\u4e9b\u56fe\u3001\u60f3\u6539\u6210\u4ec0\u4e48\u6548\u679c\u3001\u8f93\u51fa\u683c\u5f0f\u548c\u662f\u5426\u9700\u8981\u4fdd\u7559\u539f\u56fe\u3002",
                "steps": "1. \u68c0\u67e5\u8f93\u5165\u56fe\u7247\n2. \u786e\u8ba4\u5904\u7406\u76ee\u6807\n3. \u5148\u7ed9\u51fa\u5904\u7406\u8ba1\u5212\n4. \u7528\u6237\u786e\u8ba4\u540e\u6267\u884c\n5. \u8f93\u51fa\u5904\u7406\u540e\u6587\u4ef6\n6. \u8bb0\u5f55\u672c\u6b21\u504f\u597d\u548c\u53c2\u6570",
            }),
            _normalize_workflow({
                "id": "wf-reference-search",
                "name": "\u627e\u8bbe\u8ba1\u53c2\u8003",
                "description": "\u9700\u8981\u8054\u7f51\u627e\u7075\u611f\u3001\u7ade\u54c1\u89c6\u89c9\u3001\u56fe\u7247\u7d20\u6750\u6216\u98ce\u683c\u53c2\u8003\u65f6\u4f7f\u7528\u3002",
                "questions": "\u5f00\u5de5\u524d\u95ee\u6e05\u695a\u884c\u4e1a\u3001\u98ce\u683c\u3001\u5e73\u53f0\u3001\u53c2\u8003\u6570\u91cf\u548c\u662f\u5426\u9700\u8981\u4e0b\u8f7d\u7d20\u6750\u3002",
                "steps": "1. \u660e\u786e\u641c\u7d22\u65b9\u5411\n2. \u641c\u7d22\u5e76\u7b5b\u9009\u53c2\u8003\n3. \u6574\u7406\u6765\u6e90\u548c\u98ce\u683c\u7279\u5f81\n4. \u603b\u7ed3\u53ef\u501f\u9274\u7684\u8bbe\u8ba1\u70b9\n5. \u628a\u6709\u4ef7\u503c\u7684\u53c2\u8003\u5199\u5165\u77e5\u8bc6/\u7ecf\u9a8c",
            }),
        ])
    elif any(word in role_text for word in ["\u7814\u7a76", "\u8d44\u6599", "\u5206\u6790", "\u8c03\u7814", "research", "analysis"]):
        presets.extend([
            _normalize_workflow({
                "id": "wf-web-research",
                "name": "\u7f51\u9875\u8c03\u7814",
                "description": "\u9700\u8981\u8054\u7f51\u641c\u96c6\u8d44\u6599\u3001\u6bd4\u8f83\u4fe1\u606f\u3001\u5199\u8c03\u7814\u7ed3\u8bba\u65f6\u4f7f\u7528\u3002",
                "questions": "\u5f00\u5de5\u524d\u95ee\u6e05\u695a\u7814\u7a76\u95ee\u9898\u3001\u8303\u56f4\u3001\u65f6\u95f4\u8981\u6c42\u3001\u6765\u6e90\u504f\u597d\u548c\u8f93\u51fa\u683c\u5f0f\u3002",
                "steps": "1. \u62c6\u89e3\u7814\u7a76\u95ee\u9898\n2. \u68c0\u67e5\u5df2\u6709\u77e5\u8bc6\n3. \u641c\u96c6\u5e76\u4ea4\u53c9\u9a8c\u8bc1\u4fe1\u606f\n4. \u6574\u7406\u6765\u6e90\n5. \u8f93\u51fa\u7ed3\u8bba\u548c\u4e0d\u786e\u5b9a\u70b9\n6. \u6c89\u6dc0\u65b0\u77e5\u8bc6",
            }),
            _normalize_workflow({
                "id": "wf-local-learning",
                "name": "\u5b66\u4e60\u672c\u5730\u8d44\u6599",
                "description": "\u9700\u8981\u8bfb\u53d6\u7528\u6237\u4e0a\u4f20\u6216\u672c\u5730\u6587\u4ef6\uff0c\u5e76\u6574\u7406\u6210\u5458\u5de5\u77e5\u8bc6\u65f6\u4f7f\u7528\u3002",
                "questions": "\u5f00\u5de5\u524d\u95ee\u6e05\u695a\u5b66\u4e60\u76ee\u6807\u3001\u91cd\u70b9\u6587\u4ef6\u3001\u5b66\u4e60\u6df1\u5ea6\u548c\u672a\u6765\u8981\u7528\u5728\u54ea\u4e9b\u4efb\u52a1\u4e0a\u3002",
                "steps": "1. \u68c0\u67e5\u8d44\u6599\u5217\u8868\n2. \u786e\u8ba4\u5b66\u4e60\u76ee\u6807\n3. \u9605\u8bfb\u5e76\u63d0\u70bc\u5173\u952e\u77e5\u8bc6\n4. \u5199\u5165\u77e5\u8bc6\u5e93\n5. \u603b\u7ed3\u672c\u6b21\u5b66\u4e60\u7684\u7ecf\u9a8c",
            }),
        ])
    elif any(word in role_text for word in ["\u4ee3\u7801", "\u7a0b\u5e8f", "\u5f00\u53d1", "code", "dev", "bug"]):
        presets.extend([
            _normalize_workflow({
                "id": "wf-code-review",
                "name": "\u68c0\u67e5\u4ee3\u7801",
                "description": "\u9700\u8981\u67e5\u627e bug\u3001\u98ce\u9669\u3001\u91cd\u6784\u70b9\u6216\u6d4b\u8bd5\u7f3a\u53e3\u65f6\u4f7f\u7528\u3002",
                "questions": "\u5f00\u5de5\u524d\u95ee\u6e05\u695a\u68c0\u67e5\u8303\u56f4\u3001\u5173\u6ce8\u98ce\u9669\u3001\u662f\u5426\u5141\u8bb8\u4fee\u6539\u548c\u9700\u8981\u54ea\u79cd\u8f93\u51fa\u3002",
                "steps": "1. \u786e\u8ba4\u68c0\u67e5\u8303\u56f4\n2. \u9605\u8bfb\u76f8\u5173\u4ee3\u7801\n3. \u5217\u51fa\u98ce\u9669\u548c\u4f18\u5148\u7ea7\n4. \u63d0\u51fa\u4fee\u590d\u65b9\u6848\n5. \u7ecf\u7528\u6237\u786e\u8ba4\u540e\u518d\u4fee\u6539\n6. \u8bb0\u5f55\u9879\u76ee\u7ecf\u9a8c",
            }),
        ])
    else:
        presets.append(_normalize_workflow({
            "id": "wf-learning",
            "name": "\u5b66\u4e60\u548c\u79ef\u7d2f",
            "description": "\u9700\u8981\u8ba9\u5458\u5de5\u56f4\u7ed5\u67d0\u4e2a\u65b9\u5411\u6301\u7eed\u5b66\u4e60\u3001\u603b\u7ed3\u5e76\u79ef\u7d2f\u7ecf\u9a8c\u65f6\u4f7f\u7528\u3002",
            "questions": "\u5f00\u5de5\u524d\u95ee\u6e05\u695a\u5b66\u4e60\u65b9\u5411\u3001\u8d44\u6599\u6765\u6e90\u3001\u8f93\u51fa\u5f62\u5f0f\u548c\u591a\u4e45\u590d\u76d8\u4e00\u6b21\u3002",
            "steps": "1. \u786e\u8ba4\u5b66\u4e60\u76ee\u6807\n2. \u68c0\u67e5\u5df2\u6709\u77e5\u8bc6\n3. \u9605\u8bfb\u6216\u641c\u7d22\u65b0\u8d44\u6599\n4. \u603b\u7ed3\u5173\u952e\u6536\u83b7\n5. \u66f4\u65b0\u77e5\u8bc6\u5e93\u548c\u7ecf\u9a8c",
        }))
    return presets

def _ensure_employee_workflows(emp: dict) -> list[dict]:
    workflows = emp.get("workflows")
    if not isinstance(workflows, list):
        workflows = []
    normalized = []
    seen = set()
    for idx, workflow in enumerate(workflows):
        if not isinstance(workflow, dict):
            continue
        wf = _normalize_workflow(workflow, fallback_name=f"\u5e38\u7528\u4efb\u52a1 {idx + 1}")
        if wf["id"] in seen:
            wf["id"] = _new_workflow_id()
        seen.add(wf["id"])
        normalized.append(wf)
    if not normalized:
        normalized.extend(_preset_workflows_for_employee(emp))
        emp["workflow_presets_seeded_at"] = emp.get("workflow_presets_seeded_at") or _now_iso()
    elif not emp.get("workflow_presets_seeded_at"):
        existing_ids = {wf.get("id") for wf in normalized}
        for preset in _preset_workflows_for_employee(emp):
            if preset.get("id") not in existing_ids:
                normalized.append(preset)
                existing_ids.add(preset.get("id"))
        emp["workflow_presets_seeded_at"] = _now_iso()
    if not any(wf.get("is_default") for wf in normalized):
        normalized[0]["is_default"] = True
    default_seen = False
    for wf in normalized:
        if wf.get("is_default") and not default_seen:
            default_seen = True
        elif wf.get("is_default"):
            wf["is_default"] = False
    emp["workflows"] = normalized
    return normalized

def _workflow_summary_for_prompt(workflow: dict | None) -> str:
    if not workflow:
        return "\u672a\u6307\u5b9a\u5e38\u7528\u4efb\u52a1\u3002"
    description = workflow.get("description", "") or "\u672a\u8bbe\u5b9a"
    questions = workflow.get("questions", "") or "\u8bf7\u6839\u636e\u4efb\u52a1\u4e3b\u52a8\u63d0\u95ee"
    steps = workflow.get("steps", "") or "\u8bf7\u5148\u6839\u636e\u4efb\u52a1\u751f\u6210\u8be6\u7ec6\u8ba1\u5212"
    parts = [
        f"\u5e38\u7528\u4efb\u52a1\uff1a{workflow.get('name', '')}",
        f"\u9002\u7528\u573a\u666f\uff1a{description}",
        f"\u5f00\u5de5\u524d\u9700\u8981\u95ee\u6e05\u695a\uff1a{questions}",
        f"\u53c2\u8003\u6b65\u9aa4\uff1a\n{steps}",
    ]
    return "\n".join(parts)

def _append_employee_experience_text(employee_id: str, text: str, title: str = "\u5de5\u4f5c\u7ecf\u9a8c"):
    exp_text = (text or "").strip()
    if not exp_text:
        return
    exp_path = _employee_dir(employee_id) / "experience.md"
    current = _read_file_safe(exp_path)
    new_exp = f"\n> {datetime.now().strftime('%Y-%m-%d %H:%M')} {title}\n{exp_text}\n"
    exp_path.parent.mkdir(parents=True, exist_ok=True)
    exp_path.write_text(current + new_exp, encoding="utf-8")

def _strip_think_blocks_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(
        r"<(?:think|thinking|reasoning|thought|REASONING_SCRATCHPAD)(?:\s[^>]*)?>.*?</(?:think|thinking|reasoning|thought|REASONING_SCRATCHPAD)\s*>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

def _merge_streamed_and_final_text(streamed_text: str, final_text: str) -> str:
    streamed = _strip_think_blocks_text(streamed_text or "").strip()
    final = _strip_think_blocks_text(final_text or "").strip()
    if final == "(no response)":
        final = ""
    if not streamed:
        return final
    if not final:
        return streamed
    if final in streamed:
        return streamed
    if streamed in final:
        return final
    return streamed.rstrip() + "\n\n" + final.lstrip()

def _finalize_agent_turn(session_id: str, session: dict, result: dict, message: str, stream_state: dict) -> str:
    """Persist an agent result even if the desktop WebSocket disappeared."""
    full_messages = result.get("messages", []) if isinstance(result, dict) else []
    final_text = result.get("final_response", "") if isinstance(result, dict) else ""
    if not final_text and full_messages:
        last = full_messages[-1]
        if last.get("role") == "assistant":
            final_text = last.get("content", "")

    streamed_text = "".join(stream_state.get("chunks") or [])
    merged_text = _merge_streamed_and_final_text(streamed_text, final_text)
    if merged_text:
        final_text = merged_text

    if full_messages:
        if final_text:
            for idx in range(len(full_messages) - 1, -1, -1):
                if full_messages[idx].get("role") == "assistant":
                    full_messages[idx] = {**full_messages[idx], "content": final_text}
                    break
            else:
                full_messages.append({"role": "assistant", "content": final_text})
        with session_lock:
            current = sessions.get(session_id)
            if current is session:
                current["history"] = full_messages
        try:
            _replace_messages_preserving_timestamps(session_id, full_messages)
        except Exception as e:
            log_msg("WARN", f"[{session_id[:12]}] Persist finished turn failed: {e}")
        try:
            if not session_db.get_session_title(session_id):
                title = _default_title_from_history(full_messages, message[:30])
                if title:
                    session_db.set_session_title(session_id, title)
                    with session_lock:
                        current = sessions.get(session_id)
                        if current is session:
                            current["title"] = title
        except Exception:
            pass

    result["__desktop_final_text"] = final_text
    result["__desktop_finalized"] = True
    log_msg("INFO", f"[{session_id[:12]}] Agent response complete, {len(final_text)} chars")
    _api_calls = result.get("api_calls", 0)
    _msg_count = len(full_messages) if full_messages else 0
    log_msg("INFO", f"[{session_id[:12]}] Turn stats: api_calls={_api_calls}, total_messages={_msg_count}")
    return final_text

def _trim_messages_for_persistence(messages: list[dict], limit: int = MAX_PERSISTED_SESSION_MESSAGES) -> list[dict]:
    """Keep desktop sessions bounded so one bad turn cannot freeze the UI."""
    full = []
    for msg in messages or []:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role == "assistant":
            role = "assistant"
        elif role == "agent":
            role = "assistant"
        elif role == "user":
            role = "user"
        elif role == "system":
            role = "system"
        else:
            continue
        text = _message_text(msg.get("content")).strip()
        upper = text.upper()
        if not text:
            continue
        if "CONTEXT COMPACTION" in upper and "REFERENCE ONLY" in upper:
            continue
        if upper.startswith("[CONTEXT COMPACTION"):
            continue
        full.append({**msg, "role": role, "content": text})
    limit = max(20, int(limit or 400))
    if len(full) <= limit:
        return full
    trimmed = full[-limit:]
    while trimmed and trimmed[0].get("role") in {"assistant", "tool"}:
        trimmed = trimmed[1:]
    return trimmed or full[-limit:]

def _final_text_from_result(result: dict) -> str:
    final_text = str((result or {}).get("final_response") or "")
    if final_text:
        return final_text
    for msg in reversed((result or {}).get("messages") or []):
        if isinstance(msg, dict) and msg.get("role") == "assistant":
            text = _message_text(msg.get("content")).strip()
            if text:
                return text
    return ""

def _safe_result_for_desktop(result: dict, persisted_user_history: list[dict]) -> dict:
    """Persist only the known desktop history plus the final assistant text.

    Some agent backends return an oversized transcript. Blindly writing that
    transcript can duplicate the entire conversation and make the desktop UI
    unresponsive. The desktop DB is the source of truth for prior messages, so
    keep the returned transcript out of persistence.
    """
    if not isinstance(result, dict):
        return result
    final_text = _final_text_from_result(result)
    safe_messages = list(persisted_user_history or [])
    if final_text:
        safe_messages.append({"role": "assistant", "content": final_text})
    return {**result, "messages": _trim_messages_for_persistence(safe_messages), "final_response": final_text}

def _employee_tasks_path(employee_id: str) -> Path:
    return _employee_dir(employee_id) / "tasks" / "index.json"

def _load_employee_tasks(employee_id: str) -> dict:
    path = _employee_tasks_path(employee_id)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("tasks"), list):
                return data
        except Exception:
            pass
    return {"tasks": []}

def _save_employee_tasks(employee_id: str, data: dict):
    path = _employee_tasks_path(employee_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _new_employee_task_id() -> str:
    return "task-" + uuid.uuid4().hex[:8]

def _latest_employee_tasks(employee_id: str, limit: int = 12) -> list[dict]:
    data = _load_employee_tasks(employee_id)
    tasks = data.get("tasks", [])
    tasks.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    return tasks[:limit]


def _employee_latest_task(employee_id: str) -> dict | None:
    """Return the most recent task for an employee, or None."""
    tasks = _latest_employee_tasks(employee_id, limit=1)
    return tasks[0] if tasks else None

def _create_employee_task(employee_id: str, workflow: dict | None, session_id: str, title: str, status: str = "planning") -> dict:
    data = _load_employee_tasks(employee_id)
    now = _now_iso()
    workflow_name = (workflow or {}).get("name", "") or "\u5e38\u7528\u4efb\u52a1"
    task = {
        "id": _new_employee_task_id(),
        "employee_id": employee_id,
        "title": (title or workflow_name or "\u5458\u5de5\u4efb\u52a1").strip(),
        "workflow_id": (workflow or {}).get("id", ""),
        "workflow_name": workflow_name,
        "status": status,
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
        "plan_confirmed_at": "",
        "completed_at": "",
        "result_summary": "",
    }
    data.setdefault("tasks", []).append(task)
    _save_employee_tasks(employee_id, data)
    return task

def _update_employee_task(employee_id: str, task_id: str, **updates) -> dict | None:
    data = _load_employee_tasks(employee_id)
    for task in data.get("tasks", []):
        if task.get("id") == task_id:
            for key, value in updates.items():
                task[key] = value
            task["updated_at"] = _now_iso()
            _save_employee_tasks(employee_id, data)
            return task
    return None

def _find_employee_task(employee_id: str, task_id: str) -> dict | None:
    data = _load_employee_tasks(employee_id)
    return next((task for task in data.get("tasks", []) if task.get("id") == task_id), None)

def _latest_employee_task_for_session(employee_id: str, session_id: str) -> dict | None:
    sid = str(session_id or "")
    tasks = _latest_employee_tasks(employee_id, limit=20)
    for status in ("planning", "running"):
        for task in tasks:
            if task.get("session_id") == sid and task.get("status") == status:
                return task
    return next((task for task in tasks if task.get("session_id") == sid), None)

def _plain_notification_text(text: str, limit: int = 90) -> str:
    value = _strip_think_blocks_text(str(text or ""))
    value = re.sub(r"`{1,3}[^`]*`{1,3}", "", value)
    value = re.sub(r"[*_#>~\[\]()]|https?://\S+", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return ""
    return value[:limit].rstrip() + ("..." if len(value) > limit else "")

def _looks_like_needs_user_input(text: str) -> bool:
    value = str(text or "")
    cues = [
        "请确认", "等待你确认", "需要你确认", "确认后", "请告诉我",
        "请补充", "需要你补充", "需要你提供", "你希望", "你想要",
        "是否", "哪一个", "哪个方向",
    ]
    return any(cue in value for cue in cues)

def _notify_session_turn_finished(session_id: str, final_text: str):
    if not final_text:
        return
    emp = _find_employee_by_session(session_id)
    sender = "Hermes"
    title = "任务完成啦"
    message = "当前对话已经处理完成，点我查看结果。"
    notify_type = "completed"
    persistent = False
    employee_id = ""

    if emp:
        employee_id = emp.get("id", "")
        sender = emp.get("name") or "员工"
        task = _latest_employee_task_for_session(employee_id, session_id)
        if task and task.get("status") == "planning":
            notify_type = "needs_confirm"
            title = "需要你确认一下"
            message = f"{sender} 已经整理好计划，等你确认后再开始干活。"
            persistent = True
        elif task and task.get("status") == "running":
            notify_type = "completed"
            title = "任务完成啦"
            message = f"{sender} 已完成“{task.get('workflow_name') or task.get('title') or '当前任务'}”，点我查看结果。"
            summary = _plain_notification_text(final_text, 120)
            _update_employee_task(employee_id, task.get("id"), status="completed", completed_at=_now_iso(), result_summary=summary)
        else:
            summary = _plain_notification_text(final_text)
            message = f"{sender} 已经回复你了。" + (f" {summary}" if summary else "")
            if _looks_like_needs_user_input(final_text):
                notify_type = "needs_input"
                title = "需要你看一下"
                persistent = True
    else:
        summary = _plain_notification_text(final_text)
        if _looks_like_needs_user_input(final_text):
            notify_type = "needs_input"
            title = "需要你看一下"
            message = "Hermes 需要你补充或确认信息，点我继续。"
            persistent = True
        elif summary:
            message = f"处理完成：{summary}"

    _emit_bubble_notification({
        "type": notify_type,
        "sender": sender,
        "title": title,
        "message": message,
        "session_id": session_id,
        "employee_id": employee_id,
        "persistent": persistent,
        "auto_hide_seconds": 0 if persistent else 10,
    })

def _read_file_safe(path: Path) -> str:
    try:
        if path.exists():
            return path.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""

def _build_profile_md(emp: dict) -> str:
    """Build profile.md content from employee dict."""
    lines = []
    lines.append(f"# {emp.get('name', '未命名')}\n")
    lines.append(f"## 基本信息")
    lines.append(f"- 名称：{emp.get('name', '')}")
    lines.append(f"- 头像：{emp.get('emoji', '🤖')}")
    if emp.get("role"):
        lines.append(f"- 角色：{emp.get('role', '')}（擅长领域/专家方向）")
    lines.append(f"- 创建时间：{emp.get('created_at', '')}\n")
    if emp.get("personality"):
        lines.append(f"## 性格特征")
        lines.append(f"- {emp.get('personality', '')}\n")
    _wc = emp.get("work_content") or ""
    _ws = emp.get("work_steps") or emp.get("steps") or ""
    _sg = emp.get("self_growth") or emp.get("learn_topics") or ""
    _workflows = _ensure_employee_workflows(emp)
    if emp.get("goal") or _wc or _ws or emp.get("notes"):
        lines.append(f"## 工作设定")
    if emp.get("goal"):
        lines.append(f"- 目标：{emp.get('goal', '')}")
    if _wc:
        lines.append(f"- 工作内容：{_wc}")
    if _ws:
        lines.append(f"- 工作步骤：{_ws}")
    if emp.get("notes"):
        lines.append(f"- 注意事项：{emp.get('notes', '')}")
    lines.append("")
    if _sg:
        lines.append(f"## 自我成长")
        lines.append(f"- 学习方向：{_sg}\n")
    if emp.get("work_mode"):
        lines.append(f"## 工作模式")
        lines.append(f"- {emp.get('work_mode', '混合模式')}")
    if _workflows:
        lines.append("")
        lines.append("## 常用任务")
        for wf in _workflows:
            marker = "（默认）" if wf.get("is_default") else ""
            lines.append(f"### {wf.get('name', '')}{marker}")
            if wf.get("description"):
                lines.append(f"- 适用场景：{wf.get('description', '')}")
            if wf.get("questions"):
                lines.append(f"- 开工前提问：{wf.get('questions', '')}")
            if wf.get("steps"):
                lines.append(f"- 参考步骤：\n{wf.get('steps', '')}")
    return "\n".join(lines)

def _find_employee_by_session(session_id: str) -> dict | None:
    data = _load_employees_index()
    for emp in data.get("employees", []):
        if emp.get("session_id") == session_id:
            return emp
    return None

def _build_agent_prompt(emp: dict) -> str | None:
    profile_path = _employee_profile_path(emp["id"])
    exp_path = _employee_dir(emp["id"]) / "experience.md"
    kn_path = _employee_dir(emp["id"]) / "knowledge.md"
    parts = []
    if profile_path.exists():
        parts.append(profile_path.read_text(encoding="utf-8"))
    if exp_path.exists():
        exp_text = exp_path.read_text(encoding="utf-8")
        if exp_text.strip() and exp_text.strip() != "# 经验积累":
            parts.append(exp_text)
    if kn_path.exists():
        kn_text = kn_path.read_text(encoding="utf-8")
        if kn_text.strip() and kn_text.strip() != "# 知识库":
            parts.append(kn_text)
    if parts:
        parts.append(
            "\n【重要】以上是你的完整角色设定卡。你必须严格扮演这个角色，"
            "回答时始终基于上述设定中的性格、角色和能力。"
            "如果用户问你擅长什么或你是谁，请根据设定回答，不要编造与设定无关的内容。"
        )
        return "\n\n".join(parts)
    return None

# --- Session management ---
sessions = {}  # {session_id: {"agent": AIAgent, "history": [], "created_at": datetime, "title": str}}
session_lock = threading.RLock()
prewarm_lock = threading.Lock()
prewarming_sessions = set()
background_review_lock = threading.Lock()
background_review_pending: dict[str, dict] = {}
background_review_timer = None
last_user_activity_at = time.time()
SESSION_LOCK_UI_TIMEOUT = float(os.environ.get("HERMES_SESSION_LOCK_UI_TIMEOUT", "0.3"))
INTERRUPT_JOIN_TIMEOUT = float(os.environ.get("HERMES_INTERRUPT_JOIN_TIMEOUT", "0.2"))
BACKGROUND_REVIEW_IDLE_SECONDS = float(os.environ.get("HERMES_DESKTOP_BACKGROUND_REVIEW_IDLE_SECONDS", "900"))
BACKGROUND_REVIEW_DISPUTE_COOLDOWN_SECONDS = float(
    os.environ.get("HERMES_DESKTOP_BACKGROUND_REVIEW_DISPUTE_COOLDOWN_SECONDS", "3600")
)
session_db = SessionDB(HERMES_HOME / "state.db")
DESKTOP_STATE_PATH = HERMES_HOME / "desktop-client" / "state.json"

# --- Auto-shutdown when browser closes ---
active_connections = 0
shutdown_timer = None
shutdown_lock = threading.Lock()
WS_SHUTDOWN_GRACE_SECONDS = float(os.environ.get("HERMES_WS_SHUTDOWN_GRACE", "120"))

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
        shutdown_timer = threading.Timer(WS_SHUTDOWN_GRACE_SECONDS, do_shutdown)
        shutdown_timer.daemon = True
        shutdown_timer.start()
        log_msg("INFO", f"Browser disconnected, server will exit in {WS_SHUTDOWN_GRACE_SECONDS:.0f}s if no reconnect...")

def _desktop_background_review_enabled() -> bool:
    value = os.environ.get("HERMES_DESKTOP_BACKGROUND_REVIEW")
    if value is None or str(value).strip() == "":
        return True
    return is_truthy_value(value)

def _mark_user_activity() -> None:
    global last_user_activity_at
    last_user_activity_at = time.time()

def _desktop_has_running_turn() -> bool:
    with session_lock:
        return any(bool((s or {}).get("running")) for s in sessions.values())

def _looks_like_tool_dispute(message: str) -> bool:
    text = (message or "").lower()
    if not text:
        return False
    dispute_terms = (
        "没执行",
        "没有执行",
        "没调用",
        "没有调用",
        "没成功",
        "没有成功",
        "没反应",
        "没创建",
        "没有创建",
        "没删除",
        "没有删除",
        "空白界面",
        "脏数据",
        "幻觉",
        "假装",
        "沙箱",
        "隔离",
        "tool_turns=0",
        "fake tool",
        "not actually",
        "did not run",
    )
    return any(term in text for term in dispute_terms)

def _schedule_background_review_check(delay: float | None = None) -> None:
    global background_review_timer
    if not _desktop_background_review_enabled():
        return
    delay = max(1.0, float(BACKGROUND_REVIEW_IDLE_SECONDS if delay is None else delay))
    with background_review_lock:
        if background_review_timer and background_review_timer.is_alive():
            return
        background_review_timer = threading.Timer(delay, _run_queued_background_review_if_idle)
        background_review_timer.daemon = True
        background_review_timer.start()

def _run_queued_background_review_if_idle() -> None:
    global background_review_timer
    with background_review_lock:
        background_review_timer = None

    if not _desktop_background_review_enabled():
        with background_review_lock:
            background_review_pending.clear()
        return

    now = time.time()
    idle_wait = (last_user_activity_at + BACKGROUND_REVIEW_IDLE_SECONDS) - now
    if _desktop_has_running_turn() or idle_wait > 0:
        _schedule_background_review_check(max(5.0, idle_wait if idle_wait > 0 else 15.0))
        return

    with background_review_lock:
        if not background_review_pending:
            return
        session_id, job = min(
            background_review_pending.items(),
            key=lambda item: float(item[1].get("queued_at") or 0),
        )
        background_review_pending.pop(session_id, None)

    try:
        spawn = job.get("spawn")
        if callable(spawn):
            log_msg("INFO", f"[{session_id[:12]}] Running queued desktop background review")
            spawn(*job.get("args", ()), **job.get("kwargs", {}))
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Queued background review failed: {e}")

    with background_review_lock:
        has_more = bool(background_review_pending)
    if has_more:
        _schedule_background_review_check(60.0)

def _install_desktop_background_review_scheduler(agent: AIAgent, session_id: str) -> None:
    original_spawn = getattr(agent, "_spawn_background_review", None)
    if not callable(original_spawn) or getattr(agent, "_desktop_background_review_scheduler", False):
        return

    if not _desktop_background_review_enabled():
        agent._memory_nudge_interval = 0
        agent._skill_nudge_interval = 0
        log_msg("INFO", f"[{session_id[:12]}] Desktop background review disabled by env")
        return

    def _queued_background_review(*args, **kwargs):
        now = time.time()
        with session_lock:
            current = sessions.get(session_id)
            if current and current.get("last_fake_execution_blocked"):
                log_msg(
                    "WARN",
                    f"[{session_id[:12]}] Skipping desktop background review after blocked fake execution",
                )
                return None
            if current:
                disputed_at = float(current.get("last_tool_dispute_at") or 0)
                if disputed_at and now - disputed_at < BACKGROUND_REVIEW_DISPUTE_COOLDOWN_SECONDS:
                    log_msg(
                        "WARN",
                        f"[{session_id[:12]}] Skipping desktop background review during tool-dispute cooldown",
                    )
                    return None
        with background_review_lock:
            background_review_pending[session_id] = {
                "spawn": original_spawn,
                "args": args,
                "kwargs": kwargs,
                "queued_at": now,
            }
        log_msg(
            "INFO",
            f"[{session_id[:12]}] Desktop background review queued; "
            f"will run after {int(BACKGROUND_REVIEW_IDLE_SECONDS)}s idle",
        )
        _schedule_background_review_check(BACKGROUND_REVIEW_IDLE_SECONDS)
        return None

    agent._desktop_background_review_scheduler = True
    agent._desktop_background_review_original_spawn = original_spawn
    agent._spawn_background_review = _queued_background_review

def do_shutdown():
    global shutdown_timer
    with shutdown_lock:
        if active_connections > 0:
            shutdown_timer = None
            return
        with session_lock:
            running_sessions = []
            for sid, session in sessions.items():
                thread = session.get("agent_thread")
                if session.get("running") and thread and thread.is_alive():
                    running_sessions.append(sid)
        if running_sessions:
            shutdown_timer = threading.Timer(30.0, do_shutdown)
            shutdown_timer.daemon = True
            shutdown_timer.start()
            log_msg("INFO", f"Shutdown deferred; {len(running_sessions)} session(s) still running")
            return
        shutdown_timer = None
    log_msg("INFO", "Shutting down (no active clients)...")
    os._exit(0)

def generate_session_id():
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

def _load_desktop_state() -> dict:
    try:
        if DESKTOP_STATE_PATH.exists():
            data = json.loads(DESKTOP_STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception as e:
        log_msg("WARN", f"Failed to load desktop state: {e}")
    return {}

def _save_desktop_state(data: dict) -> None:
    try:
        DESKTOP_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        DESKTOP_STATE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log_msg("WARN", f"Failed to save desktop state: {e}")

def _session_exists(session_id: str) -> bool:
    if not session_id:
        return False
    with session_lock:
        if session_id in sessions:
            return True
    try:
        return bool(session_db.get_session(session_id))
    except Exception:
        return False

def _employee_session_ids() -> set[str]:
    try:
        return {
            str(emp.get("session_id"))
            for emp in (_load_employees_index().get("employees") or [])
            if emp.get("session_id")
        }
    except Exception:
        return set()

def _latest_main_session_id() -> str:
    employee_sids = _employee_session_ids()
    try:
        rows = session_db.list_sessions_rich(
            source=SESSION_SOURCE,
            limit=200,
            order_by_last_active=True,
        )
        for row in rows:
            sid = row.get("id") or row.get("session_id") or ""
            msg_count = int(row.get("message_count") or 0)
            if sid and sid not in employee_sids and msg_count > 0:
                return sid
    except Exception as e:
        log_msg("WARN", f"Failed to find latest main session from DB: {e}")

    with session_lock:
        candidates = [
            (sid, s)
            for sid, s in sessions.items()
            if sid not in employee_sids and (s.get("history") or s.get("agent"))
        ]
    if not candidates:
        # Last resort: any non-employee session with messages
        try:
            rows = session_db.list_sessions_rich(source=SESSION_SOURCE, limit=5, order_by_last_active=True)
            for row in rows:
                sid = row.get("id") or ""
                if sid and sid not in employee_sids and int(row.get("message_count") or 0) > 0:
                    return sid
        except Exception:
            pass
        return ""
    candidates.sort(key=lambda item: item[1].get("created_at") or datetime.min, reverse=True)
    return candidates[0][0]

def _get_main_session_id() -> str:
    state = _load_desktop_state()
    sid = str(state.get("main_session_id") or "")
    if _session_exists(sid):
        return sid
    return _latest_main_session_id()

def _set_main_session_id(session_id: str) -> None:
    state = _load_desktop_state()
    state["main_session_id"] = session_id
    state["main_session_updated_at"] = datetime.now().isoformat()
    _save_desktop_state(state)

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
        if _is_internal_frontend_message(role, content):
            continue
        item = {"role": role, "content": content}
        if msg.get("timestamp") is not None:
            item["timestamp"] = msg.get("timestamp")
        visible.append(item)
    return visible

def _is_internal_frontend_message(role: str, content: str) -> bool:
    text = (content or "").strip()
    if not text:
        return False
    upper = text[:500].upper()
    if "CONTEXT COMPACTION" in upper and "REFERENCE ONLY" in upper:
        return True
    if upper.startswith("[CONTEXT COMPACTION"):
        return True
    if role == "system" and ("REFERENCE ONLY" in upper or "COMPACTED" in upper):
        return True
    return False

def _load_history_from_db(session_id: str) -> list[dict]:
    try:
        return session_db.get_messages_as_conversation(session_id, include_ancestors=True)
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Failed to load DB history: {e}")
        return []

def _load_display_history_from_db(session_id: str, limit: int = DISPLAY_HISTORY_LIMIT) -> list[dict]:
    """Load frontend history with DB timestamps without changing agent replay shape."""
    try:
        session_ids = [session_id]
        lineage = getattr(session_db, "_session_lineage_root_to_tip", None)
        if callable(lineage):
            session_ids = lineage(session_id)
        limit = max(1, min(int(limit or DISPLAY_HISTORY_LIMIT), 1000))
        placeholders = ",".join("?" for _ in session_ids)
        with session_db._lock:
            rows = session_db._conn.execute(
                "SELECT role, content, timestamp FROM ("
                f"SELECT id, role, content, timestamp FROM messages WHERE session_id IN ({placeholders}) "
                "ORDER BY id DESC LIMIT ?"
                ") ORDER BY id",
                tuple(session_ids) + (limit,),
            ).fetchall()
        decode = getattr(session_db, "_decode_content", None)
        history = []
        for row in rows:
            content = row["content"]
            if callable(decode):
                content = decode(content)
            history.append({
                "role": row["role"],
                "content": content,
                "timestamp": row["timestamp"],
            })
        return history
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Failed to load display history: {e}")
        return []

def _prepare_agent_history_for_turn(history: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (prefix_to_preserve, recent_history_for_agent)."""
    full = list(history or [])
    limit = max(1, int(AGENT_REPLAY_HISTORY_LIMIT or 80))
    if len(full) <= limit:
        return [], full
    start = len(full) - limit
    # Avoid starting replay with orphaned assistant/tool records.
    while start < len(full) and full[start].get("role") in {"assistant", "tool"}:
        start += 1
    if start >= len(full):
        start = max(0, len(full) - limit)
    return full[:start], full[start:]

def _requires_real_tool_action(message: str) -> bool:
    text = str(message or "").lower()
    if not text:
        return False
    action_words = [
        "\u521b\u5efa", "\u65b0\u5efa", "\u5199\u5165", "\u5199\u4e2a", "\u4fdd\u5b58",
        "\u5220\u9664", "\u590d\u5236", "\u79fb\u52a8", "\u91cd\u547d\u540d",
        "\u6253\u5f00", "\u5173\u95ed", "\u70b9\u51fb", "\u8f93\u5165", "\u53d1\u9001",
        "\u7c98\u8d34", "\u4e0b\u8f7d", "\u4e0a\u4f20", "\u8fd0\u884c", "\u6267\u884c",
        "\u64cd\u4f5c", "\u6d4b\u8bd5", "\u8bd5\u8bd5", "\u5c1d\u8bd5", "\u751f\u6210",
        "create", "write", "save", "delete", "copy", "move", "rename",
        "open", "click", "type", "send", "paste", "download", "upload", "run",
        "execute", "operate", "test", "try", "generate",
    ]
    target_words = [
        "\u684c\u9762", "\u6587\u4ef6", "\u6587\u4ef6\u5939", "\u76ee\u5f55",
        "\u5fae\u4fe1", "qq", "\u7a97\u53e3", "\u672c\u5730", "\u7535\u8111",
        "\u597d\u53cb", "\u6d88\u606f", "\u811a\u672c", "\u6280\u80fd",
        "desktop", "file", "folder", "directory", "wechat", "window", "local",
        "message", "script", "skill",
    ]
    return any(word in text for word in action_words) and any(word in text for word in target_words)

def _result_used_real_tool(result: dict) -> bool:
    if not isinstance(result, dict):
        return False
    for msg in result.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "tool" or msg.get("tool_call_id") or msg.get("tool_name"):
            return True
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            return True
    return False

def _fake_execution_guard_text() -> str:
    return (
        "我刚才没有真正调用任何本地工具，所以不能说已经执行成功。"
        "这类任务必须实际调用文件/终端/桌面自动化工具并验证结果后，才能告诉你完成。"
        "请重新发送这条任务，我会按工具结果一步一步执行。"
    )

def _replace_messages_preserving_timestamps(session_id: str, messages: list[dict]) -> None:
    """Replace messages while preserving timestamps for already persisted rows."""
    messages = _trim_messages_for_persistence(messages)
    old_timestamps: list[float] = []
    try:
        with session_db._lock:
            rows = session_db._conn.execute(
                "SELECT timestamp FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        old_timestamps = [float(row["timestamp"]) for row in rows if row["timestamp"] is not None]
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Load old timestamps failed: {e}")

    session_db.replace_messages(session_id, messages)

    if not old_timestamps:
        return
    try:
        with session_db._lock:
            rows = session_db._conn.execute(
                "SELECT id FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            for idx, row in enumerate(rows[:len(old_timestamps)]):
                session_db._conn.execute(
                    "UPDATE messages SET timestamp = ? WHERE id = ?",
                    (old_timestamps[idx], row["id"]),
                )
            session_db._conn.commit()
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Restore old timestamps failed: {e}")

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

def _validate_session_id(session_id: str) -> str:
    sid = str(session_id or "").strip()
    if not SESSION_ID_RE.match(sid):
        raise HTTPException(status_code=400, detail="Invalid session id")
    return sid


def get_session_dir(session_id: str) -> Path:
    sid = _validate_session_id(session_id)
    root = (HERMES_HOME / "desktop-client" / "sessions").resolve()
    d = (root / sid).resolve()
    try:
        d.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session path")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _session_file_path(session_id: str, filename: str) -> Path:
    base = get_session_dir(session_id).resolve()
    target = (base / filename).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return target

def _empty_session():
    return {
        "agent": None,
        "history": [],
        "created_at": datetime.now(),
        "title": "",
        "callbacks": {},
        "running": False,
        "agent_thread": None,
        "interrupt_requested": False,
        "run_id": 0,
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

def _combine_system_prompts(*parts: str | None) -> str:
    return "\n\n".join(str(part).strip() for part in parts if str(part or "").strip())

def _desktop_runtime_system_prompt() -> str:
    desktop_path = Path.home() / "Desktop"
    return (
        "Hermes Desktop runtime rules:\n"
        f"- You are running in the user's real local Windows desktop app. "
        f"The user profile is {Path.home()} and the Desktop folder is {desktop_path}.\n"
        "- The terminal tool is configured as a local terminal. Do not claim it is a sandbox, "
        "container, or virtual filesystem unless a tool result proves that for this run.\n"
        "- Windows terminal shells may differ. Prefer explicit absolute Windows paths for "
        "user-visible files, and verify filesystem operations with read_file, Test-Path, "
        "Get-Item, or an equivalent tool result before saying they succeeded.\n"
        "- Never tell the user a file was created, deleted, a window was clicked, text was typed, "
        "or a message was sent unless the latest tool result confirms the action or the user confirms it.\n"
        "- If a tool call fails, returns an API quota/rate-limit error, or has an uncertain result, "
        "say that plainly and ask for the smallest useful next verification.\n"
        "- For desktop UI automation, use the available computer_use/cua-driver capability according "
        "to its actual schema and returned result. Do not invent tool names, parameters, paths, or outcomes.\n"
        "- When a task involves a skill and needs scripts, create, edit, debug, and run those scripts "
        "inside that skill's own scripts directory. Do not scatter skill scripts on the Desktop, "
        "project root, global scripts folders, or tools folders unless the user explicitly asks.\n"
        "- If the user contradicts a previous claimed success, trust the user's observation and re-check "
        "from the current state instead of defending the earlier result."
    )

def create_agent(session_id: str) -> AIAgent:
    cfg = load_config()
    agent_cfg = cfg.get("agent", {})
    system_prompt = _combine_system_prompts(
        agent_cfg.get("system_prompt", ""),
        _desktop_runtime_system_prompt(),
    )
    model, runtime = _resolve_desktop_runtime(cfg)
    enabled_toolsets = _load_enabled_toolsets(cfg)
    log_msg(
        "INFO",
        f"[{session_id[:12]}] Desktop agent toolsets: "
        f"{', '.join(enabled_toolsets or []) or 'default'}",
    )

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
        verbose_logging=True,
        session_id=session_id,
        session_db=session_db,
        platform=SESSION_SOURCE,
        ephemeral_system_prompt=system_prompt or None,
        reasoning_config=_load_reasoning_config(cfg),
        service_tier=_load_service_tier(cfg),
        request_overrides=runtime.get("request_overrides"),
        enabled_toolsets=enabled_toolsets,
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
    agent._desktop_base_system_prompt = system_prompt
    agent._tool_use_enforcement = True
    _install_desktop_background_review_scheduler(agent, session_id)
    invalidate_prompt = getattr(agent, "_invalidate_system_prompt", None)
    if callable(invalidate_prompt):
        try:
            invalidate_prompt()
        except Exception:
            pass
    try:
        fresh_prompt = agent._build_system_prompt(None)
        agent._cached_system_prompt = fresh_prompt
        if session_db:
            session_db.update_system_prompt(session_id, fresh_prompt)
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Failed to refresh desktop system prompt: {e}")
    return agent

def _apply_employee_prompt_to_agent(agent: AIAgent, session_id: str) -> None:
    emp = _find_employee_by_session(session_id)
    if not emp:
        return
    sp = _build_agent_prompt(emp)
    if sp:
        base_prompt = getattr(agent, "_desktop_base_system_prompt", "") or agent.ephemeral_system_prompt
        agent.ephemeral_system_prompt = _combine_system_prompts(base_prompt, sp)

def _prewarm_session_agent(session_id: str, reason: str = "startup") -> None:
    """Create the agent in the background so the first user message starts faster."""
    try:
        sid = _validate_session_id(session_id)
    except Exception:
        return
    with prewarm_lock:
        if sid in prewarming_sessions:
            return
        prewarming_sessions.add(sid)

    def _worker():
        started = time.time()
        try:
            _ensure_session_record(sid)
            with session_lock:
                s = sessions.setdefault(sid, _empty_session())
                has_agent = s.get("agent") is not None
                is_running = bool(s.get("running"))
            if has_agent or is_running:
                return

            log_msg("INFO", f"[{sid[:12]}] Prewarming agent ({reason})...")
            history = _load_history_from_db(sid)
            agent = create_agent(sid)
            _apply_employee_prompt_to_agent(agent, sid)

            with session_lock:
                s = sessions.setdefault(sid, _empty_session())
                if not s.get("history"):
                    s["history"] = history
                if s.get("agent") is None and not s.get("running"):
                    s["agent"] = agent
                    elapsed = time.time() - started
                    log_msg("INFO", f"[{sid[:12]}] Agent prewarmed in {elapsed:.2f}s")
        except Exception as e:
            log_msg("WARN", f"[{sid[:12]}] Agent prewarm failed: {e}")
        finally:
            with prewarm_lock:
                prewarming_sessions.discard(sid)

    threading.Thread(target=_worker, daemon=True).start()

def _wait_for_prewarmed_agent(session_id: str, timeout: float = 8.0) -> AIAgent | None:
    deadline = time.time() + max(0.0, timeout)
    while time.time() < deadline:
        with session_lock:
            s = sessions.get(session_id)
            if s and s.get("agent") is not None:
                return s.get("agent")
        with prewarm_lock:
            still_prewarming = session_id in prewarming_sessions
        if not still_prewarming:
            return None
        time.sleep(0.1)
    with session_lock:
        s = sessions.get(session_id)
        if s and s.get("agent") is not None:
            return s.get("agent")
    return None

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

@app.post("/api/client-log")
async def api_client_log(request: Request):
    """Accept lightweight diagnostics from the desktop webview."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    event = str(payload.get("event") or "client").replace("\n", " ")[:40]
    detail = json.dumps(payload, ensure_ascii=False, default=str)[:500]
    log_msg("CLIENT", f"{event}: {detail}")
    return {"ok": True}

@app.post("/api/bubble/notify")
async def api_bubble_notify(request: Request):
    """Send a desktop bubble notification if the native bubble is available."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    ok = _emit_bubble_notification(payload)
    return {"ok": ok}

@app.get("/api/bubble/pending")
async def api_bubble_pending():
    """Return and clear the session requested by a bubble notification click."""
    global bubble_pending_target
    with bubble_pending_lock:
        target = dict(bubble_pending_target)
        bubble_pending_target = {"session_id": "", "employee_id": ""}
    return target

# ========== Employee API ==========

@app.get("/api/employees")
async def list_employees():
    try:
        data = _load_employees_index()
        employees = data.get("employees", [])
        for emp in employees:
            _ensure_employee_workflows(emp)
            emp["max_slots"] = MAX_EMPLOYEES
            # Attach latest task for home-page display
            emp["latest_task"] = _employee_latest_task(emp["id"])
        _save_employees_index(data)
        return {"ok": True, "employees": employees, "max": MAX_EMPLOYEES}
    except Exception as e:
        log_msg("WARN", f"List employees failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees")
async def create_employee(request: Request):
    try:
        body = await request.json()
        name = (body.get("name") or "").strip()
        if not name:
            return {"ok": False, "error": "员工名称不能为空"}
        data = _load_employees_index()
        employees = data.get("employees", [])
        if len(employees) >= MAX_EMPLOYEES:
            return {"ok": False, "error": f"最多创建{MAX_EMPLOYEES}个员工"}
        emp_id = "emp-" + uuid.uuid4().hex[:8]
        emp = {
            "id": emp_id,
            "name": name,
            "emoji": (body.get("emoji") or "😊").strip(),
            "role": (body.get("role") or "").strip(),
            "personality": (body.get("personality") or "").strip(),
            "work_content": (body.get("work_content") or "").strip(),
            "work_steps": (body.get("work_steps") or "").strip(),
            "goal": (body.get("goal") or "").strip(),
            "self_growth": (body.get("self_growth") or "").strip(),
            "notes": (body.get("notes") or "").strip(),
            "work_mode": (body.get("work_mode") or "manual").strip(),
            "created_at": datetime.now().isoformat(),
        }
        if isinstance(body.get("workflows"), list):
            emp["workflows"] = body.get("workflows")
        _ensure_employee_workflows(emp)
        employees.append(emp)
        _save_employees_index(data)
        profile_path = _employee_profile_path(emp_id)
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(_build_profile_md(emp), encoding="utf-8")
        (_employee_dir(emp_id) / "experience.md").write_text("# 经验积累\n\n", encoding="utf-8")
        (_employee_dir(emp_id) / "knowledge.md").write_text("# 知识库\n\n", encoding="utf-8")
        (_employee_dir(emp_id) / "knowledge" / "source").mkdir(parents=True, exist_ok=True)
        emp["session_id"] = emp_id
        emp["max_slots"] = MAX_EMPLOYEES
        return {"ok": True, "employee": emp}
    except Exception as e:
        log_msg("WARN", f"Create employee failed: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/api/employees/{employee_id}")
async def get_employee(employee_id: str):
    try:
        data = _load_employees_index()
        for emp in data.get("employees", []):
            if emp["id"] == employee_id:
                _ensure_employee_workflows(emp)
                _save_employees_index(data)
                pp = _employee_profile_path(employee_id)
                emp["profile_md"] = pp.read_text(encoding="utf-8") if pp.exists() else ""
                emp["max_slots"] = MAX_EMPLOYEES
                return {"ok": True, "employee": emp}
        raise HTTPException(status_code=404, detail="Employee not found")
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Get employee failed: {e}")
        return {"ok": False, "error": str(e)}

@app.put("/api/employees/{employee_id}")
async def update_employee(employee_id: str, request: Request):
    try:
        body = await request.json()
        data = _load_employees_index()
        for emp in data.get("employees", []):
            if emp["id"] == employee_id:
                for key in ["name", "emoji", "role", "personality",
                           "goal", "work_content", "work_steps", "self_growth",
                           "notes", "work_mode", "session_id"]:
                    if key in body:
                        emp[key] = (body[key] or "").strip()
                if "workflows" in body and isinstance(body["workflows"], list):
                    emp["workflows"] = body["workflows"]
                _ensure_employee_workflows(emp)
                _save_employees_index(data)
                _employee_profile_path(employee_id).write_text(
                    _build_profile_md(emp), encoding="utf-8"
                )
                emp["max_slots"] = MAX_EMPLOYEES
                return {"ok": True, "employee": emp}
        raise HTTPException(status_code=404, detail="Employee not found")
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Update employee failed: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/api/employees/{employee_id}/workflows")
async def list_employee_workflows(employee_id: str):
    try:
        data = _load_employees_index()
        for emp in data.get("employees", []):
            if emp["id"] == employee_id:
                workflows = _ensure_employee_workflows(emp)
                _save_employees_index(data)
                return {"ok": True, "workflows": workflows}
        raise HTTPException(status_code=404, detail="Employee not found")
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"List workflows failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/workflows")
async def create_employee_workflow(employee_id: str, request: Request):
    try:
        body = await request.json()
        data = _load_employees_index()
        for emp in data.get("employees", []):
            if emp["id"] == employee_id:
                workflows = _ensure_employee_workflows(emp)
                wf = _normalize_workflow(body, fallback_name="\u65b0\u5e38\u7528\u4efb\u52a1")
                if wf.get("is_default"):
                    for item in workflows:
                        item["is_default"] = False
                workflows.append(wf)
                _save_employees_index(data)
                _employee_profile_path(employee_id).write_text(_build_profile_md(emp), encoding="utf-8")
                return {"ok": True, "workflow": wf, "workflows": workflows}
        raise HTTPException(status_code=404, detail="Employee not found")
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Create workflow failed: {e}")
        return {"ok": False, "error": str(e)}

@app.put("/api/employees/{employee_id}/workflows/{workflow_id}")
async def update_employee_workflow(employee_id: str, workflow_id: str, request: Request):
    try:
        body = await request.json()
        data = _load_employees_index()
        for emp in data.get("employees", []):
            if emp["id"] == employee_id:
                workflows = _ensure_employee_workflows(emp)
                for idx, item in enumerate(workflows):
                    if item.get("id") == workflow_id:
                        updated = dict(item)
                        for key in ["name", "description", "steps", "questions"]:
                            if key in body:
                                updated[key] = body.get(key) or ""
                        for key in ["enabled", "is_default", "default_inputs"]:
                            if key in body:
                                updated[key] = body.get(key)
                        updated["updated_at"] = _now_iso()
                        workflows[idx] = _normalize_workflow(updated)
                        if workflows[idx].get("is_default"):
                            for other in workflows:
                                if other.get("id") != workflow_id:
                                    other["is_default"] = False
                        if not any(wf.get("is_default") for wf in workflows):
                            workflows[0]["is_default"] = True
                        _save_employees_index(data)
                        _employee_profile_path(employee_id).write_text(_build_profile_md(emp), encoding="utf-8")
                        return {"ok": True, "workflow": workflows[idx], "workflows": workflows}
                raise HTTPException(status_code=404, detail="Workflow not found")
        raise HTTPException(status_code=404, detail="Employee not found")
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Update workflow failed: {e}")
        return {"ok": False, "error": str(e)}

@app.delete("/api/employees/{employee_id}/workflows/{workflow_id}")
async def delete_employee_workflow(employee_id: str, workflow_id: str):
    try:
        data = _load_employees_index()
        for emp in data.get("employees", []):
            if emp["id"] == employee_id:
                workflows = _ensure_employee_workflows(emp)
                if len(workflows) <= 1:
                    return {"ok": False, "error": "\u81f3\u5c11\u4fdd\u7559\u4e00\u4e2a\u5e38\u7528\u4efb\u52a1"}
                next_workflows = [wf for wf in workflows if wf.get("id") != workflow_id]
                if len(next_workflows) == len(workflows):
                    raise HTTPException(status_code=404, detail="Workflow not found")
                if not any(wf.get("is_default") for wf in next_workflows):
                    next_workflows[0]["is_default"] = True
                emp["workflows"] = next_workflows
                _save_employees_index(data)
                _employee_profile_path(employee_id).write_text(_build_profile_md(emp), encoding="utf-8")
                return {"ok": True, "workflows": next_workflows}
        raise HTTPException(status_code=404, detail="Employee not found")
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Delete workflow failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/workflows/capture")
async def capture_employee_workflow(employee_id: str, request: Request):
    try:
        body = await request.json()
        mode = (body.get("mode") or "experience").strip()
        workflow_id = (body.get("workflow_id") or "").strip()
        name = (body.get("name") or "\u8fd9\u6b21\u7684\u597d\u505a\u6cd5").strip()
        notes = (body.get("notes") or "").strip()
        result = (body.get("result") or "").strip()
        task_id = (body.get("task_id") or "").strip()
        data = _load_employees_index()
        for emp in data.get("employees", []):
            if emp["id"] != employee_id:
                continue
            workflows = _ensure_employee_workflows(emp)
            selected = next((wf for wf in workflows if wf.get("id") == workflow_id), None)
            notes_text = notes or "\u672a\u586b\u5199"
            result_text = result or "\u672a\u63d0\u4f9b"
            experience = (
                f"## {name}\n\n"
                f"### \u7528\u6237\u53cd\u9988/\u60f3\u4fdd\u7559\u7684\u505a\u6cd5\n{notes_text}\n\n"
                f"### \u672c\u6b21\u7ed3\u679c\u6458\u8981\n{result_text}\n"
            )
            _append_employee_experience_text(employee_id, experience, "\u7528\u6237\u9a8c\u6536\u540e\u6c89\u6dc0")

            workflow = None
            if mode == "new":
                workflow = _normalize_workflow({
                    "name": name,
                    "description": notes or (selected or {}).get("description", ""),
                    "questions": (selected or {}).get("questions", ""),
                    "steps": (selected or {}).get("steps", ""),
                    "enabled": True,
                    "is_default": False,
                })
                workflows.append(workflow)
            elif mode == "update" and selected:
                selected["description"] = notes or selected.get("description", "")
                selected["updated_at"] = _now_iso()
                workflow = selected

            task = None
            if task_id:
                task = _update_employee_task(
                    employee_id,
                    task_id,
                    status="done",
                    completed_at=_now_iso(),
                    result_summary=result,
                )

            _save_employees_index(data)
            _employee_profile_path(employee_id).write_text(_build_profile_md(emp), encoding="utf-8")
            return {"ok": True, "mode": mode, "workflow": workflow, "workflows": workflows, "task": task}
        raise HTTPException(status_code=404, detail="Employee not found")
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Capture workflow failed: {e}")
        return {"ok": False, "error": str(e)}

@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: str):
    try:
        data = _load_employees_index()
        employees = data.get("employees", [])
        data["employees"] = [e for e in employees if e["id"] != employee_id]
        if len(data["employees"]) == len(employees):
            raise HTTPException(status_code=404, detail="Employee not found")
        _save_employees_index(data)
        emp_dir = _employee_dir(employee_id)
        if emp_dir.exists():
            import shutil
            shutil.rmtree(str(emp_dir))
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Delete employee failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/experience")
async def append_employee_experience(employee_id: str, request: Request):
    try:
        body = await request.json()
        exp_text = (body.get("experience") or "").strip()
        if not exp_text:
            return {"ok": False, "error": "经验内容为空"}
        _append_employee_experience_text(employee_id, exp_text)
        return {"ok": True}
    except Exception as e:
        log_msg("WARN", f"Append experience failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/trigger")
async def trigger_employee(employee_id: str, request: Request):
    try:
        body = await request.json()
        message = body.get("message", "")
        workflow_id = (body.get("workflow_id") or "").strip()
        data = _load_employees_index()
        emp = next((e for e in data.get("employees", []) if e["id"] == employee_id), None)
        if not emp:
            return {"ok": False, "error": "Employee not found"}
        workflows = _ensure_employee_workflows(emp)
        workflow = next((wf for wf in workflows if wf.get("id") == workflow_id), None)
        if workflow is None:
            workflow = next((wf for wf in workflows if wf.get("is_default")), workflows[0] if workflows else None)
        task_text = (message or "\u5f00\u59cb\u51c6\u5907\u8fd9\u4e2a\u5e38\u7528\u4efb\u52a1").strip()
        session_id = emp.get("session_id") or employee_id
        task = _create_employee_task(employee_id, workflow, session_id, task_text, "planning")
        prompt = (
            f"{task_text}\n\n"
            f"\u672c\u6b21\u4efb\u52a1\u8bb0\u5f55\uff1a{task.get('id')}\n\n"
            f"{_workflow_summary_for_prompt(workflow)}\n\n"
            "\u8bf7\u4e0d\u8981\u7acb\u523b\u5f00\u59cb\u6700\u7ec8\u6267\u884c\u3002"
            "\u5148\u50cf\u4e00\u4f4d\u9760\u8c31\u5458\u5de5\u4e00\u6837\uff0c\u5c3d\u91cf\u95ee\u6e05\u695a\u5173\u952e\u95ee\u9898\uff1b"
            "\u5982\u679c\u4fe1\u606f\u5df2\u7ecf\u8db3\u591f\uff0c\u8bf7\u5148\u7ed9\u51fa\u4e00\u4efd\u8be6\u7ec6\u3001\u5168\u9762\u7684\u672c\u6b21\u5de5\u4f5c\u8ba1\u5212\u3002"
            "\u8ba1\u5212\u9700\u5305\u542b\uff1a\u4f60\u7406\u89e3\u7684\u76ee\u6807\u3001\u8fd8\u9700\u8981\u7528\u6237\u8865\u5145\u7684\u4fe1\u606f\u3001"
            "\u51c6\u5907\u91c7\u7528\u7684\u6b65\u9aa4\u3001\u4e2d\u9014\u9700\u8981\u786e\u8ba4\u7684\u8282\u70b9\u3001\u6700\u7ec8\u8f93\u51fa\u4ec0\u4e48\u3002"
            "\u6700\u540e\u8bf7\u660e\u786e\u7b49\u5f85\u7528\u6237\u786e\u8ba4\u540e\u518d\u5f00\u59cb\u5e72\u6d3b\u3002"
        )
        _save_employees_index(data)
        return {"ok": True, "employee_id": employee_id, "message": prompt,
                "workflow": workflow, "task": task, "session_id": session_id}
    except Exception as e:
        log_msg("WARN", f"Trigger employee failed: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/api/employees/{employee_id}/tasks")
async def list_employee_tasks(employee_id: str, limit: int = 12):
    try:
        data = _load_employees_index()
        emp = next((e for e in data.get("employees", []) if e["id"] == employee_id), None)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")
        limit = max(1, min(int(limit or 12), 50))
        return {"ok": True, "tasks": _latest_employee_tasks(employee_id, limit)}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"List employee tasks failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/tasks/{task_id}/confirm")
async def confirm_employee_task(employee_id: str, task_id: str, request: Request):
    try:
        data = _load_employees_index()
        emp = next((e for e in data.get("employees", []) if e["id"] == employee_id), None)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")
        task = _find_employee_task(employee_id, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        body = await request.json()
        note = (body.get("note") or "").strip()
        now = _now_iso()
        task = _update_employee_task(
            employee_id,
            task_id,
            status="running",
            plan_confirmed_at=now,
            user_confirm_note=note,
        )
        note_text = f"\n\u7528\u6237\u8865\u5145\u8bf4\u660e\uff1a{note}\n" if note else ""
        prompt = (
            f"\u7528\u6237\u5df2\u786e\u8ba4\u4efb\u52a1 {task_id} \u7684\u5de5\u4f5c\u8ba1\u5212\u3002"
            f"{note_text}"
            "\u73b0\u5728\u8bf7\u6309\u521a\u624d\u786e\u8ba4\u7684\u8ba1\u5212\u5f00\u59cb\u771f\u6b63\u6267\u884c\u3002"
            "\u6267\u884c\u4e2d\u5982\u679c\u9047\u5230\u4f1a\u5f71\u54cd\u7ed3\u679c\u7684\u5173\u952e\u95ee\u9898\uff0c\u53ef\u4ee5\u6682\u505c\u5e76\u8be2\u95ee\u7528\u6237\uff1b"
            "\u5982\u679c\u4fe1\u606f\u8db3\u591f\uff0c\u8bf7\u76f4\u63a5\u5b8c\u6210\u4efb\u52a1\u5e76\u7ed9\u51fa\u6e05\u6670\u7ed3\u679c\u3002"
            "\u5b8c\u6210\u65f6\u8bf7\u5728\u7ed3\u5c3e\u7528\u201c\u4efb\u52a1\u7ed3\u679c\u201d\u548c\u201c\u53ef\u6c89\u6dc0\u7ecf\u9a8c\u201d\u4e24\u90e8\u5206\u7b80\u8981\u603b\u7ed3\u3002"
        )
        return {"ok": True, "task": task, "message": prompt, "session_id": emp.get("session_id") or employee_id}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Confirm employee task failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/tasks/{task_id}/complete")
async def complete_employee_task(employee_id: str, task_id: str, request: Request):
    try:
        body = await request.json()
        result_summary = (body.get("result_summary") or "").strip()
        task = _update_employee_task(
            employee_id,
            task_id,
            status="done",
            completed_at=_now_iso(),
            result_summary=result_summary,
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"ok": True, "task": task}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Complete employee task failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/knowledge")
async def upload_knowledge(employee_id: str, file: UploadFile = File(...)):
    """Upload learning materials for an employee. Saved to knowledge/source/ folder."""
    try:
        data = _load_employees_index()
        emp = next((e for e in data.get("employees", []) if e["id"] == employee_id), None)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")
        source_dir = _employee_dir(employee_id) / "knowledge" / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(file.filename).name
        filepath = source_dir / safe_name
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        return {"ok": True, "filename": safe_name, "size": len(content)}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Upload knowledge failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/learn")
async def start_learning(employee_id: str, request: Request):
    """Start a learning session: AI reads files in knowledge/source/ and distills into knowledge.md."""
    try:
        body = await request.json()
        depth = (body.get("depth") or "deep").strip()
        files_param = body.get("files") or []
        data = _load_employees_index()
        emp = next((e for e in data.get("employees", []) if e["id"] == employee_id), None)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")
        source_dir = _employee_dir(employee_id) / "knowledge" / "source"
        kn_path = _employee_dir(employee_id) / "knowledge.md"
        if not source_dir.exists() or not any(source_dir.iterdir()):
            return {"ok": False, "error": "没有可学习的文件，请先上传资料"}
        # Build learning prompt
        depth_map = {
            "quick": "快速浏览（5%），只看标题和摘要",
            "extract": "提取要点（20%），提取关键信息",
            "deep": "深度学习（50%），理解核心概念和逻辑",
            "full": "全面学习（100%），完整掌握所有细节",
        }
        depth_instruction = depth_map.get(depth, depth_map["deep"])
        files_list = "\n".join(f"- {f.name}" for f in source_dir.iterdir() if f.is_file())
        learning_prompt = (
            f"你需要学习以下文件中的知识，学习深度：{depth_instruction}。\n\n"
            f"可用文件：\n{files_list}\n\n"
            f"请逐一阅读这些文件，提取关键知识，然后将学习成果整理写入 {kn_path} 文件。\n"
            f"学习成果要结构化：包含核心概念、关键方法、重要结论。\n"
            f"学习完成后，请在回复末尾用 📝 经验： 标记总结本次学习的关键收获。"
        )
        return {"ok": True, "employee_id": employee_id, "message": learning_prompt,
                "session_id": emp.get("session_id") or employee_id}
    except HTTPException:
        raise
    except Exception as e:
        log_msg("WARN", f"Start learning failed: {e}")
        return {"ok": False, "error": str(e)}

@app.post("/api/employees/{employee_id}/generate-workflow")
async def generate_workflow(employee_id: str):
    """Generate work steps (workflow) from employee profile using AI."""
    try:
        data = _load_employees_index()
        emp = next((e for e in data.get("employees", []) if e["id"] == employee_id), None)
        if not emp:
            raise HTTPException(status_code=404, detail="Employee not found")
        profile_md = _build_profile_md(emp)
        prompt = (
            "根据以下员工档案，生成详细的工作流程步骤。\n\n"
            f"{profile_md}\n\n"
            "请分析这个员工的角色、工作目标和内容，输出一个结构化的步骤列表。\n"
            "每个步骤应该是具体可执行的，包含：步骤序号、步骤名称、具体操作描述。\n"
            "输出格式：\n"
            "1. 步骤名称：操作描述\n"
            "2. 步骤名称：操作描述\n"
            "..."
        )
        return {"ok": True, "employee_id": employee_id, "message": prompt,
                "session_id": emp.get("session_id") or employee_id}
    except Exception as e:
        log_msg("WARN", f"Generate workflow failed: {e}")
        return {"ok": False, "error": str(e)}

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
    _prewarm_session_agent(session_id, reason="new-session")
    return {"session_id": session_id}

@app.get("/api/main-session")
async def get_main_session():
    """Return the remembered main-chat session, falling back to latest non-employee chat."""
    session_id = _get_main_session_id()
    if session_id:
        _prewarm_session_agent(session_id, reason="main-session")
    return {"session_id": session_id}

@app.post("/api/main-session")
async def set_main_session(request: Request):
    data = await request.json()
    session_id = str(data.get("session_id") or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    _ensure_session_record(session_id)
    _set_main_session_id(session_id)
    _prewarm_session_agent(session_id, reason="set-main-session")
    return {"ok": True, "session_id": session_id}

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
async def get_history(session_id: str, limit: int = DISPLAY_HISTORY_LIMIT):
    db_row = None
    try:
        db_row = session_db.get_session(session_id)
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Failed to inspect DB session: {e}")

    with session_lock:
        s = sessions.get(session_id)

    if not s and not db_row:
        raise HTTPException(status_code=404, detail="Session not found")

    display_history = _load_display_history_from_db(session_id, limit=limit)
    if not display_history:
        display_history = (s or {}).get("history") or []

    with session_lock:
        if session_id not in sessions:
            sessions[session_id] = _empty_session()
        if db_row:
            sessions[session_id]["created_at"] = datetime.fromtimestamp(float(db_row.get("started_at") or time.time()))
            sessions[session_id]["title"] = db_row.get("title") or _default_title_from_history(display_history)

    return {"history": _history_for_frontend(display_history)}

@app.get("/api/session/{session_id}/status")
async def get_session_status(session_id: str):
    try:
        session_id = _validate_session_id(session_id)
    except HTTPException:
        raise
    acquired = session_lock.acquire(timeout=SESSION_LOCK_UI_TIMEOUT)
    if not acquired:
        log_msg("WARN", f"[{session_id[:12]}] Status lock busy; reporting stopping")
        return {"ok": True, "session_id": session_id, "running": False, "stopping": True, "lock_busy": True}
    try:
        session = sessions.get(session_id)
        thread = (session or {}).get("agent_thread")
        interrupting = bool((session or {}).get("interrupt_requested"))
        running = (bool((session or {}).get("running")) or bool(thread and thread.is_alive())) and not interrupting
    finally:
        session_lock.release()
    return {"ok": True, "session_id": session_id, "running": running, "stopping": interrupting}

@app.post("/api/session/{session_id}/interrupt")
async def interrupt_session(session_id: str):
    acquired = session_lock.acquire(timeout=SESSION_LOCK_UI_TIMEOUT)
    if not acquired:
        log_msg("WARN", f"[{session_id[:12]}] Interrupt lock busy")
        return {"ok": True, "status": "interrupting", "lock_busy": True}
    try:
        session = sessions.get(session_id)
        agent = (session or {}).get("agent")
        thread = (session or {}).get("agent_thread")
        running = bool((session or {}).get("running")) or bool(thread and thread.is_alive())
        if session and running:
            session["interrupt_requested"] = True
            session["running"] = False
            session["agent_thread"] = None
            session["agent"] = None
            session["run_id"] = int(session.get("run_id") or 0) + 1
    finally:
        session_lock.release()

    if not session or not agent:
        return {"ok": False, "status": "idle"}
    if hasattr(agent, "interrupt"):
        try:
            agent.interrupt()
            log_msg("INFO", f"[{session_id[:12]}] Interrupt requested")
            _emit_session_event(session_id, {"type": "status", "text": "interrupting"})
            return {"ok": True, "status": "interrupted" if running else "idle"}
        except Exception as e:
            log_msg("WARN", f"[{session_id[:12]}] Interrupt signal failed after local detach: {e}")
            return {"ok": True, "status": "detached"}
    log_msg("INFO", f"[{session_id[:12]}] Interrupt detached unsupported agent")
    _emit_session_event(session_id, {"type": "status", "text": "interrupting"})
    return {"ok": True, "status": "detached"}

@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    with session_lock:
        if session_id in sessions:
            del sessions[session_id]
    try:
        state = _load_desktop_state()
        if state.get("main_session_id") == session_id:
            state.pop("main_session_id", None)
            state.pop("main_session_updated_at", None)
            _save_desktop_state(state)
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] Main session state cleanup failed: {e}")
    try:
        session_db.delete_session(session_id)
    except Exception as e:
        log_msg("WARN", f"[{session_id[:12]}] DB delete failed: {e}")
    return {"ok": True}

@app.post("/api/upload/{session_id}")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    session_dir = get_session_dir(session_id) / "uploads"
    session_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename or "upload.bin").name or "upload.bin"
    filepath = (session_dir / safe_name).resolve()
    try:
        filepath.relative_to(session_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload path")

    content = await file.read()
    max_bytes = 100 * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")
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
    filepath = _session_file_path(session_id, filename)
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

# ── Console server integration ────────────────────────────────────────
CONSOLE_BASE_URL = os.environ.get("HERMES_CONSOLE_URL", "https://139.196.176.26")
_httpx_verify = os.environ.get("HERMES_CONSOLE_VERIFY_SSL", "0") not in ("0", "false", "no")


@app.get("/api/skills/console-square")
async def get_console_square_skills():
    """Fetch skill list from the Hermes Console server."""
    try:
        import httpx
        resp = httpx.get(f"{CONSOLE_BASE_URL}/api/skills/square", timeout=10, verify=_httpx_verify)
        if resp.status_code == 200:
            skills = resp.json()
            return {"skills": skills, "source": "console"}
    except Exception as e:
        log_msg("WARN", f"Console skills fetch failed: {e}")
    return {"skills": [], "source": "console", "error": "unavailable"}


@app.post("/api/skills/console-install/{skill_id}")
async def install_console_skill(skill_id: int, request: Request):
    """Download a skill ZIP from the Console server and install it locally."""
    import shutil, zipfile as _zipfile, tempfile
    try:
        body = await request.json()
        skill_name = body.get("name", str(skill_id))
    except Exception:
        skill_name = str(skill_id)

    # 1. Download from console
    try:
        import httpx
        resp = httpx.get(f"{CONSOLE_BASE_URL}/api/skills/{skill_id}/download", timeout=60, verify=_httpx_verify)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Skill download failed")
        zip_bytes = resp.content
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Download error: {e}")

    # 2. Extract to skills/{skill_name}/ directory
    skill_dir = SKILLS_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            zf.extractall(str(skill_dir))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extract error: {e}")

    log_msg("INFO", f"Installed skill from console: {skill_name} (id={skill_id}) to {skill_dir}")
    return {"ok": True, "name": skill_name, "path": str(skill_dir)}


@app.get("/api/skills/featured")
async def get_featured_skills():
    """Get featured/popular skills from Hermes Console server."""
    # First try console server
    try:
        import httpx
        log_msg("INFO", f"Fetching skills from console: {CONSOLE_BASE_URL}")
        resp = httpx.get(f"{CONSOLE_BASE_URL}/api/skills/square", timeout=8, verify=_httpx_verify)
        log_msg("INFO", f"Console skills response: {resp.status_code}")
        if resp.status_code == 200:
            skills = resp.json()
            log_msg("INFO", f"Console skills count: {len(skills) if isinstance(skills, list) else 'not list'}")
            if isinstance(skills, list) and skills:
                result = []
                for s in skills:
                    result.append({
                        "name": s.get("name", ""),
                        "description": s.get("description", ""),
                        "source": "console",
                        "identifier": str(s.get("id", "")),
                        "tags": [s.get("category", ""), s.get("version", "")],
                        "install_cmd": "",
                    })
                return {"skills": result, "count": len(result), "source": "console"}
    except Exception as e:
        log_msg("WARN", f"Console skills fetch failed: {e}")
    # Fallback: try uskill.cn
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
    if not _ws_request_is_allowed(websocket):
        await websocket.close(code=1008)
        return
    try:
        session_id = _validate_session_id(session_id)
    except HTTPException:
        await websocket.close(code=1008)
        return
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
    stream_state = {
        "chunks": [],
        "guard_required": False,
        "tool_seen": False,
        "buffered_events": [],
    }
    client_connected = True

    async def safe_send(payload: dict) -> bool:
        nonlocal client_connected
        if not client_connected:
            return False
        try:
            await websocket.send_json(payload)
            return True
        except Exception:
            client_connected = False
            return False

    def emit_event(event: dict):
        """Called from agent thread; schedule push to WS."""
        try:
            if event.get("type") == "tool":
                stream_state["tool_seen"] = True
                buffered = list(stream_state.get("buffered_events") or [])
                stream_state["buffered_events"] = []
                for buffered_event in buffered:
                    main_loop.call_soon_threadsafe(msg_queue.put_nowait, buffered_event)
            if event.get("type") == "delta" and event.get("text"):
                stream_state["chunks"].append(str(event.get("text") or ""))
                if stream_state.get("guard_required") and not stream_state.get("tool_seen"):
                    stream_state.setdefault("buffered_events", []).append(event)
                    return
        except Exception:
            pass
        main_loop.call_soon_threadsafe(
            msg_queue.put_nowait, event,
        )

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "").strip()
            stream_state["chunks"] = []
            stream_state["buffered_events"] = []
            stream_state["tool_seen"] = False
            stream_state["guard_required"] = _requires_real_tool_action(message)

            if not message:
                await websocket.send_json({"type": "error", "text": "Empty message"})
                continue

            if message == "__ping__":
                await websocket.send_json({"type": "info", "text": "pong"})
                continue

            _mark_user_activity()

            # Get session and lazily create agent on first message
            with session_lock:
                if session_id not in sessions:
                    sessions[session_id] = _empty_session()
                s = sessions[session_id]
                if _looks_like_tool_dispute(message):
                    s["last_tool_dispute_at"] = time.time()
                s["callbacks"] = {"emit": emit_event}
                already_running = bool(s.get("running"))
            if already_running:
                await websocket.send_json({"type": "error", "text": "Session is already running"})
                continue
            if s["agent"] is None:
                try:
                    await websocket.send_json({"type": "status", "text": "Initializing agent..."})
                    prewarmed_agent = _wait_for_prewarmed_agent(session_id, timeout=8.0)
                    if prewarmed_agent is not None:
                        s["agent"] = prewarmed_agent
                        log_msg("INFO", f"Using prewarmed agent for {session_id[:12]}")
                    else:
                        log_msg("INFO", f"Creating agent for session {session_id[:12]}...")
                        _ensure_session_record(session_id)
                        s["agent"] = create_agent(session_id)
                        log_msg("INFO", f"Agent created for {session_id[:12]}")
                    _apply_employee_prompt_to_agent(s["agent"], session_id)
                except Exception as e:
                    log_msg("ERROR", f"Agent creation failed: {e}")
                    await websocket.send_json({"type": "error", "text": f"Failed to initialize agent: {e}"})
                    continue
            session = s

            # Always refresh employee prompt (profile may have been edited)
            emp = _find_employee_by_session(session_id)
            if emp and session["agent"]:
                _apply_employee_prompt_to_agent(session["agent"], session_id)

            # Check for session switch
            if message.startswith("/switch "):
                new_sid = message.split(" ", 1)[1].strip()
                try:
                    new_sid = _validate_session_id(new_sid)
                except HTTPException:
                    await websocket.send_json({"type": "error", "text": "Invalid session id"})
                    continue
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
                session["run_id"] = int(session.get("run_id") or 0) + 1
                session["interrupt_requested"] = False
                run_id = session["run_id"]
                persisted_user_history = list(session["history"])
            try:
                _replace_messages_preserving_timestamps(session_id, persisted_user_history)
            except Exception as e:
                log_msg("WARN", f"[{session_id[:12]}] Persist user message failed: {e}")
            history_prefix, agent_history = _prepare_agent_history_for_turn(conversation_history)
            log_msg("INFO", f"[{session_id[:12]}] User: {message[:60]}")
            log_msg("INFO", f"[{session_id[:12]}] History length: {len(conversation_history)} messages (agent replay: {len(agent_history)})")

            # Auto-title on first exchange
            user_count = len([m for m in session["history"] if m.get("role") == "user"])
            if not session.get("title") and user_count == 1:
                title = message[:30] + ("..." if len(message) > 30 else "")
                session["title"] = title

            # Signal frontend that agent is thinking
            await safe_send({"type": "status", "text": "thinking"})

            # Run agent in background thread
            result_holder = {}
            error_holder = {}

            def run_agent():
                try:
                    r = session["agent"].run_conversation(
                        user_message=message,
                        conversation_history=agent_history,
                        task_id=session_id,
                    )
                    used_real_tool = _result_used_real_tool(r)
                    if _requires_real_tool_action(message) and not used_real_tool:
                        log_msg(
                            "WARN",
                            f"[{session_id[:12]}] Blocked text-only execution claim for tool-required request",
                        )
                        stream_state["chunks"] = []
                        stream_state["buffered_events"] = []
                        with session_lock:
                            current = sessions.get(session_id)
                            if current is session:
                                current["last_fake_execution_blocked"] = True
                        r = {
                            "messages": persisted_user_history + [
                                {"role": "assistant", "content": _fake_execution_guard_text()}
                            ],
                            "final_response": _fake_execution_guard_text(),
                            "api_calls": (r or {}).get("api_calls", 1) if isinstance(r, dict) else 1,
                            "__desktop_blocked_fake_execution": True,
                            "__desktop_discard_stream": True,
                        }
                    elif used_real_tool:
                        with session_lock:
                            current = sessions.get(session_id)
                            if current is session:
                                current["last_fake_execution_blocked"] = False
                    if isinstance(r, dict):
                        r = _safe_result_for_desktop(r, persisted_user_history)
                    with session_lock:
                        current = sessions.get(session_id)
                        stale_or_cancelled = (
                            current is not session
                            or int(current.get("run_id") or 0) != run_id
                            or bool(current.get("interrupt_requested"))
                        )
                    if stale_or_cancelled:
                        if isinstance(r, dict):
                            r["interrupted"] = True
                        result_holder["result"] = r
                        return
                    try:
                        _finalize_agent_turn(session_id, session, r, message, stream_state)
                    except Exception as finalize_error:
                        log_msg("WARN", f"[{session_id[:12]}] Finalize finished turn failed: {finalize_error}")
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
                    with session_lock:
                        current = sessions.get(session_id)
                        if current is session:
                            current["running"] = False
                            current["agent_thread"] = None
                            current["interrupt_requested"] = False
                    main_loop.call_soon_threadsafe(msg_queue.put_nowait, None)

            agent_thread = threading.Thread(target=run_agent, daemon=True)
            with session_lock:
                session["running"] = True
                session["agent_thread"] = agent_thread
            agent_thread.start()

            # Drain queue while agent runs (streaming output)
            cancelled_by_interrupt = False
            while agent_thread.is_alive() or not msg_queue.empty():
                with session_lock:
                    current = sessions.get(session_id)
                    cancelled_by_interrupt = (
                        current is not session
                        or int((current or {}).get("run_id") or 0) != run_id
                        or bool((current or {}).get("interrupt_requested"))
                        or (current or {}).get("agent_thread") is not agent_thread
                    )
                if cancelled_by_interrupt:
                    break
                try:
                    msg = await asyncio.wait_for(msg_queue.get(), timeout=0.05)
                    if msg is None:  # Sentinel — agent finished
                        break
                    await safe_send(msg)
                except asyncio.TimeoutError:
                    continue

            agent_thread.join(timeout=INTERRUPT_JOIN_TIMEOUT if cancelled_by_interrupt else 30)
            with session_lock:
                if not agent_thread.is_alive():
                    session["running"] = False
                    session["agent_thread"] = None
                    session["interrupt_requested"] = False
            if cancelled_by_interrupt and "result" not in result_holder and "error" not in error_holder:
                result_holder["result"] = {
                    "messages": persisted_user_history,
                    "final_response": "",
                    "interrupted": True,
                }

            # Process result
            if "result" in result_holder:
                result = result_holder["result"]
                full_messages = result.get("messages", [])
                interrupted_unfinalized = bool(result.get("interrupted")) and not result.get("__desktop_finalized")
                if full_messages and not result.get("__desktop_finalized") and not interrupted_unfinalized:
                    with session_lock:
                        session["history"] = full_messages

                final_text = result.get("__desktop_final_text", result.get("final_response", ""))
                if not result.get("__desktop_finalized"):
                    log_msg("INFO", f"[{session_id[:12]}] Agent response complete, {len(final_text)} chars")
                    _api_calls = result.get("api_calls", 0)
                    _msg_count = len(full_messages) if full_messages else 0
                    log_msg("INFO", f"[{session_id[:12]}] Turn stats: api_calls={_api_calls}, total_messages={_msg_count}")
                if not final_text and full_messages:
                    last = full_messages[-1]
                    if last.get("role") == "assistant":
                        final_text = last.get("content", "")
                if result.get("interrupted"):
                    await safe_send({"type": "info", "text": "Interrupted"})
                if interrupted_unfinalized:
                    final_text = ""
                streamed_text = "" if result.get("__desktop_discard_stream") else "".join(stream_state.get("chunks") or [])
                merged_text = final_text if result.get("__desktop_finalized") else _merge_streamed_and_final_text(streamed_text, final_text)
                if merged_text and not result.get("__desktop_finalized") and not interrupted_unfinalized:
                    final_text = merged_text
                    if full_messages:
                        for idx in range(len(full_messages) - 1, -1, -1):
                            if full_messages[idx].get("role") == "assistant":
                                full_messages[idx] = {**full_messages[idx], "content": final_text}
                                break
                        else:
                            full_messages.append({"role": "assistant", "content": final_text})
                        with session_lock:
                            session["history"] = full_messages
                        try:
                            _replace_messages_preserving_timestamps(session_id, full_messages)
                        except Exception as e:
                            log_msg("WARN", f"[{session_id[:12]}] Replace merged history failed: {e}")

                await safe_send({
                    "type": "done",
                    "text": final_text or "(no response)",
                    "interrupted": bool(result.get("interrupted")),
                })
                if final_text and not result.get("interrupted"):
                    try:
                        _notify_session_turn_finished(session_id, final_text)
                    except Exception as e:
                        log_msg("WARN", f"[{session_id[:12]}] Bubble turn notification failed: {e}")
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
                await safe_send({
                    "type": "error",
                    "text": f"Agent error: {error_holder['error']}",
                })
            try:
                latest_history = _load_history_from_db(session_id)
                if latest_history:
                    with session_lock:
                        session["history"] = latest_history
                await safe_send({"type": "session.updated", "session_id": session_id})
            except Exception:
                pass

    except WebSocketDisconnect as e:
        log_msg("INFO", f"WebSocket disconnect for {session_id[:12]} code={getattr(e, 'code', None)}")
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
                thread = session.get("agent_thread")
                if not thread or not thread.is_alive():
                    session["running"] = False
                    session["agent_thread"] = None
                    session["interrupt_requested"] = False
        active_connections = max(0, active_connections - 1)
        log_msg("INFO", f"Client disconnected (active: {active_connections})")
        if active_connections == 0:
            schedule_shutdown()

# --- Startup ---

if __name__ == "__main__":
    import argparse
    _ap = argparse.ArgumentParser()
    _ap.add_argument("--bubble-only", action="store_true", help="Start with floating bubble only (no main window)")
    _ap.add_argument("--serve-only", action="store_true", help="Start only the local Hermes server; an external launcher will open the UI")
    _ap.add_argument("--browser", action="store_true", help="Open Hermes in the system browser instead of a native pywebview window")
    _ap.add_argument("--app-window", action="store_true", help="Open Hermes in a browser app window without the normal browser chrome")
    _ap.add_argument("--native", action="store_true", help="Force the native pywebview window")
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
    SERVE_ONLY = _args.serve_only
    APP_WINDOW_MODE = (_args.app_window or is_truthy_value(os.environ.get("HERMES_DESKTOP_APP_WINDOW"))) and not _args.native
    BROWSER_MODE = (_args.browser or APP_WINDOW_MODE or is_truthy_value(os.environ.get("HERMES_DESKTOP_BROWSER"))) and not _args.native
    if (BROWSER_MODE or SERVE_ONLY) and sys.platform != "win32":
        register_browser_bubble_fallbacks()

    def _open_web_app_window(target_url: str) -> bool:
        """Open the desktop UI as a standalone app-like browser window."""
        import subprocess

        candidates: list[Path] = []
        for env_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env_name)
            if not base:
                continue
            root = Path(base)
            candidates.extend([
                root / "Microsoft" / "Edge" / "Application" / "msedge.exe",
                root / "Google" / "Chrome" / "Application" / "chrome.exe",
            ])

        for exe in candidates:
            if not exe.exists():
                continue
            try:
                subprocess.Popen(
                    [str(exe), f"--app={target_url}", "--new-window"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x00000008 if sys.platform == "win32" else 0,
                )
                log_msg("INFO", f"Opened Hermes app window with {exe}")
                return True
            except Exception as e:
                log_msg("WARN", f"Failed to open app window with {exe}: {e}")
        return False

    def _open_browser_ui(target_url: str):
        if APP_WINDOW_MODE and _open_web_app_window(target_url):
            return
        try:
            import webbrowser
            log_msg("INFO", f"Opening Hermes in browser: {target_url}")
            webbrowser.open(target_url)
        except Exception as e:
            log_msg("ERROR", f"Failed to open browser: {type(e).__name__}: {e}")
            log_msg("ERROR", traceback.format_exc())

    def _preferred_desktop_python() -> str:
        candidates = [
            HERMES_HOME / "runtime" / "python311" / "python.exe",
            HERMES_HOME / "hermes-agent" / "venv" / "Scripts" / "python.exe",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return sys.executable

    def _call_existing_desktop(action: str = "restore") -> bool:
        try:
            import urllib.request as _urlreq
            import json as _json
            _urlreq.urlopen(f"{url}/api/bubble/status", timeout=0.7).read()
            payload = _json.dumps({"action": action}).encode("utf-8")
            req = _urlreq.Request(
                f"{url}/api/bubble/update",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            _urlreq.urlopen(req, timeout=0.7).read()
            return True
        except Exception:
            return False

    if not BUBBLE_ONLY and _call_existing_desktop("restore"):
        if BROWSER_MODE:
            _open_browser_ui(url)
        log_msg("INFO", "Existing Hermes Desktop instance found; restored it and exiting this duplicate launcher")
        os._exit(0)

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
    try:
        startup_main_session = _get_main_session_id()
        if startup_main_session:
            _prewarm_session_agent(startup_main_session, reason="startup-main-session")
    except Exception as e:
        log_msg("WARN", f"Startup main-session prewarm skipped: {e}")

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

    class _BLENDFUNCTION(_ct.Structure):
        _fields_ = [
            ("BlendOp", _wt.BYTE),
            ("BlendFlags", _wt.BYTE),
            ("SourceConstantAlpha", _wt.BYTE),
            ("AlphaFormat", _wt.BYTE),
        ]

    class _BITMAPINFOHEADER(_ct.Structure):
        _fields_ = [
            ("biSize", _wt.DWORD),
            ("biWidth", _ct.c_long),
            ("biHeight", _ct.c_long),
            ("biPlanes", _wt.WORD),
            ("biBitCount", _wt.WORD),
            ("biCompression", _wt.DWORD),
            ("biSizeImage", _wt.DWORD),
            ("biXPelsPerMeter", _ct.c_long),
            ("biYPelsPerMeter", _ct.c_long),
            ("biClrUsed", _wt.DWORD),
            ("biClrImportant", _wt.DWORD),
        ]

    class _RGBQUAD(_ct.Structure):
        _fields_ = [
            ("rgbBlue", _wt.BYTE),
            ("rgbGreen", _wt.BYTE),
            ("rgbRed", _wt.BYTE),
            ("rgbReserved", _wt.BYTE),
        ]

    class _BITMAPINFO(_ct.Structure):
        _fields_ = [
            ("bmiHeader", _BITMAPINFOHEADER),
            ("bmiColors", _RGBQUAD * 1),
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
        _user32.GetDC.argtypes = [_wt.HWND]
        _user32.GetDC.restype = _wt.HDC
        _user32.ReleaseDC.argtypes = [_wt.HWND, _wt.HDC]
        _user32.ReleaseDC.restype = _ct.c_int
        _user32.GetClientRect.argtypes = [_wt.HWND, _ct.POINTER(_wt.RECT)]
        _user32.GetClientRect.restype = _wt.BOOL
        _user32.GetWindowRect.argtypes = [_wt.HWND, _ct.POINTER(_wt.RECT)]
        _user32.GetWindowRect.restype = _wt.BOOL
        _user32.FillRect.argtypes = [_wt.HDC, _ct.POINTER(_wt.RECT), _wt.HBRUSH]
        _user32.FillRect.restype = _ct.c_int
        _user32.FindWindowW.argtypes = [_wt.LPCWSTR, _wt.LPCWSTR]
        _user32.FindWindowW.restype = _wt.HWND
        _user32.EnumWindows.argtypes = [_ct.c_void_p, _wt.LPARAM]
        _user32.EnumWindows.restype = _wt.BOOL
        _user32.GetWindowTextLengthW.argtypes = [_wt.HWND]
        _user32.GetWindowTextLengthW.restype = _ct.c_int
        _user32.GetWindowTextW.argtypes = [_wt.HWND, _wt.LPWSTR, _ct.c_int]
        _user32.GetWindowTextW.restype = _ct.c_int
        _user32.IsWindow.argtypes = [_wt.HWND]
        _user32.IsWindow.restype = _wt.BOOL
        _user32.IsWindowVisible.argtypes = [_wt.HWND]
        _user32.IsWindowVisible.restype = _wt.BOOL
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
        _user32.DestroyWindow.argtypes = [_wt.HWND]
        _user32.DestroyWindow.restype = _wt.BOOL

        _gdi32.CreateEllipticRgn.argtypes = [_ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int]
        _gdi32.CreateEllipticRgn.restype = _wt.HRGN
        _gdi32.Ellipse.argtypes = [_wt.HDC, _ct.c_int, _ct.c_int, _ct.c_int, _ct.c_int]
        _gdi32.Ellipse.restype = _wt.BOOL
        _gdi32.CreateCompatibleDC.argtypes = [_wt.HDC]
        _gdi32.CreateCompatibleDC.restype = _wt.HDC
        _gdi32.CreateCompatibleBitmap.argtypes = [_wt.HDC, _ct.c_int, _ct.c_int]
        _gdi32.CreateCompatibleBitmap.restype = _wt.HBITMAP
        _gdi32.CreateDIBSection.argtypes = [
            _wt.HDC, _ct.POINTER(_BITMAPINFO), _wt.UINT,
            _ct.POINTER(_ct.c_void_p), _wt.HANDLE, _wt.DWORD,
        ]
        _gdi32.CreateDIBSection.restype = _wt.HBITMAP
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

    _EnumWindowsProc = _ct.WINFUNCTYPE(_wt.BOOL, _wt.HWND, _wt.LPARAM)

    def _find_hermes_main_window():
        """Find either the native window or the Edge/Chrome app window."""
        exact = _user32.FindWindowW(None, "Hermes Desktop")
        if exact and _user32.IsWindow(exact):
            return exact

        found = {"hwnd": None}

        @_EnumWindowsProc
        def _enum_proc(hwnd, _lparam):
            try:
                if not _user32.IsWindowVisible(hwnd):
                    return True
                length = _user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True
                buf = _ct.create_unicode_buffer(length + 1)
                _user32.GetWindowTextW(hwnd, buf, length + 1)
                title = (buf.value or "").strip()
                if "Hermes Desktop" in title:
                    found["hwnd"] = hwnd
                    return False
            except Exception:
                return True
            return True

        _user32.EnumWindows(_enum_proc, 0)
        return found["hwnd"]

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
    WM_LBUTTONDOWN = 0x0201
    WM_RBUTTONDOWN = 0x204
    WM_PAINT = 0x000F
    WM_DESTROY = 0x0002

    # GDI objects
    TRANSPARENT = 1
    SRCCOPY = 0x00CC0020
    BI_RGB = 0
    DIB_RGB_COLORS = 0
    ULW_ALPHA = 0x00000002
    AC_SRC_OVER = 0
    AC_SRC_ALPHA = 1
    RGB_FORMAT = lambda r, g, b: (r) | (g << 8) | (b << 16)
    COLOR_KEY = RGB_FORMAT(255, 0, 255)  # magenta as transparent

    BUBBLE_SIZE = 56
    NOTIFY_W = 286
    NOTIFY_H = 144

    # Shared state for the floating bubble
    _bubble_state = {
        "hwnd": None,
        "visible": False,
        "text": "",
        "main_hwnd": None,
        "ready_event": threading.Event(),
        "logo_hbitmap": None,  # HBITMAP of the bubble icon
        "notify_hwnd": None,
        "notify_hbitmap": None,
        "notify_timer": None,
        "notification": {},
        "notify_buttons": {},
        "unread": False,
    }

    def _premultiplied_bgra_to_hbitmap(raw: bytes, width: int, height: int):
        bmi = _BITMAPINFO()
        bmi.bmiHeader.biSize = _ct.sizeof(_BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height  # top-down DIB
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        bmi.bmiHeader.biSizeImage = width * height * 4

        bits = _ct.c_void_p()
        screen_dc = _user32.GetDC(None)
        if not screen_dc:
            return None
        try:
            hbitmap = _gdi32.CreateDIBSection(
                screen_dc, _ct.byref(bmi), DIB_RGB_COLORS, _ct.byref(bits), None, 0
            )
        finally:
            _user32.ReleaseDC(None, screen_dc)
        if not hbitmap or not bits.value:
            return None

        _ct.memmove(bits, raw, min(len(raw), width * height * 4))
        return hbitmap

    def _rgba_to_premultiplied_hbitmap(image):
        """Create a 32-bit premultiplied-alpha HBITMAP for UpdateLayeredWindow."""
        rgba = image.convert("RGBA")
        width, height = rgba.size
        raw = bytearray(width * height * 4)
        idx = 0
        for r, g, b, a in rgba.getdata():
            raw[idx] = (b * a) // 255
            raw[idx + 1] = (g * a) // 255
            raw[idx + 2] = (r * a) // 255
            raw[idx + 3] = a
            idx += 4
        return _premultiplied_bgra_to_hbitmap(bytes(raw), width, height)

    def _load_bubble_png(png_path):
        """Build a crisp pony bubble bitmap and load it as a premultiplied HBITMAP."""
        try:
            try:
                from PIL import Image as _PILImage
            except Exception as e:
                raw_path = STATIC_DIR / "bubble_icon_56.bgra"
                if raw_path.exists():
                    raw = raw_path.read_bytes()
                    hbitmap = _premultiplied_bgra_to_hbitmap(raw, BUBBLE_SIZE, BUBBLE_SIZE)
                    if hbitmap:
                        _bubble_state["logo_hbitmap"] = hbitmap
                        log_msg("WARN", f"Pillow unavailable; using bundled bubble bitmap: {e}")
                        return True
                log_msg("ERROR", f"Bubble icon load failed; Pillow unavailable: {e}")
                return False

            fallback_path = str(STATIC_DIR / "bubble_pony_idle.bmp")
            source_path = png_path if os.path.exists(png_path) else fallback_path
            if not os.path.exists(source_path):
                return False

            src = _PILImage.open(source_path).convert("RGBA")

            side = min(src.size)
            left = max(0, (src.width - side) // 2)
            top = max(0, (src.height - side) // 2)
            src = src.crop((left, top, left + side, top + side))

            # Work at 3x final size. Remove only the pale background connected
            # to the image border, keeping internal whites such as the eyes.
            hi_size = BUBBLE_SIZE * 3
            logo = src.resize((hi_size, hi_size), _PILImage.LANCZOS).convert("RGBA")
            rgb = logo.convert("RGB")
            hsv = logo.convert("HSV")
            bg_mask = _PILImage.new("L", (hi_size, hi_size), 0)
            bg_px = bg_mask.load()
            rgb_px = rgb.load()
            hsv_px = hsv.load()
            stack = []
            for x in range(hi_size):
                stack.append((x, 0))
                stack.append((x, hi_size - 1))
            for y in range(hi_size):
                stack.append((0, y))
                stack.append((hi_size - 1, y))
            while stack:
                x, y = stack.pop()
                if x < 0 or y < 0 or x >= hi_size or y >= hi_size or bg_px[x, y]:
                    continue
                r, g, b = rgb_px[x, y]
                _h, sat, val = hsv_px[x, y]
                if not ((sat < 34 and val > 188) or (r > 232 and g > 232 and b > 232)):
                    continue
                bg_px[x, y] = 255
                stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
            logo.putalpha(_PILImage.eval(bg_mask, lambda value: 0 if value else 255))

            final_rgba = logo.resize((BUBBLE_SIZE, BUBBLE_SIZE), _PILImage.LANCZOS).convert("RGBA")
            hbitmap = _rgba_to_premultiplied_hbitmap(final_rgba)
            if hbitmap:
                _bubble_state["logo_hbitmap"] = hbitmap
                return True
            return False
        except Exception as e:
            log_msg("ERROR", f"Bubble icon load failed: {type(e).__name__}: {e}")
            return False

    def _reload_bubble_logo():
        # Once loaded, the HBITMAP is good for the lifetime of the bubble.
        # Regenerating is expensive (PIL flood-fill) and unnecessary.
        if _bubble_state.get("logo_hbitmap"):
            return True
        try:
            bubble_png_path = str(STATIC_DIR / "bubble_icon.png")
            return _load_bubble_png(bubble_png_path)
        except Exception:
            return False

    _BubbleWndProcType = _ct.WINFUNCTYPE(
        _LRESULT, _wt.HWND, _wt.UINT, _wt.WPARAM, _wt.LPARAM,
    )

    def _update_bubble_layered(hwnd):
        """Refresh the floating bubble using per-pixel alpha."""
        logo_bmp = _bubble_state.get("logo_hbitmap")
        if not (hwnd and logo_bmp):
            return False

        rect = _wt.RECT()
        if not _user32.GetWindowRect(hwnd, _ct.byref(rect)):
            return False

        screen_dc = _user32.GetDC(None)
        if not screen_dc:
            return False
        mem_dc = _gdi32.CreateCompatibleDC(screen_dc)
        if not mem_dc:
            _user32.ReleaseDC(None, screen_dc)
            return False

        old_bmp = _gdi32.SelectObject(mem_dc, logo_bmp)
        pt_dst = _wt.POINT(rect.left, rect.top)
        size = _wt.SIZE(BUBBLE_SIZE, BUBBLE_SIZE)
        pt_src = _wt.POINT(0, 0)
        blend = _BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
        ok = _user32.UpdateLayeredWindow(
            hwnd, screen_dc, _ct.byref(pt_dst), _ct.byref(size),
            mem_dc, _ct.byref(pt_src), 0, _ct.byref(blend), ULW_ALPHA
        )

        _gdi32.SelectObject(mem_dc, old_bmp)
        _gdi32.DeleteDC(mem_dc)
        _user32.ReleaseDC(None, screen_dc)
        return bool(ok)

    def _draw_bubble(hwnd):
        """Validate paint requests; the bubble itself is drawn with alpha."""
        ps = _PAINTSTRUCT()
        hdc = _user32.BeginPaint(hwnd, _ct.byref(ps))
        if hdc:
            _user32.EndPaint(hwnd, _ct.byref(ps))
        _update_bubble_layered(hwnd)

    def _xy_from_lparam(lparam):
        x = lparam & 0xFFFF
        y = (lparam >> 16) & 0xFFFF
        if x >= 0x8000:
            x -= 0x10000
        if y >= 0x8000:
            y -= 0x10000
        return x, y

    def _point_in_rect(x, y, rect_tuple):
        if not rect_tuple:
            return False
        left, top, right, bottom = rect_tuple
        return left <= x <= right and top <= y <= bottom

    def _notify_font(size: int, bold: bool = False):
        from PIL import ImageFont as _PILImageFont
        font_names = ["msyhbd.ttc" if bold else "msyh.ttc", "simhei.ttf", "arial.ttf"]
        for name in font_names:
            path = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / name
            if path.exists():
                return _PILImageFont.truetype(str(path), size=size)
        return _PILImageFont.load_default()

    def _wrap_pil_text(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
        value = re.sub(r"\s+", " ", str(text or "")).strip()
        if not value:
            return []
        lines: list[str] = []
        current = ""
        for ch in value:
            trial = current + ch
            bbox = draw.textbbox((0, 0), trial, font=font)
            if bbox[2] - bbox[0] <= max_width or not current:
                current = trial
            else:
                lines.append(current)
                current = ch
                if len(lines) >= max_lines:
                    break
        if current and len(lines) < max_lines:
            lines.append(current)
        if lines and len(lines) == max_lines:
            original = "".join(lines)
            if len(original) < len(value):
                while lines[-1] and draw.textbbox((0, 0), lines[-1] + "...", font=font)[2] > max_width:
                    lines[-1] = lines[-1][:-1]
                lines[-1] = lines[-1].rstrip() + "..."
        return lines

    def _draw_centered_pil(draw, rect_tuple, label: str, font, fill):
        left, top, right, bottom = rect_tuple
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = left + ((right - left) - text_w) // 2 - bbox[0]
        y = top + ((bottom - top) - text_h) // 2 - bbox[1] - 1
        draw.text((x, y), label, font=font, fill=fill)

    def _render_notification_bitmap():
        """Render the notification card to a BMP and load it as HBITMAP."""
        try:
            from PIL import Image as _PILImage
            from PIL import ImageDraw as _PILImageDraw

            notice = dict(_bubble_state.get("notification") or {})
            sender = str(notice.get("sender") or "Hermes")[:18]
            title = str(notice.get("title") or "有新消息")[:24]
            message = str(notice.get("message") or "点我查看详情")
            ntype = str(notice.get("type") or "completed")

            bg = (255, 0, 255)
            img = _PILImage.new("RGB", (NOTIFY_W, NOTIFY_H), bg)
            draw = _PILImageDraw.Draw(img)
            shadow = (238, 222, 206)
            card = (255, 252, 247)
            border = (232, 132, 108) if ntype in {"needs_confirm", "needs_input"} else (229, 166, 102)
            text = (58, 45, 36)
            soft = (148, 119, 94)
            red = (211, 70, 56)

            draw.rounded_rectangle((8, 10, NOTIFY_W - 6, NOTIFY_H - 5), radius=12, fill=shadow)
            draw.rounded_rectangle((4, 4, NOTIFY_W - 10, NOTIFY_H - 10), radius=12, fill=card, outline=border, width=1)

            title_font = _notify_font(16, True)
            sender_font = _notify_font(12, False)
            msg_font = _notify_font(13, False)
            btn_font = _notify_font(13, True)

            draw.ellipse((16, 14, 40, 38), fill=(255, 234, 172), outline=border, width=1)
            try:
                avatar_src = _PILImage.open(STATIC_DIR / "bubble_icon.png").convert("RGBA")
                side = min(avatar_src.size)
                avatar_src = avatar_src.crop(((avatar_src.width - side) // 2, (avatar_src.height - side) // 2, (avatar_src.width + side) // 2, (avatar_src.height + side) // 2))
                avatar = avatar_src.resize((22, 22), _PILImage.LANCZOS)
                mask = _PILImage.new("L", (22, 22), 0)
                mask_draw = _PILImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, 21, 21), fill=255)
                img.paste(avatar.convert("RGB"), (17, 15), mask)
            except Exception:
                draw.text((24, 16), "H", font=_notify_font(14, True), fill=red)
            draw.text((48, 12), sender, font=sender_font, fill=soft)
            draw.text((48, 31), title, font=title_font, fill=text)

            lines = _wrap_pil_text(draw, message, msg_font, NOTIFY_W - 36, 2)
            y = 58
            for line in lines:
                draw.text((18, y), line, font=msg_font, fill=text)
                y += 21

            button_w = 74
            button_h = 28
            gap = 12
            right = NOTIFY_W - 22
            primary = (right - button_w, NOTIFY_H - 40, right, NOTIFY_H - 40 + button_h)
            secondary = (primary[0] - gap - button_w, primary[1], primary[0] - gap, primary[3])
            close_rect = (NOTIFY_W - 30, 11, NOTIFY_W - 13, 28)
            _bubble_state["notify_buttons"] = {
                "primary": primary,
                "secondary": secondary,
                "close": close_rect,
            }
            draw.rounded_rectangle(secondary, radius=12, fill=(252, 242, 233), outline=(232, 203, 180), width=1)
            _draw_centered_pil(draw, secondary, "稍后", btn_font, soft)
            draw.rounded_rectangle(primary, radius=12, fill=red)
            _draw_centered_pil(draw, primary, "查看", btn_font, (255, 255, 255))
            _draw_centered_pil(draw, close_rect, "×", _notify_font(15, True), (170, 133, 104))

            temp_bmp = str(STATIC_DIR / "_bubble_notify_temp.bmp")
            img.save(temp_bmp, format="BMP")
            hbitmap = _user32.LoadImageW(None, temp_bmp, 0, 0, 0, 0x0010)
            if hbitmap:
                if _bubble_state.get("notify_hbitmap"):
                    _gdi32.DeleteObject(_bubble_state["notify_hbitmap"])
                _bubble_state["notify_hbitmap"] = hbitmap
                return True
        except Exception as e:
            log_msg("WARN", f"Render bubble notification failed: {e}")
        return False

    def _draw_notification(hwnd):
        ps = _PAINTSTRUCT()
        hdc = _user32.BeginPaint(hwnd, _ct.byref(ps))
        if not hdc:
            return
        rect = _wt.RECT()
        _user32.GetClientRect(hwnd, _ct.byref(rect))
        mem_dc = _gdi32.CreateCompatibleDC(hdc)
        bmp = _gdi32.CreateCompatibleBitmap(hdc, rect.right, rect.bottom)
        old_bmp = _gdi32.SelectObject(mem_dc, bmp)
        magenta_brush = _gdi32.CreateSolidBrush(COLOR_KEY)
        _user32.FillRect(mem_dc, _ct.byref(rect), magenta_brush)
        _gdi32.DeleteObject(magenta_brush)
        notify_bmp = _bubble_state.get("notify_hbitmap")
        if notify_bmp:
            src_dc = _gdi32.CreateCompatibleDC(mem_dc)
            old_src = _gdi32.SelectObject(src_dc, notify_bmp)
            _gdi32.BitBlt(mem_dc, 0, 0, NOTIFY_W, NOTIFY_H, src_dc, 0, 0, SRCCOPY)
            _gdi32.SelectObject(src_dc, old_src)
            _gdi32.DeleteDC(src_dc)
        _gdi32.BitBlt(hdc, 0, 0, rect.right, rect.bottom, mem_dc, 0, 0, SRCCOPY)
        _gdi32.SelectObject(mem_dc, old_bmp)
        _gdi32.DeleteObject(bmp)
        _gdi32.DeleteDC(mem_dc)
        _user32.EndPaint(hwnd, _ct.byref(ps))

    def _hide_notification(clear_unread: bool = False):
        timer = _bubble_state.get("notify_timer")
        if timer:
            try:
                timer.cancel()
            except Exception:
                pass
            _bubble_state["notify_timer"] = None
        hwnd = _bubble_state.get("notify_hwnd")
        if hwnd:
            _user32.ShowWindow(hwnd, 0)
        if clear_unread:
            _bubble_state["unread"] = False
            if _bubble_state.get("hwnd"):
                _user32.InvalidateRect(_bubble_state["hwnd"], None, True)

    def _position_notification_window():
        bwnd = _bubble_state.get("hwnd")
        screen_w = _user32.GetSystemMetrics(0)
        screen_h = _user32.GetSystemMetrics(1)
        bx = screen_w - BUBBLE_SIZE - 40
        by = screen_h - BUBBLE_SIZE - 60
        if bwnd:
            rect = _wt.RECT()
            if _user32.GetWindowRect(bwnd, _ct.byref(rect)):
                bx, by = rect.left, rect.top
        x = bx - NOTIFY_W - 12 if bx + BUBBLE_SIZE + NOTIFY_W + 12 > screen_w else bx + BUBBLE_SIZE + 12
        y = max(16, min(by - 62, screen_h - NOTIFY_H - 32))
        return x, y

    def _create_notification_window():
        if _bubble_state.get("notify_hwnd"):
            return _bubble_state["notify_hwnd"]
        try:
            import random
            wcname = f"HermesBubbleNotify{random.randint(1000, 9999)}"
            wndcls = WNDCLASSW()
            wndcls.lpfnWndProc = _ct.cast(_notify_wndproc_fn, _ct.c_void_p)
            wndcls.hInstance = _kernel32.GetModuleHandleW(None)
            wndcls.lpszClassName = wcname
            wndcls.hbrBackground = _gdi32.GetStockObject(5)
            wndcls.hCursor = _user32.LoadCursorW(None, 32649)
            reg_ok = _user32.RegisterClassW(_ct.byref(wndcls))
            reg_err = _kernel32.GetLastError()
            if not reg_ok and reg_err != 1410:
                log_msg("ERROR", f"Failed to register notification class: {reg_err}")
                return None
            x, y = _position_notification_window()
            hwnd = _user32.CreateWindowExW(
                WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST,
                wcname, "Hermes Notification", WS_POPUP,
                x, y, NOTIFY_W, NOTIFY_H,
                None, None, wndcls.hInstance, None
            )
            if not hwnd:
                log_msg("ERROR", "Could not create notification window")
                return None
            _user32.SetLayeredWindowAttributes(hwnd, COLOR_KEY, 255, LWA_ALPHA | LWA_COLORKEY)
            _bubble_state["notify_hwnd"] = hwnd
            return hwnd
        except Exception as e:
            log_msg("ERROR", f"Notification window create exception: {e}")
            return None

    def _show_notification(payload: dict):
        notice = dict(payload or {})
        session_id = str(notice.get("session_id") or "")
        if session_id:
            notice["session_id"] = session_id
        if _bubble_state.get("hwnd"):
            _user32.InvalidateRect(_bubble_state["hwnd"], None, True)
        # Only pop the card when the user is actually in bubble mode.
        # Don't store anything if bubble is hidden — user sees the response
        # in the main window, so there's nothing to "remind" later.
        if not (_bubble_state.get("visible") or BUBBLE_ONLY):
            return
        _bubble_state["notification"] = notice
        _bubble_state["unread"] = True
        hwnd = _create_notification_window()
        if not hwnd:
            return
        if not _render_notification_bitmap():
            return
        x, y = _position_notification_window()
        _user32.SetWindowPos(hwnd, -1, x, y, NOTIFY_W, NOTIFY_H, 0x0040 | 0x0010)
        _user32.ShowWindow(hwnd, 5)
        _user32.InvalidateRect(hwnd, None, True)
        _user32.UpdateWindow(hwnd)

        timer = _bubble_state.get("notify_timer")
        if timer:
            try:
                timer.cancel()
            except Exception:
                pass
        auto_hide = int(notice.get("auto_hide_seconds") or 0)
        if auto_hide > 0 and not bool(notice.get("persistent")):
            timer = threading.Timer(auto_hide, lambda: _hide_notification(clear_unread=False))
            timer.daemon = True
            timer.start()
            _bubble_state["notify_timer"] = timer

    def _open_notification_session():
        notice = dict(_bubble_state.get("notification") or {})
        sid = str(notice.get("session_id") or "")
        employee_id = str(notice.get("employee_id") or "")
        if sid or employee_id:
            _set_bubble_pending_session(sid, employee_id)
        _hide_notification(clear_unread=True)
        _restore_from_bubble()

    def _make_notify_wndproc():
        @_BubbleWndProcType
        def notify_wndproc(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_PAINT:
                    _draw_notification(hwnd)
                    return 0
                if msg == WM_LBUTTONDOWN:
                    x, y = _xy_from_lparam(lparam)
                    buttons = _bubble_state.get("notify_buttons") or {}
                    if _point_in_rect(x, y, buttons.get("secondary")) or _point_in_rect(x, y, buttons.get("close")):
                        _hide_notification(clear_unread=False)
                        return 0
                    _open_notification_session()
                    return 0
                if msg == WM_DESTROY:
                    if _bubble_state.get("notify_hbitmap"):
                        _gdi32.DeleteObject(_bubble_state["notify_hbitmap"])
                        _bubble_state["notify_hbitmap"] = None
                    _bubble_state["notify_hwnd"] = None
                    return 0
                return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)
            except Exception:
                return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        return notify_wndproc

    _notify_wndproc_fn = _make_notify_wndproc()
    bubble_notify_callback = _show_notification

    # WndProc for bubble window
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
        _hide_notification(clear_unread=True)
        mhwnd = _bubble_state.get("main_hwnd")
        if not (mhwnd and _user32.IsWindow(mhwnd)):
            mhwnd = _find_hermes_main_window()
            if mhwnd:
                _bubble_state["main_hwnd"] = mhwnd
        if mhwnd and _user32.IsWindow(mhwnd):
            _user32.ShowWindow(mhwnd, 5)   # SW_SHOW - restores window and taskbar icon
            _user32.SetForegroundWindow(mhwnd)
            # Hide the bubble
            bwnd = _bubble_state.get("hwnd")
            if bwnd:
                _user32.ShowWindow(bwnd, 0)  # SW_HIDE
                _bubble_state["visible"] = False
        elif SERVE_ONLY or BROWSER_MODE:
            _open_browser_ui(url)
            bwnd = _bubble_state.get("hwnd")
            if bwnd:
                _user32.ShowWindow(bwnd, 0)
                _bubble_state["visible"] = False
        elif BUBBLE_ONLY:
            # No main window yet (bubble-only startup): launch the main window
            import subprocess
            _script = os.path.abspath(__file__)
            _cwd = str(HERMES_HOME / "desktop-client")
            _python = _preferred_desktop_python()
            log_msg("INFO", f"Bubble restore launching main window with Python: {_python}")
            subprocess.Popen(
                [_python, _script],
                cwd=_cwd,
                creationflags=0x00000008 if sys.platform == "win32" else 0
            )
            # Destroy this bubble-only process's bubble so the keep-alive loop exits
            bwnd = _bubble_state.get("hwnd")
            if bwnd:
                _user32.DestroyWindow(bwnd)
                _bubble_state["hwnd"] = None
            os._exit(0)

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
                _bubble_state["ready_event"].set()
                return

            _bubble_state["hwnd"] = hwnd
            _bubble_state["ready_event"].set()

            # Load PNG icon
            _reload_bubble_logo()
            _update_bubble_layered(hwnd)
            _create_notification_window()

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
            shown = False
            if not _bubble_state.get("hwnd"):
                _bubble_state["ready_event"].wait(timeout=1.0)
            if _bubble_state.get("hwnd"):
                bwnd = _bubble_state["hwnd"]
                logo_ok = _reload_bubble_logo()
                screen_w = _user32.GetSystemMetrics(0)
                screen_h = _user32.GetSystemMetrics(1)
                _user32.ShowWindow(bwnd, 5)  # SW_SHOW
                pos_ok = _user32.SetWindowPos(
                    bwnd, -1,  # HWND_TOPMOST
                    screen_w - BUBBLE_SIZE - 40, screen_h - BUBBLE_SIZE - 60,
                    BUBBLE_SIZE, BUBBLE_SIZE,
                    0x0040 | 0x0010  # SWP_SHOWWINDOW | SWP_NOACTIVATE
                )
                layer_ok = _update_bubble_layered(bwnd)
                if not (logo_ok and pos_ok and layer_ok):
                    err = _kernel32.GetLastError()
                    log_msg("ERROR", f"Bubble show failed: logo={logo_ok} pos={bool(pos_ok)} layer={layer_ok} err={err}")
                    _user32.ShowWindow(bwnd, 0)
                    _bubble_state["visible"] = False
                    return {
                        "ok": False,
                        "visible": False,
                        "error": "bubble_render_failed",
                        "detail": f"logo={logo_ok} pos={bool(pos_ok)} layer={layer_ok} err={err}",
                    }
                _bubble_state["visible"] = True
                shown = True
                if _bubble_state.get("unread") and _bubble_state.get("notification"):
                    _show_notification(_bubble_state.get("notification") or {})
            else:
                log_msg("WARN", "Bubble hwnd is None, cannot show")
                return {"ok": False, "visible": False, "error": "bubble_not_ready"}
            # Hide main window (and its taskbar icon) when bubble is shown
            mhwnd = _bubble_state.get("main_hwnd")
            if not (mhwnd and _user32.IsWindow(mhwnd)):
                mhwnd = _find_hermes_main_window()
                if mhwnd:
                    _bubble_state["main_hwnd"] = mhwnd
            if shown and mhwnd and _user32.IsWindow(mhwnd):
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

        if BUBBLE_ONLY or SERVE_ONLY or BROWSER_MODE:
            # In app-window/browser mode there is no pywebview-owned HWND, but
            # the floating pony can still live as a native Win32 window.
            log_msg("INFO", "Bubble-capable mode: creating floating bubble...")
            try:
                bubble_thread = threading.Thread(target=_create_floating_bubble, daemon=True)
                bubble_thread.start()
                _bubble_state["ready_event"].wait(timeout=3.0)
                log_msg("INFO", f"Bubble init done: hwnd={_bubble_state.get('hwnd')}")
            except Exception as e:
                log_msg("ERROR", f"Failed to create floating bubble: {e}")
            if not BUBBLE_ONLY:
                for _ in range(60):
                    hwnd = _find_hermes_main_window()
                    if hwnd:
                        _bubble_state["main_hwnd"] = hwnd
                        if hicon_small:
                            _user32.SendMessageW(hwnd, WM_SETICON, 0, hicon_small)
                            _user32.SetClassLongW(hwnd, GCL_HICONSM, hicon_small)
                        if hicon_big:
                            _user32.SendMessageW(hwnd, WM_SETICON, 1, hicon_big)
                            _user32.SetClassLongW(hwnd, GCL_HICON, hicon_big)
                        log_msg("INFO", "App-window hwnd found for bubble restore/hide")
                        break
                    _time.sleep(0.5)
            return

        main_hwnd_val = None

        for i in range(50):
            _time.sleep(0.2)
            hwnd = _find_hermes_main_window()
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
    if BUBBLE_ONLY or SERVE_ONLY:
        _bubble_state["ready_event"].wait(timeout=5.0)

    if BUBBLE_ONLY:
        # Bubble-only mode: keep process alive as long as the bubble exists
        log_msg("INFO", "Bubble-only mode active. Double-click bubble to open main window.")
        while _bubble_state.get("hwnd") and _user32.IsWindow(_bubble_state["hwnd"]):
            _time.sleep(1)
        log_msg("INFO", "Bubble closed, exiting...")
        os._exit(0)
    elif SERVE_ONLY:
        log_msg("INFO", "Serve-only mode active with native bubble support.")
        try:
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            log_msg("INFO", "Serve-only mode interrupted, exiting...")
        os._exit(0)
    elif BROWSER_MODE:
        _open_browser_ui(url)
        try:
            while True:
                _time.sleep(1)
        except KeyboardInterrupt:
            log_msg("INFO", "Browser mode interrupted, exiting...")
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
