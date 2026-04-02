/**
 * sampler_scheduler_counter.js
 * ----------------------------
 * UI features for SamplerSchedulerIterator:
 *   1. Live progress counter in the node title ("Iterator: Step X / Y")
 *   2. Auto-stop after the last combination — waits for the full prompt
 *      to finish before stopping, so the last image is always saved.
 *   3. Refresh button — calls /rogala/refresh_sampler_config on the server
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

// True when the iterator has signalled DONE and we are waiting for
// the current prompt to finish before stopping the queue.
let _pendingStop = false;

// ---------------------------------------------------------------------------
// Listen for prompt completion — fires after every finished execution
// ---------------------------------------------------------------------------
api.addEventListener("execution_success", () => {
    if (!_pendingStop) return;
    _pendingStop = false;
    _doStop();
});

// Also handle execution_error so we don't get stuck waiting
api.addEventListener("execution_error", () => {
    if (!_pendingStop) return;
    _pendingStop = false;
    _doStop();
});

// ---------------------------------------------------------------------------
// Extension
// ---------------------------------------------------------------------------
app.registerExtension({
    name: "rogala.SamplerSchedulerCounter",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "SamplerSchedulerIterator") return;

        // ----------------------------------------------------------------
        // 1. onExecuted — title counter + schedule stop when done
        // ----------------------------------------------------------------
        const _onExecuted = nodeType.prototype.onExecuted;

        nodeType.prototype.onExecuted = function (message) {
            _onExecuted?.apply(this, arguments);

            if (message?.text?.[0]) {
                this.title = "Iterator: " + message.text[0];
            }

            if (message?.done?.[0] === true) {
                // Don't stop immediately — wait for execution_success so
                // the last image finishes saving before we interrupt.
                _pendingStop = true;
                console.log("[rogala] Last step reached — will stop after prompt completes.");
            }

            this.setDirtyCanvas(true);
        };

        // ----------------------------------------------------------------
        // 2. onNodeCreated — add Refresh button
        // ----------------------------------------------------------------
        const _onNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            _onNodeCreated?.apply(this, arguments);

            this.addWidget(
                "button",
                "Refresh",
                null,
                async () => {
                    try {
                        const resp = await fetch("/rogala/refresh_sampler_config", {
                            method: "POST",
                        });
                        if (resp.ok) {
                            console.log("[rogala] Sampler config refreshed.");
                        } else {
                            console.warn("[rogala] Refresh failed:", resp.status);
                        }
                    } catch (err) {
                        console.error("[rogala] Refresh error:", err);
                    }
                },
                { serialize: false }
            );
        };
    },
});

// ---------------------------------------------------------------------------
// _doStop — clicks "Stop Run (Instant)" if visible, then clears queue
// ---------------------------------------------------------------------------
async function _doStop() {
    try {
        // Click the Stop button if Run (Instant) / Run mode is active
        const allButtons = document.querySelectorAll("button");
        for (const btn of allButtons) {
            const txt = btn.textContent?.trim() ?? "";
            if (txt.includes("Stop Run")) {
                btn.click();
                console.log("[rogala] Clicked:", txt);
                break;
            }
        }

        // Clear queue + interrupt as fallback for normal Queue mode
        await fetch("/queue", {
            method  : "POST",
            headers : { "Content-Type": "application/json" },
            body    : JSON.stringify({ clear: true }),
        });

        await fetch("/interrupt", { method: "POST" });

        console.log("[rogala] Iterator done — queue stopped.");
    } catch (err) {
        console.error("[rogala] _doStop error:", err);
    }
}
