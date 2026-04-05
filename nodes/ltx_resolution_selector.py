"""
LtxResolutionSelector
=====================
Selects the correct input resolution and frame count for LTX Video models.

Supports three modes:
  - Dev (no upscale)  : standard LTX Dev resolutions, rounded to mult of 32
  - x1.5 Distilled   : input size that yields the target after x1.5 upscale
  - x2  Distilled    : input size that yields the target after x2  upscale

Category : rogala/Video
Version  : 2.0.0
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CATEGORY  = "rogala/Video"
_NODE_NAME = "LtxResolutionSelector"

# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

# DEV — display label → (actual_w, actual_h) rounded UP to nearest mult of 32
DEV_PRESETS: dict[str, tuple[int, int]] = {
    "640x360 (Landscape)":   (640,  384),
    "768x432 (Landscape)":   (768,  448),
    "864x480 (Landscape)":   (864,  480),
    "960x544 (Landscape)":   (960,  544),
    "1280x720 (Landscape)":  (1280, 736),
    "1920x1080 (Landscape)": (1920, 1088),
    "360x640 (Portrait)":    (384,  640),
    "432x768 (Portrait)":    (448,  768),
    "480x864 (Portrait)":    (480,  864),
    "544x960 (Portrait)":    (544,  960),
    "720x1280 (Portrait)":   (736,  1280),
    "1080x1920 (Portrait)":  (1088, 1920),
}

# UPSCALE — display label → { scale_factor: (input_w, input_h) }
UPSCALE_PRESETS: dict[str, dict[float, tuple[int, int]]] = {
    "960x544 (Landscape)":   {1.5: (640,  352),  2.0: (480,  272)},
    "1280x720 (Landscape)":  {1.5: (864,  480),  2.0: (640,  352)},
    "1920x1080 (Landscape)": {1.5: (1280, 720),  2.0: (960,  544)},
    "544x960 (Portrait)":    {1.5: (352,  640),  2.0: (272,  480)},
    "720x1280 (Portrait)":   {1.5: (480,  864),  2.0: (352,  640)},
    "1080x1920 (Portrait)":  {1.5: (720,  1280), 2.0: (544,  960)},
}

MODE_OPTIONS: list[str] = [
    "Dev (no upscale)",
    "x1.5 Distilled",
    "x2 Distilled",
]

DEV_TARGETS     = list(DEV_PRESETS.keys())
UPSCALE_TARGETS = list(UPSCALE_PRESETS.keys())

# ---------------------------------------------------------------------------
# Description shown in the ? popup (Markdown supported)
# ---------------------------------------------------------------------------
_DESCRIPTION = """\
## LTX Resolution Selector

Selects the correct **input resolution** and **frame count** for LTX Video models.
Supports Dev mode and Distilled upscale modes (x1.5 and x2).

---

### Inputs

| Pin | Default | Description |
|---|---|---|
| `mode` | Dev (no upscale) | Render mode — see table below. |
| `dev_target` | 960x544 | Target resolution for Dev mode (12 options). |
| `upscale_target` | 1920x1080 | Target resolution for Distilled modes (6 options). |
| `fps` | 24.0 | Frames per second (1–120). Passed through to output. |
| `duration_sec` | 5 | Clip duration in seconds (1–300). |

**mode options:**

| Value | Description |
|---|---|
| `Dev (no upscale)` | Standard LTX Dev sizes, rounded UP to nearest multiple of 32. |
| `x1.5 Distilled` | Returns input size needed to reach the target after x1.5 upscale. |
| `x2 Distilled` | Returns input size needed to reach the target after x2 upscale. |

### Outputs

| Pin | Type | Description |
|---|---|---|
| `width` | INT | Input width in pixels (multiple of 32). |
| `height` | INT | Input height in pixels (multiple of 32). |
| `length` | INT | Frame count: `1 + 8 x round(fps x sec / 8)`. |
| `fps` | FLOAT | Passthrough of the fps input. |

### Example

To render a 5-second clip at 1920x1080 using x2 Distilled:
- `mode` = `x2 Distilled`
- `upscale_target` = `1920x1080 (Landscape)`
- `fps` = 24, `duration_sec` = 5
- Node outputs: `width=960, height=544, length=121, fps=24`
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _calc_frame_count(fps: float, duration_sec: int) -> int:
    """Return LTX-compatible frame count: 1 + 8 * round(fps * sec / 8)."""
    return 1 + 8 * round(fps * duration_sec / 8)


# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

class LtxResolutionSelector:
    """
    Selects input resolution and frame count for LTX Video models.

    Inputs
    ------
    mode : STRING (enum)
        Render mode — Dev, x1.5 Distilled, or x2 Distilled.
    dev_target : STRING (enum)
        Target resolution when mode is Dev.
    upscale_target : STRING (enum)
        Target resolution when mode is x1.5 or x2 Distilled.
    fps : FLOAT
        Frames per second (passthrough to output).
    duration_sec : INT
        Desired clip duration in seconds.

    Outputs
    -------
    width : INT
        Input width in pixels (multiple of 32).
    height : INT
        Input height in pixels (multiple of 32).
    length : INT
        Frame count compatible with LTX scheduler.
    fps : FLOAT
        Passthrough of the fps input.
    """

    # ------------------------------------------------------------------
    # ComfyUI metadata
    # ------------------------------------------------------------------
    CATEGORY    = _CATEGORY
    FUNCTION    = "execute"
    DESCRIPTION = _DESCRIPTION

    RETURN_TYPES  = ("INT", "INT", "INT", "FLOAT")
    RETURN_NAMES  = ("width", "height", "length", "fps")

    # ------------------------------------------------------------------
    # Input definition
    # ------------------------------------------------------------------
    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {
                "mode": (
                    MODE_OPTIONS,
                    {
                        "default": "Dev (no upscale)",
                        "tooltip": "Rendering mode: Dev uses standard sizes; Distilled modes return the correct input size for the chosen upscale factor.",
                    },
                ),
                "dev_target": (
                    DEV_TARGETS,
                    {
                        "default": "960x544 (Landscape)",
                        "tooltip": "Target resolution for Dev (no upscale) mode.",
                    },
                ),
                "upscale_target": (
                    UPSCALE_TARGETS,
                    {
                        "default": "1920x1080 (Landscape)",
                        "tooltip": "Desired output resolution for x1.5 or x2 Distilled mode.",
                    },
                ),
                "fps": (
                    "FLOAT",
                    {
                        "default": 24.0,
                        "min": 1.0,
                        "max": 120.0,
                        "step": 0.01,
                        "tooltip": "Frames per second — used to calculate frame count and passed through to output.",
                    },
                ),
                "duration_sec": (
                    "INT",
                    {
                        "default": 5,
                        "min": 1,
                        "max": 300,
                        "step": 1,
                        "tooltip": "Clip duration in seconds — used to calculate frame count.",
                    },
                ),
            }
        }

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute(
        self,
        mode: str,
        dev_target: str,
        upscale_target: str,
        fps: float,
        duration_sec: int,
    ) -> tuple:
        """
        Resolve width/height based on mode and target, then compute frame count.

        Returns
        -------
        tuple[int, int, int, float]
            (width, height, length, fps)
        """
        if mode == "Dev (no upscale)":
            w, h = DEV_PRESETS[dev_target]
            print(f"[rogala/LtxResolutionSelector] DEV: {dev_target} → {w}x{h}")

        elif mode == "x1.5 Distilled":
            w, h = UPSCALE_PRESETS[upscale_target][1.5]
            print(f"[rogala/LtxResolutionSelector] x1.5: input {w}x{h} → target {upscale_target}")

        else:  # x2 Distilled
            w, h = UPSCALE_PRESETS[upscale_target][2.0]
            print(f"[rogala/LtxResolutionSelector] x2: input {w}x{h} → target {upscale_target}")

        length = _calc_frame_count(fps, duration_sec)
        print(f"[rogala/LtxResolutionSelector] fps={fps}, duration={duration_sec}s → frames={length}")

        return (w, h, length, fps)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS: dict = {
    "LtxResolutionSelector": LtxResolutionSelector,
}
