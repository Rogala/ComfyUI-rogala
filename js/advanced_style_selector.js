/**
 * Advanced Style Selector — ComfyUI DOM Widget
 * js/advanced_style_selector.js
 *
 * Uses addDOMWidget (like easy-use StylesSelector) so clicks, scroll,
 * hover all work natively — no canvas hit-testing needed.
 */

import { app } from "../../scripts/app.js";

const NODE_NAME = "AdvancedStyleSelector";
const PW = 670; // minimum node width

// ── CSS ────────────────────────────────────────────────────────────────────
// Colors use ComfyUI theme CSS variables so the panel follows light/dark
// theme automatically. Only the accent green is kept as a brand color.
//
// ComfyUI variables we rely on:
//   --comfy-menu-bg     — panel background
//   --comfy-input-bg    — input/button background
//   --input-text        — text in inputs
//   --fg-color          — primary text color
//   --border-color      — borders / separators
//   --descrip-text      — muted/secondary text color
const CSS = `
.rg-panel {
  background: var(--comfy-menu-bg, #1a1f1c);
  border: 1px solid var(--border-color, #2d4a38);
  border-radius: 6px;
  font-family: monospace;
  color: var(--fg-color, #c8e8c8);
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  user-select: none;
  overflow: hidden;
}
.rg-header { display: none; }  /* legacy — header removed in v14 */
.rg-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  min-height: 38px;
  height: 38px;
  border-bottom: 1px solid var(--border-color, #2d4a38);
  border-radius: 6px 6px 0 0;
  flex-wrap: nowrap;
  overflow: hidden;
}
.rg-model-sel {
  background: var(--comfy-input-bg, #1a2820);
  border: 1px solid var(--border-color, #2d4a38);
  border-radius: 4px;
  color: var(--fg-color, #c8e8c8); font-family: monospace; font-size: 13px;
  padding: 4px 8px; cursor: pointer;
  flex: 1 1 auto; min-width: 0;
}
.rg-cats-row {
  display: flex;
  align-items: stretch;
  gap: 6px;
  padding: 6px;
  border-bottom: 1px solid var(--border-color, #2d4a38);
}
.rg-cats-row > .rg-trash {
  align-self: center;
  flex-shrink: 0;
  overflow: hidden;
  min-width: 0;
}
.rg-cats {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  align-items: center;
  flex: 1 1 auto;
  min-width: 0;
}
.rg-cat {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 4px;
  border: 0.5px solid var(--border-color, #2d4a38);
  background: var(--comfy-input-bg, #1a2820);
  font-size: 13px;
  color: var(--descrip-text, #5a7a68);
  cursor: pointer;
  transition: all 0.15s;
}
.rg-cat.active { color: var(--fg-color, #c8e8c8); border-width: 1.5px; }
.rg-cat .dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: var(--border-color, #2a3a30);
  flex-shrink: 0;
}
.rg-cat.active .dot { background: #4aaa6a; }

.rg-active-strip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 6px;
  min-height: 50px;
  border-bottom: 1px solid var(--border-color, #2d4a38);
  flex-wrap: wrap;
}
.rg-active-strip:has(.rg-mini) {
  min-height: 100px;
}

.rg-trash {
  padding: 5px 12px;
  border-radius: 4px;
  border: 0.5px solid var(--border-color, #2d4a38);
  background: var(--comfy-input-bg, #1a2820);
  cursor: pointer;
  font-size: 18px;
  flex-shrink: 0;
}
.rg-trash.has-sel { background: #3a1a1a; color: #dd7777; }
.rg-no-sel { font-size: 14px; color: var(--descrip-text, #5a7a68); opacity: 0.7; }
.rg-tag {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 2px 6px 2px 4px;
  border-radius: 4px;
  border: 1px solid #4aaa6a;
  background: var(--comfy-input-bg, #152218);
  font-size: 9px;
  color: var(--fg-color, #c8e8c8);
}
.rg-tag .slot { font-weight: bold; color: #4aaa6a; font-size: 8px; }
.rg-tag .rm   { color: #dd7777; cursor: pointer; font-size: 11px; font-weight: bold; margin-left: 2px; }

/* Mini thumbnail in active strip (replaces text tag) */
.rg-mini {
  position: relative;
  width: 90px; height: 90px;
  border: 1.5px solid #4aaa6a;
  border-radius: 4px;
  background: var(--comfy-input-bg, #152218);
  flex-shrink: 0;
  cursor: pointer;
  overflow: hidden;
  box-sizing: border-box;
}
.rg-mini-img {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.rg-mini-img img { width: 100%; height: 100%; object-fit: contain; display: block; }
.rg-mini-init {
  font-family: monospace; font-size: 16px; font-weight: bold;
  opacity: 0.85;
}
.rg-mini-slot {
  position: absolute; top: 0; left: 0;
  width: 20px; height: 20px;
  border-radius: 0 0 5px 0;
  color: #000;
  font-family: monospace; font-size: 12px; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
  z-index: 2;
}
.rg-mini-rm {
  position: absolute; top: -1px; right: 2px;
  color: #dd7777;
  font-size: 18px; font-weight: bold;
  text-shadow: 0 0 3px #000, 0 0 3px #000;
  cursor: pointer;
  z-index: 3;
  line-height: 1;
}
.rg-mini-rm:hover { color: #ff5555; }

.rg-search { padding: 5px 6px; border-bottom: 1px solid var(--border-color, #2d4a38); }
.rg-search input {
  width: 100%;
  box-sizing: border-box;
  background: var(--comfy-input-bg, #111815);
  border: 0.5px solid var(--border-color, #2d4a38);
  border-radius: 4px;
  color: var(--input-text, var(--fg-color, #c8e8c8));
  font-family: monospace;
  font-size: 14px;
  padding: 6px 10px;
  outline: none;
}
.rg-search input:focus { border-color: #4aaa6a; }

.rg-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  padding: 6px;
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  align-content: flex-start;
  scrollbar-width: thin;
  scrollbar-color: #1e5a38 transparent;
  min-width: 0;
  overflow-x: hidden;
}
.rg-grid::-webkit-scrollbar { width: 5px; }
.rg-grid::-webkit-scrollbar-track { background: transparent; }
.rg-grid::-webkit-scrollbar-thumb { background: #1e5a38; border-radius: 2px; }

.rg-thumb { width: 120px; cursor: pointer; position: relative; flex-shrink: 0; }
.rg-thumb-img {
  width: 120px; height: 120px;
  border-radius: 4px;
  border: 0.5px solid var(--border-color, #2a3a55);
  background: var(--comfy-input-bg, #1a2318);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden; position: relative;
}
.rg-thumb-img .color-strip {
  position: absolute; top: 0; left: 0; right: 0; height: 6px;
  border-radius: 4px 4px 0 0;
}
.rg-thumb-img img {
  width: 100%; height: 100%; object-fit: contain;
  position: absolute; top: 0; left: 0;
}
.rg-thumb-img .initials { font-family: monospace; font-size: 13px; position: relative; z-index: 1; }
.rg-thumb.active .rg-thumb-img { border: 1.5px solid #4aaa6a; background: var(--comfy-input-bg, #152218); }
.rg-badge {
  position: absolute; top: 5px; right: 5px;
  width: 19px; height: 19px; border-radius: 50%;
  background: #4aaa6a; color: #000;
  font-size: 11px; font-weight: bold;
  display: flex; align-items: center; justify-content: center;
  z-index: 2;
}
.rg-lbl {
  font-size: 13px; font-family: monospace; color: var(--descrip-text, #5a7a68);
  margin-top: 4px; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; width: 120px;
}
.rg-thumb.active .rg-lbl { color: #4aaa6a; }

/* Favorites star button */
.rg-fav {
  position: absolute; bottom: 4px; right: 4px;
  font-size: 16px; line-height: 1;
  cursor: pointer; z-index: 3;
  opacity: 0; transition: opacity 0.15s;
  text-shadow: 0 0 4px #000, 0 0 4px #000;
  user-select: none;
}
.rg-thumb:hover .rg-fav { opacity: 1; }
.rg-fav.active { opacity: 1; }

.rg-popup {
  position: fixed;
  background: var(--comfy-menu-bg, #0e1512);
  border: 1px solid var(--border-color, #2d4a38);
  border-radius: 6px;
  padding: 11px; width: 300px;
  font-family: monospace; font-size: 13px;
  z-index: 99999; pointer-events: none;
  max-height: 360px; overflow: hidden;
  color: var(--fg-color, #c8e8c8);
  line-height: 1.4;
}
.rg-popup .pname  { font-size: 15px; font-weight: bold; color: var(--fg-color, #c8e8c8); margin-bottom: 6px; }
.rg-popup .plabel { font-weight: bold; margin-top: 7px; font-size: 13px; }
.rg-popup .ppos   { color: #88cc99; }
.rg-popup .pneg   { color: #cc8888; }
.rg-popup .plabel-pos { color: #4aaa6a; }
.rg-popup .plabel-neg { color: #dd7777; }
.rg-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 10px; border-top: 1px solid var(--border-color, #2d4a38); gap: 8px;
}
.rg-use-neg {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; color: var(--fg-color, #c8e8c8); cursor: pointer;
}
.rg-use-neg input { accent-color: #4aaa6a; cursor: pointer; width: 16px; height: 16px; }
.rg-reload-btn {
  background: var(--comfy-input-bg, #1a2820);
  border: 1px solid var(--border-color, #2d4a38);
  border-radius: 4px;
  color: #4aaa6a; font-family: monospace; font-size: 14px;
  padding: 5px 14px; cursor: pointer;
}
.rg-reload-btn:hover { background: var(--comfy-menu-bg, #222b25); border-color: #4aaa6a; }
.rg-mode-sel {
  background: var(--comfy-input-bg, #1a2820);
  border: 1px solid var(--border-color, #2d4a38);
  border-radius: 4px;
  color: #4aaa6a; font-family: monospace; font-size: 14px;
  padding: 5px 10px; cursor: pointer;
}
`;

function injectNodeCSS() {
  if (document.getElementById("rg-node-sep-css")) return;
  const s = document.createElement("style");
  s.id = "rg-node-sep-css";
  // Target textarea elements inside ComfyUI node — add separator between them
  s.textContent = `
    .litegraph .node_widget textarea ~ textarea,
    .litegraph textarea + textarea {
      margin-top: 8px !important;
      border-top: 1px solid #555 !important;
    }
  `;
  document.head.appendChild(s);
}

function injectCSS() {
  if (document.getElementById("rg-style-selector-css")) return;
  const s = document.createElement("style");
  s.id = "rg-style-selector-css";
  s.textContent = CSS;
  document.head.appendChild(s);
}

// ── Colour helpers ─────────────────────────────────────────────────────────
// 15-color palette, generated from HSL with 24° hue steps and alternating
// lightness (42% / 50%) so no two categories look the same. Works well on
// both dark and light ComfyUI themes.
//   0: red        1: orange     2: olive      3: lime        4: green
//   5: bright-grn 6: teal-grn   7: teal       8: cyan        9: blue
//  10: indigo    11: purple    12: violet    13: magenta    14: pink
const CAT_PALETTE = [
  "#9e3737", "#bc7342", "#9e8937", "#a4bc42", "#609e37",
  "#42bc42", "#379e60", "#42bca4", "#37899e", "#4273bc",
  "#37379e", "#7342bc", "#89379e", "#bc42a4", "#9e3760",
];

const FAVORITES_CAT = "⭐ Favorites";
const FAVORITES_COLOR = "#d4a017";  // gold — distinct from all palette entries

// Explicit mapping from category name to palette index. Using a hash
// function on short strings like "3D" / "Art" produced collisions (same
// color for multiple categories), so we map known categories directly.
// Indices are deliberately spread across the hue wheel (step ≈ 5) so that
// alphabetically-adjacent categories end up with visually-distant colors.
// New/unknown categories fall back to the djb2 hash + palette.
const CAT_COLOR_INDEX = {
  "3D":              0,    // red
  "Art":             5,    // bright green
  "World Culture":  10,    // indigo
  "Craft":           2,    // olive
  "Design":          7,    // teal
  "Drawing":        12,    // violet
  "Experimental":    4,    // green
  "Fashion":         9,    // blue
  "Game":           14,    // pink
  "Illustration":    6,    // teal-green
  "Other":          11,    // purple
  "Painting":        1,    // orange
  "Photography":     8,    // cyan
  "Vector":         13,    // magenta
  // index 3 (lime) reserved for any future category
};
function catColor(cat) {
  if (cat === FAVORITES_CAT) return FAVORITES_COLOR;
  if (cat in CAT_COLOR_INDEX) return CAT_PALETTE[CAT_COLOR_INDEX[cat]];
  let h = 5381;
  for (let i = 0; i < cat.length; i++) h = ((h << 5) + h) + cat.charCodeAt(i);
  return CAT_PALETTE[Math.abs(h) % CAT_PALETTE.length];
}

// ── Popup singleton ────────────────────────────────────────────────────────
let _popup = null;
function getPopup() {
  if (!_popup) {
    _popup = document.createElement("div");
    _popup.className = "rg-popup";
    _popup.style.display = "none";
    document.body.appendChild(_popup);
  }
  return _popup;
}
function showPopup(style, e) {
  const p = getPopup();
  const pos = (style.prompt || "").replace("{prompt}", "…");
  const neg = style.negative_prompt || "";
  p.innerHTML = `
    <div class="pname">${style.name}</div>
    <hr style="border-color:#2d4a38;margin:4px 0">
    <div class="plabel plabel-pos">Positive:</div>
    <div class="ppos">${pos.slice(0, 300) || "—"}</div>
    <div class="plabel plabel-neg">Negative:</div>
    <div class="pneg">${neg.slice(0, 200) || "—"}</div>
  `;
  p.style.display = "block";
  movePopup(e);
}
function movePopup(e) {
  const p = getPopup();
  if (p.style.display === "none") return;
  const pw = 240, ph = p.offsetHeight || 200;
  let x = e.clientX + 12;
  let y = e.clientY + 12;
  if (x + pw > window.innerWidth)  x = e.clientX - pw - 12;
  if (y + ph > window.innerHeight) y = e.clientY - ph - 12;
  p.style.left = x + "px";
  p.style.top  = y + "px";
}
function hidePopup() { getPopup().style.display = "none"; }

// ── StylePanel — pure DOM ──────────────────────────────────────────────────
class StylePanel {
  constructor(node) {
    this.node       = node;
    this.styles     = [];
    this.categories = [];
    this.favorites  = new Set();  // keys of favorited styles
    this.checkedCats= new Set();
    this.selected   = [];
    this.search     = "";
    this.filtered   = [];
    this.loaded     = false;
    this._thumbTimestamp = Date.now();
    this._elCats    = null;
    this._elStrip   = null;
    this._elSearch  = null;
    this._elGrid    = null;
    this.el         = null;
    this._build();
    this._load();
  }

  _w(name) {
    return this.node._hiddenWidgets?.[name] || this.node.widgets?.find(w => w.name === name);
  }

  // Unique key for a style. Many entries in styles.json share the same
  // `name` across different categories (e.g. "Sci Fi" exists in 3D, Fashion
  // and more), so identifying by name alone causes duplicates in the
  // selected list. We identify by "category::name" everywhere.
  _key(s) { return (s.category || "Other") + "::" + s.name; }

  _syncToWidgets() {
    ["style_1","style_2","style_3","style_4","style_5","style_6"].forEach((n, i) => {
      const w = this._w(n);
      if (w) w.value = this.selected[i] ? this._key(this.selected[i]) : "";
    });
    const wc = this._w("iterator_categories");
    if (wc) wc.value = [...this.checkedCats].join(",");
  }

  _syncFromWidgets() {
    this.selected = [];
    ["style_1","style_2","style_3","style_4","style_5","style_6"].forEach(n => {
      const w = this._w(n);
      if (w?.value) {
        // Accept both "category::name" (new) and plain "name" (legacy) for
        // backwards compatibility with workflows saved by earlier versions.
        const val = String(w.value);
        let s = null;
        if (val.includes("::")) {
          s = this.styles.find(st => this._key(st) === val);
        }
        if (!s) {
          s = this.styles.find(st => st.name === val);
        }
        if (s) this.selected.push(s);
      }
    });
    const wc = this._w("iterator_categories");
    if (wc?.value) {
      wc.value.split(",").map(s => s.trim()).filter(Boolean)
        .forEach(c => this.checkedCats.add(c));
    }
    this._filter();
  }

  async _load() {
    try {
      const [stylesRes, favsRes, modelsRes] = await Promise.all([
        fetch("/rogala/styles"),
        fetch("/rogala/favorites"),
        fetch("/rogala/thumbnails/presets"),
      ]);
      if (!stylesRes.ok) throw new Error(stylesRes.status);
      this.styles = await stylesRes.json();

      // Load favorites set
      if (favsRes.ok) {
        const favsData = await favsRes.json();
        this.favorites = new Set(favsData.favorites || []);
      }

      // Populate model preset dropdown
      if (modelsRes.ok && this._elModel) {
        const modelsData = await modelsRes.json();
        const presets = modelsData.presets || [];
		const savedModel = this._elModel.value;
        // Keep only the default option, add presets after
        while (this._elModel.options.length > 1) this._elModel.remove(1);
        for (const p of presets) {
          if (p === 'my_style') continue;
          const o = document.createElement('option');
          o.value = p; o.textContent = p;
          this._elModel.appendChild(o);
        }
        if (savedModel && [...this._elModel.options].some(o => o.value === savedModel)) {
          this._elModel.value = savedModel;
        } else {
          // Also try to restore from widget value (e.g. after tab switch)
          const tpw = this._w('thumbnail_preset');
          if (tpw?.value && [...this._elModel.options].some(o => o.value === tpw.value)) {
            this._elModel.value = tpw.value;
          }
        }
      }

      // Build categories list — My Styles first, Favorites second (if non-empty), then alphabetical
      const allCats = [...new Set(this.styles.map(s => s.category || "Other"))];
      const hasMyStyles = allCats.includes("My Styles");
      const regularCats = allCats.filter(c => c !== "My Styles").sort();
      let cats = regularCats;
      if (this.favorites.size > 0) cats = [FAVORITES_CAT, ...cats];
      if (hasMyStyles) cats = ["My Styles", ...cats];
      this.categories = cats;

      this.loaded = true;
      this._syncFromWidgets();
	  hidePopup();
      this._renderCats();
      this._renderGrid(true);
      this._renderStrip();
    } catch(e) {
      console.warn("[StylePanel] load failed:", e);
      if (this._elGrid) this._elGrid.textContent = "Failed to load styles.";
    }
  }

  _filter() {
    const q  = this.search.toLowerCase();
    const fc = this.checkedCats.size > 0;
    this.filtered = this.styles.filter(s => {
      const cat = s.category || "Other";
      const key = this._key(s);
      // Category filter
      if (fc) {
        const inFavCat = this.checkedCats.has(FAVORITES_CAT) && this.favorites.has(key);
        const inRegCat = this.checkedCats.has(cat);
        if (!inFavCat && !inRegCat) return false;
      }
      // Search filter
      if (q && !s.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }

  toggle(style) {
    const key = this._key(style);
    const i = this.selected.findIndex(s => this._key(s) === key);
    if (i >= 0) this.selected.splice(i, 1);
    else {
      if (this.selected.length >= 6) this.selected.shift();
      this.selected.push(style);
    }
    this._syncToWidgets();
    this._renderStrip();
    this._renderGrid();
  }

  remove(i) { this.selected.splice(i, 1); this._syncToWidgets(); this._renderStrip(); this._renderGrid(); }
  clear()   { this.selected = []; this._syncToWidgets(); this._renderStrip(); this._renderGrid(); }

  async _saveMyStyle() {
    const name = this._elStyleName?.value?.trim();
    if (!name) { alert("Please enter a style name."); return; }
    const positive = this._w("positive_text")?.value || "";
    const negative = this._w("negative_text")?.value || "";
    if (!positive) { alert("Positive prompt is empty."); return; }
    try {
      this._elSaveStyle.textContent = "Saving...";
      this._elSaveStyle.disabled = true;
      const res = await fetch("/rogala/my_styles/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, positive, negative }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      // Update field with sanitized name returned from server
      if (data.name) this._elStyleName.value = data.name;
      this._elSaveStyle.textContent = data.updated ? "Updated ✓" : "Saved ✓";
      this._thumbTimestamp = Date.now();
      await this.reload();
      setTimeout(() => {
        this._elSaveStyle.textContent = "Save Style";
        this._elSaveStyle.disabled = false;
        this._elStyleName.value = "";
      }, 2000);
    } catch(e) {
      console.error("[StylePanel] saveMyStyle failed:", e);
      this._elSaveStyle.textContent = "Error ✗";
      this._elSaveStyle.disabled = false;
      setTimeout(() => { this._elSaveStyle.textContent = "Save Style"; }, 2000);
    }
  }

  async toggleFavorite(style, starEl) {
    const key = this._key(style);
    try {
      const res = await fetch("/rogala/favorites/toggle", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      const data = await res.json();
      this.favorites = new Set(data.favorites || []);

      // Update star visual
      starEl.textContent = this.favorites.has(key) ? "⭐" : "☆";
      starEl.classList.toggle("active", this.favorites.has(key));

      // Rebuild categories
      const allCats2 = [...new Set(this.styles.map(s => s.category || "Other"))];
      const hasMyStyles2 = allCats2.includes("My Styles");
      const regularCats2 = allCats2.filter(c => c !== "My Styles").sort();
      let cats2 = regularCats2;
      if (this.favorites.size > 0) cats2 = [FAVORITES_CAT, ...cats2];
      if (hasMyStyles2) cats2 = ["My Styles", ...cats2];
      this.categories = cats2;
      this._renderCats();
	  hidePopup();
      this._filter();
      this._renderGrid();
    } catch(e) {
      console.warn("[StylePanel] toggleFavorite failed:", e);
    }
  }

  _build() {
    injectCSS();
    const panel = document.createElement("div");
    panel.className = "rg-panel";

    console.log("[rogala] Style Gallery v17-fixed loaded");

    // ── Toolbar: mode selector + model preset + reload ──────────────────
    const toolbar = document.createElement("div");
    toolbar.className = "rg-toolbar";

    this._elMode = document.createElement('select');
    this._elMode.className = 'rg-mode-sel';
    this._elMode.style.flex = '0 0 auto';
    ['Manual','Iterator'].forEach(m => {
      const o = document.createElement('option'); o.value = m; o.textContent = m;
      this._elMode.appendChild(o);
    });
    this._elMode.addEventListener('change', e => { if (this._onModeChange) this._onModeChange(e.target.value); });
    toolbar.appendChild(this._elMode);

    // Model preset dropdown — populated from thumbnails/styles subfolders via API
    this._elModel = document.createElement('select');
    this._elModel.className = 'rg-model-sel';
    this._elModel.style.flex = '1 1 80px';
    this._elModel.style.minWidth = '80px';
    this._elModel.title = "Select model thumbnail preset. Folders must be named with letters, digits and underscores only (e.g. FLUX_1, SDXL_base). Create a subfolder in thumbnails/ with your model name and place style thumbnails there.";
    const _defaultOpt = document.createElement('option');
    _defaultOpt.value = ''; _defaultOpt.textContent = 'Default (SDXL 1.0)';
    this._elModel.appendChild(_defaultOpt);
    this._elModel.addEventListener('change', () => {
      const w = this._w('thumbnail_preset');
      if (w) w.value = this._elModel.value;
      this._thumbTimestamp = Date.now();
      this._renderGrid(true);
    });
    toolbar.appendChild(this._elModel);

    this._elReload = document.createElement('button');
    this._elReload.className = 'rg-reload-btn';
    this._elReload.textContent = 'Reload Styles';
    this._elReload.addEventListener('click', async () => {
      await fetch('/rogala/reload_styles', { method: 'POST' });
      await this.reload();
    });
    toolbar.appendChild(this._elReload);

    // Style name input — for saving custom styles
    this._elStyleName = document.createElement('input');
    this._elStyleName.type = 'text';
    this._elStyleName.className = 'rg-model-sel';
    this._elStyleName.placeholder = 'Style name...';
    this._elStyleName.title = 'Style name: letters, digits and underscores only. Spaces and special characters are replaced automatically.';
    this._elStyleName.style.flex = '1 1 80px';
    this._elStyleName.style.minWidth = '80px';
    // Auto-sanitize: spaces → underscore, remove invalid chars
    this._elStyleName.addEventListener('input', e => {
      const pos = e.target.selectionStart;
      const clean = e.target.value.replace(/\s+/g, '_').replace(/[^\w]/g, '');
      if (clean !== e.target.value) {
        e.target.value = clean;
        e.target.setSelectionRange(pos, pos);
      }
    });
    toolbar.appendChild(this._elStyleName);

    // Save Style button
    this._elSaveStyle = document.createElement('button');
    this._elSaveStyle.className = 'rg-reload-btn';
    this._elSaveStyle.textContent = 'Save Style';
    this._elSaveStyle.title = 'Save current positive/negative prompts as a custom style to my_styles.json';
    this._elSaveStyle.addEventListener('click', () => this._saveMyStyle());
    toolbar.appendChild(this._elSaveStyle);

    panel.appendChild(toolbar);

    // ── Categories row ───────────────────────────────────────────────────
    const catsRow = document.createElement("div");
    catsRow.className = "rg-cats-row";

    this._elCatsTrash = document.createElement("div");
    this._elCatsTrash.className = "rg-trash";
    this._elCatsTrash.textContent = "🗑";
    this._elCatsTrash.title = "Clear selected categories";
    this._elCatsTrash.addEventListener("click", () => {
      if (this.checkedCats.size === 0) return;
      this.checkedCats.clear();
      this._filter(); this._syncToWidgets(); this._renderCats(); this._renderGrid(true);
    });
    catsRow.appendChild(this._elCatsTrash);

    this._elCats = document.createElement("div");
    this._elCats.className = "rg-cats";
    this._elCats.textContent = "Loading…";
    catsRow.appendChild(this._elCats);

    panel.appendChild(catsRow);

    this._elStrip = document.createElement("div");
    this._elStrip.className = "rg-active-strip";
    panel.appendChild(this._elStrip);

    const srh = document.createElement("div");
    srh.className = "rg-search";
    this._elSearch = document.createElement("input");
    this._elSearch.type = "text";
    this._elSearch.placeholder = "🔍  Search styles…";
    this._elSearch.addEventListener("input", () => {
      this.search = this._elSearch.value;
      this._filter();
      this._renderGrid();
    });
    this._elSearch.addEventListener("keydown", e => e.stopPropagation());
    srh.appendChild(this._elSearch);
    panel.appendChild(srh);

    this._elGrid = document.createElement("div");
    this._elGrid.className = "rg-grid";
    this._elGrid.textContent = "Loading styles…";
    panel.appendChild(this._elGrid);


    // footer — checkboxes only
    const footer = document.createElement('div');
    footer.className = 'rg-footer';

    this._elUseNeg = document.createElement('label');
    this._elUseNeg.className = 'rg-use-neg';
    const negCb = document.createElement('input');
    negCb.type = 'checkbox'; negCb.checked = true;
    negCb.addEventListener('change', e => { if (this._onUseNegChange) this._onUseNegChange(e.target.checked); });
    this._elUseNeg.appendChild(negCb);
    this._elUseNeg.appendChild(document.createTextNode(' use_negative'));
    footer.appendChild(this._elUseNeg);

    this._elAppendCounter = document.createElement('label');
    this._elAppendCounter.className = 'rg-use-neg';
    const counterCb = document.createElement('input');
    counterCb.type = 'checkbox'; counterCb.checked = false;
    counterCb.addEventListener('change', e => {
      const w = this._w('append_counter');
      if (w) w.value = e.target.checked;
    });
    this._elAppendCounter.appendChild(counterCb);
    this._elAppendCounter.appendChild(document.createTextNode(' name_timestamp'));
    footer.appendChild(this._elAppendCounter);

    this._elSavePrompt = document.createElement('label');
    this._elSavePrompt.className = 'rg-use-neg';
    const saveCb = document.createElement('input');
    saveCb.type = 'checkbox'; saveCb.checked = false;
    saveCb.addEventListener('change', e => {
      const w = this._w('save_prompt');
      if (w) w.value = e.target.checked;
    });
    this._elSavePrompt.appendChild(saveCb);
    this._elSavePrompt.appendChild(document.createTextNode(' save_prompt'));
    footer.appendChild(this._elSavePrompt);

    panel.appendChild(footer);

    this.el = panel;
  }

  _renderCats() {
    this._elCats.innerHTML = "";

    // Update the external trash button's active state
    if (this._elCatsTrash) {
      this._elCatsTrash.classList.toggle("has-sel", this.checkedCats.size > 0);
    }

    for (const cat of this.categories) {
      if (cat === FAVORITES_CAT && this.favorites.size === 0) continue;
      const checked = this.checkedCats.has(cat);
      const col = catColor(cat);
      const btn = document.createElement("div");
      btn.className = "rg-cat" + (checked ? " active" : "");
      if (checked) { btn.style.borderColor = col; btn.style.background = col + "22"; }

      const dot = document.createElement("span");
      dot.className = "dot";
      if (checked) dot.style.background = col;

      const lbl = document.createElement("span");
      lbl.textContent = cat;

      btn.appendChild(dot); btn.appendChild(lbl);
      btn.addEventListener("click", () => {
        this.checkedCats.has(cat) ? this.checkedCats.delete(cat) : this.checkedCats.add(cat);
        this._filter(); this._syncToWidgets(); this._renderCats(); this._renderGrid(true);
      });
      this._elCats.appendChild(btn);
    }
  }

  _renderStrip() {
    this._elStrip.innerHTML = "";
    const trash = document.createElement("div");
    trash.className = "rg-trash" + (this.selected.length ? " has-sel" : "");
    trash.textContent = "🗑";
    trash.title = "Clear all selected styles";
    trash.addEventListener("click", () => this.clear());
    this._elStrip.appendChild(trash);

    if (this.selected.length === 0) {
      const msg = document.createElement("span");
      msg.className = "rg-no-sel";
      msg.textContent = "No styles selected — click thumbnails below";
      this._elStrip.appendChild(msg);
    } else {
      this.selected.forEach((s, i) => {
        const col = catColor(s.category || "Other");

        // Mini thumbnail tag
        const tag = document.createElement("div");
        tag.className = "rg-mini";
        tag.style.borderColor = col;
        tag.title = `${s.category} — ${s.name}`;

        // Slot number in corner
        const slot = document.createElement("div");
        slot.className = "rg-mini-slot";
        slot.textContent = i + 1;
        slot.style.background = col;
        tag.appendChild(slot);

        // Thumbnail image (or initials fallback)
        const img = document.createElement("div");
        img.className = "rg-mini-img";
        if (s.thumbnail) {
          const fn = s.thumbnail.split(/[\\/]/).pop();
          const model = this._elModel?.value || '';
          const isMyStyle = s.category === "My Styles";
          const base = isMyStyle
            ? `/rogala/thumbnails/my_style/${fn}`
            : model ? `/rogala/thumbnails/${model}/${fn}` : `/rogala/thumbnails/styles/${fn}`;
          const imgEl = document.createElement("img");
          imgEl.src = `${base}?t=${this._thumbTimestamp}`;
          imgEl.onerror = () => {
            imgEl.onerror = null;
            imgEl.style.display = "none";
            if (!isMyStyle && model) {
              imgEl.src = `/rogala/thumbnails/styles/${fn}?t=${this._thumbTimestamp}`;
              imgEl.style.display = "";
            }
          };
          img.appendChild(imgEl);
        } else {
          const init = document.createElement("span");
          init.className = "rg-mini-init";
          init.style.color = col;
          init.textContent = s.name.split(/[\s\-_>]+/).slice(0, 2)
            .map(w => w[0]?.toUpperCase() || "").join("");
          img.appendChild(init);
        }
        tag.appendChild(img);

        // Close × button
        const rm = document.createElement("span");
        rm.className = "rg-mini-rm";
        rm.textContent = "×";
        rm.title = `Remove ${s.name}`;
        rm.addEventListener("click", e => { e.stopPropagation(); this.remove(i); });
        tag.appendChild(rm);

        // Reuse the grid popup on hover so user can read prompt/negative
        tag.addEventListener("mouseenter", e => showPopup(s, e));
        tag.addEventListener("mousemove",  e => movePopup(e));
        tag.addEventListener("mouseleave", () => hidePopup());

        this._elStrip.appendChild(tag);
      });
    }
  }

  _makeThumb(style) {
    const col = catColor(style.category || "Other");
    const thumb = document.createElement("div");
    thumb.className = "rg-thumb";
    thumb.dataset.key = this._key(style);
    thumb.dataset.catcolor = col;

    const imgBox = document.createElement("div");
    imgBox.className = "rg-thumb-img";

    const strip = document.createElement("div");
    strip.className = "color-strip";
    strip.style.background = col;
    imgBox.appendChild(strip);

    const init2 = document.createElement("span");
    init2.className = "initials";
    init2.style.color = col + "99";
    init2.textContent = style.name.split(/[\s\-_>]+/).slice(0, 2)
      .map(w => w[0]?.toUpperCase() || "").join("");
    imgBox.appendChild(init2);

    if (style.thumbnail) {
      const fn  = style.thumbnail.split(/[\\/]/).pop();
      const img = document.createElement("img");
      const model = this._elModel?.value || '';
      const isMyStyle = style.category === "My Styles";
      const base = isMyStyle
        ? `/rogala/thumbnails/my_style/${fn}`
        : model ? `/rogala/thumbnails/${model}/${fn}` : `/rogala/thumbnails/styles/${fn}`;
      img.src = `${base}?t=${this._thumbTimestamp}`;
      img.style.display = "none";
      img.onload  = () => { img.style.display = ""; init2.style.display = "none"; };
      // fallback to base folder if model-specific thumbnail not found
      img.onerror = () => {
        if (!isMyStyle && model) {
          img.onerror = null;
          img.src = `/rogala/thumbnails/styles/${fn}?t=${this._thumbTimestamp}`;
          img.style.display = "";
          init2.style.display = "none";
        } else {
          img.src = "";
          img.onerror = null;
          img.style.display = "none";
        }
      };
      imgBox.appendChild(img);
    }

    const badge = document.createElement("div");
    badge.className = "rg-badge";
    badge.style.display = "none";
    badge.style.background = col;
    imgBox.appendChild(badge);

    // Favorites star — bottom-right corner, visible on hover
    const star = document.createElement("div");
    star.className = "rg-fav" + (this.favorites.has(this._key(style)) ? " active" : "");
    star.textContent = this.favorites.has(this._key(style)) ? "⭐" : "☆";
    star.title = "Add to Favorites";
    star.addEventListener("click", e => {
      e.stopPropagation();   // don't toggle style selection
      this.toggleFavorite(style, star);
    });
    imgBox.appendChild(star);

    thumb.appendChild(imgBox);

    const lbl = document.createElement("div");
    lbl.className = "rg-lbl"; lbl.textContent = style.name; lbl.title = style.name;
    thumb.appendChild(lbl);

    thumb.addEventListener("click",      ()  => this.toggle(style));
    thumb.addEventListener("mouseenter", e   => showPopup(style, e));
    thumb.addEventListener("mousemove",  e   => movePopup(e));
    thumb.addEventListener("mouseleave", ()  => hidePopup());

    return thumb;
  }

  _updateThumbState(thumb, style) {
    const key = this._key(style);
    const activeIdx = this.selected.findIndex(s => this._key(s) === key);
    const badge = thumb.querySelector(".rg-badge");
    const imgBox = thumb.querySelector(".rg-thumb-img");
    const lbl    = thumb.querySelector(".rg-lbl");
    const star   = thumb.querySelector(".rg-fav");
    const col    = thumb.dataset.catcolor || "#4aaa6a";

    // Active selection state
    if (activeIdx >= 0) {
      thumb.classList.add("active");
      badge.textContent = activeIdx + 1;
      badge.style.display = "flex";
      if (imgBox) { imgBox.style.border = "1.5px solid " + col; imgBox.style.background = col + "22"; }
      if (lbl) lbl.style.color = col;
    } else {
      thumb.classList.remove("active");
      badge.style.display = "none";
      if (imgBox) { imgBox.style.border = ""; imgBox.style.background = ""; }
      if (lbl) lbl.style.color = "";
    }

    // Favorites star state
    if (star) {
      const isFav = this.favorites.has(key);
      star.textContent = isFav ? "⭐" : "☆";
      star.classList.toggle("active", isFav);
    }
  }

  _renderGrid(forceRebuild = false) {
    if (!this.loaded) { this._elGrid.textContent = "Loading…"; return; }
    if (!this.filtered.length) { this._elGrid.textContent = "No styles found."; return; }

    const existing = this._elGrid.querySelectorAll(".rg-thumb");
    const needsRebuild = forceRebuild ||
      existing.length !== this.filtered.length ||
      (existing.length > 0 && existing[0].dataset.key !== this._key(this.filtered[0]));

    if (needsRebuild) {
		hidePopup();
      this._elGrid.innerHTML = "";
      for (const style of this.filtered) {
        const thumb = this._makeThumb(style);
        this._updateThumbState(thumb, style);
        this._elGrid.appendChild(thumb);
      }
    } else {
      existing.forEach((thumb, i) => {
        this._updateThumbState(thumb, this.filtered[i]);
      });
    }
  }
  async reload() {
    this.loaded = false;
    this._thumbTimestamp = Date.now();
    this._elGrid.textContent = "Reloading…";
    await this._load();
  }
}

// ── Register ───────────────────────────────────────────────────────────────
app.registerExtension({
  name: "rogala.AdvancedStyleSelector",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData.name !== NODE_NAME) return;

    const _onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      _onCreated?.apply(this, arguments);
      injectNodeCSS();

      // Hide internal widgets. We DON'T remove them from this.widgets
      // because ComfyUI serializes widget values from that array when saving
      // the workflow. Instead we mark them as converted-widget AND override
      // computeSize to [0, 0] (not -4) so the canvas renderer doesn't paint
      // a faint outline in the gap between textareas and the DOM panel.
      const HIDE = ["style_1","style_2","style_3","style_4","style_5","style_6","iterator_categories","mode","iterator_seed","append_counter","save_prompt","thumbnail_preset"];
      for (const name of HIDE) {
        const w = this.widgets?.find(w => w.name === name);
        if (w) {
          w.type = "converted-widget";
          w.computeSize = () => [0, 0];
          w.hidden = true;
          if (w.inputEl) w.inputEl.style.display = "none";
        }
      }

      // hide use_negative widget — controlled by panel footer
      setTimeout(() => {
        const uw = this.widgets?.find(w => w.name === "use_negative");
        if (uw) {
          uw.hidden = true;
          uw.computeSize = () => [0, 0];
          uw.type = "converted-widget";
        }
      }, 0);

      // _hiddenWidgets alias kept for API compatibility — now just points
      // into this.widgets.
      this._hiddenWidgets = {};

      // Helper: find widget by name regardless of visibility
      const _findWidget = (name) =>
        this.widgets?.find(w => w.name === name);

      const _toggleNeg = (show) => {
        const uw = _findWidget("use_negative");
        const nw = _findWidget("negative_text");
        if (uw) uw.value = show;
        if (!nw) return;
        nw.hidden = !show;
        if (!show) { nw._savedCS = nw.computeSize; nw.computeSize = () => [0, -4]; }
        else if (nw._savedCS) { nw.computeSize = nw._savedCS; }
        if (nw.inputEl) nw.inputEl.style.display = show ? "" : "none";
        this.setSize(this.computeSize());
        app.graph.setDirtyCanvas(true, true);
      };

      // Force textarea heights. In the new ComfyUI frontend, multiline
      // textarea widgets get a `size-full` wrapper and stretch to fill the
      // node height — which steals space from our DOM gallery. We clamp them
      // to a fixed height instead.
      const TEXTAREA_H = 75;
      const _lockTextareaHeight = () => {
        for (const wname of ["positive_text", "negative_text"]) {
          const tw = this.widgets?.find(w => w.name === wname);
          if (!tw) continue;
          if (tw.inputEl) {
            tw.inputEl.style.height      = TEXTAREA_H + "px";
            tw.inputEl.style.minHeight   = TEXTAREA_H + "px";
            tw.inputEl.style.maxHeight   = TEXTAREA_H + "px";
            tw.inputEl.style.marginBottom = "4px";
            tw.inputEl.rows = 3;
            const wrap = tw.inputEl.parentElement;
            if (wrap && wrap.classList?.contains("dom-widget")) {
              wrap.style.height    = TEXTAREA_H + "px";
              wrap.style.minHeight = TEXTAREA_H + "px";
              wrap.style.maxHeight = TEXTAREA_H + "px";
            }
          }
          tw.computeSize = () => [0, TEXTAREA_H + 4];
        }
      };
      setTimeout(_lockTextareaHeight, 50);
      setTimeout(_lockTextareaHeight, 300);

      // DOM gallery widget
      const sp = new StylePanel(this);
      this._sp = sp;
      sp._onUseNegChange = (val) => _toggleNeg(val);
      sp._onModeChange = (val) => {
        const mw = _findWidget("mode");
        if (mw) mw.value = val;
      };
      setTimeout(() => {
        const uw = _findWidget("use_negative");
        const mw = _findWidget("mode");
        const acw = _findWidget("append_counter");
        const acb = sp._elAppendCounter?.querySelector("input");
        if (acb && acw) acb.checked = acw.value === true;
        const spw = _findWidget("save_prompt");
        const spb = sp._elSavePrompt?.querySelector("input");
        if (spb && spw) spb.checked = spw.value === true;
        const tpw = _findWidget("thumbnail_preset");
        if (tpw?.value && sp._elModel) {
          const opts = [...sp._elModel.options];
          if (opts.some(o => o.value === tpw.value)) {
            sp._elModel.value = tpw.value;
            sp._thumbTimestamp = Date.now();
          }
        }
        if (sp._elMode && mw) sp._elMode.value = mw.value || "Manual";

        // Restore use_negative state without triggering setDirtyCanvas.
        // Calling _toggleNeg here would mark the node as changed and cause
        // an automatic queue run when switching tabs.
        const cb = sp._elUseNeg?.querySelector("input");
        if (cb && uw) {
          const show = uw.value !== false;
          cb.checked = show;
          const nw = _findWidget("negative_text");
          if (!show && nw) {
            nw.hidden = true;
            nw._savedCS = nw.computeSize;
            nw.computeSize = () => [0, -4];
            if (nw.inputEl) nw.inputEl.style.display = "none";
          }
        }
      }, 0); //200 default

      // Add the DOM widget using the OFFICIAL addDOMWidget API options.
      // Per the ComfyUI frontend TypeScript signature:
      //   getMinHeight/getMaxHeight/getHeight are the documented way to
      //   control DOM widget sizing. Custom computeSize is NOT part of the
      //   API and is unreliable in the new frontend.
      //
      // Dynamic height: instead of a fixed GALLERY_H we compute the height
      // from the node's current size at every call. When the user drags the
      // node taller, getHeight() returns more — so the gallery grows too.
      const MIN_GALLERY_H = 680;   // never collapse below this
      const DEFAULT_GALLERY_H = 900;
      // Pixels taken up by title + positive_text + negative_text + margins.
      // Rough estimate — doesn't need to be exact, any error just leaves
      // a small gap or forces a tiny scroll; the panel is a flex column
      // internally so it handles whatever height we give it.
      const OVERHEAD = 200;

      const _computeGalleryH = () => {
        const nodeH = this.size?.[1] || 0;
        if (nodeH <= 0) return DEFAULT_GALLERY_H;
        return Math.max(MIN_GALLERY_H, nodeH - OVERHEAD);
      };

      this.addDOMWidget("style_gallery", "btn", sp.el, {
        serialize: false,
        hideOnZoom: false,
        getMinHeight: () => MIN_GALLERY_H,
        getMaxHeight: () => 4000,           // effectively unbounded
        getHeight:    () => _computeGalleryH(),
      });

      // When the node is resized by the user, ComfyUI doesn't automatically
      // re-query getHeight(), so we nudge it: update the internal panel size
      // and request a canvas redraw.
      const _prevOnResize = this.onResize;
      this.onResize = function (size) {
        _prevOnResize?.apply(this, arguments);
        app.graph.setDirtyCanvas(true, true);
      };
    };

    // enforce min width only — DOM widget handles its own height
    const _computeSize = nodeType.prototype.computeSize;
    nodeType.prototype.computeSize = function (w) {
      const base = _computeSize?.apply(this, arguments) ?? [PW, 200];
      base[0] = Math.max(base[0], PW);
      return base;
    };
  },
});
