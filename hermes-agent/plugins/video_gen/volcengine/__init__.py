"""Volcengine video generation — Seedance via /api/plan/v3 (task-based)."""

from __future__ import annotations

import logging, os, time, json
from typing import Any, Dict, List, Optional, Tuple

import httpx

from agent.video_gen_provider import (
    COMMON_ASPECT_RATIOS, COMMON_RESOLUTIONS,
    DEFAULT_ASPECT_RATIO, DEFAULT_RESOLUTION,
    VideoGenProvider, error_response, save_bytes_video, save_b64_video,
    success_response,
)

logger = logging.getLogger(__name__)

API_BASE = "https://ark.cn-beijing.volces.com/api/plan/v3"
TASKS_URL = f"{API_BASE}/contents/generations/tasks"
POLL_INTERVAL = 3.0
POLL_TIMEOUT = 300

_MODELS: Dict[str, Dict[str, Any]] = {
    "doubao-seedance-1-5-pro": {
        "display": "Seedance 1.5 Pro", "speed": "~60s/12s",
        "strengths": "1080p，12秒，音画同步，方言",
    },
    "doubao-seedance-2.0": {
        "display": "Seedance 2.0", "speed": "~30s/5s",
        "strengths": "最强版，视频编辑/延长",
    },
    "doubao-seedance-2.0-fast": {
        "display": "Seedance 2.0 Fast", "speed": "~15s/5s",
        "strengths": "快速版",
    },
}

DEFAULT_MODEL = "doubao-seedance-1-5-pro"

_RESOLUTION_MAP = {"480p": "854x480", "540p": "960x540", "720p": "1280x720", "1080p": "1920x1080"}


def _load_config() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        sec = load_config().get("video_gen")
        return sec if isinstance(sec, dict) else {}
    except Exception:
        return {}


def _resolve_api_key() -> str:
    cfg = _load_config()
    volc = cfg.get("volcengine") if isinstance(cfg.get("volcengine"), dict) else {}
    key = volc.get("api_key") or cfg.get("api_key")
    if key: return str(key)
    try:
        from hermes_cli.config import load_config as lc
        main = lc()
        for cp in main.get("custom_providers") or []:
            if isinstance(cp, dict) and cp.get("api_key"):
                return str(cp["api_key"])
        return str((main.get("model") or {}).get("api_key", ""))
    except Exception:
        return os.environ.get("ARK_API_KEY", "")


def _resolve_model() -> Tuple[str, Dict[str, Any]]:
    cfg = _load_config()
    volc = cfg.get("volcengine") if isinstance(cfg.get("volcengine"), dict) else {}
    m = volc.get("model") or cfg.get("model")
    if m and m in _MODELS: return m, _MODELS[m]
    return DEFAULT_MODEL, _MODELS[DEFAULT_MODEL]


def _make_headers(api_key: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


class VolcengineVideoGenProvider(VideoGenProvider):

    @property
    def name(self) -> str: return "volcengine"

    @property
    def display_name(self) -> str: return "火山引擎 · 即梦(视频)"

    def is_available(self) -> bool: return bool(_resolve_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": mid, "display": m["display"], "speed": m["speed"],
                 "strengths": m["strengths"], "price": "~3.67 元/5s",
                 "modalities": ["text", "image"]}
                for mid, m in _MODELS.items()]

    def default_model(self) -> Optional[str]: return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {"name": "火山引擎 · 即梦(视频)", "badge": "paid",
                "tag": "doubao-seedance via /api/plan/v3",
                "env_vars": [{"key": "ARK_API_KEY", "prompt": "Ark API Key"}]}

    def capabilities(self) -> Dict[str, Any]:
        return {"modalities": ["text", "image"],
                "aspect_ratios": list(COMMON_ASPECT_RATIOS),
                "resolutions": list(COMMON_RESOLUTIONS),
                "max_duration": 12, "min_duration": 3}

    def generate(self, prompt: str, image_url: Optional[str] = None,
                 aspect_ratio: str = DEFAULT_ASPECT_RATIO,
                 duration: int = 5, resolution: str = DEFAULT_RESOLUTION,
                 **kwargs: Any) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(error="Prompt is required", error_type="invalid_argument",
                                  provider="volcengine")
        api_key = _resolve_api_key()
        if not api_key:
            return error_response(error="ARK_API_KEY not found", error_type="auth_required",
                                  provider="volcengine")

        model_id, meta = _resolve_model()
        headers = _make_headers(api_key)
        size = _RESOLUTION_MAP.get(resolution, _RESOLUTION_MAP["720p"])

        # 1. Create task
        payload: Dict[str, Any] = {"model": model_id, "prompt": prompt,
                                   "size": size, "duration": duration}
        if image_url:
            payload["image"] = image_url

        try:
            r = httpx.post(TASKS_URL, json=payload, headers=headers, timeout=30)
            if r.status_code != 200:
                return error_response(error=f"创建任务失败 HTTP {r.status_code}: {r.text[:200]}",
                                      error_type="api_error", provider="volcengine", model=model_id)
            data = r.json()
            task_id = data.get("id") or data.get("task_id")
            if not task_id:
                return error_response(error="未获取到 task_id", error_type="empty_response",
                                      provider="volcengine", model=model_id)
        except Exception as exc:
            return error_response(error=f"创建任务异常: {exc}", error_type="api_error",
                                  provider="volcengine", model=model_id)

        # 2. Poll until done
        deadline = time.time() + POLL_TIMEOUT
        while time.time() < deadline:
            time.sleep(POLL_INTERVAL)
            try:
                r2 = httpx.get(f"{TASKS_URL}/{task_id}", headers=headers, timeout=15)
                if r2.status_code != 200:
                    return error_response(error=f"查询任务失败 HTTP {r2.status_code}",
                                          error_type="api_error", provider="volcengine")
                task = r2.json()
                status = task.get("status", "") or task.get("state", "")
                if status in ("succeeded", "completed", "done", "success"):
                    # Extract video URL / b64
                    video_url = task.get("video_url") or task.get("url")
                    b64 = task.get("b64_json") or task.get("data")
                    output = task.get("output") or {}
                    if isinstance(output, dict):
                        video_url = video_url or output.get("video_url") or output.get("url")
                        b64 = b64 or output.get("b64_json") or output.get("data")
                    if video_url and isinstance(video_url, str) and video_url.startswith("http"):
                        dl = httpx.get(video_url, timeout=120)
                        dl.raise_for_status()
                        path = str(save_bytes_video(dl.content, prefix=f"seedance_{model_id}"))
                    elif b64:
                        path = str(save_b64_video(b64, prefix=f"seedance_{model_id}"))
                    else:
                        return error_response(error="任务完成但无视频数据",
                                              error_type="empty_response",
                                              provider="volcengine", model=model_id)
                    return success_response(video=path, model=model_id, prompt=prompt,
                                            aspect_ratio=aspect_ratio, duration=duration,
                                            provider="volcengine", extra={"resolution": resolution})
                elif status in ("failed", "error", "cancelled"):
                    return error_response(error=f"视频生成{status}: {task.get('error','')}",
                                          error_type="api_error", provider="volcengine")
                # else: pending / processing - continue polling
            except Exception as exc:
                return error_response(error=f"轮询异常: {exc}", error_type="api_error",
                                      provider="volcengine", model=model_id)

        return error_response(error="视频生成超时", error_type="timeout",
                              provider="volcengine", model=model_id)


def register(ctx) -> None:
    ctx.register_video_gen_provider(VolcengineVideoGenProvider())
