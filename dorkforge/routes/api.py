"""
DorkForge - API Routes
========================

Handles JSON API endpoints for generation, configuration, export,
and combination counting.
"""

import csv
import io
import json

from flask import Blueprint, Response, jsonify, request

from dorkforge.engine import DorkConfig, DorkGenerator

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Lazy-initialized shared instances
_config: DorkConfig = None
_generator: DorkGenerator = None


def _get_config() -> DorkConfig:
    global _config
    if _config is None:
        _config = DorkConfig.get_instance()
    return _config


def _get_generator() -> DorkGenerator:
    global _generator
    if _generator is None:
        _generator = DorkGenerator(_get_config())
    return _generator


@api_bp.route("/config")
def get_config():
    """Return the current configuration for the frontend."""
    config = _get_config()
    engines = {}
    for eid in config.get_all_engine_ids():
        eng = config.get_engine(eid)
        if eng is None:
            continue
        engines[eid] = {
            "name": eng["name"],
            "operators": eng["operators"],
            "filetypes": eng.get("filetype_list", []),
            "boolean_operators": eng.get("boolean_operators", {}),
        }
    return jsonify({
        "engines": engines,
        "default_keywords": config.default_keywords,
        "rules": config.generation_rules,
    })


@api_bp.route("/count", methods=["POST"])
def count():
    """Return estimated total combinations without generating dorks."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON data provided.", "count": 0}), 400

    keywords = data.get("keywords", [])
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split("\n") if k.strip()]

    generator = _get_generator()
    total = generator.count_combinations(
        engine_id=data.get("engine", "google"),
        keywords=keywords,
        selected_operators=data.get("operators", []),
        selected_filetypes=data.get("filetypes", []),
        custom_site=data.get("site", ""),
        include_exclusions=data.get("exclusions", []),
    )

    return jsonify({"count": total})


@api_bp.route("/generate", methods=["POST"])
def generate():
    """Generate dork queries from user input.

    max_results behaviour:
      - 0  -> generate ALL possible combinations (no artificial limit)
      - >0 -> cap at that number
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400

    engine_id = data.get("engine", "google")
    keywords = data.get("keywords", [])
    selected_operators = data.get("operators", [])
    selected_filetypes = data.get("filetypes", [])
    custom_site = data.get("site", "")
    use_quotes = data.get("use_quotes", False)
    exclusions = data.get("exclusions", [])

    # Parse max_results: 0 = all, positive = custom limit
    try:
        max_results = int(data.get("max_results", 100))
        if max_results < 0:
            max_results = 0
    except (ValueError, TypeError):
        max_results = 100

    # Handle string inputs (newline-delimited)
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split("\n") if k.strip()]
    if isinstance(exclusions, str):
        exclusions = [e.strip() for e in exclusions.split("\n") if e.strip()]

    generator = _get_generator()
    result = generator.generate(
        engine_id=engine_id,
        keywords=keywords,
        selected_operators=selected_operators,
        selected_filetypes=selected_filetypes,
        custom_site=custom_site,
        use_quotes=use_quotes,
        include_exclusions=exclusions,
        max_results=max_results,
        shuffle=True,
    )

    return jsonify(result)


@api_bp.route("/export", methods=["POST"])
def export():
    """Export dorks in TXT, CSV, or JSON format."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON data provided."}), 400

    dorks = data.get("dorks", [])
    fmt = data.get("format", "txt")
    engine_name = data.get("engine_name", "DorkForge")

    if not dorks:
        return jsonify({"error": "No dorks to export."}), 400

    if fmt == "txt":
        content = "\n".join(dorks) + "\n"
        return Response(
            content,
            mimetype="text/plain",
            headers={
                "Content-Disposition": "attachment; filename=dorkforge_export.txt"
            },
        )

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["#", "Dork Query", "Engine"])
        for i, d in enumerate(dorks, 1):
            writer.writerow([i, d, engine_name])
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=dorkforge_export.csv"
            },
        )

    if fmt == "json":
        from dorkforge import __version__
        export_data = {
            "generator": "DorkForge",
            "version": __version__,
            "engine": engine_name,
            "total": len(dorks),
            "dorks": dorks,
        }
        return Response(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            mimetype="application/json",
            headers={
                "Content-Disposition": "attachment; filename=dorkforge_export.json"
            },
        )

    return jsonify({"error": f"Unknown format: {fmt}"}), 400
