"""
DorkForge v5.0 - Comprehensive Test Suite
=============================================

Tests:
    1. DorkConfig - Configuration loading and validation (8 engines)
    2. DorkBuilder - Per-engine syntax generation (incl. auto-quoting)
    3. DorkValidator - Rule-based validation
    4. DorkGenerator - End-to-end generation
    5. DorkGenerator - Generate ALL (max_results=0)
    6. DorkGenerator - Multi-operator pair combinations
    7. DorkGenerator - count_combinations
    8. Multi-engine syntax correctness
    9. Edge cases and error handling
   10. Flask API endpoints (including /api/count)
"""

import json
import os
import sys
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dorkforge.engine import DorkConfig, DorkBuilder, DorkGenerator, DorkValidator


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
        expected = ["google", "bing", "duckduckgo", "yahoo", "yandex", "baidu", "shodan", "github"]
        for e in expected:
            self.assertIn(e, engines)
        self.assertEqual(len(engines), 8)

    def test_google_operators(self):
        ops = self.config.get_operators("google")
        for expected in ["intitle", "site", "filetype", "inurl", "intext", "before", "after"]:
            self.assertIn(expected, ops)

    def test_bing_operators(self):
        ops = self.config.get_operators("bing")
        for expected in ["site", "intitle", "inbody", "filetype", "linkfromdomain"]:
            self.assertIn(expected, ops)

    def test_duckduckgo_operators(self):
        ops = self.config.get_operators("duckduckgo")
        self.assertIn("site", ops)
        self.assertIn("intitle", ops)
        self.assertIn("filetype", ops)
        self.assertIn("inbody", ops)

    def test_yahoo_operators(self):
        ops = self.config.get_operators("yahoo")
        self.assertIn("site", ops)
        self.assertIn("hostname", ops)
        self.assertIn("link", ops)

    def test_yandex_operators(self):
        ops = self.config.get_operators("yandex")
        self.assertIn("site", ops)
        self.assertIn("mime", ops)
        self.assertIn("host", ops)
        self.assertIn("lang", ops)

    def test_baidu_operators(self):
        ops = self.config.get_operators("baidu")
        self.assertIn("site", ops)
        self.assertIn("intitle", ops)
        self.assertIn("filetype", ops)

    def test_shodan_operators(self):
        ops = self.config.get_operators("shodan")
        for expected in ["hostname", "port", "os", "country", "vuln", "http.title"]:
            self.assertIn(expected, ops)

    def test_github_operators(self):
        ops = self.config.get_operators("github")
        for expected in ["in:name", "in:file", "filename", "language", "extension"]:
            self.assertIn(expected, ops)

    def test_filetypes_loaded(self):
        fts = self.config.get_filetypes("google")
        self.assertIn("pdf", fts)
        self.assertIn("php", fts)
        self.assertIn("sql", fts)
        self.assertIn("key", fts)
        self.assertIn("pem", fts)
        self.assertGreater(len(fts), 30)

    def test_default_keywords_expanded(self):
        kws = self.config.default_keywords
        self.assertIn("Credentials", kws)
        self.assertIn("Infrastructure", kws)
        self.assertIn("Vulnerable Pages", kws)
        self.assertIn("IoT & Devices", kws)
        self.assertIn("Cloud & APIs", kws)
        self.assertIn("login", kws["Credentials"])

    def test_generation_rules(self):
        rules = self.config.generation_rules
        self.assertIn("mutually_exclusive", rules)
        self.assertIn("max_operators_per_dork", rules)
        self.assertIn("max_dork_length", rules)
        self.assertEqual(rules["max_operators_per_dork"], 5)
        self.assertEqual(rules["max_dork_length"], 512)

    def test_engine_display_name(self):
        self.assertEqual(self.config.get_engine_display_name("google"), "Google")
        self.assertEqual(self.config.get_engine_display_name("yandex"), "Yandex")
        self.assertEqual(self.config.get_engine_display_name("shodan"), "Shodan")
        self.assertEqual(self.config.get_engine_display_name("github"), "GitHub")

    def test_nonexistent_engine(self):
        self.assertIsNone(self.config.get_engine("nonexistent"))
        self.assertEqual(self.config.get_operators("nonexistent"), {})
        self.assertEqual(self.config.get_filetypes("nonexistent"), [])
        self.assertEqual(self.config.get_boolean_ops("nonexistent"), {})

    def test_boolean_ops_loaded(self):
        google_bools = self.config.get_boolean_ops("google")
        self.assertIn("AND", google_bools)
        self.assertIn("OR", google_bools)
        self.assertIn("NOT", google_bools)
        self.assertIn("EXACT", google_bools)

    def test_yandex_boolean_ops(self):
        yandex_bools = self.config.get_boolean_ops("yandex")
        self.assertEqual(yandex_bools["AND"], " && ")
        self.assertEqual(yandex_bools["OR"], " | ")
        self.assertEqual(yandex_bools["NOT"], " ~~")

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

    def test_google_operator_term_single_word(self):
        builder = DorkBuilder(self.config, "google")
        self.assertEqual(builder.build_operator_term("intitle", "login"), "intitle:login")
        self.assertEqual(builder.build_operator_term("filetype", "pdf"), "filetype:pdf")
        self.assertEqual(builder.build_operator_term("site", "example.com"), "site:example.com")

    def test_google_operator_term_multi_word_auto_quotes(self):
        builder = DorkBuilder(self.config, "google")
        self.assertEqual(
            builder.build_operator_term("intitle", "admin panel"),
            'intitle:"admin panel"'
        )
        self.assertEqual(
            builder.build_operator_term("inurl", "admin panel"),
            'inurl:"admin panel"'
        )

    def test_site_never_quoted(self):
        builder = DorkBuilder(self.config, "google")
        self.assertEqual(
            builder.build_operator_term("site", "example.com"),
            "site:example.com"
        )

    def test_filetype_never_quoted(self):
        builder = DorkBuilder(self.config, "google")
        self.assertEqual(builder.build_operator_term("filetype", "pdf"), "filetype:pdf")

    def test_bing_operator_term_multi_word(self):
        builder = DorkBuilder(self.config, "bing")
        self.assertEqual(
            builder.build_operator_term("intitle", "admin panel"),
            'intitle:"admin panel"'
        )
        self.assertEqual(
            builder.build_operator_term("inbody", "password reset"),
            'inbody:"password reset"'
        )

    def test_duckduckgo_operator_term_multi_word(self):
        builder = DorkBuilder(self.config, "duckduckgo")
        self.assertEqual(
            builder.build_operator_term("intitle", "admin panel"),
            'intitle:"admin panel"'
        )

    def test_yandex_operator_term(self):
        builder = DorkBuilder(self.config, "yandex")
        self.assertEqual(builder.build_operator_term("site", "example.com"), "site:example.com")
        self.assertEqual(builder.build_operator_term("mime", "pdf"), "mime:pdf")
        self.assertEqual(
            builder.build_operator_term("intitle", "admin panel"),
            'intitle:"admin panel"'
        )

    def test_shodan_operator_term(self):
        builder = DorkBuilder(self.config, "shodan")
        self.assertEqual(builder.build_operator_term("port", "443"), "port:443")
        self.assertEqual(builder.build_operator_term("country", "US"), "country:US")
        self.assertEqual(
            builder.build_operator_term("http.title", "admin panel"),
            'http.title:"admin panel"'
        )

    def test_github_operator_term(self):
        builder = DorkBuilder(self.config, "github")
        self.assertEqual(builder.build_operator_term("language", "python"), "language:python")
        self.assertEqual(builder.build_operator_term("filename", ".env"), "filename:.env")

    def test_google_join_terms_and(self):
        builder = DorkBuilder(self.config, "google")
        result = builder.join_terms(["intitle:login", "filetype:php"], "AND")
        self.assertEqual(result, "intitle:login filetype:php")

    def test_bing_join_terms_and(self):
        builder = DorkBuilder(self.config, "bing")
        result = builder.join_terms(["intitle:login", "filetype:php"], "AND")
        self.assertEqual(result, "intitle:login AND filetype:php")

    def test_yandex_join_terms_and(self):
        builder = DorkBuilder(self.config, "yandex")
        result = builder.join_terms(["site:test.com", "mime:pdf"], "AND")
        self.assertEqual(result, "site:test.com && mime:pdf")

    def test_google_negate_term(self):
        builder = DorkBuilder(self.config, "google")
        self.assertEqual(builder.negate_term("facebook.com"), "-facebook.com")

    def test_bing_negate_term(self):
        builder = DorkBuilder(self.config, "bing")
        self.assertEqual(builder.negate_term("facebook.com"), "NOT facebook.com")

    def test_yandex_negate_term(self):
        builder = DorkBuilder(self.config, "yandex")
        self.assertEqual(builder.negate_term("facebook.com"), "~~facebook.com")

    def test_unknown_operator_returns_value(self):
        builder = DorkBuilder(self.config, "google")
        self.assertEqual(builder.build_operator_term("nonexistent", "test"), "test")


class TestDorkValidator(unittest.TestCase):
    """Test dork validation rules."""

    def setUp(self):
        self.config = get_config()
        self.validator = DorkValidator(self.config)

    def test_valid_simple_dork(self):
        self.assertTrue(self.validator.is_valid("intitle:login", "google"))

    def test_valid_multi_operator(self):
        self.assertTrue(self.validator.is_valid("intitle:login filetype:php", "google"))

    def test_valid_quoted_operator_value(self):
        self.assertTrue(self.validator.is_valid('intitle:"admin panel"', "google"))

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
        long_dork = "intitle:" + "a" * 600
        self.assertFalse(self.validator.is_valid(long_dork, "google"))

    def test_five_operators_valid(self):
        """max_operators_per_dork is now 5."""
        dork = "intitle:a inurl:b intext:c filetype:d site:e"
        self.assertTrue(self.validator.is_valid(dork, "google"))

    def test_six_operators_invalid(self):
        dork = "intitle:a inurl:b intext:c filetype:d site:e inanchor:f"
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
        for d in result["dorks"]:
            self.assertIn("site:example.com", d)

    def test_google_with_quotes(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["admin panel"],
            use_quotes=True,
        )
        for d in result["dorks"]:
            self.assertIn('"admin panel"', d)

    def test_google_multi_word_operator_auto_quotes(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["admin panel"],
            selected_operators=["intitle"],
            shuffle=False,
        )
        for d in result["dorks"]:
            if "intitle:" in d:
                self.assertIn('intitle:"admin panel"', d)

    def test_google_with_exclusions(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle"],
            include_exclusions=["facebook.com"],
        )
        for d in result["dorks"]:
            self.assertIn("-facebook.com", d)

    # -- Generate ALL (max_results=0) --

    def test_generate_all_no_limit(self):
        """max_results=0 should return ALL valid dorks."""
        result = self.gen.generate(
            engine_id="google",
            keywords=[f"kw{i}" for i in range(10)],
            selected_operators=["intitle", "inurl"],
            max_results=0,
            shuffle=False,
        )
        # Should be at least 10*2 = 20 single-op combos + 10 pair combos = 30
        self.assertGreaterEqual(result["total_generated"], 30)
        self.assertEqual(result["total_generated"], result["total_possible"])

    def test_generate_all_with_filetypes(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login", "admin"],
            selected_operators=["intitle"],
            selected_filetypes=["pdf", "php"],
            max_results=0,
            shuffle=False,
        )
        # Single-op combos: 1*2*2=4, bare kw+ft: 2*2=4 => at least 8
        self.assertGreaterEqual(result["total_generated"], 8)

    # -- Multi-operator pairs --

    def test_multi_operator_pairs(self):
        """Two operators should generate pair combinations."""
        result = self.gen.generate(
            engine_id="google",
            keywords=["admin"],
            selected_operators=["intitle", "inurl"],
            max_results=0,
            shuffle=False,
        )
        # Single combos: 2*1=2, pair combos: 1*1=1 => total 3
        self.assertEqual(result["total_possible"], 3)
        has_pair = any("intitle:" in d and "inurl:" in d for d in result["dorks"])
        self.assertTrue(has_pair, "Should contain a pair combination")

    def test_multi_operator_pairs_with_filetype(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["admin"],
            selected_operators=["intitle", "inurl"],
            selected_filetypes=["php"],
            max_results=0,
            shuffle=False,
        )
        # Single: 2*1*1=2, bare: 1*1=1, pair+ft: 1*1*1=1, pair only: 1*1=1 => 5
        self.assertEqual(result["total_possible"], 5)

    # -- count_combinations --

    def test_count_combinations_basic(self):
        count = self.gen.count_combinations(
            engine_id="google",
            keywords=["login", "admin"],
            selected_operators=["intitle"],
        )
        self.assertEqual(count, 2)

    def test_count_combinations_with_pairs(self):
        count = self.gen.count_combinations(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle", "inurl"],
        )
        # 2 single + 1 pair = 3
        self.assertEqual(count, 3)

    def test_count_combinations_with_filetypes(self):
        count = self.gen.count_combinations(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle"],
            selected_filetypes=["pdf", "php"],
        )
        # single: 1*1*2=2, bare: 1*2=2 => 4
        self.assertEqual(count, 4)

    # -- Multi-engine generation --

    def test_bing_generation(self):
        result = self.gen.generate(
            engine_id="bing",
            keywords=["login"],
            selected_operators=["intitle"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine_name"], "Bing")

    def test_yandex_generation(self):
        result = self.gen.generate(
            engine_id="yandex",
            keywords=["login"],
            selected_operators=["intitle"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine_name"], "Yandex")

    def test_shodan_generation(self):
        result = self.gen.generate(
            engine_id="shodan",
            keywords=["apache"],
            selected_operators=["http.title"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine_name"], "Shodan")

    def test_github_generation(self):
        result = self.gen.generate(
            engine_id="github",
            keywords=["password"],
            selected_operators=["filename"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine_name"], "GitHub")

    def test_baidu_generation(self):
        result = self.gen.generate(
            engine_id="baidu",
            keywords=["admin"],
            selected_operators=["intitle"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        self.assertEqual(result["engine_name"], "Baidu")

    def test_empty_keywords(self):
        result = self.gen.generate(engine_id="google", keywords=[])
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
        result = self.gen.generate(engine_id="google", keywords=["test"])
        required_keys = ["dorks", "total_generated", "total_possible",
                         "engine", "engine_name", "warnings"]
        for key in required_keys:
            self.assertIn(key, result)


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

    def test_yandex_syntax_uses_double_ampersand(self):
        result = self.gen.generate(
            engine_id="yandex",
            keywords=["login"],
            selected_operators=["intitle"],
            selected_filetypes=["pdf"],
            shuffle=False,
        )
        for d in result["dorks"]:
            if "intitle:" in d and "mime:" in d:
                self.assertIn(" && ", d)

    def test_all_engines_produce_valid_dorks(self):
        # Skip Shodan (no filetypes, no site operator)
        for engine_id in self.config.get_all_engine_ids():
            ops = self.config.get_operators(engine_id)
            # Pick first available text operator
            text_op = None
            for candidate in ["intitle", "http.title", "in:name", "inurl"]:
                if candidate in ops:
                    text_op = candidate
                    break
            if text_op is None:
                continue

            result = self.gen.generate(
                engine_id=engine_id,
                keywords=["login", "admin"],
                selected_operators=[text_op],
            )
            self.assertGreater(
                len(result["dorks"]), 0,
                f"Engine '{engine_id}' produced no dorks",
            )
            for d in result["dorks"]:
                self.assertEqual(d.strip(), d, f"[{engine_id}] Whitespace: '{d}'")
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
        result = self.gen.generate(engine_id="nonexistent", keywords=["login"])
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

    def test_use_quotes_does_not_double_quote_operator_values(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["admin panel"],
            selected_operators=["intitle"],
            use_quotes=True,
            shuffle=False,
        )
        for d in result["dorks"]:
            self.assertNotIn('""', d, f"Double quotes found: '{d}'")

    def test_shodan_no_filetypes(self):
        """Shodan has no filetypes - should still work."""
        result = self.gen.generate(
            engine_id="shodan",
            keywords=["apache"],
            selected_operators=["hostname", "port"],
            max_results=0,
        )
        self.assertGreater(len(result["dorks"]), 0)

    def test_negative_max_results_treated_as_zero(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle"],
            max_results=-5,
        )
        # -5 should be treated as 0 (generate all)
        self.assertGreater(len(result["dorks"]), 0)


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
        self.assertIn("shodan", data["engines"])
        self.assertIn("github", data["engines"])
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
        self.assertGreater(len(data["dorks"]), 0)

    def test_api_generate_all(self):
        """max_results=0 should return all combinations."""
        resp = self.client.post("/api/generate", json={
            "engine": "google",
            "keywords": ["login", "admin"],
            "operators": ["intitle", "inurl"],
            "max_results": 0,
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        # 2 ops * 2 kw = 4 single + 1 pair * 2 kw = 2 pair => 6
        self.assertEqual(data["total_generated"], 6)

    def test_api_generate_no_data(self):
        resp = self.client.post("/api/generate",
                                data="not json",
                                content_type="text/plain")
        self.assertIn(resp.status_code, (400, 415))

    def test_api_generate_empty_keywords(self):
        resp = self.client.post("/api/generate", json={
            "engine": "google",
            "keywords": [],
        })
        data = resp.get_json()
        self.assertEqual(len(data["dorks"]), 0)

    def test_api_count(self):
        resp = self.client.post("/api/count", json={
            "engine": "google",
            "keywords": ["login", "admin"],
            "operators": ["intitle", "inurl"],
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["count"], 6)

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

    def test_api_export_json(self):
        resp = self.client.post("/api/export", json={
            "dorks": ["intitle:login"],
            "format": "json",
            "engine_name": "Google",
        })
        self.assertEqual(resp.status_code, 200)
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


if __name__ == "__main__":
    unittest.main()
