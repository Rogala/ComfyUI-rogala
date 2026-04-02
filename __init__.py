"""
ComfyUI-rogala
==============
Custom node pack for ComfyUI by rogala.

All nodes follow a unified structure:
- Category  : rogala/<subcategory>
- Node name : PascalCase, no prefix (e.g. SamplerSchedulerIterator)
- Display   : "Readable Name [rogala]"
- Docs      : English only, DESCRIPTION field + doc_popup.js
- Menu      : Single top-level entry "rogala"
"""

# ---------------------------------------------------------------------------
# Node imports
# ---------------------------------------------------------------------------
from .nodes.sampler_scheduler_iterator import NODE_CLASS_MAPPINGS as _SAMPLER_NODES
from .nodes.sampler_scheduler_iterator import refresh_config
from .nodes.aligned_text_overlay       import NODE_CLASS_MAPPINGS as _TEXT_NODES
from .nodes.ltx_resolution_selector    import NODE_CLASS_MAPPINGS as _VIDEO_NODES

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS: dict = {
    **_SAMPLER_NODES,
    **_TEXT_NODES,
    **_VIDEO_NODES,
}

NODE_DISPLAY_NAMES: dict = {
    "SamplerSchedulerIterator": "Sampler Scheduler Iterator [rogala]",
    "AlignedTextOverlay":       "Aligned Text Overlay [rogala]",
    "LtxResolutionSelector":    "LTX Resolution Selector [rogala]",
}

# ---------------------------------------------------------------------------
# Web extensions (JS)
# ---------------------------------------------------------------------------
WEB_DIRECTORY = "./js"

# ---------------------------------------------------------------------------
# Custom API routes
# ---------------------------------------------------------------------------
try:
    from aiohttp import web
    from server import PromptServer

    @PromptServer.instance.routes.post("/rogala/refresh_sampler_config")
    async def _refresh_sampler_config(request):
        """
        Regenerate config/sampler_scheduler.json from the live KSampler lists.
        Called by the Refresh button on SamplerSchedulerIterator.
        """
        try:
            refresh_config()
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "message": str(e)}, status=500)

except Exception:
    pass  # Server not available during testing / offline import

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAMES", "WEB_DIRECTORY"]
