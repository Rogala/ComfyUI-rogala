"""
SamplerSchedulerIterator
========================
Iterates over sampler × scheduler combinations one pair per execution.

Reference list is taken from ComfyUI (KSampler) on demand — never at
import time — so it always reflects all installed nodes.

Pressing the Refresh button on the node:
  - regenerates config/sampler_scheduler.json (reference, do not edit)
  - creates config/sampler_scheduler_user.json if missing (edit this one)
  - resets the counter to 0

User customisation is done via config/sampler_scheduler_user.json.

Category : rogala/Samplers
Version  : 2.0.0
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import json
import os
import random

import comfy.samplers

# ---------------------------------------------------------------------------
# Dynamic return types proxy
# ---------------------------------------------------------------------------

class _DynamicReturnTypes(list):
    """
    Proxy for RETURN_TYPES that reads KSampler lists at access time.

    Inherits from list so ComfyUI can JSON-serialize it for object_info.
    __getitem__ is overridden to always return the live KSampler lists —
    even if another node replaced KSampler.SCHEDULERS after our module loaded.
    """
    def __init__(self):
        super().__init__(["SAMPLER", "SCHEDULER", "STRING"])

    def __getitem__(self, idx):
        live = [
            comfy.samplers.KSampler.SAMPLERS,
            comfy.samplers.KSampler.SCHEDULERS,
            "STRING",
        ]
        return live[idx]  # supports int, negative index, and slice

    def __iter__(self):
        yield comfy.samplers.KSampler.SAMPLERS
        yield comfy.samplers.KSampler.SCHEDULERS
        yield "STRING"

    def __len__(self) -> int:
        return 3


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CATEGORY  = "rogala/Samplers"
_NODE_NAME = "SamplerSchedulerIterator"

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config")
_REF_PATH   = os.path.join(_CONFIG_DIR, "sampler_scheduler.json")
_USER_PATH  = os.path.join(_CONFIG_DIR, "sampler_scheduler_user.json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=4)


# Module-level reset flag — set by HTTP route, consumed by next execute()
_reset_requested: bool = False


def refresh_config() -> None:
    """
    Regenerate sampler_scheduler.json from the live KSampler lists.
    Create sampler_scheduler_user.json as a full copy only if it does
    not already exist (never overwrites the user's customised list).

    Call this after all ComfyUI nodes are loaded — e.g. via the
    Refresh button on the node — to get the complete sampler/scheduler list.
    """
    ref = {
        "samplers":   list(comfy.samplers.KSampler.SAMPLERS),
        "schedulers": list(comfy.samplers.KSampler.SCHEDULERS),
    }
    _write_json(_REF_PATH, ref)
    print(
        f"[rogala/SamplerSchedulerIterator] Reference updated: "
        f"{len(ref['samplers'])} samplers, {len(ref['schedulers'])} schedulers."
    )

    if not os.path.exists(_USER_PATH):
        _write_json(_USER_PATH, ref)
        print("[rogala/SamplerSchedulerIterator] Created sampler_scheduler_user.json")

    global _reset_requested
    _reset_requested = True
    print("[rogala/SamplerSchedulerIterator] Counter reset scheduled.")


def _load_user_config() -> tuple[list[str], list[str]]:
    """
    Load samplers and schedulers from sampler_scheduler_user.json.
    Falls back to the live KSampler lists if the file is missing or broken.
    Entries not present in the live KSampler reference are filtered out
    automatically to prevent type-mismatch errors.
    """
    ref_samplers   = list(comfy.samplers.KSampler.SAMPLERS)
    ref_schedulers = list(comfy.samplers.KSampler.SCHEDULERS)

    try:
        with open(_USER_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        samplers   = [s for s in data.get("samplers",   ref_samplers)   if s in ref_samplers]
        schedulers = [s for s in data.get("schedulers", ref_schedulers) if s in ref_schedulers]

        if not samplers:
            samplers = ref_samplers
        if not schedulers:
            schedulers = ref_schedulers

        return samplers, schedulers

    except Exception:
        return ref_samplers, ref_schedulers

# ---------------------------------------------------------------------------
# Description shown in the ? popup (Markdown supported)
# ---------------------------------------------------------------------------
_DESCRIPTION = """\
## Sampler Scheduler Iterator

Iterates over **sampler x scheduler** combinations one pair per execution.
Outputs each pair to connected nodes (e.g. KSampler, Aligned Text Overlay).
Node title updates automatically: `Iterator: Step 3 / 12`.
Queue stops automatically after the last combination.

> **Note:** Press **Refresh** before first use. This reads all installed
> samplers and schedulers from ComfyUI and writes the reference file.
> The counter resets to 0.

---

### Inputs

This node has no inputs. Configure combinations in `.\\ComfyUI\\custom_nodes\\ComfyUI-rogala\\config\\sampler_scheduler_user.json`.

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
"""

# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

class SamplerSchedulerIterator:
    """
    Iterates sampler x scheduler combinations from sampler_scheduler_user.json.

    RETURN_TYPES is a proxy object that reads KSampler lists at access time —
    new entries added by other nodes after import are always reflected,
    preventing type-mismatch errors.

    The Refresh button regenerates the reference config from the live KSampler
    lists and resets the counter. User entries not in the reference are
    filtered out automatically.

    Outputs
    -------
    sampler_name : SAMPLER
        The current sampler string.
    scheduler : SCHEDULER
        The current scheduler string.
    external_text : STRING
        Formatted string "sampler-scheduler" for use in text overlays.
    """

    # ------------------------------------------------------------------
    # ComfyUI metadata
    # ------------------------------------------------------------------
    CATEGORY    = _CATEGORY
    FUNCTION    = "execute"
    DESCRIPTION = _DESCRIPTION
    OUTPUT_NODE = True  # Required for UI counter updates

    # list (not tuple) — holds a live reference so entries added by other
    # nodes after import are visible when ComfyUI validates the prompt
    RETURN_TYPES  = _DynamicReturnTypes()
    RETURN_NAMES  = ("sampler_name", "scheduler", "external_text")

    # ------------------------------------------------------------------
    # Input definition — no inputs, Refresh button is added via JS
    # ------------------------------------------------------------------
    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {"required": {}}

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def __init__(self) -> None:
        self._index: int = 0

    @classmethod
    def IS_CHANGED(cls, **kwargs) -> float:
        """
        Force re-execution on every queue run so the counter advances.

        Intentionally returns a random value each time — this signals
        ComfyUI that the node output is never cacheable. Without this,
        the counter would not advance between consecutive queue runs.
        This is by design, not a bug.
        """
        return random.random()

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute(self) -> dict:
        """
        Return the next sampler / scheduler pair.

        Reads sampler_scheduler_user.json on every call (hot-reload).
        Unknown entries are filtered against the live KSampler reference.
        Stops the queue automatically after the last combination.

        Returns
        -------
        dict
            ComfyUI result dict with ui text and output tuple.
        """
        samplers, schedulers = _load_user_config()

        total_s   = len(samplers)
        total_sch = len(schedulers)
        total     = total_s * total_sch

        # Reset counter if Refresh was pressed
        global _reset_requested
        if _reset_requested:
            self._index = 0
            _reset_requested = False
            print("[rogala/SamplerSchedulerIterator] Counter reset by Refresh.")

        # Guard: reset if config shrank since last run, or total is zero (broken config)
        if total == 0:
            print("[rogala/SamplerSchedulerIterator] WARNING: no samplers or schedulers loaded — check config.")
            return {
                "ui":     {"text": ("ERROR: empty config",), "done": (True,)},
                "result": ("euler", "normal", "ERROR: empty config"),
            }
        if self._index >= total:
            self._index = 0

        idx       = self._index
        sampler   = samplers[(idx // total_sch) % total_s]
        scheduler = schedulers[idx % total_sch]

        external_text = f"{sampler}-{scheduler}"
        self._index  += 1
        done          = self._index >= total

        progress_text = (
            f"DONE — Step {idx + 1} / {total}" if done
            else f"Step: {idx + 1} / {total}"
        )

        print(
            f"[rogala/SamplerSchedulerIterator] {progress_text} — "
            f"sampler={sampler}, scheduler={scheduler}"
        )

        if done:
            self._index = 0

        return {
            "ui":     {"text": (progress_text,), "done": (done,)},
            "result": (sampler, scheduler, external_text),
        }


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
NODE_CLASS_MAPPINGS: dict = {
    "SamplerSchedulerIterator": SamplerSchedulerIterator,
}
