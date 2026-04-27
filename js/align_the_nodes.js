import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "My.OrderTool.BottomStationary",
    async setup() {

        // ─── Localization (UI tooltips only) — 9 languages: en, uk, de, fr, es, it, pt, zh, ja ──
        const LOCALES = {
    en: {
        alignLeft:   "Align Left",
        alignRight:  "Align Right",
        alignTop:    "Align Top",
        alignBottom: "Align Bottom",
        distributeH: "Distribute Horizontally",
        distributeV: "Distribute Vertically",
        matchWidth:  "Match Width (widest)",
        deselect:    "Deselect All",
        scaleDown:   "Scale Down",
        scaleUp:     "Scale Up",
    },
    uk: {
        alignLeft:   "Вирівняти по лівому краю",
        alignRight:  "Вирівняти по правому краю",
        alignTop:    "Вирівняти по верхньому краю",
        alignBottom: "Вирівняти по нижньому краю",
        distributeH: "Розподілити по горизонталі",
        distributeV: "Розподілити по вертикалі",
        matchWidth:  "Однакова ширина (по найширшій)",
        deselect:    "Скасувати виділення",
        scaleDown:   "Зменшити",
        scaleUp:     "Збільшити",
    },
    de: {
        alignLeft:   "Links ausrichten",
        alignRight:  "Rechts ausrichten",
        alignTop:    "Oben ausrichten",
        alignBottom: "Unten ausrichten",
        distributeH: "Horizontal verteilen",
        distributeV: "Vertikal verteilen",
        matchWidth:  "Breite angleichen (breiteste)",
        deselect:    "Auswahl aufheben",
        scaleDown:   "Verkleinern",
        scaleUp:     "Vergrößern",
    },
    fr: {
        alignLeft:   "Aligner à gauche",
        alignRight:  "Aligner à droite",
        alignTop:    "Aligner en haut",
        alignBottom: "Aligner en bas",
        distributeH: "Distribuer horizontalement",
        distributeV: "Distribuer verticalement",
        matchWidth:  "Uniformiser la largeur (la plus grande)",
        deselect:    "Tout désélectionner",
        scaleDown:   "Réduire",
        scaleUp:     "Agrandir",
    },
    es: {
        alignLeft:   "Alinear a la izquierda",
        alignRight:  "Alinear a la derecha",
        alignTop:    "Alinear en la parte superior",
        alignBottom: "Alinear en la parte inferior",
        distributeH: "Distribuir horizontalmente",
        distributeV: "Distribuir verticalmente",
        matchWidth:  "Igualar ancho (el más ancho)",
        deselect:    "Deseleccionar todo",
        scaleDown:   "Reducir",
        scaleUp:     "Ampliar",
    },
    it: {
        alignLeft:   "Allinea a sinistra",
        alignRight:  "Allinea a destra",
        alignTop:    "Allinea in alto",
        alignBottom: "Allinea in basso",
        distributeH: "Distribuisci orizzontalmente",
        distributeV: "Distribuisci verticalmente",
        matchWidth:  "Uniforma la larghezza (più ampia)",
        deselect:    "Deseleziona tutto",
        scaleDown:   "Riduci",
        scaleUp:     "Ingrandisci",
    },
    pt: {
        alignLeft:   "Alinhar à esquerda",
        alignRight:  "Alinhar à direita",
        alignTop:    "Alinhar ao topo",
        alignBottom: "Alinhar à base",
        distributeH: "Distribuir horizontalmente",
        distributeV: "Distribuir verticalmente",
        matchWidth:  "Igualar largura (à maior)",
        deselect:    "Desmarcar tudo",
        scaleDown:   "Reduzir",
        scaleUp:     "Ampliar",
    },
    zh: {
        alignLeft:   "左对齐",
        alignRight:  "右对齐",
        alignTop:    "顶对齐",
        alignBottom: "底对齐",
        distributeH: "水平分布",
        distributeV: "垂直分布",
        matchWidth:  "匹配宽度（最宽）",
        deselect:    "取消选择",
        scaleDown:   "缩小",
        scaleUp:     "放大",
    },
    ja: {
        alignLeft:   "左揃え",
        alignRight:  "右揃え",
        alignTop:    "上揃え",
        alignBottom: "下揃え",
        distributeH: "横方向に均等配置",
        distributeV: "縦方向に均等配置",
        matchWidth:  "幅を揃える（最大に合わせる）",
        deselect:    "選択を解除",
        scaleDown:   "縮小",
        scaleUp:     "拡大",
    }
        };

        // Detect browser language, fallback to English
        const detectLang = () => {
            const raw = (navigator.language || navigator.userLanguage || "en").toLowerCase();
            const code = raw.split("-")[0];
            return LOCALES[code] ? code : "en";
        };

        const t = LOCALES[detectLang()];

        // ─── Button size levels ───────────────────────────────────
        // Instead of scaling the whole panel, we scale only button size.
        // Panel position (bottom: 6px) stays fixed at all times.
        // Sizes: -2 / -1 / 0 / +1 / +2
        const BTN_SIZES  = [20, 26, 32, 38, 44]; // px width & height per level
        const FONT_SIZES = [16, 18, 20, 22, 24]; // px icon font size per level
        const SCALE_BASE = 2;                     // index of "0" level
        let sizeIndex = SCALE_BASE;

        // Auto base size offset based on screen width (1080p / 2K / 4K)
        const getAutoOffset = () => {
            const w = window.innerWidth;
            if (w > 2560) return 2;  // shift up 2 levels on 4K
            if (w > 1920) return 1;  // shift up 1 level on 2K
            return 0;
        };

        // All buttons registered here for bulk resize
        const allBtns = [];

        const applySize = () => {
            const idx  = Math.min(BTN_SIZES.length - 1, sizeIndex + getAutoOffset());
            const size = BTN_SIZES[idx];
            const font = FONT_SIZES[idx];
            allBtns.forEach(btn => {
                btn.style.width    = `${size}px`;
                btn.style.height   = `${size}px`;
                btn.style.fontSize = `${font}px`;
            });
        };

        window.addEventListener('resize', applySize);

        // ─── Collapse state ───────────────────────────────────────
        let isCollapsed = false;

        // ─── Wrapper (fixed anchor — contains panel + line handle) ─
        const wrapper = document.createElement("div");
        wrapper.style.cssText = `
            position: fixed;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            z-index: 10001;
            display: flex;
            flex-direction: column;
            align-items: center;
        `;

        // ─── Panel ────────────────────────────────────────────────
        const menu = document.createElement("div");

        menu.style.cssText = `
            background: rgba(20, 20, 20, 0.85);
            border: 1px solid #444;
            display: flex;
            align-items: center;
            padding: 8px 12px;
            gap: 6px;
            border-radius: 12px 12px 0 0;
            box-shadow: 0 -5px 25px rgba(0,0,0,0.6);
            backdrop-filter: blur(10px);
            opacity: 0.5;
            transition: opacity 0.3s ease, border-color 0.3s ease,
                        transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        `;

        // ─── Line handle (variant B) ───────────────────────────────
        // Thin pill-shaped bar, always visible at the bottom.
        // Orange when collapsed, gray when expanded.
        const handle = document.createElement("div");
        handle.title = "Show / Hide toolbar";
        handle.style.cssText = `
            width: 48px;
            height: 4px;
            background: #555;
            border-radius: 2px 2px 0 0;
            cursor: pointer;
            transition: background 0.2s, width 0.2s;
            flex-shrink: 0;
        `;

        handle.onmouseover = () => {
            handle.style.background = "#ff9000";
            handle.style.width      = "60px";
        };
        handle.onmouseout = () => {
            handle.style.background = isCollapsed ? "#ff9000" : "#555";
            handle.style.width      = "48px";
        };
        handle.onclick = () => {
            isCollapsed = !isCollapsed;
            if (isCollapsed) {
                menu.style.transform     = `translateY(calc(100% + 4px))`;
                menu.style.opacity       = "0";
                menu.style.pointerEvents = "none";
                handle.style.background  = "#ff9000";
            } else {
                menu.style.transform     = "translateY(0)";
                menu.style.opacity       = "0.5";
                menu.style.pointerEvents = "auto";
                handle.style.background  = "#555";
            }
        };

        // Wake up panel on hover (only when expanded)
        menu.onmouseover = () => {
            if (isCollapsed) return;
            menu.style.opacity     = "1";
            menu.style.borderColor = "#666";
        };
        menu.onmouseout = () => {
            if (isCollapsed) return;
            menu.style.opacity     = "0.5";
            menu.style.borderColor = "#444";
        };

        // ─── Button factory ───────────────────────────────────────
        const createBtn = (text, title, onClick, customStyle = "") => {
            const btn = document.createElement("button");
            btn.innerText = text;
            btn.style.cssText = `
                cursor: pointer;
                width: 40px; height: 40px;
                display: flex; align-items: center; justify-content: center;
                background: #333; color: #eee; border: 1px solid #444;
                border-radius: 8px; font-size: 16px;
                transition: all 0.2s;
                position: relative;
                ${customStyle}
            `;

            const tip = document.createElement("div");
            tip.innerText = title;
            tip.style.cssText = `
                position: absolute;
                bottom: calc(100% + 1px);
                left: 0;
                background: rgba(20, 20, 20, 0.92);
                color: #eee;
                font-size: 14px;
                padding: 4px 8px;
                border-radius: 6px;
                border: 1px solid #555;
                white-space: nowrap;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.15s;
                z-index: 10002;
            `;
            btn.appendChild(tip);

            btn.onmouseover = () => {
                btn.style.borderColor = "#ff9000";
                btn.style.background  = "#444";
                btn.style.transform   = "translateY(-3px)";
                btn.style.boxShadow   = "0 4px 10px rgba(255, 144, 0, 0.2)";
                tip.style.opacity     = "1";
            };
            btn.onmouseout = () => {
                btn.style.borderColor = "#444";
                btn.style.background  = "#333";
                btn.style.transform   = "translateY(0)";
                btn.style.boxShadow   = "none";
                tip.style.opacity     = "0";
            };
            btn.onclick = onClick;
            menu.appendChild(btn);
            allBtns.push(btn);
            return btn;
        };

        const addSep = () => {
            const sep = document.createElement("div");
            sep.style.cssText = "width:1px; background:#555; margin:6px 4px; align-self:stretch;";
            menu.appendChild(sep);
        };

        // ─── Node logic ───────────────────────────────────────────
        const getNodes = () => Object.values(app.canvas.selected_nodes);

        const run = (fn) => {
            if (getNodes().length < 2) return;
            fn();
            app.canvas.setDirty(true, true);
        };

        const actions = {
            alignLeft: () => {
                const n = getNodes();
                const x = Math.min(...n.map(o => o.pos[0]));
                n.forEach(o => o.pos[0] = x);
            },
            alignRight: () => {
                const n = getNodes();
                const x = Math.max(...n.map(o => o.pos[0] + o.size[0]));
                n.forEach(o => o.pos[0] = x - o.size[0]);
            },
            alignTop: () => {
                const n = getNodes();
                const y = Math.min(...n.map(o => o.pos[1]));
                n.forEach(o => o.pos[1] = y);
            },
            alignBottom: () => {
                const n = getNodes();
                const y = Math.max(...n.map(o => o.pos[1] + o.size[1]));
                n.forEach(o => o.pos[1] = y - o.size[1]);
            },
            // Distribute evenly accounting for node sizes (gap between edges, not centers)
            distributeH: () => {
                const n = getNodes();
                const spanX = Math.max(...n.map(o => o.pos[0])) - Math.min(...n.map(o => o.pos[0]));
                const spanY = Math.max(...n.map(o => o.pos[1])) - Math.min(...n.map(o => o.pos[1]));
                if (spanY > spanX) {
                    const avgX = n.reduce((s, o) => s + o.pos[0] + o.size[0] / 2, 0) / n.length;
                    n.forEach(o => { o.pos[0] = avgX - o.size[0] / 2; });
                } else {
                    const sorted = n.slice().sort((a, b) => a.pos[0] - b.pos[0]);
                    const totalWidth = sorted.reduce((s, o) => s + o.size[0], 0);
                    const spanX2 = sorted[sorted.length - 1].pos[0] + sorted[sorted.length - 1].size[0] - sorted[0].pos[0];
                    const gap = (spanX2 - totalWidth) / (sorted.length - 1);
                    let cursor = sorted[0].pos[0];
                    sorted.forEach(o => { o.pos[0] = cursor; cursor += o.size[0] + gap; });
                }
            },
            distributeV: () => {
                const n = getNodes();
                const spanX = Math.max(...n.map(o => o.pos[0])) - Math.min(...n.map(o => o.pos[0]));
                const spanY = Math.max(...n.map(o => o.pos[1])) - Math.min(...n.map(o => o.pos[1]));
                if (spanX > spanY) {
                    const avgY = n.reduce((s, o) => s + o.pos[1] + o.size[1] / 2, 0) / n.length;
                    n.forEach(o => { o.pos[1] = avgY - o.size[1] / 2; });
                } else {
                    const sorted = n.slice().sort((a, b) => a.pos[1] - b.pos[1]);
                    const totalHeight = sorted.reduce((s, o) => s + o.size[1], 0);
                    const spanY2 = sorted[sorted.length - 1].pos[1] + sorted[sorted.length - 1].size[1] - sorted[0].pos[1];
                    const gap = (spanY2 - totalHeight) / (sorted.length - 1);
                    let cursor = sorted[0].pos[1];
                    sorted.forEach(o => { o.pos[1] = cursor; cursor += o.size[1] + gap; });
                }
            },
            // Set all nodes to the widest node's width, rounded to nearest 5px
            matchWidth: () => {
                const n = getNodes();
                const maxW = Math.max(...n.map(o => o.size[0]));
                const w = Math.round(maxW / 5) * 5;
                const spanX = Math.max(...n.map(o => o.pos[0])) - Math.min(...n.map(o => o.pos[0]));
                const spanY = Math.max(...n.map(o => o.pos[1])) - Math.min(...n.map(o => o.pos[1]));
                if (spanX > spanY) {
                    n.forEach(o => { o.size[0] = w; });
                } else {
                    const minX = Math.min(...n.map(o => o.pos[0]));
                    n.forEach(o => { o.size[0] = w; o.pos[0] = minX; });
                }
            },
        };

        // ─── UI ───────────────────────────────────────────────────

        // Group 1: Alignment
        createBtn("←", t.alignLeft,   () => run(actions.alignLeft));
        createBtn("→", t.alignRight,  () => run(actions.alignRight));
        createBtn("↑", t.alignTop,    () => run(actions.alignTop));
        createBtn("↓", t.alignBottom, () => run(actions.alignBottom));

        addSep();

        // Group 2: Distribution
        createBtn("⇔", t.distributeH, () => run(actions.distributeH));
        createBtn("⇳", t.distributeV, () => run(actions.distributeV));

        addSep();

        // Group 3: Size & Utilities
        createBtn("▤", t.matchWidth, () => run(actions.matchWidth));
        createBtn("✕", t.deselect,   () => app.canvas.deselectAllNodes(),
            "color: #e05050; border-color: #553333;");

        addSep();

        // Group 4: Button size control
        // Scale indicator: -2 / -1 / 0 / +1 / +2
        const scaleIndicator = document.createElement("div");
        scaleIndicator.style.cssText = `
            color: #666; font-size: 12px; width: 26px;
            text-align: center; user-select: none;
            font-weight: 600; letter-spacing: -0.02em;
            font-variant-numeric: tabular-nums;
        `;

        const updateIndicator = () => {
            const level = sizeIndex - SCALE_BASE;
            scaleIndicator.textContent = level === 0 ? "0" : (level > 0 ? `+${level}` : `${level}`);
            scaleIndicator.style.color = level === 0 ? "#666" : "#ff9000";
        };

        // Note: − and + buttons ARE added to allBtns — they scale together with action buttons
        const btnMinus = document.createElement("button");
        btnMinus.innerText = "−";
        btnMinus.style.cssText = `
            cursor: pointer; width: 40px; height: 40px;
            display: flex; align-items: center; justify-content: center;
            background: #333; color: #aaa; border: 1px solid #444;
            border-radius: 8px; font-size: 22px; font-weight: 300;
            transition: all 0.2s; flex-shrink: 0; position: relative;
        `;
        const tipMinus = document.createElement("div");
        tipMinus.innerText = t.scaleDown;
        tipMinus.style.cssText = `
            position: absolute; bottom: calc(100% + 1px); left: 0;
            background: rgba(20,20,20,0.92); color: #eee; font-size: 14px;
            padding: 4px 8px; border-radius: 6px; border: 1px solid #555;
            white-space: nowrap; pointer-events: none; opacity: 0;
            transition: opacity 0.15s; z-index: 10002;
        `;
        btnMinus.appendChild(tipMinus);
        btnMinus.onmouseover = () => { btnMinus.style.borderColor = "#ff9000"; btnMinus.style.color = "#ff9000"; btnMinus.style.background = "#444"; tipMinus.style.opacity = "1"; };
        btnMinus.onmouseout  = () => { btnMinus.style.borderColor = "#444";    btnMinus.style.color = "#aaa";    btnMinus.style.background = "#333"; tipMinus.style.opacity = "0"; };
        btnMinus.onclick = () => {
            if (sizeIndex > 0) { sizeIndex--; applySize(); updateIndicator(); }
        };

        const btnPlus = document.createElement("button");
        btnPlus.innerText = "+";
        btnPlus.style.cssText = `
            cursor: pointer; width: 40px; height: 40px;
            display: flex; align-items: center; justify-content: center;
            background: #333; color: #aaa; border: 1px solid #444;
            border-radius: 8px; font-size: 22px; font-weight: 300;
            transition: all 0.2s; flex-shrink: 0; position: relative;
        `;
        const tipPlus = document.createElement("div");
        tipPlus.innerText = t.scaleUp;
        tipPlus.style.cssText = `
            position: absolute; bottom: calc(100% + 1px); left: 0;
            background: rgba(20,20,20,0.92); color: #eee; font-size: 14px;
            padding: 4px 8px; border-radius: 6px; border: 1px solid #555;
            white-space: nowrap; pointer-events: none; opacity: 0;
            transition: opacity 0.15s; z-index: 10002;
        `;
        btnPlus.appendChild(tipPlus);
        btnPlus.onmouseover = () => { btnPlus.style.borderColor = "#ff9000"; btnPlus.style.color = "#ff9000"; btnPlus.style.background = "#444"; tipPlus.style.opacity = "1"; };
        btnPlus.onmouseout  = () => { btnPlus.style.borderColor = "#444";    btnPlus.style.color = "#aaa";    btnPlus.style.background = "#333"; tipPlus.style.opacity = "0"; };
        btnPlus.onclick = () => {
            if (sizeIndex < BTN_SIZES.length - 1) { sizeIndex++; applySize(); updateIndicator(); }
        };

        menu.appendChild(btnMinus);
        allBtns.push(btnMinus);
        menu.appendChild(scaleIndicator);
        menu.appendChild(btnPlus);
        allBtns.push(btnPlus);

        updateIndicator();

        // Build: wrapper → menu (panel) + handle (thin line, always visible)
        wrapper.appendChild(menu);
        wrapper.appendChild(handle);
        document.body.appendChild(wrapper);
        applySize();
    }
});
