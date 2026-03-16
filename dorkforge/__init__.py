"""
DorkForge - Professional Dork Query Generator
===============================================

A modular web application for building and managing
dork queries across multiple search engines (Google, Bing,
DuckDuckGo, Yahoo) with correct syntax per engine.

Architecture:
    config/          - JSON configuration (operators, filetypes, rules)
    dorkforge/
        engine/      - Core query generation logic (DorkGenerator, DorkBuilder)
        state/       - Centralized application state management
        ui/          - Legacy UI widgets (Tkinter, deprecated)
        ui/widgets/  - Legacy reusable widget components
        data/        - Legacy data sets (operators, keywords, filetypes)
        utils/       - Shared utilities (styling, helpers)
    app.py           - Flask web application
    templates/       - Jinja2 HTML templates
    static/          - CSS, JS, assets
"""

__version__ = "3.0.0"
__app_name__ = "DorkForge"
