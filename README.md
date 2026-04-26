# ComfyUI-rogala

Custom node pack for [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

## Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/rogala/ComfyUI-rogala
```

Restart ComfyUI. All nodes appear under the **rogala** menu.

## Project structure

```
ComfyUI-rogala/
├── __init__.py          # Entry point — registers all nodes
├── pyproject.toml       # Package metadata
├── fonts/               # Fonts used by text overlay nodes
│   └── *.ttf            # Place any TTF font file here
├── nodes/               # One .py file per node (or logical group)
│   └── _template.py     # Copy this to create a new node
├── js/                  # Frontend extensions loaded by ComfyUI
├── config/              # JSON configuration files
│   └── categories.json  # Category definitions
└── web/                 # Static web assets (CSS, icons) if needed
```
---

# Advanced Style Selector 🎨

A custom ComfyUI node for visual style selection with a built-in thumbnail gallery. Applies one or more styles to positive/negative prompts and encodes them directly to **CONDITIONING** — no extra CLIPTextEncode node needed.

---

## Features

- **Visual gallery** — browse styles as thumbnails with category filtering and search
- **Up to 6 styles simultaneously** — selected styles are merged into a single conditioning output
- **Two modes** — Manual (click to select) and Iterator (cycles through styles automatically, one per queue run)
- **Favorites** — click ⭐ on any thumbnail to save it to `config/favorites_styles.json`, appears as a separate category at the top
- **name_timestamp** — optional checkbox to append a timestamp to `style_name` output for unique filenames when connected to Save Image
- **save_prompt** — optional checkbox to save positive and negative prompts to a JSON file in `output/prompts/` after each run
- **Category colors** — each category has a unique color across the full hue wheel
- **Hover popup** — shows full prompt and negative prompt text on thumbnail hover
- **Live reload** — reload styles from disk without restarting ComfyUI
- **Model thumbnail presets** — create a subfolder in `thumbnails/` named after your model (e.g. `FLUX_1`, `WAN_2_2`) and place style thumbnails there. Select the preset from the dropdown in the node — missing thumbnails fall back to the base `styles/` folder. Folder names: letters, digits and underscores only.
- **Theme aware** — follows ComfyUI light/dark theme via CSS variables
- **Resizable** — gallery height grows with the node when you drag it taller
- **Negative conditioning control** — toggle between encoded negative or ConditioningZeroOut (for Flux, SD3, etc.)
- **Styles format** — `config/styles.json`, each entry has `name`, `category`, `prompt`, `negative_prompt`, `thumbnail`. Use `{prompt}` in prompt field to insert user text at a specific position.
- **Installation** — Find the node under **rogala/Prompting → Advanced Style Selector**

---

<img width="1502" height="844" alt="style2" src="https://github.com/user-attachments/assets/4a2182ad-aa45-4066-b2a4-f64cdca9a6de" />

---

## Inputs

| Pin | Type | Description |
|-----|------|-------------|
| `clip` | CLIP | Connect from Load Checkpoint |
| `positive_text` | STRING | Your positive prompt. Styles are applied on top. |
| `negative_text` | STRING | Your negative prompt. Hidden when use_negative is OFF. |

### Hidden widget inputs (controlled by the gallery UI)

| Widget | Description |
|--------|-------------|
| `use_negative` | ON: encode negative normally. OFF: output ConditioningZeroOut |
| `mode` | Manual or Iterator |
| `style_1` … `style_6` | Active style slots (synced by the gallery) |
| `iterator_categories` | Comma-separated categories to iterate over (empty = all) |
| `iterator_seed` | Seed for iterator order (0 = alphabetical) |
| `append_counter` | Enable name_timestamp suffix on style_name output |

---

## Outputs

| Pin | Type | Description |
|-----|------|-------------|
| `positive` | CONDITIONING | Encoded positive prompt with all selected styles applied |
| `negative` | CONDITIONING | Encoded negative prompt, or ConditioningZeroOut |
| `style_name` | STRING | Active style names joined by `-` for use in file naming |

---

## Modes

### Manual
Select up to 6 styles by clicking thumbnails in the gallery. Active styles appear in the strip at the top of the panel as thumbnails with their slot number. Click `×` to remove a style, or use the 🗑 button to clear all.

### Iterator
Cycles through all styles in the selected categories automatically — one style per queue run. Stops after the last style and resets. Use **Reload Styles** after changing the style list to reset the iterator.

---

## Gallery UI

| Element | Description |
|---------|-------------|
| 🗑 (left of categories) | Clear selected category filters |
| Category pills | Click to filter gallery by category. Active categories are highlighted in their category color |
| ⭐ Favorites | First category if non-empty. Click ⭐ on any thumbnail to add/remove |
| Active strip | Shows currently selected styles as thumbnails. Hover for prompt details |
| 🗑 (in strip) | Clear all selected styles |
| Search | Filter by style name |
| Thumbnail grid | Click to select/deselect. Badge shows slot number (1–6) |
| `use_negative` | Toggle negative conditioning mode |
| `name_timestamp` | Toggle timestamp suffix on style_name output |
| Mode selector | Switch between Manual and Iterator |
| Reload Styles | Hot-reload `config/styles.json` without restarting ComfyUI |

---

## Script for Aligning Nodes

A lightweight frontend extension that adds a persistent toolbar at the bottom of the canvas
for aligning, distributing, and resizing selected nodes.

![Capture](https://github.com/user-attachments/assets/d44a254b-6e57-4bf7-8aa3-e46cc6bc0ffa)

**Features:** align left / right / top / bottom · distribute horizontally and vertically
(gap-aware, not center-based) · match width to widest node (aligns to leftmost) · deselect all

The toolbar auto-scales based on screen resolution (1080p / 2K / 4K) and includes manual
size control (5 levels, −2 to +2) so the buttons stay comfortable at any display density.
Localized tooltips (EN, UK-UA, DE, FR, ES, IT, PT-BR, ZH, JA)

> Independent implementation inspired by [KayTool](https://github.com/kk8bit/kaytool)
> (kk8bit) and [ComfyUI-NodeAligner](https://github.com/Tenney95/ComfyUI-NodeAligner)
> (Tenney95). No shared code — similar idea, different approach.

---

## LTX Video 2.3 — FMLFLTX + SamplerLTXV

A two-node pipeline for LTX Video 2.3 distilled models with spatial upscaling.
**FMLFLTX_2.3** prepares the latent space from up to 6 guide images.
**SamplerLTXV_2.3** runs a two-pass denoise — low resolution first, then upscale and refinement.

Inspired by the workflows of [WhatDreamsCost](https://github.com/WhatDreamsCost/WhatDreamsCost-ComfyUI)
and [princepainter](https://github.com/princepainter/ComfyUI-PainterLTXV2).

---

### FMLFLTX_2.3

Loads up to 6 guide images and distributes them evenly across the video timeline.
Outputs video and audio latents ready for **SamplerLTXV_2.3**.

#### Inputs

| Pin | Default | Description |
|---|---|---|
| `video_vae` | — | Video VAE for image encoding. |
| `audio_vae` | — | Audio VAE for empty audio latent creation. |
| `img_compression` | 18 | JPEG pre-compression strength (0 = disabled). |
| `width` | 768 | Latent width — connect from **LTX Resolution Selector**. |
| `height` | 512 | Latent height — connect from **LTX Resolution Selector**. |
| `length` | 97 | Frame count — connect from **LTX Resolution Selector**. |
| `fps` | 25.0 | Frames per second — connect from **LTX Resolution Selector**. |
| `batch_size` | 1 | Batch size. |
| `image_1 … image_6` | — | Guide images (optional). Connect only the slots you need. |
| `strength_1 … strength_6` | 1.0 | Conditioning strength per image (1.0 = fully conditioned). |

#### Frame placement

Images are placed at evenly-spaced positions across the full video duration:

| Images connected | Placement |
|---|---|
| 1 | frame 0 |
| 2 | 0%, 50% |
| 3 | 0%, 33%, 66% |
| 4 | 0%, 25%, 50%, 75% |
| 5 | 0%, 20%, 40%, 60%, 80% |
| 6 | 0%, 17%, 33%, 50%, 67%, 83% |

Recommended number of images by video duration (targeting ~8 sec per image):

| Duration | Images | Interval |
|---|---|---|
| 10–15 sec | 2 | ~7 sec |
| 20–25 sec | 3 | ~8 sec |
| 30–35 sec | 4 | ~8 sec |
| 40–50 sec | 5–6 | ~8 sec |
| 50–60 sec | 6 | ~8–10 sec |

#### Outputs

| Pin | Description |
|---|---|
| `latent` | Combined video + audio NestedTensor (legacy). |
| `video_latent` | Video latent → connect to **SamplerLTXV_2.3** `video_latent`. |
| `audio_latent` | Empty audio latent → connect to **SamplerLTXV_2.3** `audio_latent`. |

---

<img width="1834" height="871" alt="Знімок екрана (53)" src="https://github.com/user-attachments/assets/1530ff46-81bd-41f7-84e6-61d5a1fde3f8" />

---

### SamplerLTXV_2.3

Two-pass sampler for LTX Video 2.3 distilled models.

**Pass 1** — full denoise at the input resolution (video + audio NestedTensor).  
**Pass 2** — spatial upscale, re-embed first/last frames at upscaled resolution, refinement denoise.

#### Inputs

| Pin | Description |
|---|---|
| `model` | Diffusion model. |
| `video_vae` | Video VAE — used for image encoding and upscale statistics. |
| `positive` | Positive conditioning. |
| `negative` | Negative conditioning. |
| `video_latent` | Connect from **FMLFLTX_2.3** `video_latent`. |
| `audio_latent` | Connect from **FMLFLTX_2.3** `audio_latent`. |
| `start_image` | First frame re-embedded after upscale (optional). |
| `end_image` | Last frame re-embedded after upscale (optional). |
| `upscale_model` | Latent upscale model for pass 2 (optional). |

**Pass 1 parameters**

| Parameter | Default | Description |
|---|---|---|
| `add_noise_1` | enable | Add noise before pass 1. |
| `noise_seed_1` | 0 | Noise seed for pass 1. |
| `steps_1` | 8 | Denoising steps for pass 1. |
| `cfg_1` | 1.0 | CFG scale for pass 1. |
| `sampler_name_1` | euler | Sampler for pass 1. |
| `scheduler_1` | linear_quadratic | Scheduler for pass 1. |
| `denoise_1` | 1.0 | Denoise strength for pass 1. |

**Pass 2 parameters**

| Parameter | Default | Description |
|---|---|---|
| `add_noise_2` | enable | Add noise before pass 2. |
| `noise_seed_2` | 0 | Noise seed for pass 2. |
| `steps_2` | 3 | Denoising steps for pass 2 (refinement). |
| `cfg_2` | 1.0 | CFG scale for pass 2. |
| `sampler_name_2` | euler | Sampler for pass 2. |
| `scheduler_2` | linear_quadratic | Scheduler for pass 2. |
| `denoise_2` | 0.4 | Denoise strength for pass 2 — lower = less change to upscaled latent. |

#### Outputs

| Pin | Description |
|---|---|
| `video_latent` | Upscaled and refined video latent → connect to VAE Decode. |
| `audio_latent` | Audio latent from pass 1 → connect to LTXV Audio VAE Decode. |

#### Recommended settings

| Resolution target | steps_1 | steps_2 | denoise_2 |
|---|---|---|---|
| up to 960×544 | 8 | 3–4 | 0.4 |
| 1280×720 | 8–12 | 4–6 | 0.4 |
| 1920×1080 | 12 | 6 | 0.4 |

---

## LTX Resolution Selector

Selects the correct **input resolution** and **frame count** for LTX Video models.
Supports Dev mode and Distilled upscale modes (x1.5 and x2).

<img width="2049" height="667" alt="LTX Resolution Selector" src="https://github.com/user-attachments/assets/2c356de9-4a04-461f-93f3-cfb043ae902e" />

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

---

## Sampler Scheduler Iterator

Iterates over **sampler x scheduler** combinations one pair per execution.
Outputs each pair to connected nodes (e.g. KSampler, Aligned Text Overlay Images).
Node title updates automatically: `Iterator: Step 3 / 12`.
Queue stops automatically after the last combination.

> **Note:** Press **Refresh** before first use. This reads all installed
> samplers and schedulers from ComfyUI and writes the reference file.
> The counter resets to 0.

<img width="1754" height="462" alt="Sampler Scheduler Iterator" src="https://github.com/user-attachments/assets/e13921a4-2fa9-41b5-86d7-9cfaac4d10ff" />

---

### Inputs

This node has no inputs. Configure combinations in `.\ComfyUI\custom_nodes\ComfyUI-rogala\config\sampler_scheduler_user.json`.

### Outputs

| Pin | Type | Description |
|---|---|---|
| `sampler_name` | SAMPLER | Current sampler — connect to KSampler. |
| `scheduler` | SCHEDULER | Current scheduler — connect to KSampler. |
| `external_text` | STRING | `"sampler | scheduler"` label — connect to Aligned Text Overlay. |

### Example

Edit `config/sampler_scheduler_user.json` to select combinations:

```json
{
    "samplers": ["euler", "dpmpp_2m", "dpmpp_3m_sde"],
    "schedulers": ["karras", "simple"]
}
```

Total = samplers x schedulers (here: 3 x 2 = **6 runs**).
Copy names from `config/sampler_scheduler.json` (generated by Refresh).
Unknown names are silently ignored.

---

## Aligned Text Overlay Images

Renders a **multi-line text block** onto an image at a chosen corner before saving.
Supports `%NodeTitle.param%` template tags resolved from the active ComfyUI prompt.

<img width="1726" height="538" alt="Aligned Text Overlay Images" src="https://github.com/user-attachments/assets/45d9ef57-4073-4978-a7a7-e4069bd3312d" />

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

---

## Aligned Text Overlay Video

Renders a **multi-line text block** onto **every frame of a video tensor**.
Supports `%NodeTitle.param%` template tags resolved from the active ComfyUI prompt.

<img width="1829" height="669" alt="aligned_text_overlay_video" src="https://github.com/user-attachments/assets/33243112-db49-4b38-a561-e1f878eda56b" />

---

### Inputs

| Pin | Default | Description |
|---|---|---|
| `images` | — | Video tensor (B, H, W, C). |
| `text_template` | see default | Template string with optional `%NodeTitle.param%` tags. |
| `vertical` | bottom | Vertical anchor: `top` or `bottom`. |
| `horizontal` | right | Horizontal anchor: `left` or `right`. |
| `font_size` | 16 | Font size in points (10–50). |
| `text_color` | white | Text colour. |
| `bg_color` | black | Background colour (`none` = transparent). |
| `bg_opacity` | 150 | Background opacity (50–250). |
| `first_frame_only` | false | Apply overlay only to the first frame (fast preview). |
| `external_text` | — | Optional string appended after the resolved template. |

### Outputs

| Pin | Type | Description |
|---|---|---|
| `images` | IMAGE | Outputs a video tensor with text overlay applied. |

### Example

Connect between VAE Decode and video output:

```
VAE Decode → AlignedTextOverlayVideo → VHS Video Combine
```

Default template pulls values directly from a KSampler node:

```
seed: %KSampler.seed% | steps: %KSampler.steps%
cfg: %KSampler.cfg% | %KSampler.sampler_name% | %KSampler.scheduler%
```

If you have multiple samplers, rename them in the graph (Right Click → Title)
and reference explicitly:

```
steps: %Sampler_1.steps%
```

`NodeTitle` must match the title shown on the node in the graph.
Numeric sampler / scheduler indices are decoded to names automatically.

Connect `external_text` from **SamplerSchedulerIterator** to append
the current `"sampler | scheduler"` pair to the overlay.

Enable `first_frame_only` for fast preview (applies overlay only to frame 0).
