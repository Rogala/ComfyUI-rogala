"""
AlignedTextOverlay
==================
Renders a multi-line text block onto an image at a chosen corner.

Supports template tags that resolve values from the active ComfyUI prompt,
plus an optional external_text input (e.g. from SamplerSchedulerIterator).

Category : rogala/Image
Version  : 1.1.0
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import re

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont

import comfy.samplers

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CATEGORY  = "rogala/Image"
_NODE_NAME = "AlignedTextOverlay"

_TEXT_COLORS: list[str] = ["white", "gray", "black", "yellow", "cyan", "lime", "navy"]
_BG_COLORS:   list[str] = ["black", "gray", "white", "none"]

_BG_RGB: dict[str, tuple[int, int, int]] = {
    "black": (0,   0,   0),
    "gray":  (64,  64,  64),
    "white": (255, 255, 255),
}

# ---------------------------------------------------------------------------
# Description shown in the ? popup (Markdown supported)
# ---------------------------------------------------------------------------
_DESCRIPTION = """\
## Aligned Text Overlay

Renders a **multi-line text block** onto an image at a chosen corner before saving.
Supports `%NodeTitle.param%` template tags resolved from the active ComfyUI prompt.

---

### Inputs

| Pin | Default | Description |
|---|---|---|
| `image` | — | Input image tensor. |
| `text_template` | see default | Template string with optional `%Node.param%` tags. |
| `vertical` | bottom | Vertical anchor: `top` or `bottom`. |
| `horizontal` | right | Horizontal anchor: `left` or `right`. |
| `font_size` | 16 | Font size in points (10–50). |
| `text_color` | white | Text colour. |
| `bg_color` | black | Background colour (`none` = transparent). |
| `bg_opacity` | 150 | Background opacity (50–250). |
| `external_text` | — | Optional string appended after the resolved template. |

### Outputs

| Pin | Type | Description |
|---|---|---|
| `image` | IMAGE | Outputs an image with a text block superimposed on top. |

### Example

Default template pulls values directly from a KSampler node:

```
seed: %KSampler.seed% | steps: %KSampler.steps%
cfg: %KSampler.cfg% | %KSampler.sampler_name% | %KSampler.scheduler%
```

`NodeTitle` must match the title shown on the node in the graph.
Numeric sampler / scheduler indices are decoded to names automatically.
Connect `external_text` from **SamplerSchedulerIterator** to append
the current `"sampler | scheduler"` pair to the overlay.
"""

# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

class AlignedTextOverlay:
    """
    Renders a text block onto an image.

    Template tags (%NodeTitle.param%) are resolved from the active ComfyUI
    prompt. Numeric sampler/scheduler indices are decoded via utils.py.
    An optional external_text input appends extra content (e.g. from
    SamplerSchedulerIterator).

    Inputs
    ------
    image : IMAGE
        Input image tensor (B, H, W, C).
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
    external_text : STRING (optional)
        Extra text appended to the resolved template.

    Outputs
    -------
    image : IMAGE
        Outputs an image with a text block superimposed on top.
    """

    # ------------------------------------------------------------------
    # ComfyUI metadata
    # ------------------------------------------------------------------
    CATEGORY     = _CATEGORY
    FUNCTION     = "execute"
    DESCRIPTION  = _DESCRIPTION

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)

    # ------------------------------------------------------------------
    # Input definition
    # ------------------------------------------------------------------
    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {
                "image": ("IMAGE",),
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
            },
            "optional": {
                "external_text": (
                    "STRING",
                    {
                        "forceInput": True,
                        "tooltip": "Extra text appended after the resolved template (e.g. from SamplerSchedulerIterator).",
                    },
                ),
            },
            "hidden": {
                "prompt":        "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute(
        self,
        image,
        text_template: str,
        vertical: str,
        horizontal: str,
        font_size: int,
        text_color: str,
        bg_color: str,
        bg_opacity: int,
        prompt=None,
        extra_pnginfo=None,
        external_text: str = "",
    ) -> tuple:
        """
        Resolve template tags, composite the text onto the image, and return
        the result as a float32 IMAGE tensor.

        Returns
        -------
        tuple[torch.Tensor]
            Single-element tuple containing the composited image.
        """
        result_text = self._resolve_template(
            text_template, prompt, extra_pnginfo
        )

        # Append external_text (already a plain string — no decoding needed)
        if external_text:
            sep = "" if (not result_text or result_text[-1] in (" ", "\n")) else " "
            result_text = f"{result_text}{sep}{external_text}"

        # -- PIL image setup --
        pixels  = 255.0 * image[0].cpu().numpy()
        img_pil = Image.fromarray(
            np.clip(pixels, 0, 255).astype(np.uint8)
        ).convert("RGBA")

        # -- font --
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        # -- measure text --
        dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        bbox = dummy_draw.multiline_textbbox((0, 0), result_text, font=font)
        tw   = bbox[2] - bbox[0]
        th   = bbox[3] - bbox[1]
        pad  = 10
        mgn  = 10

        # -- position --
        img_w, img_h = img_pil.size
        x = img_w - tw - pad * 2 - mgn if horizontal == "right" else mgn
        y = img_h - th - pad * 2 - mgn if vertical   == "bottom" else mgn

        # -- composite layer --
        txt_layer = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
        draw      = ImageDraw.Draw(txt_layer)

        if bg_color != "none":
            rgb = _BG_RGB.get(bg_color, (0, 0, 0))
            draw.rectangle(
                [x, y, x + tw + pad * 2, y + th + pad * 2],
                fill=(rgb[0], rgb[1], rgb[2], bg_opacity),
            )

        draw.multiline_text((x + pad, y + pad), result_text, fill=text_color, font=font)

        composited = Image.alpha_composite(img_pil, txt_layer).convert("RGB")
        result = (
            torch.from_numpy(
                np.array(composited).astype(np.float32) / 255.0
            ).unsqueeze(0)
        )

        return (result,)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_template(
        self,
        template: str,
        prompt: dict | None,
        extra_pnginfo: dict | None,
    ) -> str:
        """
        Replace all %NodeTitle.param% tags with values from the active prompt.

        Numeric sampler/scheduler values are decoded to string names using
        the lists from config/sampler_scheduler.json.

        Parameters
        ----------
        template : str
            Raw template string.
        prompt : dict | None
            ComfyUI prompt dict (node_id → node_data).
        extra_pnginfo : dict | None
            Extra PNG info containing workflow node titles.

        Returns
        -------
        str
            Template with all resolvable tags replaced.
        """
        if prompt is None:
            return template

        samplers   = list(comfy.samplers.KSampler.SAMPLERS)
        schedulers = list(comfy.samplers.KSampler.SCHEDULERS)

        # Build title → node_id lookup from workflow metadata
        title_map: dict[str, str] = {}
        if extra_pnginfo and "workflow" in extra_pnginfo:
            for n in extra_pnginfo["workflow"]["nodes"]:
                node_id = str(n["id"])
                title   = n.get("title", n.get("type", ""))
                title_map[node_id] = title

        tags = re.findall(r"%([\w\s\(\)\-]+)\.([\w\s\-]+)%", template)
        result = template

        for node_name, param_name in tags:
            val = self._find_param(
                node_name, param_name, prompt, title_map, samplers, schedulers
            )
            if val is not None:
                if isinstance(val, list):
                    val = val[0]
                result = result.replace(f"%{node_name}.{param_name}%", str(val))

        return result

    def _find_param(
        self,
        node_name: str,
        param_name: str,
        prompt: dict,
        title_map: dict[str, str],
        samplers: list[str],
        schedulers: list[str],
    ):
        """
        Search all prompt nodes for one matching node_name and return
        the value of param_name from its inputs.

        Returns None if not found.
        """
        for node_id, node_data in prompt.items():
            title      = title_map.get(str(node_id), "")
            class_type = node_data.get("class_type", "")

            if title == node_name or class_type == node_name:
                inputs = node_data.get("inputs", {})
                if param_name not in inputs:
                    continue

                val = inputs[param_name]

                # Decode numeric indices returned by some ComfyUI versions
                if isinstance(val, int):
                    if "sampler" in param_name.lower() and val < len(samplers):
                        val = samplers[val]
                    elif "scheduler" in param_name.lower() and val < len(schedulers):
                        val = schedulers[val]

                return val

        return None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS: dict = {
    "AlignedTextOverlay": AlignedTextOverlay,
}
