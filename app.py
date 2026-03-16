"""
DorkForge - Flask Web Application
===================================

Professional web-based Google Dork Generator supporting
Google, Bing, DuckDuckGo, and Yahoo with correct syntax per engine.
"""

import json
import csv
import io
from flask import Flask, render_template, request, jsonify, Response

from dorkforge.engine import DorkConfig, DorkGenerator

app = Flask(__name__)

# Initialize config and engine at startup
config = DorkConfig.get_instance()
generator = DorkGenerator(config)


@app.route("/")
def index():
    """Render the main application page."""
    engines = {}
    for eid in config.get_all_engine_ids():
        eng = config.get_engine(eid)
        engines[eid] = {
            "name": eng["name"],
            "operators": {
                k: v["description"] for k, v in eng["operators"].items()
            },
            "filetypes": eng.get("filetype_list", []),
        }
    default_keywords = config.default_keywords
    return render_template(
        "index.html",
        engines=engines,
        default_keywords=default_keywords,
    )


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Generate dork queries from user input."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400

    engine_id = data.get("engine", "google")
    keywords = data.get("keywords", [])
    selected_operators = data.get("operators", [])
    selected_filetypes = data.get("filetypes", [])
    custom_site = data.get("site", "")
    use_quotes = data.get("use_quotes", False)
    exclusions = data.get("exclusions", [])
    max_results = min(int(data.get("max_results", 100)), 10000)

    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split("\n") if k.strip()]

    if isinstance(exclusions, str):
        exclusions = [e.strip() for e in exclusions.split("\n") if e.strip()]

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


@app.route("/api/config")
def api_config():
    """Return the current configuration for the frontend."""
    engines = {}
    for eid in config.get_all_engine_ids():
        eng = config.get_engine(eid)
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


@app.route("/api/export", methods=["POST"])
def api_export():
    """Export dorks in various formats."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided."}), 400

    dorks = data.get("dorks", [])
    fmt = data.get("format", "txt")
    engine_name = data.get("engine_name", "DorkForge")

    if fmt == "txt":
        content = "\n".join(dorks) + "\n"
        return Response(
            content,
            mimetype="text/plain",
            headers={"Content-Disposition": f"attachment; filename=dorkforge_export.txt"},
        )
    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["#", "Dork Query", "Engine"])
        for i, d in enumerate(dorks, 1):
            writer.writerow([i, d, engine_name])
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=dorkforge_export.csv"},
        )
    elif fmt == "json":
        export_data = {
            "generator": "DorkForge",
            "version": "3.0.0",
            "engine": engine_name,
            "total": len(dorks),
            "dorks": dorks,
        }
        return Response(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename=dorkforge_export.json"},
        )

    return jsonify({"error": "Unknown format."}), 400


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
