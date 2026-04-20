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

NODE_CLASS_MAPPINGS: dict = {
    **_SAMPLER_NODES,
    **_IMAGE_NODES,
    **_VIDEO_NODES,
    **_LTX_NODES,
    **_FMLF_NODES,
    **_SAMPLER_LTX_NODES,
}

NODE_DISPLAY_NAMES: dict = {
    "SamplerSchedulerIterator":  "Sampler Scheduler Iterator",
    "AlignedTextOverlayImages":  "Aligned Text Overlay Images",
    "AlignedTextOverlayVideo":   "Aligned Text Overlay Video",
    "LtxResolutionSelector":     "LTX Resolution Selector",
    "FmlfLtx23":                 "FMLFLTX_2.3",
    "SamplerLtxv23":             "SamplerLTXV_2.3",
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

    print("[rogala] API route registered: POST /rogala/refresh_sampler_config")

except Exception as e:
    print(f"[rogala] WARNING: failed to register API routes — {e}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAMES", "WEB_DIRECTORY"]
