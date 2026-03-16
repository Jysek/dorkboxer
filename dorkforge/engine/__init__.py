"""
DorkForge - Core Dork Generation Engine
========================================

Pure-logic engine with ZERO UI dependencies.
Generates syntactically correct dork queries for multiple search engines
using operators and keywords loaded from configuration.
"""

import json
import os
import random
import itertools
from typing import List, Dict, Optional, Tuple, Set


class DorkConfig:
    """Loads and manages configuration for search engines, operators, and filetypes."""

    _instance = None

    @classmethod
    def get_instance(cls) -> "DorkConfig":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton (for testing)."""
        cls._instance = None

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # __file__ = dorkforge/engine/__init__.py
            # Go up 3 levels: engine/ -> dorkforge/ -> project_root/
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            config_path = os.path.join(
                project_root,
                "config",
                "default_config.json",
            )
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

    @property
    def search_engines(self) -> Dict:
        return self._config.get("search_engines", {})

    @property
    def default_keywords(self) -> Dict[str, List[str]]:
        return self._config.get("default_keywords", {})

    @property
    def generation_rules(self) -> Dict:
        return self._config.get("generation_rules", {})

    def get_engine(self, engine_id: str) -> Optional[Dict]:
        return self.search_engines.get(engine_id)

    def get_operators(self, engine_id: str) -> Dict:
        engine = self.get_engine(engine_id)
        if engine is None:
            return {}
        return engine.get("operators", {})

    def get_filetypes(self, engine_id: str) -> List[str]:
        engine = self.get_engine(engine_id)
        if engine is None:
            return []
        return engine.get("filetype_list", [])

    def get_boolean_ops(self, engine_id: str) -> Dict:
        engine = self.get_engine(engine_id)
        if engine is None:
            return {}
        return engine.get("boolean_operators", {})

    def get_all_engine_ids(self) -> List[str]:
        return list(self.search_engines.keys())

    def get_engine_display_name(self, engine_id: str) -> str:
        engine = self.get_engine(engine_id)
        if engine is None:
            return engine_id
        return engine.get("name", engine_id)


class DorkBuilder:
    """Builds syntactically correct dork queries for a specific search engine.

    Handles spacing, quoting, and operator formatting per engine syntax.
    """

    def __init__(self, config: DorkConfig, engine_id: str = "google"):
        self.config = config
        self.engine_id = engine_id
        self.engine = config.get_engine(engine_id) or {}
        self.operators = self.engine.get("operators", {})
        self.boolean_ops = self.engine.get("boolean_operators", {})

    def build_operator_term(self, operator_key: str, value: str) -> str:
        """Build a single operator:value term with correct syntax.

        Examples:
            build_operator_term("intitle", "login")  -> "intitle:login"
            build_operator_term("filetype", "pdf")    -> "filetype:pdf"
        """
        op_def = self.operators.get(operator_key)
        if op_def is None:
            return value

        syntax = op_def["syntax"]
        return syntax.replace("{value}", value)

    def quote_value(self, value: str) -> str:
        """Wrap value in quotes using the engine's exact-match syntax."""
        exact_syntax = self.boolean_ops.get("EXACT", '"{value}"')
        if exact_syntax is None:
            return value
        return exact_syntax.replace("{value}", value)

    def join_terms(self, terms: List[str], operator: str = "AND") -> str:
        """Join multiple dork terms with the correct boolean connector.

        The connector depends on the search engine:
          - Google AND = space
          - Bing AND = " AND "
          - etc.
        """
        joiner = self.boolean_ops.get(operator, " ")
        if joiner is None:
            joiner = " "
        return joiner.join(terms)

    def negate_term(self, term: str) -> str:
        """Negate a term using the engine's NOT syntax."""
        not_syntax = self.boolean_ops.get("NOT", " -")
        if not_syntax is None:
            return f"-{term}"
        return f"{not_syntax.strip()}{term}"


class DorkValidator:
    """Validates generated dorks against configuration rules."""

    def __init__(self, config: DorkConfig):
        self.config = config
        rules = config.generation_rules
        self._mutually_exclusive: List[Set[str]] = [
            set(group) for group in rules.get("mutually_exclusive", [])
        ]
        self._max_ops = rules.get("max_operators_per_dork", 4)
        self._max_len = rules.get("max_dork_length", 256)

    def is_valid(self, dork: str, engine_id: str) -> bool:
        """Check if a dork string is valid."""
        if not dork or not dork.strip():
            return False

        if len(dork) > self._max_len:
            return False

        operators_found = self._extract_operators(dork, engine_id)

        if len(operators_found) > self._max_ops:
            return False

        # Check mutually exclusive operators
        for exclusive_group in self._mutually_exclusive:
            found_in_group = [op for op in operators_found if op in exclusive_group]
            if len(set(found_in_group)) > 1:
                return False

        # Check duplicate non-site operators
        op_counts: Dict[str, int] = {}
        for op in operators_found:
            op_counts[op] = op_counts.get(op, 0) + 1
        for op, count in op_counts.items():
            if count > 1 and op != "site":
                return False

        return True

    def _extract_operators(self, dork: str, engine_id: str) -> List[str]:
        """Extract operator names from a dork string."""
        engine_ops = self.config.get_operators(engine_id)
        operators_found = []
        parts = dork.split()
        for part in parts:
            part_lower = part.lower().strip('"').strip("(").strip(")")
            if ":" in part_lower:
                prefix = part_lower.split(":")[0]
                if prefix in engine_ops:
                    operators_found.append(prefix)
        return operators_found


class DorkGenerator:
    """Main dork generation engine.

    Generates valid dork queries by combining operators, keywords, and
    filetypes according to the correct syntax for each search engine.
    """

    def __init__(self, config: Optional[DorkConfig] = None):
        self.config = config or DorkConfig.get_instance()
        self.validator = DorkValidator(self.config)

    def generate(
        self,
        engine_id: str,
        keywords: List[str],
        selected_operators: Optional[List[str]] = None,
        selected_filetypes: Optional[List[str]] = None,
        custom_site: Optional[str] = None,
        use_quotes: bool = False,
        include_exclusions: Optional[List[str]] = None,
        max_results: int = 100,
        shuffle: bool = True,
    ) -> Dict:
        """Generate dork queries.

        Args:
            engine_id: Search engine ID (google, bing, duckduckgo, yahoo).
            keywords: List of target keywords.
            selected_operators: Operator keys to use (e.g., ["intitle", "inurl"]).
            selected_filetypes: File extensions to target (e.g., ["pdf", "php"]).
            custom_site: Optional site: domain restriction.
            use_quotes: Whether to quote keywords for exact match.
            include_exclusions: Keywords to negate with NOT operator.
            max_results: Maximum number of dorks to generate.
            shuffle: Randomize output order.

        Returns:
            Dict with 'dorks', 'total_generated', 'engine', 'warnings'.
        """
        builder = DorkBuilder(self.config, engine_id)
        available_ops = self.config.get_operators(engine_id)
        warnings: List[str] = []

        if not keywords:
            return {
                "dorks": [],
                "total_generated": 0,
                "total_possible": 0,
                "engine": engine_id,
                "engine_name": self.config.get_engine_display_name(engine_id),
                "warnings": ["No keywords provided."],
            }

        # Validate selected operators exist for this engine
        if selected_operators:
            valid_ops = [op for op in selected_operators if op in available_ops]
            invalid_ops = [op for op in selected_operators if op not in available_ops]
            if invalid_ops:
                warnings.append(
                    f"Operators not available for {engine_id}: {', '.join(invalid_ops)}"
                )
            selected_operators = valid_ops
        else:
            selected_operators = []

        # Validate filetypes
        available_filetypes = self.config.get_filetypes(engine_id)
        if selected_filetypes:
            valid_ft = [ft for ft in selected_filetypes if ft in available_filetypes]
            invalid_ft = [ft for ft in selected_filetypes if ft not in available_filetypes]
            if invalid_ft:
                warnings.append(
                    f"Filetypes not available for {engine_id}: {', '.join(invalid_ft)}"
                )
            selected_filetypes = valid_ft
        else:
            selected_filetypes = []

        # Check filetype operator availability
        has_filetype_op = "filetype" in available_ops or "ext" in available_ops
        filetype_op_key = "filetype" if "filetype" in available_ops else "ext"
        if selected_filetypes and not has_filetype_op:
            warnings.append(f"Filetype operator not available for {engine_id}.")
            selected_filetypes = []

        # Build all dork combinations
        all_dorks: List[str] = []

        # Process keywords
        processed_keywords = []
        for kw in keywords:
            kw = kw.strip()
            if not kw:
                continue
            if use_quotes and " " in kw:
                processed_keywords.append(builder.quote_value(kw))
            elif use_quotes:
                processed_keywords.append(builder.quote_value(kw))
            else:
                processed_keywords.append(kw)

        if not processed_keywords:
            return {
                "dorks": [],
                "total_generated": 0,
                "total_possible": 0,
                "engine": engine_id,
                "engine_name": self.config.get_engine_display_name(engine_id),
                "warnings": ["No valid keywords after processing."],
            }

        # Build exclusion suffix
        exclusion_parts = []
        if include_exclusions:
            for exc in include_exclusions:
                exc = exc.strip()
                if exc:
                    exclusion_parts.append(builder.negate_term(exc))
        exclusion_suffix = " ".join(exclusion_parts) if exclusion_parts else ""

        # Site prefix
        site_prefix = ""
        if custom_site and custom_site.strip():
            site_op = available_ops.get("site")
            if site_op:
                site_prefix = builder.build_operator_term("site", custom_site.strip())

        # Generate combinations
        # Strategy: operator + keyword [+ filetype] [+ site] [+ exclusions]
        if selected_operators and selected_filetypes:
            # operator:keyword filetype:ext [site:domain] [-exclusions]
            for op_key, kw, ft in itertools.product(
                selected_operators, processed_keywords, selected_filetypes
            ):
                # Skip filetype operators combined with filetype values
                if op_key in ("filetype", "ext"):
                    continue
                parts = []
                parts.append(builder.build_operator_term(op_key, kw))
                parts.append(builder.build_operator_term(filetype_op_key, ft))
                if site_prefix:
                    parts.append(site_prefix)
                dork = builder.join_terms(parts)
                if exclusion_suffix:
                    dork = f"{dork} {exclusion_suffix}"
                all_dorks.append(dork)

            # Also generate filetype-only dorks: keyword filetype:ext
            for kw, ft in itertools.product(processed_keywords, selected_filetypes):
                parts = [kw, builder.build_operator_term(filetype_op_key, ft)]
                if site_prefix:
                    parts.append(site_prefix)
                dork = builder.join_terms(parts)
                if exclusion_suffix:
                    dork = f"{dork} {exclusion_suffix}"
                all_dorks.append(dork)

        elif selected_operators:
            # operator:keyword [site:domain] [-exclusions]
            for op_key, kw in itertools.product(selected_operators, processed_keywords):
                parts = [builder.build_operator_term(op_key, kw)]
                if site_prefix:
                    parts.append(site_prefix)
                dork = builder.join_terms(parts)
                if exclusion_suffix:
                    dork = f"{dork} {exclusion_suffix}"
                all_dorks.append(dork)

        elif selected_filetypes:
            # keyword filetype:ext [site:domain] [-exclusions]
            for kw, ft in itertools.product(processed_keywords, selected_filetypes):
                parts = [kw, builder.build_operator_term(filetype_op_key, ft)]
                if site_prefix:
                    parts.append(site_prefix)
                dork = builder.join_terms(parts)
                if exclusion_suffix:
                    dork = f"{dork} {exclusion_suffix}"
                all_dorks.append(dork)

        else:
            # Just keywords [site:domain] [-exclusions]
            for kw in processed_keywords:
                parts = [kw]
                if site_prefix:
                    parts.append(site_prefix)
                dork = builder.join_terms(parts)
                if exclusion_suffix:
                    dork = f"{dork} {exclusion_suffix}"
                all_dorks.append(dork)

        # Deduplicate
        seen: Set[str] = set()
        unique_dorks: List[str] = []
        for d in all_dorks:
            d_clean = d.strip()
            if d_clean and d_clean not in seen:
                seen.add(d_clean)
                unique_dorks.append(d_clean)

        total_possible = len(unique_dorks)

        # Validate
        valid_dorks: List[str] = []
        invalid_count = 0
        for d in unique_dorks:
            if self.validator.is_valid(d, engine_id):
                valid_dorks.append(d)
            else:
                invalid_count += 1

        if invalid_count > 0:
            warnings.append(f"Filtered {invalid_count} invalid combinations.")

        # Shuffle and limit
        if shuffle:
            random.shuffle(valid_dorks)

        result_dorks = valid_dorks[:max_results]

        return {
            "dorks": result_dorks,
            "total_generated": len(result_dorks),
            "total_possible": total_possible,
            "engine": engine_id,
            "engine_name": self.config.get_engine_display_name(engine_id),
            "warnings": warnings,
        }
