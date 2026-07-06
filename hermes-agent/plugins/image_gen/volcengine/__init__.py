"""Volcengine image generation — Seedream via /api/plan/v3."""

from __future__ import annotations

import base64, logging, os
from typing import Any, Dict, List, Optional, Tuple

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO, ImageGenProvider,
    error_response, resolve_aspect_ratio, save_b64_image, success_response,
)

logger = logging.getLogger(__name__)

API_BASE_DEFAULT = "https://ark.cn-beijing.volces.com/api/plan/v3"

_MODELS: Dict[str, Dict[str, Any]] = {
    "doubao-seedream-5.0-lite": {
        "display": "Seedream 5.0 Lite", "speed": "~8s",
        "strengths": "最新版轻量，1K-4K",
    },
}

DEFAULT_MODEL = "doubao-seedream-5.0-lite"

_SIZE_MAP = {"landscape": "2560x1440", "square": "2048x2048", "portrait": "1440x2560"}


def _load_config() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        sec = load_config().get("image_gen")
        return sec if isinstance(sec, dict) else {}
    except Exception as e:
        logger.debug("load image_gen config: %s", e)
        return {}


def _resolve_api_base() -> str:
    """Read base_url from image_gen config, fallback to main model config, then default."""
    cfg = _load_config()
    volc = cfg.get("volcengine") if isinstance(cfg.get("volcengine"), dict) else {}
    url = volc.get("base_url") or cfg.get("base_url")
    if url: return str(url).rstrip("/")
    try:
        from hermes_cli.config import load_config as lc
        main = lc()
        main_url = (main.get("model") or {}).get("base_url", "")
        if main_url: return str(main_url).rstrip("/")
    except Exception:
        pass
    return API_BASE_DEFAULT


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


class VolcengineImageGenProvider(ImageGenProvider):

    @property
    def name(self) -> str: return "volcengine"

    @property
    def display_name(self) -> str: return "火山引擎 · 即梦(图片)"

    def is_available(self) -> bool: return bool(_resolve_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [{"id": mid, "display": m["display"], "speed": m["speed"],
                 "strengths": m["strengths"], "price": "~0.02-0.08 元/张"}
                for mid, m in _MODELS.items()]

    def default_model(self) -> Optional[str]: return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {"name": "火山引擎 · 即梦(图片)", "badge": "paid",
                "tag": "doubao-seedream via /api/plan/v3",
                "env_vars": [{"key": "ARK_API_KEY", "prompt": "Ark API Key"}]}

    def generate(self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO,
                 **kwargs: Any) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)
        if not prompt:
            return error_response(error="Prompt is required", error_type="invalid_argument",
                                  provider="volcengine", aspect_ratio=aspect)

        api_key = _resolve_api_key()
        if not api_key:
            return error_response(error="ARK_API_KEY not found", error_type="auth_required",
                                  provider="volcengine")

        model_id, meta = _resolve_model()
        # Prefer caller-specified size, fall back to aspect ratio map
        size = kwargs.get("size") or _SIZE_MAP.get(aspect, _SIZE_MAP["square"])

        try:
            from openai import OpenAI
            client = OpenAI(base_url=_resolve_api_base(), api_key=api_key)
            response = client.images.generate(model=model_id, prompt=prompt, size=size,
                                              n=1, response_format="b64_json")
        except Exception as exc:
            logger.debug("Seedream failed", exc_info=True)
            return error_response(error=f"即梦生图失败: {exc}", error_type="api_error",
                                  provider="volcengine", model=model_id)

        data = getattr(response, "data", None) or []
        if not data:
            return error_response(error="未返回图片数据", error_type="empty_response",
                                  provider="volcengine", model=model_id)

        b64 = getattr(data[0], "b64_json", None)
        if not b64:
            return error_response(error="无 b64_json", error_type="empty_response",
                                  provider="volcengine", model=model_id)

        try:
            path = str(save_b64_image(b64, prefix=f"seedream_{model_id}"))
        except Exception as exc:
            return error_response(error=f"保存图片失败: {exc}", error_type="io_error",
                                  provider="volcengine", model=model_id)

        return success_response(image=path, model=model_id, prompt=prompt,
                                aspect_ratio=aspect, provider="volcengine",
                                extra={"size": size})


def register(ctx) -> None:
    ctx.register_image_gen_provider(VolcengineImageGenProvider())
