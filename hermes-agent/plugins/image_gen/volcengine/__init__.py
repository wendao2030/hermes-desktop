"""Volcengine (Jimeng/Seedream) image generation backend.

Uses the same Ark API key as the chat model — no separate key needed.
Models: doubao-seedream-4-0 / 4-5 / 5-0, all via OpenAI-compatible SDK.
"""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from agent.image_gen_provider import (
    DEFAULT_ASPECT_RATIO,
    ImageGenProvider,
    error_response,
    resolve_aspect_ratio,
    save_b64_image,
    success_response,
)

logger = logging.getLogger(__name__)

API_BASE = "https://ark.cn-beijing.volces.com/api/v3"

_MODELS: Dict[str, Dict[str, Any]] = {
    "doubao-seedream-4-0-250828": {
        "display": "Seedream 4.0",
        "speed": "~8s",
        "strengths": "文生图/图生图/组图，1K-4K",
    },
    "doubao-seedream-4-5-251128": {
        "display": "Seedream 4.5",
        "speed": "~15s",
        "strengths": "增强画质，1K-4K",
    },
    "doubao-seedream-5.0": {
        "display": "Seedream 5.0",
        "speed": "~8s",
        "strengths": "最新版，支持联网搜图",
    },
}

DEFAULT_MODEL = "doubao-seedream-4-0-250828"

_SIZE_MAP = {
    "landscape": "1024x576",
    "square": "1024x1024",
    "portrait": "576x1024",
}


def _load_config() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config
        cfg = load_config()
        section = cfg.get("image_gen") if isinstance(cfg, dict) else None
        return section if isinstance(section, dict) else {}
    except Exception as exc:
        logger.debug("Could not load image_gen config: %s", exc)
        return {}


def _resolve_api_key() -> str:
    """Resolve Ark API key: image_gen config → model config → env."""
    cfg = _load_config()
    volc_cfg = cfg.get("volcengine") if isinstance(cfg.get("volcengine"), dict) else {}
    key = volc_cfg.get("api_key") or cfg.get("api_key")
    if key:
        return str(key)

    # Fall back to the main model's api_key
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


class VolcengineImageGenProvider(ImageGenProvider):
    """火山引擎即梦(Seedream) 图像生成后端."""

    @property
    def name(self) -> str:
        return "volcengine"

    @property
    def display_name(self) -> str:
        return "火山引擎 · 即梦"

    def is_available(self) -> bool:
        return bool(_resolve_api_key())

    def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": mid, "display": meta["display"], "speed": meta["speed"],
             "strengths": meta["strengths"], "price": "~0.02-0.08 元/张"}
            for mid, meta in _MODELS.items()
        ]

    def default_model(self) -> Optional[str]:
        return DEFAULT_MODEL

    def get_setup_schema(self) -> Dict[str, Any]:
        return {
            "name": "火山引擎 · 即梦",
            "badge": "paid",
            "tag": "doubao-seedream — 文生图/图生图/组图",
            "env_vars": [
                {"key": "ARK_API_KEY", "prompt": "火山引擎 Ark API Key",
                 "url": "https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey"},
            ],
        }

    def generate(
        self, prompt: str, aspect_ratio: str = DEFAULT_ASPECT_RATIO, **kwargs: Any
    ) -> Dict[str, Any]:
        prompt = (prompt or "").strip()
        aspect = resolve_aspect_ratio(aspect_ratio)
        if not prompt:
            return error_response(
                error="Prompt is required",
                error_type="invalid_argument",
                provider="volcengine",
                aspect_ratio=aspect,
            )

        api_key = _resolve_api_key()
        if not api_key:
            return error_response(
                error="ARK_API_KEY not found. Set in config.yaml image_gen.volcengine.api_key.",
                error_type="auth_required",
                provider="volcengine",
                aspect_ratio=aspect,
            )

        try:
            from openai import OpenAI
        except ImportError:
            return error_response(
                error="openai Python package not installed (pip install openai)",
                error_type="missing_dependency",
                provider="volcengine",
                aspect_ratio=aspect,
            )

        model_id, meta = _resolve_model()
        size = _SIZE_MAP.get(aspect, _SIZE_MAP["square"])
        client = OpenAI(base_url=API_BASE, api_key=api_key)

        try:
            response = client.images.generate(
                model=model_id,
                prompt=prompt,
                size=size,
                n=1,
                response_format="b64_json",
            )
        except Exception as exc:
            logger.debug("Seedream generation failed", exc_info=True)
            return error_response(
                error=f"即梦生图失败: {exc}",
                error_type="api_error",
                provider="volcengine",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        data = getattr(response, "data", None) or []
        if not data:
            return error_response(
                error="即梦未返回图片数据",
                error_type="empty_response",
                provider="volcengine",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        first = data[0]
        b64 = getattr(first, "b64_json", None)
        if not b64:
            return error_response(
                error="即梦返回的数据中没有 b64_json 字段",
                error_type="empty_response",
                provider="volcengine",
                model=model_id,
            )

        try:
            saved_path = save_b64_image(b64, prefix=f"seedream_{model_id}")
        except Exception as exc:
            return error_response(
                error=f"保存图片失败: {exc}",
                error_type="io_error",
                provider="volcengine",
                model=model_id,
                prompt=prompt,
                aspect_ratio=aspect,
            )

        return success_response(
            image=str(saved_path),
            model=model_id,
            prompt=prompt,
            aspect_ratio=aspect,
            provider="volcengine",
            extra={"size": size},
        )


def register(ctx) -> None:
    ctx.register_image_gen_provider(VolcengineImageGenProvider())
