"""Volcengine (Jimeng/Seedance) video generation backend.

Uses the same Ark API key as the chat model — no separate key needed.
Models: doubao-seedance-1-0-pro / 1-5-pro / 2-0, via OpenAI-compatible SDK.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from agent.video_gen_provider import (
    COMMON_ASPECT_RATIOS,
    COMMON_RESOLUTIONS,
    DEFAULT_ASPECT_RATIO,
    DEFAULT_RESOLUTION,
    VideoGenProvider,
    error_response,
    save_bytes_video,
    save_b64_video,
    success_response,
)

logger = logging.getLogger(__name__)

API_BASE = "https://ark.cn-beijing.volces.com/api/v3"
VIDEO_CACHE_DIR = os.path.expanduser("~/.hermes/cache/videos")

_MODELS: Dict[str, Dict[str, Any]] = {
    "doubao-seedance-1-0-pro": {
        "display": "Seedance 1.0 Pro",
        "speed": "~41s/5s",
        "strengths": "1080p，5~10秒",
    },
    "doubao-seedance-1-5-pro": {
        "display": "Seedance 1.5 Pro",
        "speed": "~60s/12s",
        "strengths": "1080p，12秒，音画同步，支持方言",
    },
    "doubao-seedance-2-0": {
        "display": "Seedance 2.0",
        "speed": "~30s/5s",
        "strengths": "最强版，视频编辑/延长",
    },
}

DEFAULT_MODEL = "doubao-seedance-1-0-pro"

_RESOLUTION_MAP = {
    "480p": "854x480",
    "540p": "960x540",
    "720p": "1280x720",
    "1080p": "1920x1080",
}


def _load_config() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        cfg = load_config()
        sec = cfg.get("video_gen") if isinstance(cfg, dict) else None
        return sec if isinstance(sec, dict) else {}
    except Exception as exc:
        logger.debug("Could not load video_gen config: %s", exc)
        return {}


def _resolve_api_key() -> str:
    """Resolve Ark API key: video_gen config → image_gen config → model config → env."""
    cfg = _load_config()
    volc_cfg = cfg.get("volcengine") if isinstance(cfg.get("volcengine"), dict) else {}
    for k in ("api_key", "base_url"):
        pass
    key = volc_cfg.get("api_key") or cfg.get("api_key")
    if key:
        return str(key)

    try:
        from hermes_cli.config import load_config as lc
        main = lc()
        model_cfg = main.get("model") if isinstance(main, dict) else {}
        custom_providers = main.get("custom_providers") or []
        for cp in custom_providers:
            if isinstance(cp, dict) and cp.get("api_key"):
                return str(cp["api_key"])
        if isinstance(model_cfg, dict):
            return str(model_cfg.get("api_key", ""))
    except Exception:
        pass

    return os.environ.get("ARK_API_KEY", "")


def _resolve_model() -> Tuple[str, Dict[str, Any]]:
    cfg = _load_config()
    volc_cfg = cfg.get("volcengine") if isinstance(cfg.get("volcengine"), dict) else {}
    candidate = volc_cfg.get("model") or cfg.get("model")
    if candidate and candidate in _MODELS:
        return candidate, _MODELS[candidate]
    return DEFAULT_MODEL, _MODELS[DEFAULT_MODEL]


class VolcengineVideoGenProvider(VideoGenProvider):

    @property
    def name(self) -> str:
        return "volcengine"

    @property
    def display_name(self) -> str:
        return "火山引擎 · 即梦(视频)"

    def is_available(self) -> bool:
        return bool(_resolve_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": mid, "display": meta["display"], "speed": meta["speed"],
             "strengths": meta["strengths"], "price": "~3.67 元/5s (1080p)",
             "modalities": ["text", "image"]}
            for mid, meta in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "火山引擎 · 即梦(视频)",
            "badge": "paid",
            "tag": "doubao-seedance — 文生视频/图生视频",
            "env_vars": [
                {"key": "ARK_API_KEY", "prompt": "火山引擎 Ark API Key",
                 "url": "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey"},
            ],
        }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "modalities": ["text", "image"],
            "aspect_ratios": list(COMMON_ASPECT_RATIOS),
            "resolutions": list(COMMON_RESOLUTIONS),
            "max_duration": 12,
            "min_duration": 3,
        }

    def generate(
        self, prompt: str,
        image_url: Optional[str] = None,
        aspect_ratio: str = DEFAULT_ASPECT_RATIO,
        duration: int = 5,
        resolution: str = DEFAULT_RESOLUTION,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        if not prompt:
            return error_response(
                error="Prompt is required", error_type="invalid_argument",
                provider="volcengine",
            )

        api_key = _resolve_api_key()
        if not api_key:
            return error_response(
                error="ARK_API_KEY not found.", error_type="auth_required",
                provider="volcengine",
            )

        try:
            from openai import OpenAI
        except ImportError:
            return error_response(
                error="openai Python package not installed",
                error_type="missing_dependency", provider="volcengine",
            )

        model_id, meta = _resolve_model()
        size = _RESOLUTION_MAP.get(resolution, _RESOLUTION_MAP["720p"])
        client = OpenAI(base_url=API_BASE, api_key=api_key)

        try:
            # Seedance via Ark — use images.generate with n=1 as fallback,
            # then try videos.generate if available
            extra: Dict[str, Any] = {"size": size, "duration": duration}
            if image_url:
                extra["image"] = image_url

            response = client.videos.generate(
                model=model_id,
                prompt=prompt,
                size=size,
                duration=duration,
                response_format="b64_json",
                extra_body=extra,
            )
        except Exception as exc1:
            # videos.generate might not exist in all openai SDK versions.
            # Fallback: raw httpx call
            try:
                payload: Dict[str, Any] = {
                    "model": model_id, "prompt": prompt,
                    "size": size, "duration": duration,
                    "response_format": "b64_json",
                }
                if image_url:
                    payload["image"] = image_url
                resp = httpx.post(
                    f"{API_BASE}/videos/generations",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=300,
                )
                if resp.status_code != 200:
                    raise Exception(f"HTTP {resp.status_code}: {resp.text[:200]}")
                data = resp.json()
                b64 = None
                results = data.get("data") or []
                if results:
                    b64 = results[0].get("b64_json")
                if b64:
                    path = str(save_b64_video(b64, prefix=f"seedance_{model_id}"))
                else:
                    return error_response(
                        error="即梦未返回视频数据",
                        error_type="empty_response", provider="volcengine",
                        model=model_id,
                    )
            except Exception as exc2:
                logger.debug("Seedance generation failed", exc_info=True)
                return error_response(
                    error=f"即梦视频生成失败: {exc2}",
                    error_type="api_error", provider="volcengine",
                    model=model_id, prompt=prompt,
                )
            return success_response(
                video=path, model=model_id, prompt=prompt,
                aspect_ratio=aspect_ratio, duration=duration,
                provider="volcengine", extra={"resolution": resolution},
            )

        # Happy path: videos.generate succeeded
        data = getattr(response, "data", None) or []
        if not data:
            return error_response(
                error="即梦未返回视频数据", error_type="empty_response",
                provider="volcengine", model=model_id,
            )

        first = data[0]
        b64 = getattr(first, "b64_json", None) or getattr(first, "url", None)
        if not b64:
            return error_response(
                error="即梦返回数据中没有视频", error_type="empty_response",
                provider="volcengine", model=model_id,
            )

        if isinstance(b64, str) and (b64.startswith("http://") or b64.startswith("https://")):
            try:
                dl = httpx.get(b64, timeout=120)
                dl.raise_for_status()
                path = str(save_bytes_video(dl.content, prefix=f"seedance_{model_id}"))
            except Exception as exc:
                return error_response(
                    error=f"下载视频失败: {exc}", error_type="io_error",
                    provider="volcengine", model=model_id,
                )
        else:
            try:
                path = str(save_b64_video(b64, prefix=f"seedance_{model_id}"))
            except Exception as exc:
                return error_response(
                    error=f"保存视频失败: {exc}", error_type="io_error",
                    provider="volcengine", model=model_id,
                )

        return success_response(
            video=path, model=model_id, prompt=prompt,
            aspect_ratio=aspect_ratio, duration=duration,
            provider="volcengine", extra={"resolution": resolution},
        )


def register(ctx) -> None:
    ctx.register_video_gen_provider(VolcengineVideoGenProvider())
