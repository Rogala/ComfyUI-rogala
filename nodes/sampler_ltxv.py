"""
SamplerLTXV_2.3
===============
Two-pass sampler for LTX Video 2.3.

Pass 1 : Full denoise — video + audio NestedTensor (like PainterSamplerLTXV).
Pass 2 : Upscale + FF/LF control + refinement denoise (like PainterLTX2VPlus
         followed by PainterSamplerLTXV with add_noise=disable).

Category : rogala/Video
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import math
import torch
import comfy.model_management
import comfy.samplers
import comfy.sample
import comfy.utils
import comfy.nested_tensor
import latent_preview

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CATEGORY = "rogala/Video"

_DESCRIPTION = """\
## SamplerLTXV 2.3

Two-pass sampler for LTX Video 2.3 distilled models with spatial upscaling.

---

### Pass 1 — Full denoise

Combines `video_latent` and `audio_latent` into a NestedTensor and runs
a full denoise cycle, identical to **PainterSamplerLTXV**.

### Pass 2 — Upscale + refinement

1. Applies spatial upscaling via `upscale_model` (like **PainterLTX2VPlus**).
2. Re-embeds `start_image` / `end_image` at the upscaled resolution.
3. Runs a short refinement denoise with independent sampler settings.

---

### Inputs

| Pin | Description |
|---|---|
| `model` | Diffusion model. |
| `video_vae` | Video VAE used for image encoding and upscale statistics. |
| `positive` | Positive conditioning. |
| `negative` | Negative conditioning. |
| `video_latent` | Video latent from **FMLF_LTX** or equivalent. |
| `audio_latent` | Audio latent from **FMLF_LTX** or equivalent. |
| `start_image` | First frame image re-embedded after upscale (optional). |
| `end_image` | Last frame image re-embedded after upscale (optional). |
| `upscale_model` | Latent upscale model for pass 2 (optional). |

### Pass 1 parameters

| Parameter | Default | Description |
|---|---|---|
| `add_noise_1` | enable | Add noise before pass 1. |
| `noise_seed_1` | 0 | Noise seed for pass 1. |
| `steps_1` | 8 | Number of steps for pass 1. |
| `cfg_1` | 1.0 | CFG scale for pass 1. |
| `sampler_name_1` | euler | Sampler algorithm for pass 1. |
| `scheduler_1` | linear_quadratic | Scheduler for pass 1. |
| `denoise_1` | 1.0 | Denoise strength for pass 1. |

### Pass 2 parameters

| Parameter | Default | Description |
|---|---|---|
| `add_noise_2` | enable | Add noise before pass 2. |
| `noise_seed_2` | 0 | Noise seed for pass 2. |
| `steps_2` | 3 | Number of steps for pass 2. |
| `cfg_2` | 1.0 | CFG scale for pass 2. |
| `sampler_name_2` | euler | Sampler algorithm for pass 2. |
| `scheduler_2` | linear_quadratic | Scheduler for pass 2. |
| `denoise_2` | 0.4 | Denoise strength for pass 2 (lower = less change). |

### Outputs

| Pin | Description |
|---|---|
| `video_latent` | Upscaled and refined video latent → connect to VAE Decode. |
| `audio_latent` | Audio latent from pass 1 → connect to LTXV Audio VAE Decode. |
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _encode_image(video_vae, image, target_height, target_width):
    """Resize and encode an image to latent space."""
    if image.shape[1] != target_height or image.shape[2] != target_width:
        pixels = comfy.utils.common_upscale(
            image.movedim(-1, 1), target_width, target_height, "bilinear", "center"
        ).movedim(1, -1)
    else:
        pixels = image
    return video_vae.encode(pixels[:, :, :, :3])


def _apply_frame_control(video_vae, samples, noise_mask, start_image, end_image):
    """
    Re-embed start/end images into the latent at the current (upscaled) resolution.
    Mirrors PainterLTX2VPlus._apply_frame_control exactly.
    """
    _, _, latent_frames, latent_height, latent_width = samples.shape
    _, height_scale, width_scale = video_vae.downscale_index_formula
    target_w = latent_width  * width_scale
    target_h = latent_height * height_scale

    if start_image is not None:
        t = _encode_image(video_vae, start_image, target_h, target_w)
        n = min(t.shape[2], latent_frames)
        samples[:, :, :n]    = t[:, :, :n]
        noise_mask[:, :, :n] = 0.0

    if end_image is not None:
        t = _encode_image(video_vae, end_image, target_h, target_w)
        n = min(t.shape[2], latent_frames)
        si = latent_frames - n
        if si < 0:
            t  = t[:, :, :latent_frames]
            si = 0
            n  = latent_frames
        samples[:, :, si:]    = t
        noise_mask[:, :, si:] = 0.0

    return samples, noise_mask


def _apply_upscale(samples, upscale_model, video_vae):
    """
    Spatial upscale in latent space.
    Mirrors PainterLTX2VPlus._apply_upscale exactly.
    """
    device         = comfy.model_management.get_torch_device()
    memory_required = comfy.model_management.module_size(upscale_model)
    model_dtype    = next(upscale_model.parameters()).dtype
    input_dtype    = samples.dtype
    memory_required += math.prod(samples.shape) * 3000.0
    comfy.model_management.free_memory(memory_required, device)
    try:
        upscale_model.to(device)
        samples   = samples.to(dtype=model_dtype, device=device)
        samples   = video_vae.first_stage_model.per_channel_statistics.un_normalize(samples)
        upsampled = upscale_model(samples)
        upsampled = video_vae.first_stage_model.per_channel_statistics.normalize(upsampled)
        return upsampled.to(dtype=input_dtype,
                            device=comfy.model_management.intermediate_device())
    finally:
        upscale_model.cpu()


def _run_sampler(model, noise_seed, steps, cfg, sampler_name, scheduler,
                 positive, negative, latent,
                 disable_noise, start_at_step, end_at_step,
                 force_full_denoise, denoise=1.0):
    """
    Core sampling call.
    Mirrors PainterSamplerLTXV execute() logic exactly.
    """
    latent_tensor = latent["samples"]
    latent_tensor = comfy.sample.fix_empty_latent_channels(model, latent_tensor)
    latent["samples"] = latent_tensor

    if disable_noise:
        noise_tensor = torch.zeros(
            latent_tensor.size(), dtype=latent_tensor.dtype,
            layout=latent_tensor.layout, device="cpu"
        )
    else:
        batch_inds   = latent.get("batch_index", None)
        noise_tensor = comfy.sample.prepare_noise(latent_tensor, noise_seed, batch_inds)

    noise_mask   = latent.get("noise_mask", None)
    disable_pbar = not comfy.utils.PROGRESS_BAR_ENABLED
    callback     = latent_preview.prepare_callback(model, steps)

    samples = comfy.sample.sample(
        model, noise_tensor, steps, cfg, sampler_name, scheduler,
        positive, negative, latent_tensor,
        denoise=denoise, disable_noise=disable_noise,
        start_step=start_at_step, last_step=end_at_step,
        force_full_denoise=force_full_denoise,
        noise_mask=noise_mask, callback=callback,
        disable_pbar=disable_pbar, seed=noise_seed
    )

    out = latent.copy()
    out["samples"] = samples
    return out


# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

class SamplerLtxv23:
    """Two-pass sampler for LTX Video 2.3 with spatial upscaling."""

    CATEGORY     = _CATEGORY
    FUNCTION     = "execute"
    DESCRIPTION  = _DESCRIPTION
    RETURN_TYPES = ("LATENT", "LATENT")
    RETURN_NAMES = ("video_latent", "audio_latent")

    @classmethod
    def INPUT_TYPES(cls):
        samplers   = comfy.samplers.KSampler.SAMPLERS
        schedulers = comfy.samplers.KSampler.SCHEDULERS
        return {
            "required": {
                # ── Model / conditioning ───────────────────────────────────
                "model":          ("MODEL",),
                "video_vae":      ("VAE",),
                "positive":       ("CONDITIONING",),
                "negative":       ("CONDITIONING",),
                "video_latent":   ("LATENT",),
                "audio_latent":   ("LATENT",),
                # ── Pass 1 ────────────────────────────────────────────────
                "add_noise_1":    (["enable", "disable"], {"default": "enable"}),
                "noise_seed_1":   ("INT", {
                    "default": 0, "min": 0, "max": 0xffffffffffffffff,
                    "control_after_generate": "randomize",
                    "tooltip": "Noise seed for pass 1.",
                }),
                "steps_1":        ("INT", {
                    "default": 8, "min": 1, "max": 10000,
                    "tooltip": "Denoising steps for pass 1.",
                }),
                "cfg_1":          ("FLOAT", {
                    "default": 1.0, "min": 0.0, "max": 100.0, "step": 0.1,
                    "tooltip": "CFG scale for pass 1.",
                }),
                "sampler_name_1": (samplers,   {"default": "euler"}),
                "scheduler_1":    (schedulers, {"default": "linear_quadratic"}),
                "denoise_1":      ("FLOAT", {
                    "default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01,
                    "tooltip": "Denoise strength for pass 1.",
                }),
                # ── Pass 2 ────────────────────────────────────────────────
                "add_noise_2":    (["enable", "disable"], {"default": "enable"}),
                "noise_seed_2":   ("INT", {
                    "default": 0, "min": 0, "max": 0xffffffffffffffff,
                    "control_after_generate": "randomize",
                    "tooltip": "Noise seed for pass 2.",
                }),
                "steps_2":        ("INT", {
                    "default": 3, "min": 1, "max": 10000,
                    "tooltip": "Denoising steps for pass 2 (refinement after upscale).",
                }),
                "cfg_2":          ("FLOAT", {
                    "default": 1.0, "min": 0.0, "max": 100.0, "step": 0.1,
                    "tooltip": "CFG scale for pass 2.",
                }),
                "sampler_name_2": (samplers,   {"default": "euler"}),
                "scheduler_2":    (schedulers, {"default": "linear_quadratic"}),
                "denoise_2":      ("FLOAT", {
                    "default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01,
                    "tooltip": "Denoise strength for pass 2. Lower = less change to upscaled latent.",
                }),
            },
            "optional": {
                "start_image":   ("IMAGE",),
                "end_image":     ("IMAGE",),
                "upscale_model": ("LATENT_UPSCALE_MODEL",),
            },
        }

    # -----------------------------------------------------------------------
    # Execution
    # -----------------------------------------------------------------------

    def execute(self, model, video_vae, positive, negative,
                video_latent, audio_latent,
                add_noise_1, noise_seed_1, steps_1, cfg_1,
                sampler_name_1, scheduler_1, denoise_1,
                add_noise_2, noise_seed_2, steps_2, cfg_2,
                sampler_name_2, scheduler_2, denoise_2,
                start_image=None, end_image=None, upscale_model=None):

        # ── Pass 1 ────────────────────────────────────────────────────────
        # Build NestedTensor (video + audio) exactly like PainterSamplerLTXV
        # when both video_latent and audio_latent are connected.

        v_samples = video_latent["samples"]
        a_samples = audio_latent["samples"]
        v_mask    = video_latent.get("noise_mask")
        a_mask    = audio_latent.get("noise_mask")

        p1_latent = video_latent.copy()
        p1_latent["samples"] = comfy.nested_tensor.NestedTensor((v_samples, a_samples))

        if v_mask is not None or a_mask is not None:
            if v_mask is None:
                v_mask = torch.ones_like(v_samples)
            if a_mask is None:
                a_mask = torch.ones_like(a_samples)
            p1_latent["noise_mask"] = comfy.nested_tensor.NestedTensor((v_mask, a_mask))

        out_1 = _run_sampler(
            model, noise_seed_1, steps_1, cfg_1, sampler_name_1, scheduler_1,
            positive, negative, p1_latent,
            disable_noise=(add_noise_1 == "disable"),
            start_at_step=0, end_at_step=10000,
            force_full_denoise=True,
            denoise=denoise_1,
        )

        # Split NestedTensor → video_s1 + audio_s1
        samples_1 = out_1["samples"]
        if isinstance(samples_1, comfy.nested_tensor.NestedTensor):
            parts    = samples_1.unbind()
            video_s1 = parts[0]
            audio_s1 = parts[1] if len(parts) >= 2 else None
        else:
            video_s1 = samples_1
            audio_s1 = None

        # Audio output comes from pass 1 (→ LTXV Audio VAE Decode)
        if audio_s1 is not None:
            audio_latent_out = {"samples": audio_s1}
        else:
            audio_latent_out = {
                "samples": torch.empty(0, device=video_s1.device, dtype=video_s1.dtype)
            }

        # ── Pass 2 ────────────────────────────────────────────────────────
        # Mirrors: PainterLTX2VPlus → PainterSamplerLTXV (add_noise=disable)

        # 2a. Spatial upscale (PainterLTX2VPlus._apply_upscale)
        if upscale_model is not None:
            video_s2 = _apply_upscale(video_s1, upscale_model, video_vae)
        else:
            video_s2 = video_s1

        # 2b. Fresh noise mask after upscale (PainterLTX2VPlus sets mask=None
        #     after upscaling; we create a new ones mask for frame control)
        batch   = video_s2.shape[0]
        lf      = video_s2.shape[2]
        mask_s2 = torch.ones(
            (batch, 1, lf, 1, 1),
            dtype=torch.float32,
            device=video_s2.device,
        )

        # 2c. Re-embed FF / LF at upscaled resolution (PainterLTX2VPlus._apply_frame_control)
        if start_image is not None or end_image is not None:
            video_s2, mask_s2 = _apply_frame_control(
                video_vae, video_s2, mask_s2, start_image, end_image
            )

        # 2d. Run refinement — plain video latent, no audio wrapping
        p2_latent = {
            "samples":    video_s2,
            "noise_mask": mask_s2,
        }

        out_2 = _run_sampler(
            model, noise_seed_2, steps_2, cfg_2, sampler_name_2, scheduler_2,
            positive, negative, p2_latent,
            disable_noise=(add_noise_2 == "disable"),
            start_at_step=0, end_at_step=10000,
            force_full_denoise=True,
            denoise=denoise_2,
        )

        video_latent_out = {"samples": out_2["samples"]}

        print(f"[SamplerLTXV_2.3] pass1 video: {video_s1.shape}")
        print(f"[SamplerLTXV_2.3] pass2 video: {out_2['samples'].shape}")

        return (video_latent_out, audio_latent_out)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

NODE_CLASS_MAPPINGS        = {"SamplerLtxv23": SamplerLtxv23}
NODE_DISPLAY_NAME_MAPPINGS = {"SamplerLtxv23": "SamplerLTXV_2.3"}
