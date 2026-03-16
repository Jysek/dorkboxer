"""
DorkForge - Core Query Generation Engine
==========================================

The DorkGenerator is a pure-logic class with ZERO UI dependencies.
It accepts structured input data and returns generated dork queries.

Design principles:
    - No tkinter imports, no GUI references
    - Fully testable with unit tests
    - Reusable (could power a CLI, web API, etc.)
    - Implements intelligent rule-based combination with operator precedence
    - Handles deduplication, filtering, and smart grouping
"""

import itertools
import random
import math
from typing import List, Dict, Set, Tuple, Optional, Callable, Any


class DorkGeneratorInput:
    """Immutable data object describing what to generate.

    This is the 'contract' between the UI and the engine.
    The UI collects user choices and packs them here.
    """

    __slots__ = (
        "box_entries", "template", "templates_all", "mode",
        "requested_count", "apply_rules", "shuffle",
    )

    def __init__(
        self,
        box_entries: Dict[str, List[str]],
        mode: str = "cartesian",
        template: Optional[Dict] = None,
        templates_all: Optional[List[Dict]] = None,
        requested_count: int = 100,
        apply_rules: bool = True,
        shuffle: bool = True,
    ):
        """
        Args:
            box_entries: Mapping of box_name -> list of entry strings.
            mode: One of 'cartesian', 'template', 'mix_all'.
            template: A single template dict (for mode='template').
            templates_all: All templates (for mode='mix_all').
            requested_count: How many dorks to produce.
            apply_rules: Whether to apply intelligent filtering rules.
            shuffle: Whether to shuffle the final output.
        """
        self.box_entries = box_entries
        self.mode = mode
        self.template = template
        self.templates_all = templates_all or []
        self.requested_count = requested_count
        self.apply_rules = apply_rules
        self.shuffle = shuffle


class DorkGeneratorResult:
    """Immutable result object returned by the engine."""

    __slots__ = ("dorks", "total_possible", "total_generated",
                 "total_filtered", "warnings")

    def __init__(
        self,
        dorks: List[str],
        total_possible: int = 0,
        total_generated: int = 0,
        total_filtered: int = 0,
        warnings: Optional[List[str]] = None,
    ):
        self.dorks = dorks
        self.total_possible = total_possible
        self.total_generated = total_generated
        self.total_filtered = total_filtered
        self.warnings = warnings or []


class OperatorRules:
    """Encapsulates the rules for intelligent combination filtering.

    Knows which operators conflict, which are mutually exclusive,
    and can validate/filter generated dork strings.
    """

    def __init__(self, rules: Optional[Dict] = None):
        if rules is None:
            from dorkforge.data import OPERATOR_RULES
            rules = OPERATOR_RULES

        self._mutually_exclusive: List[Set[str]] = [
            set(group) for group in rules.get("mutually_exclusive", [])
        ]
        self._conflicting_pairs: List[Tuple[str, str]] = [
            tuple(pair) for pair in rules.get("conflicting_pairs", [])
        ]
        self._requires_value: Set[str] = set(rules.get("requires_value", []))
        self._domain_operators: Set[str] = set(rules.get("domain_operators", []))
        self._filetype_operators: Set[str] = set(rules.get("filetype_operators", []))

    def is_valid_combination(self, dork_parts: List[str]) -> bool:
        """Check if a list of dork segments forms a valid combination.

        Args:
            dork_parts: The individual segments of a dork query.

        Returns:
            True if the combination is valid per the rules.
        """
        joined = " ".join(dork_parts).lower()
        operators_found = []

        for part in dork_parts:
            part_lower = part.lower().strip()
            # Extract the operator prefix (everything up to and including ':')
            if ":" in part_lower:
                op = part_lower[:part_lower.index(":") + 1]
                operators_found.append(op)

        # Check mutually exclusive
        for exclusive_group in self._mutually_exclusive:
            found_in_group = [op for op in operators_found if op in exclusive_group]
            if len(set(found_in_group)) > 1:
                return False

        # Check conflicting pairs
        for op_a, op_b in self._conflicting_pairs:
            if op_a in operators_found and op_b in operators_found:
                return False

        # Check for duplicate operators (e.g., two intitle: in one query)
        op_counts = {}
        for op in operators_found:
            op_counts[op] = op_counts.get(op, 0) + 1
        for op, count in op_counts.items():
            if count > 1 and op not in self._domain_operators:
                return False

        return True

    def filter_dorks(self, dorks: List[str]) -> Tuple[List[str], int]:
        """Filter a list of dork strings, removing invalid ones.

        Returns:
            Tuple of (filtered_dorks, count_removed).
        """
        valid = []
        removed = 0
        for dork in dorks:
            parts = dork.split()
            if self.is_valid_combination(parts):
                valid.append(dork)
            else:
                removed += 1
        return valid, removed


class DorkGenerator:
    """The main query generation engine.

    Usage:
        generator = DorkGenerator()
        input_data = DorkGeneratorInput(
            box_entries={"Search Operator": ["intitle:", "inurl:"], "Keyword": ["login", "admin"]},
            mode="cartesian",
            requested_count=50,
        )
        result = generator.generate(input_data)
        print(result.dorks)
        print(f"Generated {result.total_generated} dorks")
    """

    def __init__(self, rules: Optional[OperatorRules] = None):
        self.rules = rules or OperatorRules()

    # ── Public API ──

    def generate(
        self,
        input_data: DorkGeneratorInput,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> DorkGeneratorResult:
        """Generate dork queries based on the input specification.

        Args:
            input_data: A DorkGeneratorInput with all generation parameters.
            progress_callback: Optional (current, total) progress reporter.

        Returns:
            A DorkGeneratorResult with the generated queries and metadata.
        """
        mode = input_data.mode
        warnings = []

        if mode == "template":
            dorks, total_possible = self._generate_template(
                input_data, progress_callback
            )
        elif mode == "mix_all":
            dorks, total_possible = self._generate_mix_all(
                input_data, progress_callback
            )
        else:
            dorks, total_possible = self._generate_cartesian(
                input_data, progress_callback
            )

        total_generated = len(dorks)

        # Deduplicate
        dorks = self._deduplicate(dorks)

        # Apply intelligent rules filtering
        total_filtered = 0
        if input_data.apply_rules:
            dorks, removed = self.rules.filter_dorks(dorks)
            total_filtered = removed
            if removed > 0:
                warnings.append(
                    f"Filtered {removed} invalid/redundant combinations "
                    f"(mutually exclusive operators, conflicts, etc.)"
                )

        # Trim to requested count
        if len(dorks) > input_data.requested_count:
            if input_data.shuffle:
                random.shuffle(dorks)
            dorks = dorks[:input_data.requested_count]
        elif input_data.shuffle:
            random.shuffle(dorks)

        return DorkGeneratorResult(
            dorks=dorks,
            total_possible=total_possible,
            total_generated=total_generated,
            total_filtered=total_filtered,
            warnings=warnings,
        )

    def calculate_total(
        self,
        input_data: DorkGeneratorInput,
    ) -> int:
        """Calculate the total possible combinations without generating."""
        mode = input_data.mode
        if mode == "template":
            if input_data.template is None:
                return 0
            return self._calc_template_total(
                input_data.template, input_data.box_entries
            )
        elif mode == "mix_all":
            total = 0
            for tmpl in input_data.templates_all:
                total += self._calc_template_total(tmpl, input_data.box_entries)
            return total
        else:
            entry_lists = [
                v for v in input_data.box_entries.values() if v
            ]
            return self._calc_cartesian_total(entry_lists)

    def validate_input(
        self, input_data: DorkGeneratorInput
    ) -> Tuple[bool, str]:
        """Validate input before generation.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not input_data.box_entries:
            return False, "No box entries provided."

        non_empty = {k: v for k, v in input_data.box_entries.items() if v}
        if len(non_empty) < 2 and input_data.mode == "cartesian":
            return False, "At least 2 boxes with entries are required for cartesian mode."

        if input_data.mode == "template":
            if input_data.template is None:
                return False, "No template selected."
            missing = self._get_missing_boxes(
                input_data.template, input_data.box_entries
            )
            if missing:
                return False, (
                    f"Template requires these boxes with entries: "
                    f"{', '.join(sorted(missing))}"
                )

        if input_data.mode == "mix_all":
            if not input_data.templates_all:
                return False, "No templates available for mix-all mode."
            usable = self._get_usable_templates(
                input_data.templates_all, input_data.box_entries
            )
            if not usable:
                return False, (
                    "None of the templates can be satisfied with current boxes."
                )

        if input_data.requested_count <= 0:
            return False, "Requested count must be positive."

        return True, ""

    # ── Private: Cartesian Mode ──

    @staticmethod
    def _calc_cartesian_total(entry_lists: List[List[str]]) -> int:
        if not entry_lists:
            return 0
        total = 1
        for el in entry_lists:
            if not el:
                return 0
            total *= len(el)
        return total

    def _generate_cartesian(
        self,
        input_data: DorkGeneratorInput,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[str], int]:
        entry_lists = [v for v in input_data.box_entries.values() if v]
        total = self._calc_cartesian_total(entry_lists)
        if total == 0:
            return [], 0

        requested = input_data.requested_count
        if requested >= total or total <= 500_000:
            results = []
            for i, combo in enumerate(itertools.product(*entry_lists)):
                dork = "".join(combo)
                results.append(dork)
                if progress_callback and (i + 1) % 5000 == 0:
                    progress_callback(i + 1, total)
            if requested < total:
                random.shuffle(results)
                results = results[:requested]
            return results, total
        else:
            return self._random_sample(entry_lists, requested, progress_callback), total

    @staticmethod
    def _random_sample(
        entry_lists: List[List[str]],
        count: int,
        progress_callback: Optional[Callable] = None,
    ) -> List[str]:
        results_set = set()
        attempts = 0
        max_attempts = count * 10
        while len(results_set) < count and attempts < max_attempts:
            combo = tuple(random.choice(el) for el in entry_lists)
            dork = "".join(combo)
            if dork not in results_set:
                results_set.add(dork)
                if progress_callback and len(results_set) % 2000 == 0:
                    progress_callback(len(results_set), count)
            attempts += 1
        return list(results_set)

    # ── Private: Template Mode ──

    @staticmethod
    def _calc_template_total(
        template: Dict, box_entries: Dict[str, List[str]]
    ) -> int:
        seen = set()
        total = 1
        for seg in template.get("segments", []):
            for box_name in seg:
                if box_name not in seen:
                    entries = box_entries.get(box_name, [])
                    if not entries:
                        return 0
                    total *= len(entries)
                    seen.add(box_name)
        return total if seen else 0

    def _generate_template(
        self,
        input_data: DorkGeneratorInput,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[str], int]:
        template = input_data.template
        if template is None:
            return [], 0
        return self._generate_from_template(
            template, input_data.box_entries,
            input_data.requested_count, progress_callback
        )

    def _generate_from_template(
        self,
        template: Dict,
        box_entries: Dict[str, List[str]],
        requested: int,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[str], int]:
        quoted_boxes = set(template.get("quoted", []))
        seen = {}
        ordered_names = []
        entry_lists = []

        for seg in template["segments"]:
            for box_name in seg:
                if box_name not in seen:
                    entries = box_entries.get(box_name, [])
                    if not entries:
                        return [], 0
                    seen[box_name] = len(ordered_names)
                    ordered_names.append(box_name)
                    entry_lists.append(entries)

        if not entry_lists:
            return [], 0

        total = self._calc_cartesian_total(entry_lists)

        if requested >= total or total <= 500_000:
            results = []
            for i, combo in enumerate(itertools.product(*entry_lists)):
                chosen = {ordered_names[j]: combo[j] for j in range(len(combo))}
                parts = []
                for seg in template["segments"]:
                    seg_str = ""
                    for box_name in seg:
                        val = chosen[box_name]
                        if box_name in quoted_boxes:
                            val = f'"{val}"'
                        seg_str += val
                    parts.append(seg_str)
                results.append(" ".join(parts))
                if progress_callback and (i + 1) % 5000 == 0:
                    progress_callback(i + 1, total)
            if requested < total:
                random.shuffle(results)
                results = results[:requested]
            return results, total
        else:
            return self._random_sample_template(
                template, ordered_names, entry_lists, quoted_boxes,
                requested, progress_callback
            ), total

    @staticmethod
    def _random_sample_template(
        template, ordered_names, entry_lists, quoted_boxes,
        count, progress_callback=None,
    ) -> List[str]:
        results_set = set()
        attempts = 0
        max_attempts = count * 10
        while len(results_set) < count and attempts < max_attempts:
            combo = tuple(random.choice(el) for el in entry_lists)
            chosen = {ordered_names[j]: combo[j] for j in range(len(combo))}
            parts = []
            for seg in template["segments"]:
                seg_str = ""
                for box_name in seg:
                    val = chosen[box_name]
                    if box_name in quoted_boxes:
                        val = f'"{val}"'
                    seg_str += val
                parts.append(seg_str)
            dork = " ".join(parts)
            if dork not in results_set:
                results_set.add(dork)
                if progress_callback and len(results_set) % 2000 == 0:
                    progress_callback(len(results_set), count)
            attempts += 1
        return list(results_set)

    # ── Private: Mix All Mode ──

    def _generate_mix_all(
        self,
        input_data: DorkGeneratorInput,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[str], int]:
        usable = self._get_usable_templates(
            input_data.templates_all, input_data.box_entries
        )
        if not usable:
            return [], 0

        total = sum(
            self._calc_template_total(t, input_data.box_entries)
            for t in usable
        )
        requested = input_data.requested_count

        if requested >= total:
            # Generate everything from all templates
            all_dorks = []
            generated = 0
            for tmpl in usable:
                dorks, _ = self._generate_from_template(
                    tmpl, input_data.box_entries, total, None
                )
                all_dorks.extend(dorks)
                generated += len(dorks)
                if progress_callback:
                    progress_callback(generated, total)
            return all_dorks, total
        else:
            # Proportional allocation
            grand_total = sum(
                self._calc_template_total(t, input_data.box_entries)
                for t in usable
            )
            all_dorks = []
            remaining = requested
            for i, tmpl in enumerate(usable):
                t = self._calc_template_total(tmpl, input_data.box_entries)
                if i == len(usable) - 1:
                    alloc = remaining
                else:
                    alloc = max(1, round(requested * t / grand_total))
                    alloc = min(alloc, remaining)
                dorks, _ = self._generate_from_template(
                    tmpl, input_data.box_entries, alloc, progress_callback
                )
                all_dorks.extend(dorks)
                remaining -= alloc
            return all_dorks, total

    # ── Private: Helpers ──

    @staticmethod
    def _deduplicate(dorks: List[str]) -> List[str]:
        seen = set()
        result = []
        for d in dorks:
            if d not in seen:
                seen.add(d)
                result.append(d)
        return result

    @staticmethod
    def _get_missing_boxes(
        template: Dict, box_entries: Dict[str, List[str]]
    ) -> List[str]:
        missing = []
        for seg in template.get("segments", []):
            for box_name in seg:
                entries = box_entries.get(box_name, [])
                if not entries and box_name not in missing:
                    missing.append(box_name)
        return missing

    @staticmethod
    def _get_usable_templates(
        templates: List[Dict], box_entries: Dict[str, List[str]]
    ) -> List[Dict]:
        usable = []
        for tmpl in templates:
            ok = True
            for seg in tmpl.get("segments", []):
                for bn in seg:
                    if not box_entries.get(bn):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                usable.append(tmpl)
        return usable
