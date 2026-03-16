"""
DorkForge - Comprehensive Unit Tests
======================================

Tests for:
    1. DorkGenerator engine (core logic, no UI)
    2. OperatorRules (intelligent filtering)
    3. AppState (centralized state management)
    4. DorkGeneratorInput/Result data objects
"""

import unittest
import sys
import os

# Ensure the parent directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dorkforge.engine import (
    DorkGenerator, DorkGeneratorInput, DorkGeneratorResult, OperatorRules,
)
from dorkforge.state import AppState, Action, BoxState, GenerationState, ResultsState
from dorkforge.data import DEFAULT_TEMPLATES, OPERATOR_RULES, DEFAULT_BOXES


# ═════════════════════════════════════════════
# Test DorkGenerator Engine
# ═════════════════════════════════════════════
class TestDorkGeneratorCartesian(unittest.TestCase):
    """Test the DorkGenerator in cartesian product mode."""

    def setUp(self):
        self.gen = DorkGenerator()

    def test_basic_cartesian_product(self):
        """Two boxes with 2 entries each -> 4 combinations."""
        inp = DorkGeneratorInput(
            box_entries={
                "Operators": ["intitle:", "inurl:"],
                "Keywords": ["login", "admin"],
            },
            mode="cartesian",
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 4)
        self.assertIn("intitle:login", result.dorks)
        self.assertIn("intitle:admin", result.dorks)
        self.assertIn("inurl:login", result.dorks)
        self.assertIn("inurl:admin", result.dorks)

    def test_three_box_product(self):
        """Three boxes: 2 x 2 x 2 = 8 combinations."""
        inp = DorkGeneratorInput(
            box_entries={
                "A": ["a1", "a2"],
                "B": ["b1", "b2"],
                "C": ["c1", "c2"],
            },
            mode="cartesian",
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 8)

    def test_all_empty_box_entries(self):
        """All-empty entries should produce zero results."""
        inp = DorkGeneratorInput(
            box_entries={"A": [], "B": []},
            mode="cartesian",
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 0)

    def test_one_empty_box_skipped(self):
        """Empty box is filtered out; non-empty box still produces results."""
        inp = DorkGeneratorInput(
            box_entries={"A": [], "B": ["test"]},
            mode="cartesian",
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        # The empty box is skipped, so only non-empty box participates
        self.assertEqual(len(result.dorks), 1)
        self.assertEqual(result.dorks[0], "test")

    def test_single_entry_boxes(self):
        """Single entry per box -> exactly 1 combination."""
        inp = DorkGeneratorInput(
            box_entries={"A": ["hello"], "B": ["world"]},
            mode="cartesian",
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 1)
        self.assertEqual(result.dorks[0], "helloworld")

    def test_requested_count_limits(self):
        """Requesting fewer than total should limit results."""
        inp = DorkGeneratorInput(
            box_entries={
                "A": [f"a{i}" for i in range(10)],
                "B": [f"b{i}" for i in range(10)],
            },
            mode="cartesian",
            requested_count=5,
            apply_rules=False,
            shuffle=False,
        )
        result = self.gen.generate(inp)
        self.assertLessEqual(len(result.dorks), 5)

    def test_deduplication(self):
        """Duplicate entries should be deduplicated."""
        inp = DorkGeneratorInput(
            box_entries={"A": ["x", "x"], "B": ["y"]},
            mode="cartesian",
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        # "xy" appears twice from product, but dedup reduces to 1
        self.assertEqual(len(result.dorks), 1)

    def test_calculate_total(self):
        """Total calculation should match product of list lengths."""
        inp = DorkGeneratorInput(
            box_entries={
                "A": ["a1", "a2", "a3"],
                "B": ["b1", "b2"],
            },
            mode="cartesian",
        )
        total = self.gen.calculate_total(inp)
        self.assertEqual(total, 6)

    def test_calculate_total_empty(self):
        inp = DorkGeneratorInput(box_entries={}, mode="cartesian")
        self.assertEqual(self.gen.calculate_total(inp), 0)


class TestDorkGeneratorTemplate(unittest.TestCase):
    """Test the DorkGenerator in template mode."""

    def setUp(self):
        self.gen = DorkGenerator()

    def test_basic_template(self):
        """Template with two segments producing correct format."""
        template = {
            "segments": [["Op", "Kw"]],
            "quoted": [],
        }
        inp = DorkGeneratorInput(
            box_entries={
                "Op": ["intitle:"],
                "Kw": ["login", "admin"],
            },
            mode="template",
            template=template,
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 2)
        self.assertIn("intitle:login", result.dorks)
        self.assertIn("intitle:admin", result.dorks)

    def test_template_with_quoted(self):
        """Quoted box values should be wrapped in double quotes."""
        template = {
            "segments": [["Keyword"]],
            "quoted": ["Keyword"],
        }
        inp = DorkGeneratorInput(
            box_entries={"Keyword": ["admin panel", "login"]},
            mode="template",
            template=template,
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 2)
        self.assertIn('"admin panel"', result.dorks)
        self.assertIn('"login"', result.dorks)

    def test_multi_segment_template(self):
        """Template with multiple segments joined by space."""
        template = {
            "segments": [
                ["Op", "Kw"],
                ["FileOp", "File"],
            ],
            "quoted": [],
        }
        inp = DorkGeneratorInput(
            box_entries={
                "Op": ["intitle:"],
                "Kw": ["login"],
                "FileOp": ["filetype:"],
                "File": ["php"],
            },
            mode="template",
            template=template,
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 1)
        self.assertEqual(result.dorks[0], "intitle:login filetype:php")

    def test_template_missing_box(self):
        """Missing box entries should produce zero results."""
        template = {
            "segments": [["Op", "MissingBox"]],
            "quoted": [],
        }
        inp = DorkGeneratorInput(
            box_entries={"Op": ["intitle:"]},
            mode="template",
            template=template,
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 0)

    def test_template_total_calculation(self):
        """Total should account for unique boxes across segments."""
        template = {
            "segments": [["A", "B"], ["A", "C"]],
            "quoted": [],
        }
        inp = DorkGeneratorInput(
            box_entries={
                "A": ["a1", "a2"],
                "B": ["b1", "b2"],
                "C": ["c1", "c2"],
            },
            mode="template",
            template=template,
        )
        # A is shared: 2 * 2 * 2 = 8
        total = self.gen.calculate_total(inp)
        self.assertEqual(total, 8)


class TestDorkGeneratorMixAll(unittest.TestCase):
    """Test the DorkGenerator in mix-all mode."""

    def setUp(self):
        self.gen = DorkGenerator()

    def test_mix_all_combines_templates(self):
        """Mix all should produce dorks from multiple templates."""
        templates = [
            {"segments": [["A"]], "quoted": []},
            {"segments": [["B"]], "quoted": []},
        ]
        inp = DorkGeneratorInput(
            box_entries={"A": ["alpha"], "B": ["beta"]},
            mode="mix_all",
            templates_all=templates,
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 2)
        self.assertIn("alpha", result.dorks)
        self.assertIn("beta", result.dorks)

    def test_mix_all_deduplication(self):
        """Overlapping templates should be deduplicated."""
        templates = [
            {"segments": [["A"]], "quoted": []},
            {"segments": [["A"]], "quoted": []},  # same template
        ]
        inp = DorkGeneratorInput(
            box_entries={"A": ["same_value"]},
            mode="mix_all",
            templates_all=templates,
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 1)

    def test_mix_all_skips_unsatisfied(self):
        """Templates missing required boxes should be skipped."""
        templates = [
            {"segments": [["A"]], "quoted": []},
            {"segments": [["Missing"]], "quoted": []},
        ]
        inp = DorkGeneratorInput(
            box_entries={"A": ["value"]},
            mode="mix_all",
            templates_all=templates,
            requested_count=100,
            apply_rules=False,
        )
        result = self.gen.generate(inp)
        self.assertEqual(len(result.dorks), 1)
        self.assertIn("value", result.dorks)


# ═════════════════════════════════════════════
# Test Operator Rules
# ═════════════════════════════════════════════
class TestOperatorRules(unittest.TestCase):
    """Test intelligent filtering rules."""

    def setUp(self):
        self.rules = OperatorRules()

    def test_mutually_exclusive_filetype_ext(self):
        """filetype: and ext: should not appear together."""
        parts = ["filetype:pdf", "ext:doc"]
        self.assertFalse(self.rules.is_valid_combination(parts))

    def test_valid_single_filetype(self):
        """A single filetype: is valid."""
        parts = ["intitle:login", "filetype:pdf"]
        self.assertTrue(self.rules.is_valid_combination(parts))

    def test_duplicate_operator_invalid(self):
        """Two intitle: operators in one query is invalid."""
        parts = ["intitle:login", "intitle:admin"]
        self.assertFalse(self.rules.is_valid_combination(parts))

    def test_valid_different_operators(self):
        """Different operators should be valid together."""
        parts = ["intitle:login", "filetype:php"]
        self.assertTrue(self.rules.is_valid_combination(parts))

    def test_conflicting_pairs(self):
        """intitle: and inurl: with same query should conflict."""
        parts = ["intitle:login", "inurl:admin"]
        # This is a conflicting pair
        self.assertFalse(self.rules.is_valid_combination(parts))

    def test_filter_dorks(self):
        """filter_dorks should remove invalid combinations."""
        dorks = [
            "intitle:login filetype:php",     # valid
            "filetype:pdf ext:doc",            # invalid (mutually exclusive)
            "intitle:admin",                   # valid
            "intitle:x intitle:y",             # invalid (duplicate)
        ]
        valid, removed = self.rules.filter_dorks(dorks)
        self.assertEqual(removed, 2)
        self.assertEqual(len(valid), 2)
        self.assertIn("intitle:login filetype:php", valid)
        self.assertIn("intitle:admin", valid)

    def test_mutually_exclusive_intitle_allintitle(self):
        """intitle: and allintitle: are mutually exclusive."""
        parts = ["intitle:test", "allintitle:other"]
        self.assertFalse(self.rules.is_valid_combination(parts))

    def test_empty_dork_valid(self):
        """An empty list is technically valid."""
        self.assertTrue(self.rules.is_valid_combination([]))

    def test_no_operator_valid(self):
        """Plain text with no operators is valid."""
        parts = ["login", "admin"]
        self.assertTrue(self.rules.is_valid_combination(parts))


class TestOperatorRulesCustom(unittest.TestCase):
    """Test OperatorRules with custom rules."""

    def test_custom_exclusive(self):
        rules = OperatorRules({
            "mutually_exclusive": [{"foo:", "bar:"}],
            "conflicting_pairs": [],
            "requires_value": [],
            "domain_operators": [],
            "filetype_operators": [],
        })
        self.assertFalse(rules.is_valid_combination(["foo:x", "bar:y"]))
        self.assertTrue(rules.is_valid_combination(["foo:x", "baz:y"]))


# ═════════════════════════════════════════════
# Test Validation
# ═════════════════════════════════════════════
class TestDorkGeneratorValidation(unittest.TestCase):
    """Test input validation."""

    def setUp(self):
        self.gen = DorkGenerator()

    def test_empty_input_invalid(self):
        inp = DorkGeneratorInput(box_entries={}, mode="cartesian")
        ok, msg = self.gen.validate_input(inp)
        self.assertFalse(ok)

    def test_single_box_cartesian_invalid(self):
        """Cartesian mode needs at least 2 boxes."""
        inp = DorkGeneratorInput(
            box_entries={"A": ["test"]},
            mode="cartesian",
        )
        ok, msg = self.gen.validate_input(inp)
        self.assertFalse(ok)

    def test_two_boxes_cartesian_valid(self):
        inp = DorkGeneratorInput(
            box_entries={"A": ["test"], "B": ["other"]},
            mode="cartesian",
        )
        ok, msg = self.gen.validate_input(inp)
        self.assertTrue(ok)

    def test_template_missing_box_invalid(self):
        template = {"segments": [["A", "Missing"]], "quoted": []}
        inp = DorkGeneratorInput(
            box_entries={"A": ["test"]},
            mode="template",
            template=template,
        )
        ok, msg = self.gen.validate_input(inp)
        self.assertFalse(ok)
        self.assertIn("Missing", msg)

    def test_template_no_template_invalid(self):
        inp = DorkGeneratorInput(
            box_entries={"A": ["test"]},
            mode="template",
            template=None,
        )
        ok, msg = self.gen.validate_input(inp)
        self.assertFalse(ok)

    def test_mix_all_no_templates_invalid(self):
        inp = DorkGeneratorInput(
            box_entries={"A": ["test"]},
            mode="mix_all",
            templates_all=[],
        )
        ok, msg = self.gen.validate_input(inp)
        self.assertFalse(ok)

    def test_negative_count_invalid(self):
        inp = DorkGeneratorInput(
            box_entries={"A": ["test"], "B": ["other"]},
            mode="cartesian",
            requested_count=-1,
        )
        ok, msg = self.gen.validate_input(inp)
        self.assertFalse(ok)


# ═════════════════════════════════════════════
# Test Progress Callback
# ═════════════════════════════════════════════
class TestDorkGeneratorProgress(unittest.TestCase):
    """Test that progress callbacks are invoked."""

    def test_progress_callback_called(self):
        gen = DorkGenerator()
        progress_calls = []

        def on_progress(current, total):
            progress_calls.append((current, total))

        inp = DorkGeneratorInput(
            box_entries={
                "A": [f"a{i}" for i in range(100)],
                "B": [f"b{i}" for i in range(100)],
            },
            mode="cartesian",
            requested_count=10000,
            apply_rules=False,
        )
        gen.generate(inp, on_progress)
        # With 10000 items, progress should be called at least once
        self.assertGreater(len(progress_calls), 0)


# ═════════════════════════════════════════════
# Test AppState
# ═════════════════════════════════════════════
class TestAppState(unittest.TestCase):
    """Test centralized state management."""

    def setUp(self):
        self.state = AppState()

    def test_add_box(self):
        box = self.state.dispatch(Action.ADD_BOX, name="Test Box")
        self.assertIsInstance(box, BoxState)
        self.assertEqual(box.name, "Test Box")
        self.assertEqual(len(self.state.boxes), 1)
        self.assertEqual(self.state.boxes[0].uid, box.uid)

    def test_add_multiple_boxes(self):
        self.state.dispatch(Action.ADD_BOX, name="Box 1")
        self.state.dispatch(Action.ADD_BOX, name="Box 2")
        self.state.dispatch(Action.ADD_BOX, name="Box 3")
        self.assertEqual(self.state.box_count, 3)

    def test_remove_box(self):
        box = self.state.dispatch(Action.ADD_BOX, name="ToRemove")
        uid = box.uid
        result = self.state.dispatch(Action.REMOVE_BOX, uid=uid)
        self.assertTrue(result)
        self.assertEqual(len(self.state.boxes), 0)

    def test_remove_nonexistent_box(self):
        result = self.state.dispatch(Action.REMOVE_BOX, uid=999)
        self.assertFalse(result)

    def test_update_entries(self):
        box = self.state.dispatch(Action.ADD_BOX, name="Test")
        self.state.dispatch(
            Action.UPDATE_BOX_ENTRIES,
            uid=box.uid,
            entries=["entry1", "entry2"],
        )
        self.assertEqual(box.entries, ["entry1", "entry2"])
        self.assertEqual(box.entry_count, 2)

    def test_toggle_box(self):
        box = self.state.dispatch(Action.ADD_BOX, name="Test", enabled=True)
        self.assertTrue(box.enabled)
        self.state.dispatch(Action.TOGGLE_BOX, uid=box.uid, enabled=False)
        self.assertFalse(box.enabled)
        self.state.dispatch(Action.TOGGLE_BOX, uid=box.uid)
        self.assertTrue(box.enabled)

    def test_rename_box(self):
        box = self.state.dispatch(Action.ADD_BOX, name="OldName")
        self.state.dispatch(Action.RENAME_BOX, uid=box.uid, name="NewName")
        self.assertEqual(box.name, "NewName")

    def test_move_box(self):
        box1 = self.state.dispatch(Action.ADD_BOX, name="First")
        box2 = self.state.dispatch(Action.ADD_BOX, name="Second")
        self.assertEqual(self.state.boxes[0].uid, box1.uid)
        self.state.dispatch(Action.MOVE_BOX, uid=box1.uid, direction=1)
        self.assertEqual(self.state.boxes[0].uid, box2.uid)
        self.assertEqual(self.state.boxes[1].uid, box1.uid)

    def test_move_box_out_of_bounds(self):
        box = self.state.dispatch(Action.ADD_BOX, name="Only")
        self.state.dispatch(Action.MOVE_BOX, uid=box.uid, direction=-1)
        # Should not crash, box stays in place
        self.assertEqual(len(self.state.boxes), 1)

    def test_active_entries(self):
        box1 = self.state.dispatch(
            Action.ADD_BOX, name="Op", entries=["intitle:"], enabled=True,
        )
        box2 = self.state.dispatch(
            Action.ADD_BOX, name="Kw", entries=["login"], enabled=True,
        )
        box3 = self.state.dispatch(
            Action.ADD_BOX, name="Disabled", entries=["test"], enabled=False,
        )
        entries = self.state.active_entries
        self.assertIn("Op", entries)
        self.assertIn("Kw", entries)
        self.assertNotIn("Disabled", entries)

    def test_active_box_count(self):
        self.state.dispatch(Action.ADD_BOX, name="A", enabled=True)
        self.state.dispatch(Action.ADD_BOX, name="B", enabled=False)
        self.state.dispatch(Action.ADD_BOX, name="C", enabled=True)
        self.assertEqual(self.state.active_box_count, 2)
        self.assertEqual(self.state.box_count, 3)


class TestAppStateTemplates(unittest.TestCase):
    """Test template-related state management."""

    def setUp(self):
        self.state = AppState()

    def test_set_cartesian_template(self):
        self.state.dispatch(Action.SET_TEMPLATE, idx=None)
        self.assertEqual(self.state.generation.mode, "cartesian")
        self.assertIsNone(self.state.generation.active_template_idx)

    def test_set_specific_template(self):
        self.state.dispatch(Action.SET_TEMPLATE, idx=0)
        self.assertEqual(self.state.generation.mode, "template")
        self.assertEqual(self.state.generation.active_template_idx, 0)

    def test_set_mix_all_template(self):
        self.state.dispatch(Action.SET_TEMPLATE, idx=-2)
        self.assertEqual(self.state.generation.mode, "mix_all")
        self.assertEqual(self.state.generation.active_template_idx, -2)

    def test_set_count(self):
        self.state.dispatch(Action.SET_COUNT, count=500)
        self.assertEqual(self.state.generation.requested_count, 500)

    def test_set_count_minimum(self):
        self.state.dispatch(Action.SET_COUNT, count=-10)
        self.assertEqual(self.state.generation.requested_count, 1)

    def test_toggle_rules(self):
        self.assertTrue(self.state.generation.apply_rules)
        self.state.dispatch(Action.TOGGLE_RULES)
        self.assertFalse(self.state.generation.apply_rules)
        self.state.dispatch(Action.TOGGLE_RULES)
        self.assertTrue(self.state.generation.apply_rules)


class TestAppStateResults(unittest.TestCase):
    """Test results state management."""

    def setUp(self):
        self.state = AppState()

    def test_set_results(self):
        dorks = ["dork1", "dork2", "dork3"]
        self.state.dispatch(
            Action.SET_RESULTS,
            dorks=dorks,
            total_possible=10,
            total_generated=5,
            total_filtered=2,
        )
        self.assertEqual(len(self.state.results.all_dorks), 3)
        self.assertEqual(len(self.state.results.filtered_dorks), 3)
        self.assertEqual(self.state.results.total_possible, 10)
        self.assertEqual(self.state.results.total_filtered, 2)

    def test_search_filter(self):
        self.state.dispatch(
            Action.SET_RESULTS,
            dorks=["intitle:login", "inurl:admin", "filetype:pdf"],
        )
        self.state.dispatch(Action.SET_SEARCH, term="intitle")
        self.assertEqual(len(self.state.results.filtered_dorks), 1)
        self.assertEqual(
            self.state.results.filtered_dorks[0], "intitle:login",
        )

    def test_search_case_insensitive(self):
        self.state.dispatch(
            Action.SET_RESULTS,
            dorks=["INTITLE:LOGIN", "inurl:admin"],
        )
        self.state.dispatch(Action.SET_SEARCH, term="intitle")
        self.assertEqual(len(self.state.results.filtered_dorks), 1)

    def test_clear_search_restores_all(self):
        self.state.dispatch(
            Action.SET_RESULTS,
            dorks=["dork1", "dork2", "dork3"],
        )
        self.state.dispatch(Action.SET_SEARCH, term="dork1")
        self.assertEqual(len(self.state.results.filtered_dorks), 1)
        self.state.dispatch(Action.SET_SEARCH, term="")
        self.assertEqual(len(self.state.results.filtered_dorks), 3)

    def test_sort_results(self):
        self.state.dispatch(
            Action.SET_RESULTS,
            dorks=["charlie", "alpha", "bravo"],
        )
        self.state.dispatch(Action.SORT_RESULTS)
        self.assertEqual(
            self.state.results.filtered_dorks,
            ["alpha", "bravo", "charlie"],
        )

    def test_clear_results(self):
        self.state.dispatch(
            Action.SET_RESULTS, dorks=["dork1", "dork2"],
        )
        self.state.dispatch(Action.CLEAR_RESULTS)
        self.assertEqual(len(self.state.results.all_dorks), 0)
        self.assertEqual(len(self.state.results.filtered_dorks), 0)


class TestAppStateSubscription(unittest.TestCase):
    """Test the observer/subscription pattern."""

    def test_subscriber_notified(self):
        state = AppState()
        notifications = []
        state.subscribe("boxes", lambda: notifications.append("boxes"))
        state.dispatch(Action.ADD_BOX, name="Test")
        self.assertIn("boxes", notifications)

    def test_subscriber_not_notified_wrong_channel(self):
        state = AppState()
        notifications = []
        state.subscribe("results", lambda: notifications.append("results"))
        state.dispatch(Action.ADD_BOX, name="Test")
        self.assertNotIn("results", notifications)

    def test_all_channel_always_notified(self):
        state = AppState()
        notifications = []
        state.subscribe("all", lambda: notifications.append("all"))
        state.dispatch(Action.ADD_BOX, name="Test")
        state.dispatch(Action.SET_COUNT, count=50)
        self.assertEqual(len(notifications), 2)

    def test_unsubscribe(self):
        state = AppState()
        notifications = []
        cb = lambda: notifications.append("called")
        state.subscribe("boxes", cb)
        state.dispatch(Action.ADD_BOX, name="Test1")
        self.assertEqual(len(notifications), 1)
        state.unsubscribe("boxes", cb)
        state.dispatch(Action.ADD_BOX, name="Test2")
        self.assertEqual(len(notifications), 1)

    def test_action_log(self):
        state = AppState()
        state.dispatch(Action.ADD_BOX, name="TestBox")
        state.dispatch(Action.SET_COUNT, count=200)
        log = state.action_log
        self.assertEqual(len(log), 2)
        self.assertIn("ADD_BOX", log[0])
        self.assertIn("SET_COUNT", log[1])


class TestAppStateSerialization(unittest.TestCase):
    """Test save/load of state."""

    def test_to_dict_and_from_dict(self):
        state = AppState()
        state.dispatch(Action.ADD_BOX, name="OpBox", entries=["intitle:", "inurl:"])
        state.dispatch(Action.ADD_BOX, name="KwBox", entries=["login", "admin"])
        state.dispatch(Action.SET_COUNT, count=250)

        data = state.to_dict()
        self.assertEqual(len(data["boxes"]), 2)
        self.assertEqual(data["boxes"][0]["name"], "OpBox")
        self.assertEqual(data["generation"]["requested_count"], 250)

        # Restore
        restored = AppState.from_dict(data)
        self.assertEqual(len(restored.boxes), 2)
        self.assertEqual(restored.boxes[0].name, "OpBox")
        self.assertEqual(restored.boxes[0].entries, ["intitle:", "inurl:"])

    def test_empty_state_serialization(self):
        state = AppState()
        data = state.to_dict()
        self.assertEqual(len(data["boxes"]), 0)
        restored = AppState.from_dict(data)
        self.assertEqual(len(restored.boxes), 0)


# ═════════════════════════════════════════════
# Test BoxState Dataclass
# ═════════════════════════════════════════════
class TestBoxState(unittest.TestCase):
    def test_is_active_enabled_with_entries(self):
        box = BoxState(uid=1, name="Test", entries=["a", "b"], enabled=True)
        self.assertTrue(box.is_active)

    def test_is_active_disabled(self):
        box = BoxState(uid=1, name="Test", entries=["a"], enabled=False)
        self.assertFalse(box.is_active)

    def test_is_active_empty_entries(self):
        box = BoxState(uid=1, name="Test", entries=[], enabled=True)
        self.assertFalse(box.is_active)

    def test_entry_count(self):
        box = BoxState(uid=1, name="Test", entries=["a", "b", "c"])
        self.assertEqual(box.entry_count, 3)


# ═════════════════════════════════════════════
# Test with Default Data
# ═════════════════════════════════════════════
class TestWithDefaultData(unittest.TestCase):
    """Integration tests using the actual default templates and data."""

    def test_default_templates_valid(self):
        """All default templates should have valid structure."""
        for tmpl in DEFAULT_TEMPLATES:
            self.assertIn("segments", tmpl)
            self.assertIn("quoted", tmpl)
            self.assertIsInstance(tmpl["segments"], list)
            for seg in tmpl["segments"]:
                self.assertIsInstance(seg, list)
                for box_name in seg:
                    self.assertIsInstance(box_name, str)

    def test_default_boxes_generate(self):
        """Using default boxes with cartesian mode should work."""
        gen = DorkGenerator()
        entries = {
            box["name"]: box["content"]
            for box in DEFAULT_BOXES
        }
        inp = DorkGeneratorInput(
            box_entries=entries,
            mode="cartesian",
            requested_count=10,
            apply_rules=False,
        )
        result = gen.generate(inp)
        self.assertGreater(len(result.dorks), 0)
        self.assertLessEqual(len(result.dorks), 10)

    def test_all_templates_with_defaults(self):
        """Each template should generate at least 1 result with defaults."""
        gen = DorkGenerator()
        entries = {
            box["name"]: box["content"]
            for box in DEFAULT_BOXES
        }
        for tmpl in DEFAULT_TEMPLATES:
            inp = DorkGeneratorInput(
                box_entries=entries,
                mode="template",
                template=tmpl,
                requested_count=5,
                apply_rules=False,
            )
            result = gen.generate(inp)
            self.assertGreater(
                len(result.dorks), 0,
                f"Template '{tmpl.get('name', tmpl.get('short'))}' produced no results",
            )

    def test_mix_all_with_defaults(self):
        """Mix all should work with default data."""
        gen = DorkGenerator()
        entries = {
            box["name"]: box["content"]
            for box in DEFAULT_BOXES
        }
        inp = DorkGeneratorInput(
            box_entries=entries,
            mode="mix_all",
            templates_all=DEFAULT_TEMPLATES,
            requested_count=20,
            apply_rules=False,
        )
        result = gen.generate(inp)
        self.assertGreater(len(result.dorks), 0)

    def test_rules_filtering_with_defaults(self):
        """Rules filtering should work without crashing on default data."""
        gen = DorkGenerator()
        entries = {
            box["name"]: box["content"]
            for box in DEFAULT_BOXES
        }
        inp = DorkGeneratorInput(
            box_entries=entries,
            mode="cartesian",
            requested_count=100,
            apply_rules=True,
        )
        result = gen.generate(inp)
        # Should have some results (some may be filtered)
        self.assertIsInstance(result.dorks, list)
        self.assertIsInstance(result.total_filtered, int)


# ═════════════════════════════════════════════
# Test DorkGeneratorResult
# ═════════════════════════════════════════════
class TestDorkGeneratorResult(unittest.TestCase):
    def test_result_fields(self):
        result = DorkGeneratorResult(
            dorks=["a", "b"],
            total_possible=10,
            total_generated=5,
            total_filtered=3,
            warnings=["test warning"],
        )
        self.assertEqual(len(result.dorks), 2)
        self.assertEqual(result.total_possible, 10)
        self.assertEqual(result.total_generated, 5)
        self.assertEqual(result.total_filtered, 3)
        self.assertEqual(result.warnings, ["test warning"])

    def test_result_defaults(self):
        result = DorkGeneratorResult(dorks=[])
        self.assertEqual(result.total_possible, 0)
        self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
