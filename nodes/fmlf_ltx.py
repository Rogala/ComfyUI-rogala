"""
FMLFLTX_2.3
===========
Loads up to 6 images and automatically distributes them across the video:
  - image_1 → frame 0 (First Frame, FF)
  - image_N → frame (length - 1) (Last Frame, LF — hard anchor for sampler)
  - image_2..N-1 → evenly spaced between FF and LF

The node counts connected images automatically — no manual frame index needed.

Outputs segment_lengths (pixel-space) for direct connection to PromptRelayEncode.
Segments are calculated between all frames EXCEPT the last anchor (image_N),
because the sampler re-embeds end_image itself in Pass 2.

Category : rogala/Video
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import io
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import comfy.model_management
import comfy.utils
import comfy.nested_tensor

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CATEGORY = "rogala/Video"
_MAX_IMGS = 6

_DESCRIPTION = """\
## FMLFLTX 2.3

Prepares video and audio latents for LTX Video 2.3 from up to 6 guide images.

Images are automatically placed at evenly-spaced positions:
- **image_1** → frame 0 (First Frame).
- **image_N** → frame (length - 1) (Last Frame — hard anchor, re-embedded by sampler in Pass 2).
- **image_2 … image_N-1** → evenly spaced at `round((length-1) * i / (N-1))` for i = 1..N-2.

Connect `width`, `height`, `length`, and `fps` from **LTX Resolution Selector**.

`segment_lengths` output is calculated between all frames except the last anchor,
and can be connected directly to **PromptRelayEncode**.

---

### Inputs

| Pin | Description |
|---|---|
| `video_vae` | Video VAE for image encoding. |
| `audio_vae` | Audio VAE for empty audio latent creation. |
| `img_compression` | JPEG pre-compression strength (0 = disabled). Matches LTXVPreprocess. |
| `width` | Latent width in pixels — connect from LTX Resolution Selector. |
| `height` | Latent height in pixels — connect from LTX Resolution Selector. |
| `length` | Frame count — connect from LTX Resolution Selector. |
| `fps` | Frames per second — used for audio latent duration. Connect from LTX Resolution Selector. |
| `batch_size` | Batch size (default 1). |
| `image_1 … image_6` | Guide images (optional). Connect only the slots you need. |
| `strength_1 … strength_6` | Conditioning strength per image (1.0 = fully conditioned, 0.0 = ignored). |

### Outputs

| Pin | Description |
|---|---|
| `latent` | Combined video + audio NestedTensor — for direct sampler input (legacy). |
| `video_latent` | Video latent only → connect to **SamplerLTXV_2.3** `video_latent`. |
| `audio_latent` | Empty audio latent → connect to **SamplerLTXV_2.3** `audio_latent`. |
| `segment_lengths` | Pixel-space frame counts per segment → connect to **PromptRelayEncode**. |
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ltxv_preprocess(image_tensor: torch.Tensor, img_compression: int) -> torch.Tensor:
    """JPEG pre-compression — mirrors LTXVPreprocess node behaviour."""
    if img_compression <= 0:
        return image_tensor
    img_np  = (image_tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    img_pil = Image.fromarray(img_np)
    buf     = io.BytesIO()
    img_pil.save(buf, format="JPEG", quality=max(1, 100 - img_compression))
    buf.seek(0)
    img_pil = Image.open(buf)
    return torch.from_numpy(np.array(img_pil).astype(np.float32) / 255.0)[None,]


def _resize_to_fit(image_tensor: torch.Tensor, target_w: int, target_h: int) -> torch.Tensor:
    """Scale by longer side + center crop to target_w x target_h."""
    _, oh, ow, _ = image_tensor.shape
    ratio = max(target_w / ow, target_h / oh)
    new_w = round(ow * ratio)
    new_h = round(oh * ratio)
    t = image_tensor.permute(0, 3, 1, 2)
    t = F.interpolate(t, size=(new_h, new_w), mode="bilinear", align_corners=False)
    x = (new_w - target_w) // 2
    y = (new_h - target_h) // 2
    t = t[:, :, y:y + target_h, x:x + target_w]
    return t.permute(0, 2, 3, 1)


def _encode_image(video_vae, image_tensor: torch.Tensor,
                  target_h: int, target_w: int) -> torch.Tensor:
    """Resize image to target resolution and encode to latent space."""
    resized = _resize_to_fit(image_tensor, target_w, target_h)
    return video_vae.encode(resized[:, :, :, :3])


def _calc_insert_frames(num_images: int, length: int) -> list[int]:
    """
    Calculate pixel-space frame indices for each image.

    - image_1  → frame 0          (FF, hard anchor)
    - image_N  → frame length-1   (LF, hard anchor — sampler re-embeds in Pass 2)
    - image_2..N-1 → evenly spaced between 0 and length-1

    With 1 image: [0]
    With 2 images: [0, length-1]
    With N images: evenly from 0 to length-1 inclusive
    """
    if num_images == 1:
        return [0]
    if num_images == 2:
        return [0, length - 1]
    return [round((length - 1) * i / (num_images - 1)) for i in range(num_images)]


def _calc_segment_lengths(insert_frames: list[int], length: int) -> str:
    """
    Calculate pixel-space segment lengths for PromptRelayEncode.

    Segments are counted between all frames EXCEPT the last one,
    because image_N is a hard sampler anchor — not a prompt segment.

    Example with 4 images at [0, 32, 64, 96] and length=97:
      segments = [32, 32, 32]  → "32,32,32"
    """
    if len(insert_frames) <= 1:
        return ""

    # All anchor frames except the last (LF anchor)
    seg_frames = insert_frames[:-1]

    segments = []
    for i in range(len(seg_frames) - 1):
        segments.append(seg_frames[i + 1] - seg_frames[i])

    # Last segment: from last middle anchor to end of video
    segments.append(length - 1 - seg_frames[-1])

    return ",".join(str(s) for s in segments)


# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

class FmlfLtx23:
    """
    Loads up to 6 guide images and builds video + audio latents
    for LTX Video 2.3. Connects directly to SamplerLTXV_2.3.
    """

    CATEGORY     = _CATEGORY
    FUNCTION     = "execute"
    DESCRIPTION  = _DESCRIPTION
    RETURN_TYPES = ("LATENT", "LATENT", "LATENT", "STRING")
    RETURN_NAMES = ("latent", "video_latent", "audio_latent", "segment_lengths")

    @classmethod
    def INPUT_TYPES(cls):
        inputs = {
            "required": {
                "video_vae": ("VAE",),
                "audio_vae": ("VAE",),
                "img_compression": ("INT", {
                    "default": 18, "min": 0, "max": 100, "step": 1,
                    "tooltip": "JPEG pre-compression strength (0 = disabled). Matches LTXVPreprocess.",
                }),
            },
            "optional": {
                "width": ("INT", {
                    "default": 768, "min": 64, "max": 4096, "step": 16,
                    "tooltip": "Latent width — connect from LTX Resolution Selector.",
                }),
                "height": ("INT", {
                    "default": 512, "min": 64, "max": 4096, "step": 16,
                    "tooltip": "Latent height — connect from LTX Resolution Selector.",
                }),
                "length": ("INT", {
                    "default": 97, "min": 9, "max": 1024, "step": 1,
                    "tooltip": "Frame count — connect from LTX Resolution Selector.",
                }),
                "fps": ("FLOAT", {
                    "default": 25.0, "min": 1.0, "max": 120.0, "step": 0.01,
                    "tooltip": "Frames per second — connect from LTX Resolution Selector.",
                }),
                "batch_size": ("INT", {
                    "default": 1, "min": 1, "max": 16,
                }),
            },
        }

        _slot_labels = {
            1: "First frame (FF) — automatically placed at frame 0.",
            6: "Last connected image becomes the Last Frame (LF) — hard anchor for sampler Pass 2.",
        }
        for i in range(1, _MAX_IMGS + 1):
            tip = _slot_labels.get(i, f"Middle frame {i - 1} — evenly spaced between FF and LF.")
            inputs["optional"][f"image_{i}"]    = ("IMAGE",)
            inputs["optional"][f"strength_{i}"] = ("FLOAT", {
                "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01,
                "tooltip": f"Conditioning strength: {tip}",
            })

        return inputs

    # -----------------------------------------------------------------------
    # Execution
    # -----------------------------------------------------------------------

    def execute(self, video_vae, audio_vae, img_compression,
                width=768, height=512, length=97, fps=25.0, batch_size=1,
                **kwargs):

        # Collect connected images in slot order
        images_by_slot = {}
        for i in range(1, _MAX_IMGS + 1):
            img = kwargs.get(f"image_{i}")
            if img is not None:
                images_by_slot[i] = img

        num_images = len(images_by_slot)

        # ── Empty video latent ─────────────────────────────────────────────
        latent_frames = ((length - 1) // 8) + 1
        latent_h      = height // 32
        latent_w      = width  // 32

        video_samples = torch.zeros(
            [batch_size, 128, latent_frames, latent_h, latent_w],
            device=comfy.model_management.intermediate_device(),
        )
        noise_mask = torch.ones(
            (batch_size, 1, latent_frames, 1, 1),
            dtype=torch.float32,
            device=video_samples.device,
        )

        # ── Encode and insert guide images ─────────────────────────────────
        insert_frames = []

        if num_images > 0:
            scale_factors = video_vae.downscale_index_formula
            time_scale    = int(scale_factors[0])
            h_scale       = int(scale_factors[1])
            w_scale       = int(scale_factors[2])
            px_target_w   = latent_w * w_scale
            px_target_h   = latent_h * h_scale

            insert_frames = _calc_insert_frames(num_images, length)

            for idx, (slot, image) in enumerate(images_by_slot.items()):
                f_idx    = insert_frames[idx]
                strength = kwargs.get(f"strength_{slot}", 1.0)
                if strength is None:
                    strength = 1.0

                image      = _ltxv_preprocess(image, img_compression)
                latent_idx = max(0, min(int(f_idx // time_scale), latent_frames - 1))
                encoded    = _encode_image(video_vae, image, px_target_h, px_target_w)
                end_index  = min(latent_idx + encoded.shape[2], latent_frames)

                video_samples[:, :, latent_idx:end_index] = encoded[:, :, :end_index - latent_idx]
                noise_mask[:, :, latent_idx:end_index]    = 1.0 - strength

                print(f"[FMLFLTX_2.3] slot={slot} → pixel_frame={f_idx} "
                      f"latent_idx={latent_idx} strength={strength}")

        # ── Segment lengths for PromptRelayEncode ─────────────────────────
        segment_lengths_str = _calc_segment_lengths(insert_frames, length)
        if segment_lengths_str:
            print(f"[FMLFLTX_2.3] segment_lengths → {segment_lengths_str}")

        # ── Empty audio latent ─────────────────────────────────────────────
        frame_rate    = int(round(fps))
        z_ch          = audio_vae.latent_channels
        a_freq        = audio_vae.latent_frequency_bins
        n_audio_lat   = audio_vae.num_of_latents_from_frames(length, frame_rate)

        audio_samples = torch.zeros(
            (batch_size, z_ch, n_audio_lat, a_freq),
            device=comfy.model_management.intermediate_device(),
        )
        audio_mask = torch.ones_like(audio_samples)

        # ── Build NestedTensor for legacy sampler compatibility ────────────
        combined_samples = comfy.nested_tensor.NestedTensor((video_samples, audio_samples))
        combined_mask    = comfy.nested_tensor.NestedTensor((noise_mask, audio_mask))

        main_latent  = {"samples": combined_samples, "noise_mask": combined_mask}
        video_latent = {"samples": video_samples,    "noise_mask": noise_mask}
        audio_latent = {"samples": audio_samples,    "noise_mask": audio_mask}

        return (main_latent, video_latent, audio_latent, segment_lengths_str)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS        = {"FmlfLtx23": FmlfLtx23}
NODE_DISPLAY_NAME_MAPPINGS = {"FmlfLtx23": "FMLFLTX_2.3"}
