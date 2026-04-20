"""
FMLFLTX_2.3
===========
Loads up to 6 images and automatically distributes them across the video:
  - image_1 → frame 0 (First Frame, FF)
  - image_N → frame (length - 1*fps) (Last Frame, LF — 1 second before end)
  - image_2..N-1 → evenly spaced between FF and LF

The node counts connected images automatically — no manual frame index needed.

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
- **image_N** → 1 second before the end (Last Frame).
- **image_2 … image_N-1** → evenly distributed between FF and LF.

Connect `width`, `height`, `length`, and `fps` from **LTX Resolution Selector**.

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
| `fps` | Frames per second — connect from LTX Resolution Selector. |
| `batch_size` | Batch size (default 1). |
| `image_1 … image_6` | Guide images (optional). Connect only the slots you need. |
| `strength_1 … strength_6` | Conditioning strength per image (1.0 = fully conditioned, 0.0 = ignored). |

### Outputs

| Pin | Description |
|---|---|
| `latent` | Combined video + audio NestedTensor — for direct sampler input (legacy). |
| `video_latent` | Video latent only → connect to **SamplerLTXV_2.3** `video_latent`. |
| `audio_latent` | Empty audio latent → connect to **SamplerLTXV_2.3** `audio_latent`. |
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


def _calc_insert_frames(num_images: int, length: int, fps: float) -> list[int]:
    """
    Calculate pixel-space frame indices for each image.
    Frames are evenly distributed from frame 0:
    frame_i = round(length * i / num_images) for i in 0..num_images-1.
    """
    return [round(length * i / num_images) for i in range(num_images)]


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
    RETURN_TYPES = ("LATENT", "LATENT", "LATENT")
    RETURN_NAMES = ("latent", "video_latent", "audio_latent")

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
            6: "Last frame (LF) — automatically placed 1 second before the end.",
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
        if num_images > 0:
            scale_factors = video_vae.downscale_index_formula
            time_scale    = int(scale_factors[0])
            h_scale       = int(scale_factors[1])
            w_scale       = int(scale_factors[2])
            px_target_w   = latent_w * w_scale
            px_target_h   = latent_h * h_scale

            insert_frames = _calc_insert_frames(num_images, length, fps)

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

        return (main_latent, video_latent, audio_latent)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS        = {"FmlfLtx23": FmlfLtx23}
NODE_DISPLAY_NAME_MAPPINGS = {"FmlfLtx23": "FMLFLTX_2.3"}
