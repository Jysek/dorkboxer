"""
DorkForge v3.0 - Comprehensive Unit Tests
===========================================

Tests for:
    1. DorkConfig (configuration loading)
    2. DorkBuilder (syntax generation per engine)
    3. DorkValidator (rule-based validation)
    4. DorkGenerator (end-to-end generation)
    5. Multi-engine syntax correctness
"""

import unittest
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dorkforge.engine import DorkConfig, DorkBuilder, DorkValidator, DorkGenerator


class TestDorkConfig(unittest.TestCase):
    """Test configuration loading."""

    def setUp(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "default_config.json",
        )
        self.config = DorkConfig(config_path)

    def test_engines_loaded(self):
        engines = self.config.get_all_engine_ids()
        self.assertIn("google", engines)
        self.assertIn("bing", engines)
        self.assertIn("duckduckgo", engines)
        self.assertIn("yahoo", engines)

    def test_google_operators(self):
        ops = self.config.get_operators("google")
        self.assertIn("intitle", ops)
        self.assertIn("site", ops)
        self.assertIn("filetype", ops)
        self.assertIn("inurl", ops)

    def test_bing_operators(self):
        ops = self.config.get_operators("bing")
        self.assertIn("site", ops)
        self.assertIn("intitle", ops)
        self.assertIn("inbody", ops)
        self.assertIn("filetype", ops)

    def test_duckduckgo_operators(self):
        ops = self.config.get_operators("duckduckgo")
        self.assertIn("site", ops)
        self.assertIn("intitle", ops)
        self.assertIn("filetype", ops)
        # DuckDuckGo has fewer operators
        self.assertNotIn("cache", ops)

    def test_yahoo_operators(self):
        ops = self.config.get_operators("yahoo")
        self.assertIn("site", ops)
        self.assertIn("hostname", ops)

    def test_filetypes_loaded(self):
        fts = self.config.get_filetypes("google")
        self.assertIn("pdf", fts)
        self.assertIn("php", fts)
        self.assertIn("sql", fts)

    def test_default_keywords(self):
        kws = self.config.default_keywords
        self.assertIn("Credentials", kws)
        self.assertIn("Infrastructure", kws)
        self.assertIn("login", kws["Credentials"])

    def test_generation_rules(self):
        rules = self.config.generation_rules
        self.assertIn("mutually_exclusive", rules)
        self.assertIn("max_operators_per_dork", rules)

    def test_engine_display_name(self):
        self.assertEqual(self.config.get_engine_display_name("google"), "Google")
        self.assertEqual(self.config.get_engine_display_name("bing"), "Bing")

    def test_nonexistent_engine(self):
        self.assertIsNone(self.config.get_engine("nonexistent"))
        self.assertEqual(self.config.get_operators("nonexistent"), {})
        self.assertEqual(self.config.get_filetypes("nonexistent"), [])


class TestDorkBuilder(unittest.TestCase):
    """Test syntax building for each search engine."""

    def setUp(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "default_config.json",
        )
        self.config = DorkConfig(config_path)

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
        """Google AND = space."""
        builder = DorkBuilder(self.config, "google")
        result = builder.join_terms(["intitle:login", "filetype:php"], "AND")
        self.assertEqual(result, "intitle:login filetype:php")

    def test_bing_join_terms_and(self):
        """Bing AND = ' AND '."""
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
        builder = DorkBuilder(self.config, "bing")
        result = builder.negate_term("facebook.com")
        self.assertEqual(result, "NOTfacebook.com")

    def test_unknown_operator_returns_value(self):
        builder = DorkBuilder(self.config, "google")
        result = builder.build_operator_term("nonexistent", "test")
        self.assertEqual(result, "test")


class TestDorkValidator(unittest.TestCase):
    """Test dork validation rules."""

    def setUp(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "default_config.json",
        )
        self.config = DorkConfig(config_path)
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
        """Multiple site: operators should be valid."""
        self.assertTrue(self.validator.is_valid("site:a.com site:b.com", "google"))

    def test_too_long_dork_invalid(self):
        long_dork = "intitle:" + "a" * 300
        self.assertFalse(self.validator.is_valid(long_dork, "google"))

    def test_plain_keyword_valid(self):
        self.assertTrue(self.validator.is_valid("login admin", "google"))


class TestDorkGenerator(unittest.TestCase):
    """Test end-to-end dork generation."""

    def setUp(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "default_config.json",
        )
        self.config = DorkConfig(config_path)
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
        # Bing uses AND joiner
        self.assertEqual(result["engine_name"], "Bing")

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
            selected_operators=["cache"],  # Not available in DDG
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
            keywords=["login", "login"],  # Duplicate keyword
            selected_operators=["intitle"],
        )
        self.assertEqual(len(result["dorks"]), len(set(result["dorks"])))

    def test_dork_spacing_correct(self):
        """Ensure no double spaces or leading/trailing whitespace."""
        result = self.gen.generate(
            engine_id="google",
            keywords=["login", "admin"],
            selected_operators=["intitle"],
            selected_filetypes=["php"],
            custom_site="example.com",
            include_exclusions=["facebook.com"],
        )
        for d in result["dorks"]:
            self.assertEqual(d.strip(), d, f"Leading/trailing whitespace in: '{d}'")
            self.assertNotIn("  ", d, f"Double space in: '{d}'")


class TestMultiEngineSyntax(unittest.TestCase):
    """Test that each engine produces syntactically correct dorks."""

    def setUp(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "default_config.json",
        )
        self.config = DorkConfig(config_path)
        self.gen = DorkGenerator(self.config)

    def test_google_syntax(self):
        """Google: operators are joined by space."""
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle"],
            selected_filetypes=["php"],
            shuffle=False,
        )
        for d in result["dorks"]:
            # Google AND is space, no "AND" keyword
            self.assertNotIn(" AND ", d)
            parts = d.split()
            for p in parts:
                if ":" in p:
                    # operator:value format
                    op_val = p.split(":", 1)
                    self.assertEqual(len(op_val), 2)

    def test_bing_syntax(self):
        """Bing: operators are joined by ' AND '."""
        result = self.gen.generate(
            engine_id="bing",
            keywords=["login"],
            selected_operators=["intitle"],
            selected_filetypes=["php"],
            shuffle=False,
        )
        for d in result["dorks"]:
            # Bing uses AND
            if "intitle:" in d and "filetype:" in d:
                self.assertIn(" AND ", d)

    def test_duckduckgo_syntax(self):
        """DuckDuckGo: space-separated like Google."""
        result = self.gen.generate(
            engine_id="duckduckgo",
            keywords=["login"],
            selected_operators=["intitle"],
            shuffle=False,
        )
        for d in result["dorks"]:
            self.assertNotIn(" AND ", d)

    def test_yahoo_syntax(self):
        """Yahoo: uses AND for joining."""
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
        """Every engine should produce non-empty, trimmed, no-double-space dorks."""
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
                self.assertEqual(d.strip(), d, f"[{engine_id}] Whitespace in: '{d}'")
                self.assertNotIn("  ", d, f"[{engine_id}] Double space in: '{d}'")
                self.assertGreater(len(d), 0, f"[{engine_id}] Empty dork")


class TestDorkGeneratorEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "default_config.json",
        )
        self.config = DorkConfig(config_path)
        self.gen = DorkGenerator(self.config)

    def test_keywords_only(self):
        """Keywords with no operators or filetypes."""
        result = self.gen.generate(
            engine_id="google",
            keywords=["login", "admin panel"],
        )
        self.assertEqual(len(result["dorks"]), 2)

    def test_filetypes_only(self):
        """Keywords + filetypes, no operators."""
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_filetypes=["pdf", "php"],
        )
        self.assertGreater(len(result["dorks"]), 0)
        for d in result["dorks"]:
            has_ft = "filetype:pdf" in d or "filetype:php" in d
            self.assertTrue(has_ft, f"Missing filetype in: '{d}'")

    def test_whitespace_keywords_stripped(self):
        result = self.gen.generate(
            engine_id="google",
            keywords=["  login  ", "  ", "admin"],
        )
        # " " should be filtered, "login" and "admin" should be trimmed
        for d in result["dorks"]:
            self.assertNotIn("  ", d)

    def test_nonexistent_engine(self):
        result = self.gen.generate(
            engine_id="nonexistent",
            keywords=["login"],
        )
        # Should still return a result (empty with warnings or just keywords)
        self.assertIsInstance(result["dorks"], list)

    def test_filetype_operator_excluded_from_combo(self):
        """If 'filetype' is in selected_operators AND filetypes are set,
        filetype should not be used as a prefix operator."""
        result = self.gen.generate(
            engine_id="google",
            keywords=["login"],
            selected_operators=["intitle", "filetype"],
            selected_filetypes=["php"],
        )
        for d in result["dorks"]:
            # Should not have filetype:filetype:php
            self.assertNotIn("filetype:filetype:", d)


if __name__ == "__main__":
    unittest.main()
