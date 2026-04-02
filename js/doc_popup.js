/**
 * doc_popup.js
 * ------------
 * Shared documentation popup for all rogala nodes.
 * No external dependencies — self-contained.
 *
 * Each node that has a DESCRIPTION field automatically gets
 * an orange "?" button in the top-right corner.
 * Clicking it opens a resizable Markdown popup.
 */

import { app } from "../../../scripts/app.js";

// ---------------------------------------------------------------------------
// Minimal Markdown → HTML renderer (no external deps)
// Supports: headings, bold, italic, inline code, code blocks,
//           tables, unordered/ordered lists, links, horizontal rules,
//           and paragraph line breaks.
// ---------------------------------------------------------------------------

/**
 * Convert a Markdown string to safe HTML.
 * Only a subset of Markdown is supported — enough for node documentation.
 *
 * @param {string} md
 * @returns {string} HTML string
 */
function renderMarkdown(md) {
  // Escape raw HTML to prevent injection
  const escape = (s) =>
    s.replace(/&/g, "&amp;")
     .replace(/</g, "&lt;")
     .replace(/>/g, "&gt;")
     .replace(/"/g, "&quot;");

  const lines  = md.split("\n");
  const out    = [];
  let inCode   = false;
  let codeBuf  = [];
  let inTable  = false;
  let inList   = false;
  let listType = "";

  const flushList = () => {
    if (inList) { out.push(`</${listType}>`); inList = false; listType = ""; }
  };
  const flushTable = () => {
    if (inTable) { out.push("</tbody></table>"); inTable = false; }
  };

  // Inline formatting applied after block structure is resolved
  const inline = (s) =>
    escape(s)
      // bold+italic
      .replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
      // bold
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      // italic
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      // inline code
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      // links  [text](url)
      .replace(
        /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
        '<a href="$2" target="_blank">$1</a>'
      );

  for (let i = 0; i < lines.length; i++) {
    const raw  = lines[i];
    const line = raw.trimEnd();

    // ---- fenced code block ----
    if (line.startsWith("```")) {
      if (!inCode) {
        flushList(); flushTable();
        inCode  = true;
        codeBuf = [];
      } else {
        out.push(`<pre><code>${escape(codeBuf.join("\n"))}</code></pre>`);
        inCode = false;
      }
      continue;
    }
    if (inCode) { codeBuf.push(raw); continue; }

    // ---- heading ----
    const hMatch = line.match(/^(#{1,6})\s+(.*)/);
    if (hMatch) {
      flushList(); flushTable();
      const level = hMatch[1].length;
      out.push(`<h${level}>${inline(hMatch[2])}</h${level}>`);
      continue;
    }

    // ---- horizontal rule ----
    if (/^[-*_]{3,}$/.test(line.trim())) {
      flushList(); flushTable();
      out.push("<hr>");
      continue;
    }

    // ---- table row ----
    if (line.startsWith("|") && line.endsWith("|")) {
      const cells = line.slice(1, -1).split("|").map((c) => c.trim());
      // separator row  |---|---|
      if (cells.every((c) => /^[-: ]+$/.test(c))) {
        // already handled by the header row below
        continue;
      }
      if (!inTable) {
        flushList();
        out.push('<table><thead><tr>');
        cells.forEach((c) => out.push(`<th>${inline(c)}</th>`));
        out.push("</tr></thead><tbody>");
        inTable = true;
      } else {
        out.push("<tr>");
        cells.forEach((c) => out.push(`<td>${inline(c)}</td>`));
        out.push("</tr>");
      }
      continue;
    }

    // ---- unordered list ----
    const ulMatch = line.match(/^(\s*)[-*+]\s+(.*)/);
    if (ulMatch) {
      flushTable();
      if (!inList || listType !== "ul") {
        flushList();
        out.push("<ul>"); inList = true; listType = "ul";
      }
      out.push(`<li>${inline(ulMatch[2])}</li>`);
      continue;
    }

    // ---- ordered list ----
    const olMatch = line.match(/^(\s*)\d+\.\s+(.*)/);
    if (olMatch) {
      flushTable();
      if (!inList || listType !== "ol") {
        flushList();
        out.push("<ol>"); inList = true; listType = "ol";
      }
      out.push(`<li>${inline(olMatch[2])}</li>`);
      continue;
    }

    // ---- blank line ----
    if (line.trim() === "") {
      flushList(); flushTable();
      out.push('<div style="margin:3px 0"></div>');
      continue;
    }

    // ---- normal paragraph line ----
    flushList(); flushTable();
    out.push(`<p>${inline(line)}</p>`);
  }

  flushList();
  flushTable();
  if (inCode) out.push(`<pre><code>${escape(codeBuf.join("\n"))}</code></pre>`);

  return out.join("\n");
}

// ---------------------------------------------------------------------------
// Stylesheet (injected once)
// ---------------------------------------------------------------------------

function ensureStylesheet() {
  const ID = "rogala-doc-popup-style";
  if (document.getElementById(ID)) return;

  const style = document.createElement("style");
  style.id = ID;
  style.textContent = `
    .rogala-doc-popup {
      background    : var(--comfy-menu-bg);
      position      : absolute;
      color         : var(--fg-color);
      font          : 11px monospace;
      line-height   : 1.3em;
      padding       : 8px;
      border-radius : 10px;
      border        : medium solid var(--border-color);
      z-index       : 5;
      overflow      : hidden;
      min-width     : 280px;
      min-height    : 80px;
    }
    .rogala-doc-popup .content-wrapper {
      overflow       : auto;
      max-height     : 100%;
      scrollbar-width: thin;
      scrollbar-color: var(--fg-color) var(--bg-color);
    }
    .rogala-doc-popup a         { color: yellow;  }
    .rogala-doc-popup a:visited { color: orange;  }
    .rogala-doc-popup a:hover   { color: red;     }
    .rogala-doc-popup table     { border-collapse: collapse; width: 100%; margin: 3px 0; }
    .rogala-doc-popup th,
    .rogala-doc-popup td        { border: 1px solid var(--border-color); padding: 2px 6px; text-align: left; }
    .rogala-doc-popup th        { background: var(--comfy-input-bg); }
    .rogala-doc-popup pre       { background: var(--comfy-input-bg); padding: 4px; border-radius: 4px; overflow-x: auto; margin: 2px 0; }
    .rogala-doc-popup code      { background: var(--comfy-input-bg); padding: 1px 3px; border-radius: 3px; }
    .rogala-doc-popup pre code  { background: none; padding: 0; }
    .rogala-doc-popup h1        { font-size: 13px; margin: 4px 0 2px; }
    .rogala-doc-popup h2        { font-size: 12px; margin: 4px 0 1px; }
    .rogala-doc-popup h3        { font-size: 11px; margin: 3px 0 1px; }
    .rogala-doc-popup p         { margin: 1px 0; }
    .rogala-doc-popup ul,
    .rogala-doc-popup ol        { margin: 1px 0; padding-left: 16px; }
    .rogala-doc-popup li        { margin: 0; }
    .rogala-doc-popup hr        { border-color: var(--border-color); margin: 4px 0; }
  `;
  document.head.appendChild(style);
}

// ---------------------------------------------------------------------------
// Popup factory
// ---------------------------------------------------------------------------

/**
 * Create and attach a documentation popup to the DOM.
 *
 * @param {string}      description  Markdown or plain-text content
 * @param {AbortSignal} signal       Used to remove event listeners on close
 * @param {Function}    onClose      Called when the close button is clicked
 * @param {object}      opts
 * @param {boolean}     [opts.scaleResize=false]  Account for canvas zoom when resizing
 * @returns {{ docElement: HTMLElement }}
 */
function createDocPopup(description, signal, onClose, opts = {}) {
  ensureStylesheet();

  // -- wrapper --
  const popup = document.createElement("div");
  popup.classList.add("rogala-doc-popup");

  // -- content --
  const content = document.createElement("div");
  content.classList.add("content-wrapper");

  content.innerHTML = renderMarkdown(description);

  popup.appendChild(content);

  // -- resize handle (bottom-right triangle) --
  const handle = document.createElement("div");
  const borderColor = getComputedStyle(document.documentElement)
    .getPropertyValue("--border-color")
    .trim();
  Object.assign(handle.style, {
    width         : "0",
    height        : "0",
    position      : "absolute",
    bottom        : "0",
    right         : "0",
    cursor        : "se-resize",
    borderTop     : "10px solid transparent",
    borderLeft    : "10px solid transparent",
    borderBottom  : `10px solid ${borderColor}`,
    borderRight   : `10px solid ${borderColor}`,
  });
  popup.appendChild(handle);

  let resizing = false, startX, startY, startW, startH;

  handle.addEventListener("mousedown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    resizing = true;
    startX = e.clientX;
    startY = e.clientY;
    startW = parseInt(getComputedStyle(popup).width,  10);
    startH = parseInt(getComputedStyle(popup).height, 10);
  }, { signal });

  document.addEventListener("mousemove", (e) => {
    if (!resizing) return;
    const scale = opts.scaleResize ? app.canvas.ds.scale : 1;
    popup.style.width  = `${startW + (e.clientX - startX) / scale}px`;
    popup.style.height = `${startH + (e.clientY - startY) / scale}px`;
  }, { signal });

  document.addEventListener("mouseup", () => { resizing = false; }, { signal });

  // -- close button --
  const closeBtn = document.createElement("div");
  closeBtn.textContent = "✕";
  Object.assign(closeBtn.style, {
    position  : "absolute",
    top       : "0",
    right     : "0",
    cursor    : "pointer",
    padding   : "5px",
    color     : "red",
    fontSize  : "12px",
  });
  closeBtn.addEventListener("mousedown", (e) => {
    e.stopPropagation();
    onClose();
  }, { signal });
  popup.appendChild(closeBtn);

  document.body.appendChild(popup);
  return { docElement: popup };
}

// ---------------------------------------------------------------------------
// Attach popup behaviour to a node type
// ---------------------------------------------------------------------------

/**
 * Add the "?" button and popup to any nodeType that has a description.
 *
 * @param {object} nodeData  Raw node schema from ComfyUI
 * @param {object} nodeType  LiteGraph node constructor
 * @param {object} [opts]
 * @param {number} [opts.icon_size=14]
 * @param {number} [opts.icon_margin=4]
 */
export function addDocumentation(nodeData, nodeType, opts = {}) {
  if (!nodeData.description) return;

  const iconSize   = opts.icon_size   ?? 14;
  const iconMargin = opts.icon_margin ?? 4;
  let   docElement = null;

  // -- draw the "?" icon --
  const origDrawFg = nodeType.prototype.onDrawForeground;
  nodeType.prototype.onDrawForeground = function (ctx) {
    const r = origDrawFg ? origDrawFg.apply(this, arguments) : undefined;
    if (this.flags.collapsed) return r;

    // open popup on first render after show_doc becomes true
    if (this.show_doc && docElement === null) {
      ({ docElement } = createDocPopup(
        nodeData.description,
        this.docCtrl.signal,
        () => {
          this.show_doc = false;
          docElement?.remove();
          docElement = null;
        },
        { scaleResize: true }
      ));
    } else if (!this.show_doc && docElement !== null) {
      docElement.remove();
      docElement = null;
    }

    // position popup relative to canvas
    if (this.show_doc && docElement) {
      const bcr    = app.canvas.canvas.getBoundingClientRect();
      const rect   = ctx.canvas.getBoundingClientRect();
      const scaleX = rect.width  / ctx.canvas.width;
      const scaleY = rect.height / ctx.canvas.height;

      const transform = new DOMMatrix()
        .scaleSelf(scaleX, scaleY)
        .multiplySelf(ctx.getTransform())
        .translateSelf(this.size[0] * scaleX * Math.max(1, window.devicePixelRatio), 0)
        .translateSelf(10, -32);

      const scale = new DOMMatrix().scaleSelf(transform.a, transform.d);

      Object.assign(docElement.style, {
        transformOrigin : "0 0",
        transform       : scale.toString(),
        left            : `${transform.a + bcr.x + transform.e}px`,
        top             : `${transform.d + bcr.y + transform.f}px`,
      });
    }

    // draw "?" icon
    const x = this.size[0] - iconSize - iconMargin;
    ctx.save();
    ctx.translate(x - 2, iconSize - 34);
    ctx.scale(iconSize / 32, iconSize / 32);
    ctx.font      = "bold 36px monospace";
    ctx.fillStyle = "orange";
    ctx.fillText("?", 0, 24);
    ctx.restore();

    return r;
  };

  // -- click detection --
  const origMouseDown = nodeType.prototype.onMouseDown;
  nodeType.prototype.onMouseDown = function (e, localPos) {
    const r    = origMouseDown ? origMouseDown.apply(this, arguments) : undefined;
    const x    = this.size[0] - iconSize - iconMargin;
    const y    = iconSize - 34;
    const hit  =
      localPos[0] > x && localPos[0] < x + iconSize &&
      localPos[1] > y && localPos[1] < y + iconSize;

    if (hit) {
      this.show_doc = !this.show_doc;
      if (this.show_doc) { this.docCtrl = new AbortController(); }
      else               { this.docCtrl?.abort(); }
      return true;
    }
    return r;
  };

  // -- cleanup on node removal --
  const origRemoved = nodeType.prototype.onRemoved;
  nodeType.prototype.onRemoved = function () {
    const r = origRemoved ? origRemoved.apply(this, []) : undefined;
    docElement?.remove();
    docElement = null;
    return r;
  };
}

// ---------------------------------------------------------------------------
// Auto-register for all rogala nodes
// ---------------------------------------------------------------------------

app.registerExtension({
  name: "rogala.DocPopup",

  async beforeRegisterNodeDef(nodeType, nodeData) {
    // Apply only to rogala nodes — identified by category starting with "rogala/"
    if (!nodeData.category?.startsWith("rogala/")) return;
    if (!nodeData.description) return;
    addDocumentation(nodeData, nodeType);
  },
});
