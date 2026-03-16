"""
DorkForge - Centralized State Management
==========================================

Implements a predictable, single-source-of-truth state management pattern.

How it works:
    1. AppState holds ALL application state in one place.
    2. Components dispatch 'actions' (method calls on AppState).
    3. AppState updates its internal state.
    4. Subscribed listeners are notified and re-render.

This eliminates bugs where different UI parts get out of sync,
and makes debugging trivial - inspect AppState to see everything.
"""

from typing import List, Dict, Optional, Callable, Any, Set
from dataclasses import dataclass, field
import copy


# ─────────────────────────────────────────────
# State Data Classes
# ─────────────────────────────────────────────
@dataclass
class BoxState:
    """State of a single operator box."""
    uid: int
    name: str
    entries: List[str] = field(default_factory=list)
    enabled: bool = True

    @property
    def is_active(self) -> bool:
        return self.enabled and len(self.entries) > 0

    @property
    def entry_count(self) -> int:
        return len(self.entries)


@dataclass
class GenerationState:
    """State of the generation configuration."""
    mode: str = "cartesian"                # cartesian | template | mix_all
    active_template_idx: Optional[int] = None  # None=cartesian, -2=mix_all, 0+=template
    requested_count: int = 100
    apply_rules: bool = True
    shuffle: bool = True


@dataclass
class ResultsState:
    """State of the generated results."""
    all_dorks: List[str] = field(default_factory=list)
    filtered_dorks: List[str] = field(default_factory=list)
    search_term: str = ""
    total_possible: int = 0
    total_generated: int = 0
    total_filtered: int = 0
    warnings: List[str] = field(default_factory=list)
    is_generating: bool = False
    progress: float = 0.0


# ─────────────────────────────────────────────
# Action Types (for debugging/logging)
# ─────────────────────────────────────────────
class Action:
    """Action constants for state changes."""
    ADD_BOX = "ADD_BOX"
    REMOVE_BOX = "REMOVE_BOX"
    UPDATE_BOX_ENTRIES = "UPDATE_BOX_ENTRIES"
    TOGGLE_BOX = "TOGGLE_BOX"
    RENAME_BOX = "RENAME_BOX"
    MOVE_BOX = "MOVE_BOX"
    SET_TEMPLATE = "SET_TEMPLATE"
    SET_COUNT = "SET_COUNT"
    SET_SEARCH = "SET_SEARCH"
    SET_RESULTS = "SET_RESULTS"
    CLEAR_RESULTS = "CLEAR_RESULTS"
    SORT_RESULTS = "SORT_RESULTS"
    SHUFFLE_RESULTS = "SHUFFLE_RESULTS"
    SET_GENERATING = "SET_GENERATING"
    SET_PROGRESS = "SET_PROGRESS"
    TOGGLE_RULES = "TOGGLE_RULES"
    LOAD_SESSION = "LOAD_SESSION"


# ─────────────────────────────────────────────
# Central App State
# ─────────────────────────────────────────────
class AppState:
    """Single source of truth for the entire application state.

    Usage:
        state = AppState()
        state.subscribe("boxes", my_callback)
        state.dispatch(Action.ADD_BOX, name="New Box")
        # -> my_callback is called with the updated boxes list
    """

    def __init__(self):
        self._boxes: List[BoxState] = []
        self._generation: GenerationState = GenerationState()
        self._results: ResultsState = ResultsState()
        self._next_uid: int = 0
        self._listeners: Dict[str, List[Callable]] = {
            "boxes": [],
            "generation": [],
            "results": [],
            "stats": [],
            "all": [],
        }
        self._action_log: List[str] = []

    # ── Properties (read-only access) ──

    @property
    def boxes(self) -> List[BoxState]:
        return self._boxes

    @property
    def generation(self) -> GenerationState:
        return self._generation

    @property
    def results(self) -> ResultsState:
        return self._results

    @property
    def active_boxes(self) -> List[BoxState]:
        return [b for b in self._boxes if b.enabled]

    @property
    def active_entries(self) -> Dict[str, List[str]]:
        """Get entries from active boxes as a dict (for the engine)."""
        return {
            b.name: b.entries
            for b in self._boxes
            if b.is_active
        }

    @property
    def box_count(self) -> int:
        return len(self._boxes)

    @property
    def active_box_count(self) -> int:
        return len(self.active_boxes)

    @property
    def action_log(self) -> List[str]:
        return list(self._action_log)

    # ── Subscription ──

    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to state changes on a channel.

        Channels: 'boxes', 'generation', 'results', 'stats', 'all'
        """
        if channel in self._listeners:
            self._listeners[channel].append(callback)

    def unsubscribe(self, channel: str, callback: Callable):
        """Remove a subscription."""
        if channel in self._listeners:
            self._listeners[channel] = [
                cb for cb in self._listeners[channel] if cb is not callback
            ]

    # ── Dispatch (all state mutations go through here) ──

    def dispatch(self, action: str, **kwargs) -> Any:
        """Dispatch an action to mutate state.

        All state changes MUST go through dispatch() to ensure
        listeners are notified consistently.
        """
        self._action_log.append(f"{action}: {kwargs}")

        result = None
        channels_changed = set()

        if action == Action.ADD_BOX:
            result = self._do_add_box(**kwargs)
            channels_changed = {"boxes", "stats"}

        elif action == Action.REMOVE_BOX:
            result = self._do_remove_box(**kwargs)
            channels_changed = {"boxes", "stats"}

        elif action == Action.UPDATE_BOX_ENTRIES:
            self._do_update_entries(**kwargs)
            channels_changed = {"boxes", "stats"}

        elif action == Action.TOGGLE_BOX:
            self._do_toggle_box(**kwargs)
            channels_changed = {"boxes", "stats"}

        elif action == Action.RENAME_BOX:
            self._do_rename_box(**kwargs)
            channels_changed = {"boxes"}

        elif action == Action.MOVE_BOX:
            self._do_move_box(**kwargs)
            channels_changed = {"boxes"}

        elif action == Action.SET_TEMPLATE:
            self._do_set_template(**kwargs)
            channels_changed = {"generation", "stats"}

        elif action == Action.SET_COUNT:
            self._do_set_count(**kwargs)
            channels_changed = {"generation"}

        elif action == Action.SET_SEARCH:
            self._do_set_search(**kwargs)
            channels_changed = {"results"}

        elif action == Action.SET_RESULTS:
            self._do_set_results(**kwargs)
            channels_changed = {"results", "stats"}

        elif action == Action.CLEAR_RESULTS:
            self._do_clear_results()
            channels_changed = {"results", "stats"}

        elif action == Action.SORT_RESULTS:
            self._do_sort_results()
            channels_changed = {"results"}

        elif action == Action.SHUFFLE_RESULTS:
            self._do_shuffle_results()
            channels_changed = {"results"}

        elif action == Action.SET_GENERATING:
            self._results.is_generating = kwargs.get("value", False)
            channels_changed = {"results"}

        elif action == Action.SET_PROGRESS:
            self._results.progress = kwargs.get("value", 0.0)
            channels_changed = {"results"}

        elif action == Action.TOGGLE_RULES:
            self._generation.apply_rules = not self._generation.apply_rules
            channels_changed = {"generation"}

        elif action == Action.LOAD_SESSION:
            self._do_load_session(**kwargs)
            channels_changed = {"boxes", "generation", "results", "stats"}

        # Notify listeners
        self._notify(channels_changed)

        return result

    # ── Private: Action Handlers ──

    def _do_add_box(self, name: str = "", entries: Optional[List[str]] = None,
                    enabled: bool = True) -> BoxState:
        self._next_uid += 1
        box = BoxState(
            uid=self._next_uid,
            name=name or f"Box {self._next_uid}",
            entries=entries or [],
            enabled=enabled,
        )
        self._boxes.append(box)
        return box

    def _do_remove_box(self, uid: int = 0) -> bool:
        for i, box in enumerate(self._boxes):
            if box.uid == uid:
                self._boxes.pop(i)
                return True
        return False

    def _do_update_entries(self, uid: int = 0, entries: Optional[List[str]] = None):
        for box in self._boxes:
            if box.uid == uid:
                box.entries = entries or []
                break

    def _do_toggle_box(self, uid: int = 0, enabled: Optional[bool] = None):
        for box in self._boxes:
            if box.uid == uid:
                if enabled is not None:
                    box.enabled = enabled
                else:
                    box.enabled = not box.enabled
                break

    def _do_rename_box(self, uid: int = 0, name: str = ""):
        for box in self._boxes:
            if box.uid == uid:
                box.name = name
                break

    def _do_move_box(self, uid: int = 0, direction: int = 0):
        for i, box in enumerate(self._boxes):
            if box.uid == uid:
                new_idx = i + direction
                if 0 <= new_idx < len(self._boxes):
                    self._boxes[i], self._boxes[new_idx] = (
                        self._boxes[new_idx], self._boxes[i]
                    )
                break

    def _do_set_template(self, idx: Optional[int] = None):
        from dorkforge.data import MIX_ALL_TEMPLATE_IDX
        if idx == MIX_ALL_TEMPLATE_IDX:
            self._generation.mode = "mix_all"
            self._generation.active_template_idx = MIX_ALL_TEMPLATE_IDX
        elif idx is not None and idx >= 0:
            self._generation.mode = "template"
            self._generation.active_template_idx = idx
        else:
            self._generation.mode = "cartesian"
            self._generation.active_template_idx = None

    def _do_set_count(self, count: int = 100):
        self._generation.requested_count = max(1, count)

    def _do_set_search(self, term: str = ""):
        self._results.search_term = term.strip().lower()
        if not self._results.search_term:
            self._results.filtered_dorks = list(self._results.all_dorks)
        else:
            self._results.filtered_dorks = [
                d for d in self._results.all_dorks
                if self._results.search_term in d.lower()
            ]

    def _do_set_results(
        self,
        dorks: Optional[List[str]] = None,
        total_possible: int = 0,
        total_generated: int = 0,
        total_filtered: int = 0,
        warnings: Optional[List[str]] = None,
    ):
        self._results.all_dorks = dorks or []
        self._results.filtered_dorks = list(self._results.all_dorks)
        self._results.total_possible = total_possible
        self._results.total_generated = total_generated
        self._results.total_filtered = total_filtered
        self._results.warnings = warnings or []
        self._results.search_term = ""
        self._results.is_generating = False
        self._results.progress = 100.0

    def _do_clear_results(self):
        self._results = ResultsState()

    def _do_sort_results(self):
        self._results.filtered_dorks.sort()

    def _do_shuffle_results(self):
        import random
        random.shuffle(self._results.filtered_dorks)

    def _do_load_session(self, boxes=None, generation=None):
        if boxes:
            self._boxes = []
            self._next_uid = 0
            for b_data in boxes:
                self._do_add_box(
                    name=b_data.get("name", ""),
                    entries=b_data.get("entries", []),
                    enabled=b_data.get("enabled", True),
                )
        if generation:
            self._generation = GenerationState(**generation)

    # ── Private: Notification ──

    def _notify(self, channels: Set[str]):
        """Notify all listeners on the affected channels."""
        notified = set()
        for channel in channels:
            for cb in self._listeners.get(channel, []):
                if id(cb) not in notified:
                    notified.add(id(cb))
                    try:
                        cb()
                    except Exception:
                        pass  # Don't let a bad listener break the state
        # Always notify 'all' listeners
        for cb in self._listeners.get("all", []):
            if id(cb) not in notified:
                notified.add(id(cb))
                try:
                    cb()
                except Exception:
                    pass

    # ── Serialization (for save/load sessions) ──

    def to_dict(self) -> Dict:
        """Serialize state for saving."""
        return {
            "boxes": [
                {
                    "name": b.name,
                    "entries": b.entries,
                    "enabled": b.enabled,
                }
                for b in self._boxes
            ],
            "generation": {
                "mode": self._generation.mode,
                "active_template_idx": self._generation.active_template_idx,
                "requested_count": self._generation.requested_count,
                "apply_rules": self._generation.apply_rules,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AppState":
        """Deserialize state from saved data."""
        state = cls()
        state.dispatch(
            Action.LOAD_SESSION,
            boxes=data.get("boxes", []),
            generation=data.get("generation"),
        )
        return state
