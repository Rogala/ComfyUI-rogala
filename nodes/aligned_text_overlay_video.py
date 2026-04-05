"""
AlignedTextOverlayVideo
=======================
Renders a multi-line text block onto every frame of a video tensor.

Supports the same template tags as AlignedTextOverlayImages (%NodeTitle.param%),
resolved from the active ComfyUI prompt, plus an optional external_text input.

Category : rogala/Video
Version  : 2.0.0
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import numpy as np
import torch
from PIL import Image, ImageDraw

from .aligned_text_overlay_images import _load_font, _resolve_template, _BG_RGB

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CATEGORY  = "rogala/Video"
_NODE_NAME = "AlignedTextOverlayVideo"

_TEXT_COLORS: list[str] = ["white", "gray", "black", "yellow", "cyan", "lime", "navy"]
_BG_COLORS:   list[str] = ["black", "gray", "white", "none"]

# ---------------------------------------------------------------------------
# Description
# ---------------------------------------------------------------------------
_DESCRIPTION = """\
## Aligned Text Overlay Video

Renders a **multi-line text block** onto **every frame** of a video tensor.
Supports `%NodeTitle.param%` template tags resolved from the active ComfyUI prompt.

---

### Inputs

| Pin | Default | Description |
|---|---|---|
| `images` | — | Video tensor (B, H, W, C) — connect VAE Decode output here. |
| `text_template` | see default | Template string with optional `%NodeTitle.param%` tags. |
| `vertical` | bottom | Vertical anchor: `top` or `bottom`. |
| `horizontal` | right | Horizontal anchor: `left` or `right`. |
| `font_size` | 16 | Font size in points (10–50). |
| `text_color` | white | Text colour. |
| `bg_color` | black | Background colour (`none` = transparent). |
| `bg_opacity` | 150 | Background opacity (50–250). |
| `first_frame_only` | false | When enabled, overlay is applied only to the first frame (fast preview). |
| `external_text` | — | Optional string appended after the resolved template. Connect **SamplerSchedulerIterator** here to embed the current sampler/scheduler pair. |

### Outputs

| Pin | Type | Description |
|---|---|---|
| `images` | IMAGE | Video tensor with text block superimposed on every frame. |

### Example

Connect this node between **VAE Decode** and **VHS Video Combine**:

```
VAE Decode -> AlignedTextOverlayVideo -> VHS Video Combine
```

Default template pulls values directly from a sampler node:

```
seed: %KSampler.seed% | steps: %KSampler.steps%
cfg: %KSampler.cfg% | %KSampler.sampler_name% | %KSampler.scheduler%
```

If your workflow has two samplers, rename them in the graph (right-click -> Title)
to e.g. `Sampler_1` / `Sampler_2` and reference them explicitly:

```
steps: %Sampler_1.steps%
```

NodeTitle must match the title shown on the node in the graph.
Sampler and scheduler values are always shown as readable names — the conversion
happens automatically.
"""

# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------
class AlignedTextOverlayVideo:
    """
    Renders a text block onto every frame of a video tensor.

    Uses the same template-tag system and font-loading logic as
    AlignedTextOverlayImages, but operates on batched IMAGE tensors
    produced by video-decoder nodes.

    Inputs
    ------
    images : IMAGE
        Video tensor (B, H, W, C) in float32 0-1 range.
    text_template : STRING
        Multi-line template. Use %NodeTitle.param% for dynamic values.
    vertical : STRING
        Vertical anchor — "top" or "bottom".
    horizontal : STRING
        Horizontal anchor — "left" or "right".
    font_size : INT
        Font size in points.
    text_color : STRING
        Colour name for the rendered text.
    bg_color : STRING
        Colour name for the background rectangle, or "none".
    bg_opacity : INT
        Alpha value for the background rectangle (50–250).
    first_frame_only : BOOLEAN
        When True only the first frame receives the overlay (fast preview).
    external_text : STRING (optional)
        Extra text appended to the resolved template.

    Outputs
    -------
    images : IMAGE
        Video tensor with text block composited onto every frame.
    """

    CATEGORY    = _CATEGORY
    FUNCTION    = "execute"
    DESCRIPTION = _DESCRIPTION

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("images",)

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {
                "images": ("IMAGE",),
                "text_template": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": (
                            "seed: %KSampler.seed% | steps: %KSampler.steps%\n"
                            "cfg: %KSampler.cfg% | %KSampler.sampler_name% | %KSampler.scheduler%"
                        ),
                        "tooltip": "Template text. Use %NodeTitle.param% to embed node values.",
                    },
                ),
                "vertical": (
                    ["bottom", "top"],
                    {
                        "default": "bottom",
                        "tooltip": "Vertical anchor for the text block.",
                    },
                ),
                "horizontal": (
                    ["right", "left"],
                    {
                        "default": "right",
                        "tooltip": "Horizontal anchor for the text block.",
                    },
                ),
                "font_size": (
                    "INT",
                    {
                        "default": 16,
                        "min": 10,
                        "max": 50,
                        "tooltip": "Font size in points.",
                    },
                ),
                "text_color": (
                    _TEXT_COLORS,
                    {
                        "default": "white",
                        "tooltip": "Text colour.",
                    },
                ),
                "bg_color": (
                    _BG_COLORS,
                    {
                        "default": "black",
                        "tooltip": "Background rectangle colour. Use 'none' for transparent.",
                    },
                ),
                "bg_opacity": (
                    "INT",
                    {
                        "default": 150,
                        "min": 50,
                        "max": 250,
                        "tooltip": "Background rectangle opacity (alpha value).",
                    },
                ),
                "first_frame_only": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "tooltip": (
                            "When enabled, only the first frame gets the overlay. "
                            "Use for fast preview before processing the full video."
                        ),
                    },
                ),
            },
            "optional": {
                "external_text": (
                    "STRING",
                    {
                        "forceInput": True,
                        "tooltip": (
                            "Extra text appended after the resolved template. "
                            "Connect SamplerSchedulerIterator here to embed "
                            "the current sampler/scheduler pair."
                        ),
                    },
                ),
            },
            "hidden": {
                "prompt":        "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def execute(
        self,
        images,
        text_template: str,
        vertical: str,
        horizontal: str,
        font_size: int,
        text_color: str,
        bg_color: str,
        bg_opacity: int,
        first_frame_only: bool = False,
        prompt=None,
        extra_pnginfo=None,
        external_text: str = "",
    ) -> tuple:
        """
        Resolve template tags, composite the text onto every video frame,
        and return the result as a float32 IMAGE tensor.

        Parameters
        ----------
        images : torch.Tensor
            Video tensor (B, H, W, C) in float32 0-1 range.
        text_template : str
            Raw template string with optional %NodeTitle.param% tags.
        vertical : str
            "top" or "bottom".
        horizontal : str
            "left" or "right".
        font_size : int
            Font size in points.
        text_color : str
            Colour name for the text.
        bg_color : str
            Colour name for the background rectangle, or "none".
        bg_opacity : int
            Alpha value for the background rectangle.
        first_frame_only : bool
            When True, only the first frame is processed.
        prompt : dict | None
            ComfyUI prompt dict injected via hidden input.
        extra_pnginfo : dict | None
            Workflow metadata injected via hidden input.
        external_text : str
            Extra text appended after the resolved template.

        Returns
        -------
        tuple[torch.Tensor]
            Single-element tuple containing the composited video tensor.
        """
        result_text = _resolve_template(text_template, prompt, extra_pnginfo)

        if external_text:
            sep = "" if (not result_text or result_text[-1] in (" ", "\n")) else " "
            result_text = f"{result_text}{sep}{external_text}"

        # Font and text dimensions are computed once for all frames
        font = _load_font(font_size)

        dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = dummy_draw.multiline_textbbox((0, 0), result_text, font=font)
        tw   = bbox[2] - bbox[0]
        th   = bbox[3] - bbox[1]
        pad  = 10
        mgn  = 10

        num_frames         = images.shape[0]
        frames_to_process  = 1 if first_frame_only else num_frames
        processed: list[np.ndarray] = []

        for i in range(num_frames):
            frame_np = images[i].cpu().numpy()  # (H, W, C) float32 0-1

            if i < frames_to_process:
                pixels  = np.clip(frame_np * 255.0, 0, 255).astype(np.uint8)
                img_pil = Image.fromarray(pixels).convert("RGBA")

                img_w, img_h = img_pil.size
                x = img_w - tw - pad * 2 - mgn if horizontal == "right" else mgn
                y = img_h - th - pad * 2 - mgn if vertical   == "bottom" else mgn

                txt_layer = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
                draw      = ImageDraw.Draw(txt_layer)

                if bg_color != "none":
                    rgb = _BG_RGB.get(bg_color, (0, 0, 0))
                    draw.rectangle(
                        [x, y, x + tw + pad * 2, y + th + pad * 2],
                        fill=(rgb[0], rgb[1], rgb[2], bg_opacity),
                    )

                draw.multiline_text(
                    (x + pad, y + pad), result_text, fill=text_color, font=font
                )

                composited = Image.alpha_composite(img_pil, txt_layer).convert("RGB")
                out_np = np.array(composited).astype(np.float32) / 255.0
            else:
                out_np = frame_np  # first_frame_only=True — copy unchanged

            processed.append(out_np)

        result_tensor = torch.from_numpy(np.stack(processed, axis=0))
        return (result_tensor,)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS: dict = {
    "AlignedTextOverlayVideo": AlignedTextOverlayVideo,
}
