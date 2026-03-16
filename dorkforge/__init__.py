"""
DorkForge - Professional Dork Query Generator
===============================================

A modular Flask web application for building and managing
dork queries across multiple search engines (Google, Bing,
DuckDuckGo, Yahoo, Yandex, Baidu, Shodan, GitHub) with
correct syntax per engine.

Architecture:
    config/              - JSON configuration (operators, filetypes, rules)
    dorkforge/
        __init__.py      - Package root, version info
        engine/          - Core query generation logic
            __init__.py  - DorkConfig, DorkBuilder, DorkValidator, DorkGenerator
        routes/          - Flask route blueprints
            __init__.py  - Route registration
            api.py       - /api/* endpoints
            views.py     - Page rendering routes
    app.py               - Flask application factory
    templates/           - Jinja2 HTML templates
    static/              - CSS, JS assets
    tests/               - Unit and integration tests
"""

__version__ = "5.0.0"
__app_name__ = "DorkForge"
