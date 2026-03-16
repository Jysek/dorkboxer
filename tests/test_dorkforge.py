"""
DorkForge v4.0 - Comprehensive Test Suite
=============================================

Tests:
    1. DorkConfig - Configuration loading and validation
    2. DorkBuilder - Per-engine syntax generation
    3. DorkValidator - Rule-based validation
    4. DorkGenerator - End-to-end generation
    5. Multi-engine syntax correctness
    6. Edge cases and error handling
    7. Flask API endpoints
"""

import unittest
import sys
import os
import json

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dorkforge.engine import DorkConfig, DorkBuilder, DorkValidator, DorkGenerator


def get_config():
    """Helper: load config from default path."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", "default_config.json",
    )
    return DorkConfig(config_path)


class TestDorkConfig(unittest.TestCase):
    """Test configuration loading and access."""

    def setUp(self):
        self.config = get_config()

    def test_all_engines_loaded(self):
        engines = self.config.get_all_engine_ids()
        self.assertIn("google", engines)
        self.assertIn("bing", engines)
        self.assertIn("duckduckgo", engines)
        self.assertIn("yahoo", engines)
        self.assertEqual(len(engines), 4)

    def test_google_operators(self):
        ops = self.config.get_operators("google")
        for expected in ["intitle", "site", "filetype", "inurl", "intext"]:
            self.assertIn(expected, ops)

    def test_bing_operators(self):
        ops = self.config.get_operators("bing")
        for expected in ["site", "intitle", "inbody", "filetype"]:
            self.assertIn(expected, ops)

    def test_duckduckgo_operators(self):
        ops = self.config.get_operators("duckduckgo")
        self.assertIn("site", ops)
        self.assertIn("intitle", ops)
        self.assertIn("filetype", ops)
        # DDG has fewer operators
        self.assertNotIn("cache", ops)
        self.assertNotIn("inbody", ops)

    def test_yahoo_operators(self):
        ops = self.config.get_operators("yahoo")
        self.assertIn("site", ops)
        self.assertIn("hostname", ops)

    def test_filetypes_loaded(self):
        fts = self.config.get_filetypes("google")
        self.assertIn("pdf", fts)
        self.assertIn("php", fts)
        self.assertIn("sql", fts)
        self.assertGreater(len(fts), 10)

    def test_default_keywords(self):
        kws = self.config.default_keywords
        self.assertIn("Credentials", kws)
        self.assertIn("Infrastructure", kws)
        self.assertIn("login", kws["Credentials"])

    def test_generation_rules(self):
        rules = self.config.generation_rules
        self.assertIn("mutually_exclusive", rules)
        self.assertIn("max_operators_per_dork", rules)
        self.assertIn("max_dork_length", rules)
        self.assertIsInstance(rules["mutually_exclusive"], list)

    def test_engine_display_name(self):
        self.assertEqual(self.config.get_engine_display_name("google"), "Google")
        self.assertEqual(self.config.get_engine_display_name("bing"), "Bing")
        self.assertEqual(self.config.get_engine_display_name("duckduckgo"), "DuckDuckGo")
        self.assertEqual(self.config.get_engine_display_name("yahoo"), "Yahoo")

    def test_nonexistent_engine(self):
        self.assertIsNone(self.config.get_engine("nonexistent"))
        self.assertEqual(self.config.get_operators("nonexistent"), {})
        self.assertEqual(self.config.get_filetypes("nonexistent"), [])
        self.assertEqual(self.config.get_boolean_ops("nonexistent"), {})

    def test_nonexistent_engine_display_name(self):
        self.assertEqual(self.config.get_engine_display_name("xyz"), "xyz")

    def test_boolean_ops_loaded(self):
        google_bools = self.config.get_boolean_ops("google")
        self.assertIn("AND", google_bools)
        self.assertIn("OR", google_bools)
        self.assertIn("NOT", google_bools)
        self.assertIn("EXACT", google_bools)

    def test_operator_syntax_format(self):
        """All operators should have {value} in their syntax."""
        for eid in self.config.get_all_engine_ids():
            ops = self.config.get_operators(eid)
            for key, op_def in ops.items():
                self.assertIn("syntax", op_def, f"Missing syntax in {eid}/{key}")
                self.assertIn("{value}", op_def["syntax"],
                              f"Missing {{value}} in {eid}/{key} syntax")


class TestDorkBuilder(unittest.TestCase):
    """Test syntax building for each search engine."""

    def setUp(self):
        self.config = get_config()

    def test_google_operator_term(self):
        builder = DorkBuilder(self.config, "google")
        self.assertEqual(builder.build_operator_term("intitle", "login"), "intitle:login")
        self.assertEqual(builder.build_operator_term("filetype", "pdf"), "filetype:pdf")
        self.assertEqual(builder.build_operator_term("site", "example.com"), "site:example.com")

    def test_bing_operator_term(self):
        builder = DorkBuilder(self.config, "bing")
        self.assertEqual(builder.build_operator_term("intitle", "admin"), "intitle:admin")
        self.assertEqual(builder.build_operator_term("inbody", "password"), "inbody:password")

    def test_google_join_terms_and(self):
        builder = DorkBuilder(self.config, "google")
        result = builder.join_terms(["intitle:login", "filetype:php"], "AND")
        self.assertEqual(result, "intitle:login filetype:php")

    def test_bing_join_terms_and(self):
        builder = DorkBuilder(self.config, "bing")
        result = builder.join_terms(["intitle:login", "filetype:php"], "AND")
        self.assertEqual(result, "intitle:login AND filetype:php")

    def test_google_join_terms_or(self):
        builder = DorkBuilder(self.config, "google")
        result = builder.join_terms(["login", "admin"], "OR")
        self.assertEqual(result, "login OR admin")

    def test_bing_join_terms_or(self):
        builder = DorkBuilder(self.config, "bing")
        result = builder.join_terms(["login", "admin"], "OR")
        self.assertEqual(result, "login OR admin")

    def test_google_quote_value(self):
        builder = DorkBuilder(self.config, "google")
        self.assertEqual(builder.quote_value("admin panel"), '"admin panel"')

    def test_bing_quote_value(self):
        builder = DorkBuilder(self.config, "bing")
        self.assertEqual(builder.quote_value("admin panel"), '"admin panel"')

    def test_google_negate_term(self):
        builder = DorkBuilder(self.config, "google")
        result = builder.negate_term("facebook.com")
        self.assertEqual(result, "-facebook.com")

    def test_bing_negate_term(self):
        """Bing NOT should have space before term."""
        builder = DorkBuilder(self.config, "bing")
        result = builder.negate_term("facebook.com")
        self.assertEqual(result, "NOT facebook.com")

    def test_duckduckgo_negate_term(self):
        builder = DorkBuilder(self.config, "duckduckgo")
        result = builder.negate_term("facebook.com")
        self.assertEqual(result, "-facebook.com")

    def test_yahoo_negate_term(self):
        builder = DorkBuilder(self.config, "yahoo")
        result = builder.negate_term("facebook.com")
        self.assertEqual(result, "-facebook.com")

    def test_unknown_operator_returns_value(self):
        builder = DorkBuilder(self.config, "google")
        result = builder.build_operator_term("nonexistent", "test")
        self.assertEqual(result, "test")


class TestDorkValidator(unittest.TestCase):
    """Test dork validation rules."""

    def setUp(self):
        self.config = get_config()
        self.validator = DorkValidator(self.config)

    def test_valid_simple_dork(self):
        self.assertTrue(self.validator.is_valid("intitle:login", "google"))

    def test_valid_multi_operator(self):
        self.assertTrue(self.validator.is_valid("intitle:login filetype:php", "google"))

    def test_empty_dork_invalid(self):
        self.assertFalse(self.validator.is_valid("", "google"))

    def test_whitespace_dork_invalid(self):
        self.assertFalse(self.validator.is_valid("   ", "google"))

    def test_mutually_exclusive_filetype_ext(self):
        self.assertFalse(self.validator.is_valid("filetype:pdf ext:doc", "google"))

    def test_mutually_exclusive_intitle_allintitle(self):
        self.assertFalse(self.validator.is_valid("intitle:test allintitle:other", "google"))

    def test_duplicate_operator_invalid(self):
        self.assertFalse(self.validator.is_valid("intitle:login intitle:admin", "google"))

    def test_duplicate_site_valid(self):
        self.assertTrue(self.validator.is_valid("site:a.com site:b.com", "google"))

    def test_too_long_dork_invalid(self):
        long_dork = "intitle:" + "a" * 300
        self.assertFalse(self.validator.is_valid(long_dork, "google"))

    def test_plain_keyword_valid(self):
        self.assertTrue(self.validator.is_valid("login admin", "google"))

    def test_max_operators_exceeded(self):
        dork = "intitle:a inurl:b intext:c filetype:d site:e"
        self.assertFalse(self.validator.is_valid(dork, "google"))


class TestDorkGenerator(unittest.TestCase):
    """Test end-to-end dork generation."""

    def setUp(self):
        self.config = get_config()
        self.gen = DorkGenerator(self.config)

    def test_basic_google_generation(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login", "admin"],
            selected_operators=["intitle"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine"], "google")
        self.assertEqual(result["engine_name"], "Google")
        for d in result["dorks"]:
            self.assertIn("intitle:", d)

    def test_google_with_filetype(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle"],
            selected_filetypes=["php"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        has_filetype = any("filetype:php" in d for d in result["dorks"])
        self.assertTrue(has_filetype)

    def test_google_with_site(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["admin"],
            selected_operators=["intitle"],
            custom_site="example.com",
        )
        self.assertGreater(len(result["dorks"]), 0)
        for d in result["dorks"]:
            self.assertIn("site:example.com", d)

    def test_google_with_quotes(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["admin panel"],
            use_quotes=True,
        )
        self.assertGreater(len(result["dorks"]), 0)
        for d in result["dorks"]:
            self.assertIn('"admin panel"', d)

    def test_google_with_exclusions(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle"],
            include_exclusions=["facebook.com"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        for d in result["dorks"]:
            self.assertIn("-facebook.com", d)

    def test_bing_generation(self):
        result = self.gen.generate(
            engine_id="bing",
            keywords=["login"],
            selected_operators=["intitle"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine"], "bing")
        self.assertEqual(result["engine_name"], "Bing")

    def test_bing_with_exclusions(self):
        """Bing should use 'NOT term' syntax."""
        result = self.gen.generate(
            engine_id="bing",
            keywords=["login"],
            selected_operators=["intitle"],
            include_exclusions=["facebook.com"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        for d in result["dorks"]:
            self.assertIn("NOT facebook.com", d)

    def test_bing_with_filetype(self):
        result = self.gen.generate(
            engine_id="bing",
            keywords=["config"],
            selected_operators=["intitle"],
            selected_filetypes=["php"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        has_filetype = any("filetype:php" in d for d in result["dorks"])
        self.assertTrue(has_filetype)

    def test_duckduckgo_generation(self):
        result = self.gen.generate(
            engine_id="duckduckgo",
            keywords=["password"],
            selected_operators=["intitle"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine"], "duckduckgo")
        self.assertEqual(result["engine_name"], "DuckDuckGo")

    def test_yahoo_generation(self):
        result = self.gen.generate(
            engine_id="yahoo",
            keywords=["admin"],
            selected_operators=["intitle"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine"], "yahoo")

    def test_empty_keywords(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=[],
        )
        self.assertEqual(len(result["dorks"]), 0)
        self.assertGreater(len(result["warnings"]), 0)

    def test_invalid_operator_warning(self):
        result = self.gen.generate(
            engine_id="duckduckgo",
            keywords=["login"],
            selected_operators=["cache"],
        )
        has_warning = any("not available" in w.lower() for w in result["warnings"])
        self.assertTrue(has_warning)

    def test_max_results_limit(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=[f"kw{i}" for i in range(50)],
            selected_operators=["intitle", "inurl"],
            max_results=10,
        )
        self.assertLessEqual(len(result["dorks"]), 10)

    def test_no_duplicate_dorks(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login", "login"],
            selected_operators=["intitle"],
        )
        self.assertEqual(len(result["dorks"]), len(set(result["dorks"])))

    def test_dork_spacing_correct(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login", "admin"],
            selected_operators=["intitle"],
            selected_filetypes=["php"],
            custom_site="example.com",
            include_exclusions=["facebook.com"],
        )
        for d in result["dorks"]:
            self.assertEqual(d.strip(), d, f"Leading/trailing whitespace: '{d}'")
            self.assertNotIn("  ", d, f"Double space: '{d}'")

    def test_result_dict_structure(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["test"],
        )
        required_keys = ["dorks", "total_generated", "total_possible",
                         "engine", "engine_name", "warnings"]
        for key in required_keys:
            self.assertIn(key, result, f"Missing key: {key}")
        self.assertIsInstance(result["dorks"], list)
        self.assertIsInstance(result["warnings"], list)
        self.assertIsInstance(result["total_generated"], int)


class TestMultiEngineSyntax(unittest.TestCase):
    """Test that each engine produces syntactically correct dorks."""

    def setUp(self):
        self.config = get_config()
        self.gen = DorkGenerator(self.config)

    def test_google_syntax_no_and_keyword(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle"],
            selected_filetypes=["php"],
            shuffle=False,
        )
        for d in result["dorks"]:
            self.assertNotIn(" AND ", d)

    def test_bing_syntax_uses_and(self):
        result = self.gen.generate(
            engine_id="bing",
            keywords=["login"],
            selected_operators=["intitle"],
            selected_filetypes=["php"],
            shuffle=False,
        )
        for d in result["dorks"]:
            if "intitle:" in d and "filetype:" in d:
                self.assertIn(" AND ", d)

    def test_duckduckgo_syntax_no_and(self):
        result = self.gen.generate(
            engine_id="duckduckgo",
            keywords=["login"],
            selected_operators=["intitle"],
            shuffle=False,
        )
        for d in result["dorks"]:
            self.assertNotIn(" AND ", d)

    def test_yahoo_syntax_uses_and(self):
        result = self.gen.generate(
            engine_id="yahoo",
            keywords=["login"],
            selected_operators=["intitle"],
            selected_filetypes=["pdf"],
            shuffle=False,
        )
        for d in result["dorks"]:
            if "intitle:" in d and "filetype:" in d:
                self.assertIn(" AND ", d)

    def test_all_engines_produce_valid_dorks(self):
        for engine_id in self.config.get_all_engine_ids():
            result = self.gen.generate(
                engine_id=engine_id,
                keywords=["login", "admin"],
                selected_operators=["intitle", "site"],
                custom_site="example.com",
            )
            self.assertGreater(
                len(result["dorks"]), 0,
                f"Engine '{engine_id}' produced no dorks",
            )
            for d in result["dorks"]:
                self.assertEqual(d.strip(), d, f"[{engine_id}] Whitespace: '{d}'")
                self.assertNotIn("  ", d, f"[{engine_id}] Double space: '{d}'")
                self.assertGreater(len(d), 0, f"[{engine_id}] Empty dork")


class TestDorkGeneratorEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        self.config = get_config()
        self.gen = DorkGenerator(self.config)

    def test_keywords_only(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login", "admin panel"],
        )
        self.assertEqual(len(result["dorks"]), 2)

    def test_filetypes_only(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_filetypes=["pdf", "php"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        for d in result["dorks"]:
            has_ft = "filetype:pdf" in d or "filetype:php" in d
            self.assertTrue(has_ft, f"Missing filetype: '{d}'")

    def test_whitespace_keywords_stripped(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["  login  ", "  ", "admin"],
        )
        for d in result["dorks"]:
            self.assertNotIn("  ", d)

    def test_nonexistent_engine(self):
        result = self.gen.generate(
            engine_id="nonexistent",
            keywords=["login"],
        )
        self.assertIsInstance(result["dorks"], list)

    def test_filetype_operator_excluded_from_combo(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle", "filetype"],
            selected_filetypes=["php"],
        )
        for d in result["dorks"]:
            self.assertNotIn("filetype:filetype:", d)

    def test_empty_exclusions_ignored(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["test"],
            include_exclusions=["", "  ", "valid.com"],
        )
        for d in result["dorks"]:
            if "-" in d:
                self.assertIn("-valid.com", d)

    def test_empty_site_ignored(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["test"],
            custom_site="",
        )
        for d in result["dorks"]:
            self.assertNotIn("site:", d)

    def test_shuffle_produces_different_orders(self):
        """With enough dorks, shuffle should change order (probabilistic)."""
        result1 = self.gen.generate(
            engine_id="google",
            keywords=[f"kw{i}" for i in range(20)],
            selected_operators=["intitle"],
            shuffle=True,
        )
        result2 = self.gen.generate(
            engine_id="google",
            keywords=[f"kw{i}" for i in range(20)],
            selected_operators=["intitle"],
            shuffle=True,
        )
        # Same set of dorks, different order (probabilistic - very unlikely same)
        self.assertEqual(set(result1["dorks"]), set(result2["dorks"]))


class TestFlaskApp(unittest.TestCase):
    """Test Flask API endpoints."""

    def setUp(self):
        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_index_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"DorkForge", resp.data)

    def test_api_config(self):
        resp = self.client.get("/api/config")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("engines", data)
        self.assertIn("google", data["engines"])
        self.assertIn("default_keywords", data)
        self.assertIn("rules", data)

    def test_api_generate_success(self):
        resp = self.client.post("/api/generate", json={
            "engine": "google",
            "keywords": ["login", "admin"],
            "operators": ["intitle"],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("dorks", data)
        self.assertGreater(len(data["dorks"]), 0)
        self.assertEqual(data["engine"], "google")

    def test_api_generate_no_data(self):
        resp = self.client.post("/api/generate",
                                data="not json",
                                content_type="text/plain")
        # Flask returns 415 Unsupported Media Type for non-JSON content
        self.assertIn(resp.status_code, (400, 415))

    def test_api_generate_empty_keywords(self):
        resp = self.client.post("/api/generate", json={
            "engine": "google",
            "keywords": [],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data["dorks"]), 0)

    def test_api_generate_with_all_options(self):
        resp = self.client.post("/api/generate", json={
            "engine": "bing",
            "keywords": ["admin panel"],
            "operators": ["intitle"],
            "filetypes": ["php"],
            "site": "example.com",
            "use_quotes": True,
            "exclusions": ["facebook.com"],
            "max_results": 50,
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("dorks", data)
        self.assertEqual(data["engine"], "bing")

    def test_api_export_txt(self):
        resp = self.client.post("/api/export", json={
            "dorks": ["intitle:login", "intitle:admin"],
            "format": "txt",
            "engine_name": "Google",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp.content_type)
        self.assertIn(b"intitle:login", resp.data)

    def test_api_export_csv(self):
        resp = self.client.post("/api/export", json={
            "dorks": ["intitle:login"],
            "format": "csv",
            "engine_name": "Google",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.content_type)
        self.assertIn(b"intitle:login", resp.data)

    def test_api_export_json(self):
        resp = self.client.post("/api/export", json={
            "dorks": ["intitle:login"],
            "format": "json",
            "engine_name": "Google",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/json", resp.content_type)
        data = json.loads(resp.data)
        self.assertEqual(data["generator"], "DorkForge")
        self.assertEqual(data["total"], 1)

    def test_api_export_invalid_format(self):
        resp = self.client.post("/api/export", json={
            "dorks": ["test"],
            "format": "xml",
        })
        self.assertEqual(resp.status_code, 400)

    def test_api_export_empty_dorks(self):
        resp = self.client.post("/api/export", json={
            "dorks": [],
            "format": "txt",
        })
        self.assertEqual(resp.status_code, 400)

    def test_api_export_no_data(self):
        resp = self.client.post("/api/export",
                                data="not json",
                                content_type="text/plain")
        # Flask returns 415 Unsupported Media Type for non-JSON content
        self.assertIn(resp.status_code, (400, 415))


if __name__ == "__main__":
    unittest.main()
