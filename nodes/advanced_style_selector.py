"""
AdvancedStyleSelector
=====================
Applies one or more visual styles to positive/negative prompts and
encodes them directly to CONDITIONING — no extra CLIPTextEncode needed.

Features
--------
- Loads styles from config/styles.json (category, name, prompt, negative_prompt)
- Up to 6 styles selected simultaneously via gallery UI (see JS widget)
- Manual mode  : select styles by clicking thumbnails in the gallery
- Iterator mode: cycles through all styles in selected categories
                 automatically (one per queue run), stops when done
- use_negative  : ON  → encode negative text normally
                  OFF → output ConditioningZeroOut (for Flux / SD3 etc.)
- Prompt logic  : if style prompt contains {prompt} → user text is inserted
                  at that position; otherwise user text is prepended
- style_name output: active style names joined with hyphens, spaces→underscores
                  e.g. "anime-cinematic-watercolor_cartoon"

Inputs
------
clip          CLIP model (from Load Checkpoint)

Outputs
-------
positive      CONDITIONING
negative      CONDITIONING  (or ZeroOut when use_negative=False)
style_name    STRING  — active style names for file naming

Category : rogala/Prompting
Version  : 1.0.0
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import json
import os
import random
import re
from datetime import datetime

import torch

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CATEGORY  = "rogala/Prompting"
_NODE_NAME = "AdvancedStyleSelector"

_CONFIG_DIR   = os.path.join(os.path.dirname(__file__), "..", "config")
_STYLES_PATH  = os.path.join(_CONFIG_DIR, "styles.json")
_THUMBS_DIR   = os.path.join(os.path.dirname(__file__), "..", "thumbnails", "styles")

# ---------------------------------------------------------------------------
# Description (shown in ? popup)
# ---------------------------------------------------------------------------
_DESCRIPTION = """\
## Advanced Style Selector

Applies visual styles to your prompt and outputs **CONDITIONING** directly —
no extra CLIPTextEncode node needed.

---

### Inputs

| Pin  | Type | Description |
|------|------|-------------|
| `clip` | CLIP | Connect from Load Checkpoint |

### Outputs

| Pin | Type | Description |
|-----|------|-------------|
| `positive` | CONDITIONING | Encoded positive prompt with styles applied |
| `negative` | CONDITIONING | Encoded negative prompt (or ZeroOut) |
| `style_name` | STRING | Active style names joined by `-` for file naming |

---

### Style prompt logic

- If style prompt contains `{prompt}` → your text replaces `{prompt}`
- Otherwise → `your text, style keywords`

### Negative conditioning

- **use_negative ON**  → negative text encoded normally via CLIP
- **use_negative OFF** → outputs ConditioningZeroOut (recommended for Flux, SD3)

### Modes

- **Manual**   → select up to 6 styles by clicking thumbnails in the gallery
- **Iterator** → cycles through all styles in checked categories one per run,
  stops automatically after the last style

### name_timestamp

When enabled, appends a timestamp to `style_name` output:
`abstract_20250424_143022` — guarantees unique filenames when connected to Save Image.

### Favorites

Click ⭐ on any thumbnail to add it to Favorites. Favorites are saved to
`config/favorites_styles.json` and appear as a separate category at the top
of the category list. Click ⭐ again to remove.

---

Styles are loaded from `config/styles.json`.
Thumbnails are loaded from `thumbnails/styles/*.jpg`.
Favorites are saved to `config/favorites_styles.json`.
"""

# ---------------------------------------------------------------------------
# Style loader
# ---------------------------------------------------------------------------

def _load_styles(path: str) -> list[dict]:
    """Load and return styles list from JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        print(f"[AdvancedStyleSelector] Cannot load styles: {e}")
        return []


def _get_categories(styles: list[dict]) -> list[str]:
    seen = []
    for s in styles:
        c = s.get("category", "Other")
        if c not in seen:
            seen.append(c)
    return sorted(seen)


def _styles_in_categories(styles: list[dict], categories: list[str]) -> list[dict]:
    if not categories:
        return styles
    return [s for s in styles if s.get("category", "Other") in categories]


def _find_style(styles: list[dict], key: str) -> dict | None:
    """
    Find a style by either 'category::name' (new format from v11 JS widget)
    or plain 'name' (legacy format, also used as fallback if no '::' in key).
    """
    if not key:
        return None
    if "::" in key:
        category, name = key.split("::", 1)
        for s in styles:
            if s.get("name") == name and s.get("category", "Other") == category:
                return s
        # category mismatch — fall through to name-only search
        for s in styles:
            if s.get("name") == name:
                return s
        return None
    # Legacy: match by name only
    for s in styles:
        if s.get("name") == key:
            return s
    return None

# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------

def _apply_style_to_prompt(user_text: str, style_prompt: str) -> str:
    """Insert user text into style prompt or prepend it."""
    if not style_prompt:
        return user_text
    if "{prompt}" in style_prompt:
        return style_prompt.replace("{prompt}", user_text)
    if user_text:
        return f"{user_text}, {style_prompt}"
    return style_prompt


def _build_prompts(
    positive_text: str,
    negative_text: str,
    selected_styles: list[dict],
) -> tuple[str, str]:
    """
    Merge user text with all selected styles.
    Positive: each style applied in sequence (chained).
    Negative: union of all style negatives + user negative.
    """
    pos = positive_text.strip()
    for style in selected_styles:
        pos = _apply_style_to_prompt(pos, style.get("prompt", "").strip())

    neg_parts = [negative_text.strip()] if negative_text.strip() else []
    for style in selected_styles:
        sn = style.get("negative_prompt", "").strip()
        if sn and sn not in neg_parts:
            neg_parts.append(sn)
    neg = ", ".join(neg_parts)

    return pos, neg


def _make_style_name(selected_styles):
    """Build file-safe style name — matches thumbnail filename format."""
    parts = []
    for s in selected_styles:
        name = s.get("name", "unknown").lower().strip()
        name = re.sub(r"[^\w\s\-]", "", name)
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"_+", "_", name)
        name = re.sub(r"\-+", "-", name)
        parts.append(name)
    return "-".join(parts) if parts else "no_style"

# ---------------------------------------------------------------------------
# CLIP encoding helpers
# ---------------------------------------------------------------------------

def _encode(clip, text: str):
    """Encode text to CONDITIONING."""
    tokens = clip.tokenize(text)
    cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
    return [[cond, {"pooled_output": pooled}]]


def _zero_out(clip, text: str):
    """Return ConditioningZeroOut equivalent."""
    tokens = clip.tokenize(text)
    cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
    zeros = torch.zeros_like(cond)
    out = {"pooled_output": torch.zeros_like(pooled)} if pooled is not None else {}
    return [[zeros, out]]

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------
_styles:    list[dict] = []
_styles_path: str      = ""
_iter_index: int       = 0
_iter_reset: bool      = False


def _ensure_styles():
    global _styles, _styles_path
    if not _styles or _styles_path != _STYLES_PATH:
        _styles = _load_styles(_STYLES_PATH)
        _styles_path = _STYLES_PATH
        print(f"[AdvancedStyleSelector] Loaded {len(_styles)} styles.")


def reload_styles():
    """Called by API route to hot-reload styles."""
    global _styles, _styles_path, _iter_index, _iter_reset
    _styles = _load_styles(_STYLES_PATH)
    _styles_path = _STYLES_PATH
    _iter_index = 0
    _iter_reset = True
    print(f"[AdvancedStyleSelector] Reloaded {len(_styles)} styles.")

# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

class AdvancedStyleSelector:
    """
    Applies visual styles to prompts and outputs CONDITIONING directly.

    Supports manual multi-select (up to 6 styles) and iterator mode
    (cycles through all styles in selected categories automatically).
    """

    CATEGORY    = _CATEGORY
    FUNCTION    = "execute"
    DESCRIPTION = _DESCRIPTION
    OUTPUT_NODE = True

    RETURN_TYPES  = ("CONDITIONING", "CONDITIONING", "STRING")
    RETURN_NAMES  = ("positive", "negative", "style_name")
    MIN_WIDTH     = 560

    @classmethod
    def INPUT_TYPES(cls):
        _ensure_styles()
        categories = _get_categories(_styles)

        return {
            "required": {
                "clip": ("CLIP",),
                "positive_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "dynamicPrompts": True,
                    "tooltip": "Your positive prompt. Styles will be applied on top.",
                }),
                "negative_text": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "dynamicPrompts": True,
                    "tooltip": "Your negative prompt. Hidden when use_negative is OFF.",
                }),
                "use_negative": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "ON: encode negative normally. OFF: output ConditioningZeroOut (for Flux/SD3).",
                }),
                # --- mode ---
                "mode": (["Manual", "Iterator"], {"default": "Manual"}),
                # --- manual selection (synced by JS widget) ---
                "style_1": ("STRING", {"default": "", "tooltip": "Selected style slot 1"}),
                "style_2": ("STRING", {"default": "", "tooltip": "Selected style slot 2"}),
                "style_3": ("STRING", {"default": "", "tooltip": "Selected style slot 3"}),
                "style_4": ("STRING", {"default": "", "tooltip": "Selected style slot 4"}),
                "style_5": ("STRING", {"default": "", "tooltip": "Selected style slot 5"}),
                "style_6": ("STRING", {"default": "", "tooltip": "Selected style slot 6"}),
                # --- iterator ---
                "iterator_categories": ("STRING", {
                    "default": "",
                    "tooltip": "Comma-separated categories to iterate. Empty = all.",
                }),
                "iterator_seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xFFFFFFFF,
                    "tooltip": "Seed for shuffling iterator order (0 = alphabetical).",
                }),
                "append_counter": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Append a timestamp to style_name output for unique filenames (e.g. abstract_20250424_143022).",
                }),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        if kwargs.get("mode") == "Iterator":
            return random.random()
        return None

    def execute(
        self,
        clip,
        positive_text: str,
        negative_text: str,
        use_negative: bool,
        mode: str,
        style_1: str,
        style_2: str,
        style_3: str,
        style_4: str,
        style_5: str,
        style_6: str,
        iterator_categories: str,
        iterator_seed: int,
        append_counter: bool,
    ):
        global _iter_index, _iter_reset
        _ensure_styles()

        # ── Resolve active styles ──────────────────────────────────────────
        if mode == "Iterator":
            cats = [c.strip() for c in iterator_categories.split(",") if c.strip()]
            pool = _styles_in_categories(_styles, cats) if cats else _styles

            if not pool:
                print("[AdvancedStyleSelector] Iterator: no styles in pool.")
                pos_cond = _encode(clip, positive_text)
                neg_cond = _encode(clip, negative_text) if use_negative else _zero_out(clip, negative_text)
                return {
                    "ui": {"text": ("No styles",), "done": (True,)},
                    "result": (pos_cond, neg_cond, "no_style"),
                }

            # Reset if requested
            if _iter_reset:
                _iter_index = 0
                _iter_reset = False

            if _iter_index >= len(pool):
                _iter_index = 0

            selected_styles = [pool[_iter_index]]
            current_idx     = _iter_index
            _iter_index    += 1
            done            = _iter_index >= len(pool)

            if done:
                _iter_index = 0

            progress = f"{'DONE — ' if done else ''}Step {current_idx + 1} / {len(pool)}"
            print(f"[AdvancedStyleSelector] Iterator: {progress} — {selected_styles[0]['name']}")

        else:
            # Manual mode
            selected_styles = []
            for slot_name in (style_1, style_2, style_3, style_4, style_5, style_6):
                if slot_name.strip():
                    s = _find_style(_styles, slot_name.strip())
                    if s:
                        selected_styles.append(s)
            done    = False
            progress = f"{len(selected_styles)} style(s) active"

        # ── Build prompts ──────────────────────────────────────────────────
        final_pos, final_neg = _build_prompts(
            positive_text, negative_text, selected_styles
        )

        # ── Encode ────────────────────────────────────────────────────────
        pos_cond = _encode(clip, final_pos)
        neg_cond = _encode(clip, final_neg) if use_negative else _zero_out(clip, final_neg)

        # ── Style name for file naming ─────────────────────────────────────
        base_name = _make_style_name(selected_styles)
        if append_counter:
            style_name = f"{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            style_name = base_name

        return {
            "ui":     {"text": (progress,), "done": (done,)},
            "result": (pos_cond, neg_cond, style_name),
        }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS: dict = {
    "AdvancedStyleSelector": AdvancedStyleSelector,
}
