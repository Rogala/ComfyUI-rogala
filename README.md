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
├── nodes/               # One .py file per node (or logical group)
│   └── _template.py     # Copy this to create a new node
├── js/                  # Frontend extensions loaded by ComfyUI
├── config/              # JSON configuration files
│   └── categories.json  # Category definitions
└── web/                 # Static web assets (CSS, icons) if needed
```

