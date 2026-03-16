#!/usr/bin/env python3
"""
DorkForge - Professional Google Dork Query Generator
=====================================================

A refactored, modular desktop application for building and managing
Google dork queries with:
    - Abstracted DorkGenerator engine (testable, reusable)
    - Intelligent rule-based combination algorithm
    - Centralized state management (single source of truth)
    - Professional UI with sidebar builder, live preview, results panel
    - Collapsible accordion sections for reduced cognitive load
    - In-panel search/filter with query highlighting

Architecture:
    dorkforge/engine/  - Core query generation logic
    dorkforge/state/   - Centralized state management
    dorkforge/ui/      - User interface components
    dorkforge/data/    - Default data sets
    dorkforge/utils/   - Shared utilities

Run: python dorkforge_app.py
No external dependencies - uses only Python standard library.
"""

import tkinter as tk
from tkinter import ttk

from dorkforge.utils import COLORS
from dorkforge.ui import DorkForgeApp


def main():
    root = tk.Tk()

    # Configure ttk style
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "TProgressbar",
        troughcolor=COLORS["bg_dark"],
        background=COLORS["accent_green"],
        darkcolor=COLORS["accent_green"],
        lightcolor=COLORS["accent_green"],
        bordercolor=COLORS["border"],
        thickness=8,
    )

    app = DorkForgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
