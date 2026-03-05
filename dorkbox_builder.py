"""
DorkBox Builder - Google Dork Combination Generator
A Python/Tkinter desktop GUI tool for creating Google Dorks
by combining structured operator fragments from multiple input boxes.

Run: python dorkbox_builder.py
No external dependencies required - uses only Python standard library.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import random
import itertools
import json
import csv
import io
import math
import threading
from collections import OrderedDict

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
APP_TITLE = "DorkBox Builder"
APP_VERSION = "1.0.0"
MIN_BOXES = 2
MAX_BOXES = 20
HUGE_REQUEST_THRESHOLD = 100_000
DEFAULT_BOX_NAMES = [
    "Search Operator", "Keyword", "Page Type", "Page Parameters"
]

# ─────────────────────────────────────────────
# Default Combination Templates
# ─────────────────────────────────────────────
# Each template defines how boxes are combined into dork strings.
# Format uses box names in parentheses. "+" means concatenate (space-joined),
# and each top-level group separated by space is a segment.
# The template entries are tuples of segments; each segment is a list of box
# references that are joined with no extra space (operator+value style).
#
# Template structure:
#   name: display name
#   description: tooltip text
#   pattern: list of segment-groups, where each segment-group is a list of
#            box-name references. Adjacent refs in a group are joined directly
#            (e.g. operator:keyword), groups are space-separated.
#   quoted: list of box names whose values should be wrapped in quotes

DEFAULT_TEMPLATES = [
    {
        "name": "Template 1: Operator+Keyword  Operator+Param",
        "short": "T1: Op+Kw  Op+Param",
        "description": "(search operator)+(keyword)  (search operator)+(page parameter)\n"
                       "Example: intitle:login  intitle:admin.php",
        "segments": [
            ["Search Operator", "Keyword"],
            ["Search Operator", "Page Parameters"],
        ],
        "quoted": [],
    },
    {
        "name": "Template 2: Site+Keyword  Filetype+PageType",
        "short": "T2: Site+Kw  File+Page",
        "description": "(site)+(keyword)  (filetype)+(page type)\n"
                       "Example: site:example.com login  filetype:php admin",
        "segments": [
            ["Search Operator", "Keyword"],
            ["Page Type", "Page Parameters"],
        ],
        "quoted": [],
    },
    {
        "name": 'Template 3: \"Keyword\"  \"PageParam\"',
        "short": 'T3: \"Kw\"  \"Param\"',
        "description": '\"(keyword)\"  \"(page parameter)\"\n'
                       'Example: \"login\"  \"admin.php\"',
        "segments": [
            ["Keyword"],
            ["Page Parameters"],
        ],
        "quoted": ["Keyword", "Page Parameters"],
    },
    {
        "name": 'Template 4: \"Keyword\"  Filetype+PageType',
        "short": 'T4: \"Kw\"  File+Page',
        "description": '\"(keyword)\"  (filetype)+(page type)\n'
                       'Example: \"admin panel\"  filetype:php login',
        "segments": [
            ["Keyword"],
            ["Page Type", "Page Parameters"],
        ],
        "quoted": ["Keyword"],
    },
]

# ─────────────────────────────────────────────
# Color Palette & Styling
# ─────────────────────────────────────────────
COLORS = {
    "bg_dark":       "#1a1a2e",
    "bg_medium":     "#16213e",
    "bg_light":      "#0f3460",
    "bg_card":       "#1e2a4a",
    "accent":        "#e94560",
    "accent_hover":  "#ff6b81",
    "accent_green":  "#00d2d3",
    "accent_yellow": "#feca57",
    "accent_blue":   "#54a0ff",
    "text_primary":  "#eaf0fb",
    "text_secondary":"#8899aa",
    "text_muted":    "#556677",
    "border":        "#2a3a5e",
    "input_bg":      "#0d1b36",
    "input_fg":      "#eaf0fb",
    "disabled_bg":   "#111827",
    "disabled_fg":   "#444e5c",
    "scrollbar_bg":  "#1e2a4a",
    "scrollbar_fg":  "#3a4a6e",
    "tag_enabled":   "#00d2d3",
    "tag_disabled":  "#e94560",
    "success":       "#10b981",
    "warning":       "#f59e0b",
    "error":         "#ef4444",
}

FONTS = {
    "title":     ("Segoe UI", 18, "bold"),
    "subtitle":  ("Segoe UI", 12),
    "heading":   ("Segoe UI", 11, "bold"),
    "body":      ("Segoe UI", 10),
    "small":     ("Segoe UI", 9),
    "mono":      ("Consolas", 10),
    "mono_sm":   ("Consolas", 9),
    "counter":   ("Segoe UI", 22, "bold"),
    "btn":       ("Segoe UI", 10, "bold"),
    "btn_sm":    ("Segoe UI", 9),
}


# ─────────────────────────────────────────────
# Tooltip Helper
# ─────────────────────────────────────────────
class ToolTip:
    """Simple hover tooltip for any widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify="left",
            background=COLORS["bg_card"], foreground=COLORS["text_primary"],
            relief="solid", borderwidth=1,
            font=FONTS["small"], padx=8, pady=4
        )
        label.pack()

    def _hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ─────────────────────────────────────────────
# Styled Button Factory
# ─────────────────────────────────────────────
def make_button(parent, text, command, style="accent", width=None, tooltip=None):
    """Create a styled button with hover effects."""
    color_map = {
        "accent":  (COLORS["accent"], COLORS["accent_hover"], "#ffffff"),
        "green":   (COLORS["accent_green"], "#33e0e0", COLORS["bg_dark"]),
        "blue":    (COLORS["accent_blue"], "#7ab8ff", "#ffffff"),
        "yellow":  (COLORS["accent_yellow"], "#ffe07a", COLORS["bg_dark"]),
        "muted":   (COLORS["border"], COLORS["bg_light"], COLORS["text_primary"]),
        "danger":  (COLORS["error"], "#ff6b6b", "#ffffff"),
    }
    bg, hover_bg, fg = color_map.get(style, color_map["accent"])
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=hover_bg, activeforeground=fg,
        font=FONTS["btn"], relief="flat", cursor="hand2",
        padx=14, pady=6, borderwidth=0, highlightthickness=0,
    )
    if width:
        btn.configure(width=width)
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    if tooltip:
        ToolTip(btn, tooltip)
    return btn


def make_small_button(parent, text, command, style="muted", tooltip=None):
    """Create a small icon/text button."""
    color_map = {
        "accent":  (COLORS["accent"], COLORS["accent_hover"], "#ffffff"),
        "green":   (COLORS["accent_green"], "#33e0e0", COLORS["bg_dark"]),
        "blue":    (COLORS["accent_blue"], "#7ab8ff", "#ffffff"),
        "yellow":  (COLORS["accent_yellow"], "#ffe07a", COLORS["bg_dark"]),
        "muted":   (COLORS["border"], COLORS["bg_light"], COLORS["text_primary"]),
        "danger":  (COLORS["error"], "#ff6b6b", "#ffffff"),
    }
    bg, hover_bg, fg = color_map.get(style, color_map["muted"])
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=hover_bg, activeforeground=fg,
        font=FONTS["btn_sm"], relief="flat", cursor="hand2",
        padx=6, pady=2, borderwidth=0, highlightthickness=0,
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    if tooltip:
        ToolTip(btn, tooltip)
    return btn


# ─────────────────────────────────────────────
# Operator Box Widget
# ─────────────────────────────────────────────
class OperatorBox:
    """Represents a single operator fragment input box."""

    _id_counter = 0

    def __init__(self, manager, parent_frame, name=None, enabled=True):
        OperatorBox._id_counter += 1
        self.uid = OperatorBox._id_counter
        self.manager = manager
        self.name = name or f"Box {self.uid}"
        self.enabled = enabled
        self._build(parent_frame)

    def _build(self, parent):
        # Main card frame
        self.frame = tk.Frame(parent, bg=COLORS["bg_card"], highlightthickness=1,
                              highlightbackground=COLORS["border"], padx=8, pady=6)

        # Header row
        hdr = tk.Frame(self.frame, bg=COLORS["bg_card"])
        hdr.pack(fill="x", pady=(0, 4))

        # Enable checkbox
        self.enabled_var = tk.BooleanVar(value=self.enabled)
        self.chk = tk.Checkbutton(
            hdr, variable=self.enabled_var, command=self._toggle_enabled,
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            selectcolor=COLORS["input_bg"], activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text_primary"], highlightthickness=0,
        )
        self.chk.pack(side="left")

        # Box name label (click to rename)
        self.name_label = tk.Label(
            hdr, text=self.name, font=FONTS["heading"],
            bg=COLORS["bg_card"], fg=COLORS["accent_green"], cursor="hand2"
        )
        self.name_label.pack(side="left", padx=(2, 0))
        self.name_label.bind("<Double-Button-1>", lambda e: self._rename())
        ToolTip(self.name_label, "Double-click to rename")

        # Entry counter
        self.counter_label = tk.Label(
            hdr, text="0 entries", font=FONTS["small"],
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"]
        )
        self.counter_label.pack(side="left", padx=(10, 0))

        # Status tag
        self.status_tag = tk.Label(
            hdr, text="ENABLED", font=("Segoe UI", 8, "bold"),
            bg=COLORS["tag_enabled"], fg=COLORS["bg_dark"], padx=6, pady=1
        )
        self.status_tag.pack(side="left", padx=(8, 0))

        # Action buttons (right side)
        btn_frame = tk.Frame(hdr, bg=COLORS["bg_card"])
        btn_frame.pack(side="right")

        make_small_button(btn_frame, "\u25B2", lambda: self.manager.move_box(self, -1),
                          tooltip="Move Up").pack(side="left", padx=1)
        make_small_button(btn_frame, "\u25BC", lambda: self.manager.move_box(self, 1),
                          tooltip="Move Down").pack(side="left", padx=1)
        make_small_button(btn_frame, "\u270E", self._rename,
                          style="blue", tooltip="Rename").pack(side="left", padx=1)
        make_small_button(btn_frame, "\u2716", lambda: self.manager.remove_box(self),
                          style="danger", tooltip="Remove Box").pack(side="left", padx=1)

        # Text input
        text_frame = tk.Frame(self.frame, bg=COLORS["bg_card"])
        text_frame.pack(fill="both", expand=True)

        self.text = tk.Text(
            text_frame, height=5, width=35,
            bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            insertbackground=COLORS["accent_green"],
            font=FONTS["mono"], relief="flat",
            selectbackground=COLORS["accent_blue"],
            selectforeground="#ffffff",
            borderwidth=0, highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent_green"],
            padx=8, pady=6, wrap="word", undo=True,
        )
        self.text.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(text_frame, command=self.text.yview,
                                 bg=COLORS["scrollbar_bg"],
                                 troughcolor=COLORS["bg_card"],
                                 activebackground=COLORS["scrollbar_fg"])
        scrollbar.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scrollbar.set)

        # Bind text changes for live counter update
        self.text.bind("<KeyRelease>", lambda e: self._update_counter())
        self._update_counter()
        self._apply_enabled_state()

    def _toggle_enabled(self):
        self.enabled = self.enabled_var.get()
        self._apply_enabled_state()
        self.manager.on_box_changed()

    def _apply_enabled_state(self):
        if self.enabled:
            self.text.configure(state="normal", bg=COLORS["input_bg"], fg=COLORS["input_fg"])
            self.name_label.configure(fg=COLORS["accent_green"])
            self.status_tag.configure(text="ENABLED", bg=COLORS["tag_enabled"], fg=COLORS["bg_dark"])
            self.frame.configure(highlightbackground=COLORS["border"])
        else:
            self.text.configure(bg=COLORS["disabled_bg"], fg=COLORS["disabled_fg"])
            self.name_label.configure(fg=COLORS["text_muted"])
            self.status_tag.configure(text="DISABLED", bg=COLORS["tag_disabled"], fg="#ffffff")
            self.frame.configure(highlightbackground=COLORS["text_muted"])

    def _rename(self):
        new_name = simpledialog.askstring(
            "Rename Box", f"Enter new name for '{self.name}':",
            initialvalue=self.name
        )
        if new_name and new_name.strip():
            self.name = new_name.strip()
            self.name_label.configure(text=self.name)

    def _update_counter(self):
        entries = self.get_entries()
        count = len(entries)
        self.counter_label.configure(text=f"{count} entr{'y' if count == 1 else 'ies'}")
        self.manager.on_box_changed()

    def get_entries(self):
        """Return non-empty lines from this box (preserving internal spacing)."""
        raw = self.text.get("1.0", "end-1c")
        # Only filter completely empty lines, don't strip whitespace
        return [line for line in raw.splitlines() if line.strip()]

    def is_active(self):
        return self.enabled and len(self.get_entries()) > 0

    def destroy(self):
        self.frame.destroy()


# ─────────────────────────────────────────────
# Box Manager
# ─────────────────────────────────────────────
class BoxManager:
    """Manages the collection of OperatorBox instances."""

    def __init__(self, app, scroll_frame):
        self.app = app
        self.scroll_frame = scroll_frame
        self.boxes = []

    def add_box(self, name=None):
        if len(self.boxes) >= MAX_BOXES:
            messagebox.showwarning("Limit Reached", f"Maximum {MAX_BOXES} boxes allowed.")
            return
        idx = len(self.boxes)
        default_name = DEFAULT_BOX_NAMES[idx] if idx < len(DEFAULT_BOX_NAMES) else f"Box {idx + 1}"
        box = OperatorBox(self, self.scroll_frame, name=name or default_name)
        self.boxes.append(box)
        self._repack()
        self.on_box_changed()
        return box

    def remove_box(self, box):
        if len(self.boxes) <= MIN_BOXES:
            messagebox.showwarning("Minimum Boxes", f"You must keep at least {MIN_BOXES} boxes.")
            return
        if messagebox.askyesno("Remove Box", f"Remove '{box.name}'?"):
            self.boxes.remove(box)
            box.destroy()
            self._repack()
            self.on_box_changed()

    def move_box(self, box, direction):
        idx = self.boxes.index(box)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.boxes):
            self.boxes[idx], self.boxes[new_idx] = self.boxes[new_idx], self.boxes[idx]
            self._repack()

    def _repack(self):
        for b in self.boxes:
            b.frame.pack_forget()
        for i, b in enumerate(self.boxes):
            b.frame.pack(fill="x", padx=4, pady=4)

    def get_active_boxes(self):
        return [b for b in self.boxes if b.enabled]

    def get_active_entries(self):
        """Return list of entry-lists from enabled boxes with entries."""
        return [b.get_entries() for b in self.boxes if b.is_active()]

    def on_box_changed(self):
        self.app.update_stats()

    def validate_for_generation(self):
        """Validate boxes before generating. Returns (ok, message)."""
        active = self.get_active_boxes()
        if len(active) < MIN_BOXES:
            return False, f"At least {MIN_BOXES} enabled boxes are required.\nCurrently enabled: {len(active)}"

        empty_names = [b.name for b in active if len(b.get_entries()) == 0]
        if empty_names:
            names_str = ", ".join(empty_names)
            return False, f"The following enabled boxes are empty:\n{names_str}\n\nAdd entries or disable them."

        return True, ""


# ─────────────────────────────────────────────
# Combination Engine
# ─────────────────────────────────────────────
class CombinationEngine:
    """Generates dork combinations from box entries."""

    @staticmethod
    def calculate_total(entry_lists):
        """Calculate total possible unique combinations."""
        if not entry_lists:
            return 0
        total = 1
        for el in entry_lists:
            total *= len(el)
        return total

    @staticmethod
    def generate_all(entry_lists):
        """Generate ALL combinations (cartesian product)."""
        if not entry_lists:
            return []
        results = []
        for combo in itertools.product(*entry_lists):
            dork = "".join(combo)
            results.append(dork)
        return results

    @staticmethod
    def generate_random_sample(entry_lists, count, progress_callback=None):
        """Generate a random sample of unique combinations."""
        if not entry_lists:
            return []

        total = CombinationEngine.calculate_total(entry_lists)
        if count >= total:
            results = CombinationEngine.generate_all(entry_lists)
            random.shuffle(results)
            return results

        # For manageable totals, generate all and sample
        if total <= 500_000:
            all_combos = CombinationEngine.generate_all(entry_lists)
            random.shuffle(all_combos)
            return all_combos[:count]

        # For very large totals, use random index picking
        results_set = set()
        attempts = 0
        max_attempts = count * 10  # safety limit

        while len(results_set) < count and attempts < max_attempts:
            combo = tuple(random.choice(el) for el in entry_lists)
            dork = "".join(combo)
            if dork not in results_set:
                results_set.add(dork)
                if progress_callback and len(results_set) % 1000 == 0:
                    progress_callback(len(results_set), count)
            attempts += 1

        results = list(results_set)
        random.shuffle(results)
        return results

    @staticmethod
    def calculate_total_template(template, box_map):
        """Calculate total combos for a template pattern.

        A template has 'segments' – each segment is a list of box-name
        references whose entries are concatenated (operator+value style).
        The segments themselves are space-joined to form a dork line.
        The cartesian product is across ALL referenced boxes.
        """
        # Collect unique box entry-lists in segment order
        seen = set()
        entry_lists = []
        for seg in template["segments"]:
            for box_name in seg:
                if box_name not in seen:
                    entries = box_map.get(box_name, [])
                    if not entries:
                        return 0
                    entry_lists.append(entries)
                    seen.add(box_name)
        return CombinationEngine.calculate_total(entry_lists) if entry_lists else 0

    @staticmethod
    def generate_all_template(template, box_map):
        """Generate ALL combinations following a template pattern."""
        quoted_boxes = set(template.get("quoted", []))

        # Collect unique boxes in order and remember positions
        seen = {}
        ordered_names = []
        entry_lists = []
        for seg in template["segments"]:
            for box_name in seg:
                if box_name not in seen:
                    entries = box_map.get(box_name, [])
                    if not entries:
                        return []
                    seen[box_name] = len(ordered_names)
                    ordered_names.append(box_name)
                    entry_lists.append(entries)

        if not entry_lists:
            return []

        results = []
        for combo in itertools.product(*entry_lists):
            # Build a lookup: box_name -> chosen value
            chosen = {ordered_names[i]: combo[i] for i in range(len(combo))}
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
            results.append(dork)
        return results

    @staticmethod
    def generate_random_sample_template(template, box_map, count, progress_callback=None):
        """Generate a random sample of unique combinations for a template."""
        total = CombinationEngine.calculate_total_template(template, box_map)
        if total == 0:
            return []
        if count >= total:
            results = CombinationEngine.generate_all_template(template, box_map)
            random.shuffle(results)
            return results

        # For manageable totals, generate all and sample
        if total <= 500_000:
            all_combos = CombinationEngine.generate_all_template(template, box_map)
            random.shuffle(all_combos)
            return all_combos[:count]

        # For very large totals, use random index picking
        quoted_boxes = set(template.get("quoted", []))
        seen_order = {}
        ordered_names = []
        entry_lists = []
        for seg in template["segments"]:
            for box_name in seg:
                if box_name not in seen_order:
                    entries = box_map.get(box_name, [])
                    if not entries:
                        return []
                    seen_order[box_name] = len(ordered_names)
                    ordered_names.append(box_name)
                    entry_lists.append(entries)

        results_set = set()
        attempts = 0
        max_attempts = count * 10

        while len(results_set) < count and attempts < max_attempts:
            combo = tuple(random.choice(el) for el in entry_lists)
            chosen = {ordered_names[i]: combo[i] for i in range(len(combo))}
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
                if progress_callback and len(results_set) % 1000 == 0:
                    progress_callback(len(results_set), count)
            attempts += 1

        results = list(results_set)
        random.shuffle(results)
        return results


# ─────────────────────────────────────────────
# Export Engine
# ─────────────────────────────────────────────
class ExportEngine:
    """Handles exporting dorks to various formats."""

    @staticmethod
    def export_txt(dorks, filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            for d in dorks:
                f.write(d + "\n")

    @staticmethod
    def export_csv(dorks, filepath):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["#", "Google Dork"])
            for i, d in enumerate(dorks, 1):
                writer.writerow([i, d])

    @staticmethod
    def export_json(dorks, filepath):
        data = {
            "generator": APP_TITLE,
            "version": APP_VERSION,
            "total": len(dorks),
            "dorks": dorks
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# Scrollable Frame Helper
# ─────────────────────────────────────────────
class ScrollableFrame(tk.Frame):
    """A frame that can be scrolled vertically."""

    def __init__(self, parent, bg=COLORS["bg_medium"], **kwargs):
        super().__init__(parent, bg=bg, **kwargs)

        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, borderwidth=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                       bg=COLORS["scrollbar_bg"],
                                       troughcolor=bg,
                                       activebackground=COLORS["scrollbar_fg"])
        self.inner_frame = tk.Frame(self.canvas, bg=bg)

        self.inner_frame.bind("<Configure>",
                              lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Resize inner frame width to match canvas
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self.inner_frame.bind("<Enter>", self._bind_mousewheel)
        self.inner_frame.bind("<Leave>", self._unbind_mousewheel)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ─────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────
class DorkBoxApp:
    """Main application window."""

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("1280x820")
        self.root.minsize(960, 600)
        self.root.configure(bg=COLORS["bg_dark"])

        # Try to set icon (fails gracefully)
        try:
            self.root.iconname(APP_TITLE)
        except Exception:
            pass

        self.generated_dorks = []
        self.filtered_dorks = []
        self.templates = list(DEFAULT_TEMPLATES)  # mutable copy
        self.active_template_idx = None  # None = cartesian product mode

        self._build_gui()
        self._init_default_boxes()

    # ── GUI Construction ──

    def _build_gui(self):
        # Top header bar
        self._build_header()

        # Main content: left panel (boxes) + right panel (output)
        self.main_pane = tk.PanedWindow(
            self.root, orient="horizontal",
            bg=COLORS["bg_dark"], sashwidth=6,
            sashrelief="flat", borderwidth=0,
        )
        self.main_pane.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._build_left_panel()
        self._build_right_panel()

    def _build_header(self):
        header = tk.Frame(self.root, bg=COLORS["bg_medium"], padx=16, pady=10)
        header.pack(fill="x")

        # Left side: title
        title_frame = tk.Frame(header, bg=COLORS["bg_medium"])
        title_frame.pack(side="left")

        tk.Label(
            title_frame, text="\u2692 DorkBox Builder",
            font=FONTS["title"], bg=COLORS["bg_medium"], fg=COLORS["accent"]
        ).pack(side="left")

        tk.Label(
            title_frame, text=f"  v{APP_VERSION}",
            font=FONTS["small"], bg=COLORS["bg_medium"], fg=COLORS["text_muted"]
        ).pack(side="left", pady=(6, 0))

        # Right side: stats
        stats_frame = tk.Frame(header, bg=COLORS["bg_medium"])
        stats_frame.pack(side="right")

        self.stat_boxes_label = tk.Label(
            stats_frame, text="Boxes: 0/0", font=FONTS["body"],
            bg=COLORS["bg_medium"], fg=COLORS["text_secondary"]
        )
        self.stat_boxes_label.pack(side="left", padx=(0, 20))

        self.stat_total_label = tk.Label(
            stats_frame, text="Total Possible: 0", font=FONTS["heading"],
            bg=COLORS["bg_medium"], fg=COLORS["accent_yellow"]
        )
        self.stat_total_label.pack(side="left")

    def _build_left_panel(self):
        left = tk.Frame(self.main_pane, bg=COLORS["bg_dark"])
        self.main_pane.add(left, minsize=420, width=520)

        # Box controls bar
        controls = tk.Frame(left, bg=COLORS["bg_dark"], pady=6)
        controls.pack(fill="x")

        tk.Label(
            controls, text="\u25A6 Operator Boxes",
            font=FONTS["heading"], bg=COLORS["bg_dark"], fg=COLORS["text_primary"]
        ).pack(side="left")

        self.box_count_label = tk.Label(
            controls, text="", font=FONTS["small"],
            bg=COLORS["bg_dark"], fg=COLORS["text_muted"]
        )
        self.box_count_label.pack(side="left", padx=(8, 0))

        make_button(controls, "+ Add Box", self._add_box, style="green",
                    tooltip="Add a new operator box").pack(side="right", padx=(4, 0))

        # Scrollable box area
        self.box_scroll = ScrollableFrame(left, bg=COLORS["bg_medium"])
        self.box_scroll.pack(fill="both", expand=True)

        self.box_manager = BoxManager(self, self.box_scroll.inner_frame)

        # ── Combination Templates Section ──
        tmpl_outer = tk.Frame(left, bg=COLORS["bg_card"], padx=12, pady=8,
                              highlightthickness=1, highlightbackground=COLORS["border"])
        tmpl_outer.pack(fill="x", pady=(8, 0))

        tmpl_hdr = tk.Frame(tmpl_outer, bg=COLORS["bg_card"])
        tmpl_hdr.pack(fill="x", pady=(0, 6))

        tk.Label(
            tmpl_hdr, text="\u2726 Combination Template",
            font=FONTS["heading"], bg=COLORS["bg_card"], fg=COLORS["accent_yellow"]
        ).pack(side="left")

        self.tmpl_mode_label = tk.Label(
            tmpl_hdr, text="Cartesian Product (all boxes)",
            font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_secondary"]
        )
        self.tmpl_mode_label.pack(side="right")

        # Template radio buttons
        self.tmpl_var = tk.IntVar(value=-1)  # -1 = cartesian product
        tmpl_scroll_frame = tk.Frame(tmpl_outer, bg=COLORS["bg_card"])
        tmpl_scroll_frame.pack(fill="x")

        # "None" option = classic cartesian product
        self.tmpl_radios = []
        r_none = tk.Radiobutton(
            tmpl_scroll_frame, text="None (Cartesian Product — all enabled boxes)",
            variable=self.tmpl_var, value=-1,
            command=self._on_template_changed,
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            selectcolor=COLORS["input_bg"], activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text_primary"],
            font=FONTS["small"], anchor="w", highlightthickness=0,
        )
        r_none.pack(fill="x", anchor="w")
        ToolTip(r_none, "Classic mode: every enabled box entry is combined\nwith every other (full cartesian product).")
        self.tmpl_radios.append(r_none)

        for idx, tmpl in enumerate(self.templates):
            r = tk.Radiobutton(
                tmpl_scroll_frame, text=tmpl["short"],
                variable=self.tmpl_var, value=idx,
                command=self._on_template_changed,
                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                selectcolor=COLORS["input_bg"], activebackground=COLORS["bg_card"],
                activeforeground=COLORS["text_primary"],
                font=FONTS["small"], anchor="w", highlightthickness=0,
            )
            r.pack(fill="x", anchor="w")
            ToolTip(r, tmpl["description"])
            self.tmpl_radios.append(r)

        # Template preview label
        self.tmpl_preview = tk.Label(
            tmpl_outer, text="", font=FONTS["mono_sm"],
            bg=COLORS["input_bg"], fg=COLORS["accent_green"],
            anchor="w", justify="left", padx=8, pady=4,
            wraplength=480,
        )
        self.tmpl_preview.pack(fill="x", pady=(6, 0))
        self._update_template_preview()

        # ── Generation controls at bottom ──
        gen_frame = tk.Frame(left, bg=COLORS["bg_card"], padx=12, pady=10,
                             highlightthickness=1, highlightbackground=COLORS["border"])
        gen_frame.pack(fill="x", pady=(8, 0))

        row1 = tk.Frame(gen_frame, bg=COLORS["bg_card"])
        row1.pack(fill="x")

        tk.Label(
            row1, text="Number of Dorks:", font=FONTS["body"],
            bg=COLORS["bg_card"], fg=COLORS["text_primary"]
        ).pack(side="left")

        self.gen_count_var = tk.StringVar(value="100")
        self.gen_entry = tk.Entry(
            row1, textvariable=self.gen_count_var, width=12,
            bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            insertbackground=COLORS["accent_green"],
            font=FONTS["mono"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent_green"],
        )
        self.gen_entry.pack(side="left", padx=(8, 0))

        self.gen_max_btn = make_small_button(
            row1, "MAX", self._set_max_count, style="yellow",
            tooltip="Set to maximum possible"
        )
        self.gen_max_btn.pack(side="left", padx=(6, 0))

        make_button(row1, "\u25B6 Generate Dorks", self._generate,
                    style="accent", tooltip="Generate dork combinations").pack(side="right")

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(gen_frame, variable=self.progress_var, maximum=100)
        # Hidden by default; shown during generation

    def _build_right_panel(self):
        right = tk.Frame(self.main_pane, bg=COLORS["bg_dark"])
        self.main_pane.add(right, minsize=380)

        # Output header
        out_header = tk.Frame(right, bg=COLORS["bg_dark"], pady=6)
        out_header.pack(fill="x")

        tk.Label(
            out_header, text="\u2263 Generated Dorks",
            font=FONTS["heading"], bg=COLORS["bg_dark"], fg=COLORS["text_primary"]
        ).pack(side="left")

        self.output_count_label = tk.Label(
            out_header, text="0 dorks", font=FONTS["small"],
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"]
        )
        self.output_count_label.pack(side="left", padx=(10, 0))

        # Search & filter bar
        search_frame = tk.Frame(right, bg=COLORS["bg_card"], padx=8, pady=6,
                                highlightthickness=1, highlightbackground=COLORS["border"])
        search_frame.pack(fill="x")

        tk.Label(
            search_frame, text="\U0001F50D", font=FONTS["body"],
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"]
        ).pack(side="left")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        self.search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            insertbackground=COLORS["accent_green"],
            font=FONTS["mono"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent_green"],
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ToolTip(self.search_entry, "Filter dorks (case-insensitive)")

        make_small_button(search_frame, "A\u2193Z", self._sort_output, style="blue",
                          tooltip="Sort alphabetically").pack(side="left", padx=2)
        make_small_button(search_frame, "\u21C5", self._shuffle_output, style="blue",
                          tooltip="Shuffle order").pack(side="left", padx=2)
        make_small_button(search_frame, "Clear", self._clear_output, style="danger",
                          tooltip="Clear output").pack(side="left", padx=2)

        # Output text area
        text_frame = tk.Frame(right, bg=COLORS["bg_dark"])
        text_frame.pack(fill="both", expand=True, pady=(4, 0))

        self.output_text = tk.Text(
            text_frame,
            bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            insertbackground=COLORS["accent_green"],
            font=FONTS["mono_sm"], relief="flat",
            selectbackground=COLORS["accent_blue"],
            selectforeground="#ffffff",
            borderwidth=0, highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent_green"],
            padx=10, pady=8, wrap="none", state="disabled",
        )
        self.output_text.pack(side="left", fill="both", expand=True)

        # Configure line number tag
        self.output_text.tag_configure("lineno", foreground=COLORS["text_muted"])
        self.output_text.tag_configure("dork", foreground=COLORS["input_fg"])
        self.output_text.tag_configure("highlight", background=COLORS["accent_blue"], foreground="#ffffff")

        out_scroll = tk.Scrollbar(text_frame, command=self.output_text.yview,
                                   bg=COLORS["scrollbar_bg"],
                                   troughcolor=COLORS["bg_dark"],
                                   activebackground=COLORS["scrollbar_fg"])
        out_scroll.pack(side="right", fill="y")
        self.output_text.configure(yscrollcommand=out_scroll.set)

        # Horizontal scrollbar
        h_scroll = tk.Scrollbar(right, orient="horizontal", command=self.output_text.xview,
                                 bg=COLORS["scrollbar_bg"],
                                 troughcolor=COLORS["bg_dark"],
                                 activebackground=COLORS["scrollbar_fg"])
        h_scroll.pack(fill="x")
        self.output_text.configure(xscrollcommand=h_scroll.set)

        # Action buttons
        btn_bar = tk.Frame(right, bg=COLORS["bg_card"], padx=10, pady=8,
                           highlightthickness=1, highlightbackground=COLORS["border"])
        btn_bar.pack(fill="x", pady=(6, 0))

        make_button(btn_bar, "\u2398 Copy Selected", self._copy_selected, style="blue",
                    tooltip="Copy selected text").pack(side="left", padx=(0, 4))
        make_button(btn_bar, "\u29C9 Copy All", self._copy_all, style="blue",
                    tooltip="Copy all dorks to clipboard").pack(side="left", padx=(0, 4))

        # Export dropdown
        export_frame = tk.Frame(btn_bar, bg=COLORS["bg_card"])
        export_frame.pack(side="right")

        make_button(export_frame, "\u21E9 Export TXT", lambda: self._export("txt"), style="green",
                    tooltip="Export as plain text").pack(side="left", padx=2)
        make_button(export_frame, "\u21E9 CSV", lambda: self._export("csv"), style="green",
                    tooltip="Export as CSV").pack(side="left", padx=2)
        make_button(export_frame, "\u21E9 JSON", lambda: self._export("json"), style="green",
                    tooltip="Export as JSON").pack(side="left", padx=2)

    # ── Default Setup ──

    def _init_default_boxes(self):
        # Start with 4 default boxes matching the template system
        b1 = self.box_manager.add_box("Search Operator")
        b2 = self.box_manager.add_box("Keyword")
        b3 = self.box_manager.add_box("Page Type")
        b4 = self.box_manager.add_box("Page Parameters")

        # Add example content
        b1.text.insert("1.0", "site:example.com\nintitle:\ninurl:\nintext:")
        b2.text.insert("1.0", "login\nadmin panel\ndashboard")
        b3.text.insert("1.0", "filetype:php\nfiletype:asp\nfiletype:html")
        b4.text.insert("1.0", "admin.php\nlogin.asp\nindex.html")

        b1._update_counter()
        b2._update_counter()
        b3._update_counter()
        b4._update_counter()

    # ── Actions ──

    def _add_box(self):
        self.box_manager.add_box()

    def _set_max_count(self):
        total = self._calc_current_total()
        self.gen_count_var.set(str(total))

    # ── Template helpers ──

    def _on_template_changed(self):
        """Called when the user selects a different template radio."""
        val = self.tmpl_var.get()
        self.active_template_idx = val if val >= 0 else None
        self._update_template_preview()
        self.update_stats()

    def _update_template_preview(self):
        """Update the preview label under the template radios."""
        idx = self.active_template_idx
        if idx is None or idx < 0 or idx >= len(self.templates):
            self.tmpl_preview.configure(
                text="Mode: Full Cartesian Product of all enabled boxes"
            )
            self.tmpl_mode_label.configure(text="Cartesian Product (all boxes)")
        else:
            tmpl = self.templates[idx]
            # Build a human-readable pattern string
            parts = []
            quoted = set(tmpl.get("quoted", []))
            for seg in tmpl["segments"]:
                seg_parts = []
                for bn in seg:
                    display = f"({bn})"
                    if bn in quoted:
                        display = f'\"({bn})\"'
                    seg_parts.append(display)
                parts.append("+".join(seg_parts))
            pattern_str = "  ".join(parts)
            self.tmpl_preview.configure(
                text=f"Pattern: {pattern_str}\n{tmpl['description']}"
            )
            self.tmpl_mode_label.configure(text=tmpl["short"])

    def _get_box_map(self):
        """Return dict mapping box name -> list of entries for enabled boxes."""
        return {b.name: b.get_entries() for b in self.box_manager.boxes if b.is_active()}

    def _calc_current_total(self):
        """Calculate total combos for the current mode/template."""
        idx = self.active_template_idx
        if idx is not None and 0 <= idx < len(self.templates):
            box_map = self._get_box_map()
            return CombinationEngine.calculate_total_template(self.templates[idx], box_map)
        else:
            entry_lists = self.box_manager.get_active_entries()
            return CombinationEngine.calculate_total(entry_lists)

    def update_stats(self):
        """Update the statistics displays."""
        total_boxes = len(self.box_manager.boxes)
        active_boxes = len(self.box_manager.get_active_boxes())
        total_combos = self._calc_current_total()

        self.stat_boxes_label.configure(text=f"Boxes: {active_boxes}/{total_boxes}")
        self.box_count_label.configure(text=f"({total_boxes}/{MAX_BOXES})")

        # Format large numbers with commas
        total_str = f"{total_combos:,}"
        self.stat_total_label.configure(text=f"Total Possible: {total_str}")

    def _generate(self):
        """Main generation action."""
        idx = self.active_template_idx
        use_template = idx is not None and 0 <= idx < len(self.templates)

        if use_template:
            # Template mode: validate that required boxes exist and have entries
            tmpl = self.templates[idx]
            box_map = self._get_box_map()
            missing = []
            for seg in tmpl["segments"]:
                for bn in seg:
                    if bn not in box_map or not box_map[bn]:
                        missing.append(bn)
            if missing:
                names = ", ".join(sorted(set(missing)))
                messagebox.showerror(
                    "Template Error",
                    f"The selected template requires these boxes to be enabled with entries:\n"
                    f"{names}\n\nPlease add/enable them or choose a different template."
                )
                return
            total = CombinationEngine.calculate_total_template(tmpl, box_map)
        else:
            # Cartesian product mode
            ok, msg = self.box_manager.validate_for_generation()
            if not ok:
                messagebox.showerror("Validation Error", msg)
                return
            entry_lists = self.box_manager.get_active_entries()
            total = CombinationEngine.calculate_total(entry_lists)

        # Parse requested count
        try:
            requested = int(self.gen_count_var.get().strip().replace(",", ""))
            if requested <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid positive number.")
            return

        if total == 0:
            messagebox.showwarning("No Combinations", "No entries found in active boxes.")
            return

        # Check if requested > total
        if requested > total:
            result = messagebox.askyesno(
                "Exceeds Maximum",
                f"Requested {requested:,} dorks but only {total:,} unique combinations exist.\n\n"
                f"Generate all {total:,} instead?"
            )
            if not result:
                return
            requested = total

        # Warn for huge requests
        if requested > HUGE_REQUEST_THRESHOLD:
            result = messagebox.askyesno(
                "Large Generation",
                f"Generating {requested:,} dorks may take a moment.\n\nContinue?"
            )
            if not result:
                return

        # Show progress
        self.progress.pack(fill="x", pady=(6, 0))
        self.progress_var.set(0)
        self.root.update_idletasks()

        # Generate
        def progress_cb(done, total_req):
            pct = (done / total_req) * 100
            self.progress_var.set(pct)
            self.root.update_idletasks()

        try:
            if use_template:
                tmpl = self.templates[idx]
                box_map = self._get_box_map()
                if requested >= total:
                    dorks = CombinationEngine.generate_all_template(tmpl, box_map)
                    random.shuffle(dorks)
                else:
                    dorks = CombinationEngine.generate_random_sample_template(
                        tmpl, box_map, requested, progress_cb
                    )
            else:
                entry_lists = self.box_manager.get_active_entries()
                if requested >= total:
                    dorks = CombinationEngine.generate_all(entry_lists)
                    random.shuffle(dorks)
                else:
                    dorks = CombinationEngine.generate_random_sample(
                        entry_lists, requested, progress_cb
                    )

            # Remove duplicates (safety)
            seen = set()
            unique_dorks = []
            for d in dorks:
                if d not in seen:
                    seen.add(d)
                    unique_dorks.append(d)

            self.generated_dorks = unique_dorks
            self.filtered_dorks = list(unique_dorks)
            self._display_dorks(self.filtered_dorks)

            self.progress_var.set(100)
            self.root.after(800, lambda: self.progress.pack_forget())

        except Exception as e:
            messagebox.showerror("Generation Error", str(e))
            self.progress.pack_forget()

    def _display_dorks(self, dorks):
        """Display dorks in the output text area."""
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")

        # Add line numbers + content
        pad = len(str(len(dorks)))
        for i, dork in enumerate(dorks, 1):
            line_num = f"{i:>{pad}}  "
            self.output_text.insert("end", line_num, "lineno")
            self.output_text.insert("end", dork + "\n", "dork")

        self.output_text.configure(state="disabled")
        self.output_count_label.configure(text=f"{len(dorks):,} dorks")

        # Apply search filter highlight if active
        if self.search_var.get().strip():
            self._highlight_search()

    def _apply_filter(self):
        """Filter displayed dorks by search term."""
        term = self.search_var.get().strip().lower()
        if not term:
            self.filtered_dorks = list(self.generated_dorks)
        else:
            self.filtered_dorks = [d for d in self.generated_dorks if term in d.lower()]
        self._display_dorks(self.filtered_dorks)

    def _highlight_search(self):
        """Highlight search matches in output."""
        term = self.search_var.get().strip()
        if not term:
            return
        self.output_text.tag_remove("highlight", "1.0", "end")
        start = "1.0"
        while True:
            pos = self.output_text.search(term, start, stopindex="end", nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(term)}c"
            self.output_text.tag_add("highlight", pos, end_pos)
            start = end_pos

    def _sort_output(self):
        if not self.filtered_dorks:
            return
        self.filtered_dorks.sort()
        self._display_dorks(self.filtered_dorks)

    def _shuffle_output(self):
        if not self.filtered_dorks:
            return
        random.shuffle(self.filtered_dorks)
        self._display_dorks(self.filtered_dorks)

    def _clear_output(self):
        self.generated_dorks = []
        self.filtered_dorks = []
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")
        self.output_count_label.configure(text="0 dorks")
        self.search_var.set("")

    def _copy_selected(self):
        try:
            selected = self.output_text.get("sel.first", "sel.last")
            if selected:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected)
                self._flash_status("Selected text copied!")
        except tk.TclError:
            messagebox.showinfo("No Selection", "Select some text first.")

    def _copy_all(self):
        if not self.filtered_dorks:
            messagebox.showinfo("Empty", "No dorks to copy.")
            return
        text = "\n".join(self.filtered_dorks)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._flash_status(f"Copied {len(self.filtered_dorks):,} dorks!")

    def _flash_status(self, msg):
        """Briefly show a status message."""
        self.output_count_label.configure(text=msg, fg=COLORS["success"])
        self.root.after(2000, lambda: self.output_count_label.configure(
            text=f"{len(self.filtered_dorks):,} dorks", fg=COLORS["text_secondary"]
        ))

    def _export(self, fmt):
        if not self.filtered_dorks:
            messagebox.showinfo("Empty", "No dorks to export. Generate some first.")
            return

        ext_map = {"txt": ("Text Files", "*.txt"), "csv": ("CSV Files", "*.csv"), "json": ("JSON Files", "*.json")}
        filetypes = [ext_map[fmt], ("All Files", "*.*")]
        filepath = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            filetypes=filetypes,
            initialfile=f"dorkbox_export.{fmt}",
            title=f"Export as {fmt.upper()}"
        )
        if not filepath:
            return

        try:
            if fmt == "txt":
                ExportEngine.export_txt(self.filtered_dorks, filepath)
            elif fmt == "csv":
                ExportEngine.export_csv(self.filtered_dorks, filepath)
            elif fmt == "json":
                ExportEngine.export_json(self.filtered_dorks, filepath)

            self._flash_status(f"Exported to {fmt.upper()}!")
            messagebox.showinfo("Export Complete",
                                f"Successfully exported {len(self.filtered_dorks):,} dorks to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{str(e)}")


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
def main():
    root = tk.Tk()

    # Configure ttk style for progress bar
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "TProgressbar",
        troughcolor=COLORS["bg_dark"],
        background=COLORS["accent_green"],
        darkcolor=COLORS["accent_green"],
        lightcolor=COLORS["accent_green"],
        bordercolor=COLORS["border"],
        thickness=8,
    )

    app = DorkBoxApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
