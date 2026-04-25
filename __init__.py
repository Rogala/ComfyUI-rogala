"""
ComfyUI-rogala
==============
Custom node pack for ComfyUI by rogala.
"""

from .nodes.sampler_scheduler_iterator  import NODE_CLASS_MAPPINGS as _SAMPLER_NODES
from .nodes.sampler_scheduler_iterator  import refresh_config
from .nodes.aligned_text_overlay_images import NODE_CLASS_MAPPINGS as _IMAGE_NODES
from .nodes.aligned_text_overlay_video  import NODE_CLASS_MAPPINGS as _VIDEO_NODES
from .nodes.ltx_resolution_selector     import NODE_CLASS_MAPPINGS as _LTX_NODES
from .nodes.fmlf_ltx                    import NODE_CLASS_MAPPINGS as _FMLF_NODES
from .nodes.sampler_ltxv                import NODE_CLASS_MAPPINGS as _SAMPLER_LTX_NODES
from .nodes.advanced_style_selector     import NODE_CLASS_MAPPINGS as _STYLE_NODES
from .nodes.advanced_style_selector     import reload_styles

import os as _os
import json as _json

_FAVORITES_PATH = _os.path.join(_os.path.dirname(__file__), "config", "favorites_styles.json")

def _load_favorites() -> list:
    try:
        with open(_FAVORITES_PATH, "r", encoding="utf-8") as f:
            return _json.load(f).get("favorites", [])
    except Exception:
        return []

def _save_favorites(favs: list) -> None:
    with open(_FAVORITES_PATH, "w", encoding="utf-8") as f:
        _json.dump({"favorites": favs}, f, ensure_ascii=False, indent=2)

# Auto-create favorites file if missing
if not _os.path.isfile(_FAVORITES_PATH):
    _save_favorites([])

NODE_CLASS_MAPPINGS: dict = {
    **_SAMPLER_NODES,
    **_IMAGE_NODES,
    **_VIDEO_NODES,
    **_LTX_NODES,
    **_FMLF_NODES,
    **_SAMPLER_LTX_NODES,
    **_STYLE_NODES,
}

NODE_DISPLAY_NAMES: dict = {
    "SamplerSchedulerIterator":  "Sampler Scheduler Iterator",
    "AlignedTextOverlayImages":  "Aligned Text Overlay Images",
    "AlignedTextOverlayVideo":   "Aligned Text Overlay Video",
    "LtxResolutionSelector":     "LTX Resolution Selector",
    "FmlfLtx23":                 "FMLFLTX_2.3",
    "SamplerLtxv23":             "SamplerLTXV_2.3",
    "AdvancedStyleSelector":     "Advanced Style Selector 🎨",
}

WEB_DIRECTORY = "./js"

try:
    from aiohttp import web
    from server import PromptServer

    @PromptServer.instance.routes.post("/rogala/refresh_sampler_config")
    async def _refresh_sampler_config(request):
        try:
            refresh_config()
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    @PromptServer.instance.routes.post("/rogala/reload_styles")
    async def _reload_styles(request):
        try:
            reload_styles()
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    @PromptServer.instance.routes.get("/rogala/styles")
    async def _get_styles(request):
        try:
            from .nodes.advanced_style_selector import _styles, _ensure_styles
            _ensure_styles()
            return web.json_response(_styles)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @PromptServer.instance.routes.get("/rogala/thumbnails/styles/{filename}")
    async def _get_thumbnail(request):
        import os
        from .nodes.advanced_style_selector import _THUMBS_DIR
        filename = request.match_info["filename"]
        path = os.path.join(_THUMBS_DIR, filename)
        if os.path.isfile(path):
            return web.FileResponse(path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
        return web.Response(status=404)

    @PromptServer.instance.routes.get("/rogala/favorites")
    async def _get_favorites(request):
        try:
            return web.json_response({"favorites": _load_favorites()})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @PromptServer.instance.routes.post("/rogala/favorites/toggle")
    async def _toggle_favorite(request):
        try:
            data = await request.json()
            key  = data.get("key", "").strip()
            if not key:
                return web.json_response({"error": "no key"}, status=400)
            favs = _load_favorites()
            if key in favs:
                favs.remove(key)
                added = False
            else:
                favs.append(key)
                added = True
            _save_favorites(favs)
            return web.json_response({"favorites": favs, "added": added})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    print("[rogala] API routes registered.")

except Exception as e:
    print(f"[rogala] WARNING: failed to register API routes — {e}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAMES", "WEB_DIRECTORY"]
