#!/usr/bin/env python3
"""
Video Generation Tool
=====================

Single ``video_generate`` tool that dispatches to a plugin-registered
video generation provider. Mirrors the ``image_generate`` design:

- ``agent/video_gen_provider.py`` defines the :class:`VideoGenProvider` ABC.
- ``agent/video_gen_registry.py`` holds the active providers (populated by
  plugins at import time).
- Each provider lives under ``plugins/video_gen/<name>/``.

The tool itself is intentionally backend-agnostic and ships **no in-tree
provider** — turn on a backend by enabling a plugin (``hermes plugins
enable video_gen/<name>``) and selecting it in ``hermes tools`` → Video
Generation.

Unified surface
---------------
One tool covers the common cases — text-to-video, image-to-video, video
edit, video extend — with a compact schema:

    prompt                   text instruction (required for generate/edit)
    operation                "generate" | "edit" | "extend"
    image_url                drives image-to-video when operation=generate
    video_url                source video for edit/extend
    reference_image_urls     list, up to provider-declared cap
    duration                 seconds (provider clamps)
    aspect_ratio             "16:9" | "9:16" | "1:1" | ...
    resolution               "480p" | "540p" | "720p" | "1080p"
    negative_prompt          optional (Pixverse/Kling style)
    audio                    optional (Veo3/Pixverse pricing tier)
    seed                     optional
    model                    optional, override the active provider's default

Providers ignore parameters they do not support. The tool layer does
**lightweight** validation (type/required-prompt) and lets each provider
do its own clamping inside :meth:`VideoGenProvider.generate` — that keeps
the tool surface stable as new providers ship with different capabilities.
"""

from __future__ import annotations

import json
import logging
import base64
import mimetypes
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.video_gen_provider import (
    COMMON_ASPECT_RATIOS,
    COMMON_RESOLUTIONS,
    DEFAULT_ASPECT_RATIO,
    DEFAULT_RESOLUTION,
    error_response,
)
from tools.registry import registry, tool_error

logger = logging.getLogger(__name__)


VIDEO_GENERATE_SCHEMA: Dict[str, Any] = {
    "name": "video_generate",
    # Placeholder — the real description is built dynamically at
    # get_tool_definitions() time so it reflects the active backend's
    # actual capabilities (which modalities / resolutions / duration
    # ranges the user's currently-selected model supports).
    # See _build_dynamic_video_schema() below and the dynamic-tool-schemas
    # skill at github/hermes-agent-dev/references/dynamic-tool-schemas.md.
    "description": "(rebuilt at get_definitions() time — see _build_dynamic_video_schema)",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Text instruction describing the desired video, motion, "
                    "subject, style, camera movement, etc."
                ),
            },
            "image_url": {
                "type": "string",
                "description": (
                    "Optional public URL of a still image. When provided, "
                    "the active backend routes to its image-to-video "
                    "endpoint (animate the image); when omitted, it routes "
                    "to text-to-video. Pass either a URL the user supplied "
                    "or a path/URL from the conversation."
                ),
            },
            "reference_image_urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of reference image URLs (style or "
                    "character refs). Only supported by some backends; "
                    "the active backend's description below indicates whether "
                    "this is honored and what the max is."
                ),
            },
            "image_asset_id": {
                "type": "string",
                "description": (
                    "Optional Hermes media asset id for image-to-video, e.g. "
                    "img_xxx from the current conversation's recent media list."
                ),
            },
            "image_asset_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of Hermes image asset ids. Use this when "
                    "the user specifies several generated/uploaded images."
                ),
            },
            "image_path": {
                "type": "string",
                "description": "Optional absolute local image path for image-to-video.",
            },
            "image_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of absolute local image paths.",
            },
            "use_recent_image": {
                "type": "boolean",
                "description": (
                    "Use the most recent image asset from this conversation. "
                    "Only use when the user explicitly refers to the latest image."
                ),
            },
            "use_recent_group": {
                "type": "boolean",
                "description": (
                    "Use the most recent image group from this conversation. "
                    "Use for phrases like 'that group of images'."
                ),
            },
            "duration": {
                "type": "integer",
                "description": (
                    "Desired video duration in seconds. Providers clamp to "
                    "their supported range (commonly 4-15s). Omit to use the "
                    "provider's default."
                ),
            },
            "aspect_ratio": {
                "type": "string",
                "enum": list(COMMON_ASPECT_RATIOS),
                "description": (
                    "Output aspect ratio. Providers clamp to their supported "
                    "set."
                ),
                "default": DEFAULT_ASPECT_RATIO,
            },
            "resolution": {
                "type": "string",
                "enum": list(COMMON_RESOLUTIONS),
                "description": (
                    "Output resolution. Providers clamp to their supported "
                    "set."
                ),
                "default": DEFAULT_RESOLUTION,
            },
            "negative_prompt": {
                "type": "string",
                "description": (
                    "Optional negative prompt — content to avoid in the "
                    "output. Supported by Pixverse, Kling, and similar; "
                    "ignored by providers that do not support it."
                ),
            },
            "audio": {
                "type": "boolean",
                "description": (
                    "Optional audio generation toggle. Supported by Veo3 and "
                    "Pixverse (affects pricing tier); ignored elsewhere."
                ),
            },
            "seed": {
                "type": "integer",
                "description": (
                    "Optional seed for reproducible outputs (provider-"
                    "dependent)."
                ),
            },
            "model": {
                "type": "string",
                "description": (
                    "Optional model override. If omitted, the user's "
                    "configured ``video_gen.model`` (set via `hermes tools` "
                    "→ Video Generation) is used. Models that the active "
                    "provider does not know are rejected."
                ),
            },
        },
        "required": ["prompt"],
    },
}


# ---------------------------------------------------------------------------
# Config readers (mirror image_generation_tool.py)
# ---------------------------------------------------------------------------


def _read_video_gen_section() -> Dict[str, Any]:
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
        section = cfg.get("video_gen") if isinstance(cfg, dict) else None
        return section if isinstance(section, dict) else {}
    except Exception as exc:
        logger.debug("Could not read video_gen config: %s", exc)
        return {}


def _read_configured_video_provider() -> Optional[str]:
    value = _read_video_gen_section().get("provider")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _read_configured_video_model() -> Optional[str]:
    value = _read_video_gen_section().get("model")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------


def check_video_generation_requirements() -> bool:
    """Return True when at least one registered provider reports available.

    Triggers plugin discovery (idempotent) so user-installed plugins are
    visible to the toolset gate.
    """
    try:
        from agent.video_gen_registry import list_providers
        from hermes_cli.plugins import _ensure_plugins_discovered

        _ensure_plugins_discovered()
        for provider in list_providers():
            try:
                if provider.is_available():
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def _resolve_active_provider():
    """Return the active provider object or None.

    Forces plugin discovery before checking the registry — handles cases
    where a long-lived session was started before a plugin was installed.
    """
    try:
        from agent.video_gen_registry import get_active_provider
        from hermes_cli.plugins import _ensure_plugins_discovered

        _ensure_plugins_discovered()
        provider = get_active_provider()
        if provider is None:
            _ensure_plugins_discovered(force=True)
            provider = get_active_provider()
        return provider
    except Exception as exc:
        logger.debug("video_gen provider resolution failed: %s", exc)
        return None


def _missing_provider_error(configured: Optional[str]) -> str:
    if configured:
        msg = (
            f"video_gen.provider='{configured}' is set but no plugin "
            f"registered that name. Run `hermes plugins list` to see "
            f"installed video gen backends, or `hermes tools` → Video "
            f"Generation to pick one."
        )
        return json.dumps(error_response(
            error=msg, error_type="provider_not_registered",
            provider=configured,
        ))
    msg = (
        "No video generation backend is configured. Run `hermes tools` → "
        "Video Generation to enable one (xAI, FAL, or Google Veo)."
    )
    return json.dumps(error_response(
        error=msg, error_type="no_provider_configured",
    ))


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def _coerce_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "on"}:
            return True
        if v in {"false", "0", "no", "off"}:
            return False
    return None


def _normalize_reference_images(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return None
    out: List[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out or None


IMAGE_INPUT_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item or "").strip()]


def _hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME")
    if raw:
        return Path(raw)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        local_home = Path(local_app_data) / "hermes"
        if local_home.exists():
            return local_home
    return Path.home() / ".hermes"


def _media_asset_rows(session_id: str, *, kind: str = "image", limit: int = 20) -> List[dict]:
    if not session_id:
        return []
    db_path = _hermes_home() / "state.db"
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path), timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, kind, source, path, url, group_id, created_at, metadata_json
            FROM media_assets
            WHERE session_id = ? AND kind = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, kind, max(1, min(int(limit), 100))),
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _media_assets_by_id(session_id: str, asset_ids: List[str]) -> List[dict]:
    if not session_id or not asset_ids:
        return []
    db_path = _hermes_home() / "state.db"
    if not db_path.exists():
        return []
    placeholders = ",".join("?" for _ in asset_ids)
    conn = sqlite3.connect(str(db_path), timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""
            SELECT id, kind, source, path, url, group_id, created_at, metadata_json
            FROM media_assets
            WHERE session_id = ? AND id IN ({placeholders}) AND kind = 'image'
            ORDER BY created_at DESC
            """,
            [session_id, *asset_ids],
        ).fetchall()
        by_id = {str(row["id"]): dict(row) for row in rows}
        return [by_id[asset_id] for asset_id in asset_ids if asset_id in by_id]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _recent_image_group(session_id: str) -> List[dict]:
    rows = _media_asset_rows(session_id, kind="image", limit=50)
    if not rows:
        return []
    group_id = rows[0].get("group_id")
    if not group_id:
        return [rows[0]]
    return [row for row in rows if row.get("group_id") == group_id]


def _local_image_to_data_url(path_value: str) -> str:
    path = Path(path_value).expanduser()
    if not path.exists() or not path.is_file():
        raise ValueError(f"image path does not exist: {path_value}")
    if path.suffix.lower() not in IMAGE_INPUT_EXTS:
        raise ValueError(f"unsupported image file type: {path.suffix}")
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _normalize_image_ref(ref: str) -> str:
    value = str(ref or "").strip()
    if not value:
        return ""
    lowered = value.lower()
    if lowered.startswith(("http://", "https://", "data:image/")):
        return value
    if lowered.startswith("/api/media/cache/"):
        rel = value.split("/api/media/cache/", 1)[1].replace("/", os.sep)
        value = str((_hermes_home() / "cache" / rel).resolve())
    return _local_image_to_data_url(value)


def _video_image_input_requested(args: Dict[str, Any]) -> bool:
    keys = (
        "image_url",
        "reference_image_urls",
        "image_asset_id",
        "image_asset_ids",
        "image_path",
        "image_paths",
        "use_recent_image",
        "use_recent_group",
    )
    return any(bool(args.get(key)) for key in keys)


def _resolve_video_image_inputs(args: Dict[str, Any], task_id: str) -> tuple[Optional[str], Optional[List[str]], List[dict]]:
    explicit_refs: List[str] = []
    asset_ids = _as_list(args.get("image_asset_id")) + _as_list(args.get("image_asset_ids"))
    paths = _as_list(args.get("image_path")) + _as_list(args.get("image_paths"))
    urls = _as_list(args.get("image_url")) + _as_list(args.get("reference_image_urls"))
    requested = _video_image_input_requested(args)
    missing_asset_ids: List[str] = []
    resolution_errors: List[str] = []

    asset_rows = _media_assets_by_id(task_id, asset_ids)
    found_asset_ids = {str(row.get("id") or "") for row in asset_rows}
    for asset_id in asset_ids:
        if asset_id not in found_asset_ids:
            missing_asset_ids.append(asset_id)

    for row in asset_rows:
        explicit_refs.append(row.get("url") or row.get("path") or "")

    explicit_refs.extend(paths)
    explicit_refs.extend(urls)

    if not explicit_refs and _coerce_bool(args.get("use_recent_group")):
        for row in _recent_image_group(task_id):
            explicit_refs.append(row.get("url") or row.get("path") or "")
    elif not explicit_refs and _coerce_bool(args.get("use_recent_image")):
        rows = _media_asset_rows(task_id, kind="image", limit=1)
        if rows:
            explicit_refs.append(rows[0].get("url") or rows[0].get("path") or "")

    if missing_asset_ids:
        raise ValueError(
            "image asset not found in this conversation: "
            + ", ".join(missing_asset_ids)
        )

    if requested and not explicit_refs:
        raise ValueError(
            "no image input could be resolved. Use a valid image_asset_id, "
            "image_path, image_url, or use_recent_image after an image has "
            "been generated or uploaded in this conversation."
        )

    normalized: List[str] = []
    used: List[dict] = []
    seen = set()
    for ref in explicit_refs:
        if not ref or ref in seen:
            continue
        seen.add(ref)
        try:
            normalized_ref = _normalize_image_ref(ref)
        except Exception as exc:
            resolution_errors.append(f"{ref}: {exc}")
            continue
        if normalized_ref:
            normalized.append(normalized_ref)
            used.append({
                "source": "asset_or_path",
                "input": ref,
                "kind": "image",
                "converted": normalized_ref[:80] + ("..." if len(normalized_ref) > 80 else ""),
            })

    if not normalized:
        if requested:
            detail = "; ".join(resolution_errors) if resolution_errors else "empty image input"
            raise ValueError(f"no usable image input could be prepared: {detail}")
        return None, None, []
    return normalized[0], normalized[1:] or None, used


def _handle_video_generate(args: Dict[str, Any], **_kw: Any) -> str:
    prompt = (args.get("prompt") or "").strip()
    task_id = str(_kw.get("task_id") or "").strip()
    duration = _coerce_int(args.get("duration"))
    aspect_ratio = (args.get("aspect_ratio") or DEFAULT_ASPECT_RATIO).strip() or DEFAULT_ASPECT_RATIO
    resolution = (args.get("resolution") or DEFAULT_RESOLUTION).strip() or DEFAULT_RESOLUTION
    negative_prompt = (args.get("negative_prompt") or "").strip() or None
    audio = _coerce_bool(args.get("audio"))
    seed = _coerce_int(args.get("seed"))
    model_override = (args.get("model") or "").strip() or None

    # Soft validation — providers do their own. Prompt is required by the
    # schema; the backend may still accept image-only on its image-to-video
    # endpoint but our surface always needs a prompt.
    if not prompt:
        return tool_error("prompt is required for video generation")

    try:
        image_url, reference_image_urls, resolved_inputs = _resolve_video_image_inputs(args, task_id)
    except Exception as exc:
        return json.dumps(error_response(
            error=f"Could not resolve image input for video generation: {exc}",
            error_type="image_input_not_found",
            prompt=prompt,
        ), ensure_ascii=False)

    # Resolve the active provider.
    configured = _read_configured_video_provider()
    provider = _resolve_active_provider()
    if provider is None:
        return _missing_provider_error(configured)

    # Resolve model: explicit arg wins, then config, then provider default.
    model = model_override or _read_configured_video_model() or provider.default_model()

    kwargs: Dict[str, Any] = {
        "model": model,
        "image_url": image_url,
        "reference_image_urls": reference_image_urls,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "negative_prompt": negative_prompt,
        "audio": audio,
        "seed": seed,
    }
    # Drop None entries so providers see clean defaults.
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    try:
        result = provider.generate(prompt=prompt, **kwargs)
    except TypeError as exc:
        # A provider that hasn't widened its signature is a bug, not a
        # caller error — log and surface a clear contract message.
        logger.warning(
            "video_gen provider '%s' rejected kwargs (signature too narrow): %s",
            getattr(provider, "name", "?"), exc,
        )
        return json.dumps(error_response(
            error=(
                f"Provider '{getattr(provider, 'name', '?')}' signature is "
                f"out of date with the video_generate schema. Report this "
                f"to the plugin author."
            ),
            error_type="provider_contract",
            provider=getattr(provider, "name", ""),
            model=model or "",
            prompt=prompt,
        ))
    except Exception as exc:
        logger.warning(
            "video_gen provider '%s' raised: %s",
            getattr(provider, "name", "?"), exc,
        )
        return json.dumps(error_response(
            error=f"Provider '{getattr(provider, 'name', '?')}' error: {exc}",
            error_type="provider_exception",
            provider=getattr(provider, "name", ""),
            model=model or "",
            prompt=prompt,
        ))

    if not isinstance(result, dict):
        return json.dumps(error_response(
            error="Provider returned a non-dict result",
            error_type="provider_contract",
            provider=getattr(provider, "name", ""),
            model=model or "",
            prompt=prompt,
        ))

    if resolved_inputs:
        result["resolved_image_inputs"] = resolved_inputs

    return json.dumps(result)


# ---------------------------------------------------------------------------
# Dynamic schema — reflect the active backend's actual capabilities
# ---------------------------------------------------------------------------
#
# Why dynamic: the user's configured backend determines which operations
# (generate/edit/extend), modalities (text / image / refs), aspect ratios,
# resolutions, durations, and audio/negative-prompt flags are real. A model
# that calls video_generate without knowing the active backend wastes a
# turn on something like "fal-ai/veo3.1/image-to-video requires image_url".
# Surfacing the per-model surface in the description means the model
# usually gets the call right on the first try.
#
# Memoization: model_tools.get_tool_definitions() keys its cache on
# config.yaml mtime, so when the user changes provider/model via
# `hermes tools` or `/skills`, the schema rebuilds automatically.


_GENERIC_DESCRIPTION = (
    "Generate a video from a text prompt (text-to-video) or animate a "
    "still image (image-to-video) using the user's configured video "
    "generation backend. Pass `image_asset_id`, `image_path`, or `image_url` "
    "to animate a specific generated/uploaded image; omit image inputs only "
    "when the user truly wants text-to-video. If an explicit image input "
    "cannot be resolved, the tool returns an error instead of silently "
    "falling back to text-to-video. The backend auto-routes to the right "
    "endpoint. The backend and model family are user-configured via "
    "`hermes tools` → Video Generation; the agent does not pick them. "
    "Long-running generations may take 30 seconds to several minutes — "
    "the call blocks until the video is ready. Returns either an HTTP "
    "URL or an absolute file path in the `video` field; display it with "
    "markdown ![description](url-or-path) and the gateway will deliver it."
)


def _format_model_caveats(
    model_meta: Dict[str, Any],
    backend_caps: Dict[str, Any],
) -> List[str]:
    """Pull human-readable caveats out of one model's catalog metadata.

    Only surfaces things that meaningfully differ from the backend's
    overall capabilities — repeating defaults is noise.
    """
    caveats: List[str] = []

    modalities = set(model_meta.get("modalities") or [])
    modality = model_meta.get("modality")  # FAL's plugin uses this key for single-modality entries
    if modality:
        modalities.add(modality)

    if "image" in modalities and "text" not in modalities:
        caveats.append(
            "this model is image-to-video only — image_url is REQUIRED; "
            "text-only calls will be rejected"
        )
    elif "text" in modalities and "image" not in modalities:
        caveats.append(
            "this model is text-to-video only — image_url is not supported"
        )

    return caveats


def _build_dynamic_video_schema() -> Dict[str, Any]:
    """Build a description that reflects the active backend's actual surface.

    Cheap: reads config (already memoized by the caller), asks the active
    provider for `capabilities()` and the active model's catalog entry,
    and formats a few lines of prose. Falls back to the generic
    description when no provider is configured or registered.
    """
    parts: List[str] = [_GENERIC_DESCRIPTION]

    configured = _read_configured_video_provider()
    configured_model = _read_configured_video_model()

    if not configured:
        parts.append(
            "\nNo video backend is configured. Calls will return an error "
            "until the user picks one via `hermes tools` → Video Generation."
        )
        return {"description": "\n".join(parts)}

    try:
        from agent.video_gen_registry import get_provider
        from hermes_cli.plugins import _ensure_plugins_discovered

        _ensure_plugins_discovered()
        provider = get_provider(configured)
    except Exception:
        provider = None

    if provider is None:
        parts.append(
            f"\nActive backend: {configured} (plugin not yet loaded — the "
            f"tool will retry discovery on first call)."
        )
        return {"description": "\n".join(parts)}

    try:
        caps = provider.capabilities() or {}
    except Exception:
        caps = {}
    try:
        models = provider.list_models() or []
    except Exception:
        models = []

    active_model = configured_model or provider.default_model()
    model_meta = next(
        (m for m in models if isinstance(m, dict) and m.get("id") == active_model),
        {},
    )

    backend_label = provider.display_name
    line = f"\nActive backend: {backend_label}"
    if active_model:
        line += f" · model: {active_model}"
    parts.append(line)

    # Model-specific caveats (the high-signal stuff)
    for c in _format_model_caveats(model_meta, caps):
        parts.append(f"- {c}")

    # Backend modality summary — only useful when the backend supports
    # both text and image. Single-modality backends are already covered by
    # the model caveat above.
    modalities = set(caps.get("modalities") or [])
    if "text" in modalities and "image" in modalities and not model_meta.get("modality"):
        parts.append(
            "- supports both text-to-video (omit image_url) and "
            "image-to-video (pass image_url) — routes automatically"
        )

    if caps.get("aspect_ratios"):
        parts.append(f"- aspect_ratio choices: {', '.join(caps['aspect_ratios'])}")
    if caps.get("resolutions"):
        parts.append(f"- resolution choices: {', '.join(caps['resolutions'])}")
    if caps.get("min_duration") and caps.get("max_duration"):
        parts.append(
            f"- duration range: {caps['min_duration']}-{caps['max_duration']}s"
        )
    if caps.get("supports_audio"):
        parts.append("- audio: pass `audio=true` to enable native audio (pricing tier)")
    if caps.get("supports_negative_prompt"):
        parts.append("- negative_prompt: supported")
    max_refs = caps.get("max_reference_images") or 0
    if max_refs:
        parts.append(f"- reference_image_urls: up to {max_refs} images")

    return {"description": "\n".join(parts)}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


registry.register(
    name="video_generate",
    toolset="video_gen",
    schema=VIDEO_GENERATE_SCHEMA,
    handler=_handle_video_generate,
    check_fn=check_video_generation_requirements,
    requires_env=[],
    is_async=False,
    emoji="🎬",
    dynamic_schema_overrides=_build_dynamic_video_schema,
)
