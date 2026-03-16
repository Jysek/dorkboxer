"""
DorkForge - Main UI Application
=================================

The redesigned interface with:
    - Left sidebar: Builder panel (collapsible operator boxes)
    - Top bar: Global actions (New Session, Save/Load Template, Generate)
    - Main content: Live Preview pane + Results pane

The UI ONLY handles display and user interaction.
All logic is delegated to the DorkGenerator engine.
All state is managed through the centralized AppState.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import threading
import json
import csv
import random

from dorkforge import __version__, __app_name__
from dorkforge.data import (
    DEFAULT_TEMPLATES, DEFAULT_BOXES, OPERATORS, KEYWORDS, FILE_TYPES,
    APP_TITLE, APP_VERSION, MIN_BOXES, MAX_BOXES, MIX_ALL_TEMPLATE_IDX,
    HUGE_REQUEST_THRESHOLD,
)
from dorkforge.engine import DorkGenerator, DorkGeneratorInput, DorkGeneratorResult
from dorkforge.state import AppState, Action
from dorkforge.utils import COLORS, FONTS, format_number
from dorkforge.ui.widgets import (
    ToolTip, make_button, make_small_button, make_icon_button,
    ScrollableFrame, AccordionSection, StatusBadge,
)


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
            "dorks": dorks,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────
# Operator Box Widget
# ─────────────────────────────────────────────
class OperatorBoxWidget:
    """UI widget for a single operator box, backed by AppState."""

    def __init__(self, app, parent_frame, box_state):
        self.app = app
        self.state = app.state
        self.box_state = box_state
        self._build(parent_frame)

    def _build(self, parent):
        self.frame = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightthickness=1, highlightbackground=COLORS["border"],
            padx=8, pady=6,
        )

        # Header row
        hdr = tk.Frame(self.frame, bg=COLORS["bg_card"])
        hdr.pack(fill="x", pady=(0, 4))

        # Enable checkbox
        self.enabled_var = tk.BooleanVar(value=self.box_state.enabled)
        self.chk = tk.Checkbutton(
            hdr, variable=self.enabled_var,
            command=self._toggle_enabled,
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text_primary"],
            highlightthickness=0,
        )
        self.chk.pack(side="left")

        # Box name label
        self.name_label = tk.Label(
            hdr, text=self.box_state.name,
            font=FONTS["heading_sm"], bg=COLORS["bg_card"],
            fg=COLORS["accent_green"], cursor="hand2",
        )
        self.name_label.pack(side="left", padx=(2, 0))
        self.name_label.bind("<Double-Button-1>", lambda e: self._rename())
        ToolTip(self.name_label, "Double-click to rename")

        # Entry counter
        self.counter_label = tk.Label(
            hdr, text=self._count_text(),
            font=FONTS["small"], bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"],
        )
        self.counter_label.pack(side="left", padx=(10, 0))

        # Status badge
        self.status_badge = StatusBadge(
            hdr,
            text="ENABLED" if self.box_state.enabled else "DISABLED",
            style="enabled" if self.box_state.enabled else "disabled",
        )
        self.status_badge.pack(side="left", padx=(8, 0))

        # Action buttons
        btn_frame = tk.Frame(hdr, bg=COLORS["bg_card"])
        btn_frame.pack(side="right")

        make_icon_button(
            btn_frame, "\U0001F4C2", self._load_from_file,
            style="yellow", tooltip="Load from TXT",
        ).pack(side="left", padx=1)
        make_icon_button(
            btn_frame, "\u25B2",
            lambda: self.state.dispatch(Action.MOVE_BOX, uid=self.box_state.uid, direction=-1),
            tooltip="Move Up",
        ).pack(side="left", padx=1)
        make_icon_button(
            btn_frame, "\u25BC",
            lambda: self.state.dispatch(Action.MOVE_BOX, uid=self.box_state.uid, direction=1),
            tooltip="Move Down",
        ).pack(side="left", padx=1)
        make_icon_button(
            btn_frame, "\u270E", self._rename,
            style="blue", tooltip="Rename",
        ).pack(side="left", padx=1)
        make_icon_button(
            btn_frame, "\u2716", self._remove,
            style="danger", tooltip="Remove",
        ).pack(side="left", padx=1)

        # Text input
        text_frame = tk.Frame(self.frame, bg=COLORS["bg_card"])
        text_frame.pack(fill="both", expand=True)

        self.text = tk.Text(
            text_frame, height=4, width=30,
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

        scrollbar = tk.Scrollbar(
            text_frame, command=self.text.yview,
            bg=COLORS["scrollbar_bg"], troughcolor=COLORS["bg_card"],
            activebackground=COLORS["scrollbar_fg"],
        )
        scrollbar.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=scrollbar.set)

        # Pre-fill content from state
        if self.box_state.entries:
            self.text.insert("1.0", "\n".join(self.box_state.entries))

        # Bind text changes -> sync to state
        self.text.bind("<KeyRelease>", lambda e: self._sync_to_state())
        self._apply_visual_state()

    def _count_text(self):
        count = self.box_state.entry_count
        return f"{count} entr{'y' if count == 1 else 'ies'}"

    def _toggle_enabled(self):
        self.state.dispatch(
            Action.TOGGLE_BOX,
            uid=self.box_state.uid,
            enabled=self.enabled_var.get(),
        )
        self._apply_visual_state()
        self.counter_label.configure(text=self._count_text())

    def _apply_visual_state(self):
        if self.box_state.enabled:
            self.text.configure(
                state="normal", bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            )
            self.name_label.configure(fg=COLORS["accent_green"])
            self.status_badge.set_style("ENABLED", "enabled")
            self.frame.configure(highlightbackground=COLORS["border"])
        else:
            self.text.configure(
                bg=COLORS["disabled_bg"], fg=COLORS["disabled_fg"],
            )
            self.name_label.configure(fg=COLORS["text_muted"])
            self.status_badge.set_style("DISABLED", "disabled")
            self.frame.configure(highlightbackground=COLORS["text_muted"])

    def _sync_to_state(self):
        raw = self.text.get("1.0", "end-1c")
        entries = [line for line in raw.splitlines() if line.strip()]
        self.state.dispatch(
            Action.UPDATE_BOX_ENTRIES,
            uid=self.box_state.uid,
            entries=entries,
        )
        self.counter_label.configure(text=self._count_text())

    def _rename(self):
        new_name = simpledialog.askstring(
            "Rename Box", f"Enter new name for '{self.box_state.name}':",
            initialvalue=self.box_state.name,
        )
        if new_name and new_name.strip():
            self.state.dispatch(
                Action.RENAME_BOX,
                uid=self.box_state.uid,
                name=new_name.strip(),
            )
            self.name_label.configure(text=self.box_state.name)

    def _remove(self):
        if len(self.state.boxes) <= MIN_BOXES:
            messagebox.showwarning(
                "Minimum Boxes",
                f"You must keep at least {MIN_BOXES} boxes.",
            )
            return
        if messagebox.askyesno("Remove Box", f"Remove '{self.box_state.name}'?"):
            self.state.dispatch(Action.REMOVE_BOX, uid=self.box_state.uid)

    def _load_from_file(self):
        filepath = filedialog.askopenfilename(
            title=f"Load entries into '{self.box_state.name}'",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to read file:\n{e}")
            return

        lines = [line for line in content.splitlines() if line.strip()]
        if not lines:
            messagebox.showinfo("Empty File", "No non-empty lines found.")
            return

        existing = self.text.get("1.0", "end-1c").strip()
        mode = "replace"
        if existing:
            answer = messagebox.askquestion(
                "Replace or Append?",
                f"Box '{self.box_state.name}' has content.\n\n"
                f"YES = Replace, NO = Append",
            )
            mode = "replace" if answer == "yes" else "append"

        if mode == "replace":
            self.text.delete("1.0", "end")
        elif not self.text.get("1.0", "end-1c").endswith("\n"):
            self.text.insert("end", "\n")

        self.text.insert("end", "\n".join(lines))
        self._sync_to_state()

    def destroy(self):
        self.frame.destroy()


# ─────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────
class DorkForgeApp:
    """Main application - redesigned with professional layout."""

    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry("1400x900")
        self.root.minsize(1100, 700)
        self.root.configure(bg=COLORS["bg_dark"])

        try:
            self.root.iconname(APP_TITLE)
        except Exception:
            pass

        # Core systems
        self.state = AppState()
        self.engine = DorkGenerator()
        self.templates = list(DEFAULT_TEMPLATES)

        # Widget references
        self.box_widgets: dict = {}  # uid -> OperatorBoxWidget

        # Build UI
        self._build_gui()
        self._init_defaults()

        # Subscribe to state changes
        self.state.subscribe("boxes", self._on_boxes_changed)
        self.state.subscribe("stats", self._on_stats_changed)
        self.state.subscribe("results", self._on_results_changed)

    # ── GUI Construction ──

    def _build_gui(self):
        self._build_top_bar()

        # Main horizontal layout
        self.main_pane = tk.PanedWindow(
            self.root, orient="horizontal",
            bg=COLORS["bg_dark"], sashwidth=6,
            sashrelief="flat", borderwidth=0,
        )
        self.main_pane.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self._build_sidebar()
        self._build_center()

    def _build_top_bar(self):
        """Top bar: global actions, session management, main generate button."""
        bar = tk.Frame(self.root, bg=COLORS["bg_medium"], padx=12, pady=8)
        bar.pack(fill="x")

        # Left: Title
        title_frame = tk.Frame(bar, bg=COLORS["bg_medium"])
        title_frame.pack(side="left")

        tk.Label(
            title_frame, text=f"\u2692 {APP_TITLE}",
            font=FONTS["title"], bg=COLORS["bg_medium"], fg=COLORS["accent"],
        ).pack(side="left")

        tk.Label(
            title_frame, text=f"  v{APP_VERSION}",
            font=FONTS["tiny"], bg=COLORS["bg_medium"], fg=COLORS["text_muted"],
        ).pack(side="left", pady=(6, 0))

        # Center: Session actions
        session_frame = tk.Frame(bar, bg=COLORS["bg_medium"])
        session_frame.pack(side="left", padx=(40, 0))

        make_button(
            session_frame, "\u2726 New Session", self._new_session,
            style="muted", tooltip="Reset all boxes to defaults",
        ).pack(side="left", padx=3)
        make_button(
            session_frame, "\u21E9 Save Template", self._save_session,
            style="blue", tooltip="Save current session to JSON file",
        ).pack(side="left", padx=3)
        make_button(
            session_frame, "\u21E7 Load Template", self._load_session,
            style="blue", tooltip="Load session from JSON file",
        ).pack(side="left", padx=3)

        # Right: Stats + Generate
        right_frame = tk.Frame(bar, bg=COLORS["bg_medium"])
        right_frame.pack(side="right")

        # Stats
        stats_frame = tk.Frame(right_frame, bg=COLORS["bg_medium"])
        stats_frame.pack(side="left", padx=(0, 16))

        self.stat_boxes_label = tk.Label(
            stats_frame, text="Boxes: 0/0",
            font=FONTS["body"], bg=COLORS["bg_medium"],
            fg=COLORS["text_secondary"],
        )
        self.stat_boxes_label.pack(side="left", padx=(0, 12))

        self.stat_total_label = tk.Label(
            stats_frame, text="Possible: 0",
            font=FONTS["heading"], bg=COLORS["bg_medium"],
            fg=COLORS["accent_yellow"],
        )
        self.stat_total_label.pack(side="left")

        # Generate button (prominent)
        make_button(
            right_frame, "\u25B6  Generate Dorks", self._generate,
            style="accent", tooltip="Generate dork combinations",
        ).pack(side="right")

    def _build_sidebar(self):
        """Left sidebar: Builder panel with boxes and templates."""
        sidebar = tk.Frame(self.main_pane, bg=COLORS["bg_sidebar"])
        self.main_pane.add(sidebar, minsize=380, width=440)

        # Sidebar header
        hdr = tk.Frame(sidebar, bg=COLORS["bg_sidebar"], pady=6, padx=8)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="\u25A6 Builder",
            font=FONTS["heading"], bg=COLORS["bg_sidebar"],
            fg=COLORS["text_primary"],
        ).pack(side="left")

        self.box_count_label = tk.Label(
            hdr, text="",
            font=FONTS["small"], bg=COLORS["bg_sidebar"],
            fg=COLORS["text_muted"],
        )
        self.box_count_label.pack(side="left", padx=(8, 0))

        make_small_button(
            hdr, "+ Add Box", self._add_box,
            style="green", tooltip="Add a new operator box",
        ).pack(side="right")

        # Scrollable area for operator boxes
        self.box_scroll = ScrollableFrame(
            sidebar, bg=COLORS["bg_sidebar"],
        )
        self.box_scroll.pack(fill="both", expand=True)

        # Template section (accordion)
        self._build_template_section(sidebar)

        # Generation controls
        self._build_gen_controls(sidebar)

    def _build_template_section(self, parent):
        """Collapsible template selector in sidebar."""
        self.tmpl_accordion = AccordionSection(
            parent, "Combination Template",
            bg=COLORS["bg_card"], accent_color=COLORS["accent_yellow"],
            initially_expanded=False, badge_text="Cartesian",
        )
        self.tmpl_accordion.pack(fill="x", padx=4, pady=(4, 0))

        content = self.tmpl_accordion.content

        # Template radio buttons
        self.tmpl_var = tk.IntVar(value=-1)
        r_none = tk.Radiobutton(
            content, text="None (Cartesian Product)",
            variable=self.tmpl_var, value=-1,
            command=self._on_template_changed,
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text_primary"],
            font=FONTS["small"], anchor="w", highlightthickness=0,
        )
        r_none.pack(fill="x", anchor="w")
        ToolTip(r_none, "Every enabled box is combined\nwith every other (full cartesian product).")

        for idx, tmpl in enumerate(self.templates):
            r = tk.Radiobutton(
                content, text=tmpl["short"],
                variable=self.tmpl_var, value=idx,
                command=self._on_template_changed,
                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                selectcolor=COLORS["input_bg"],
                activebackground=COLORS["bg_card"],
                activeforeground=COLORS["text_primary"],
                font=FONTS["small"], anchor="w", highlightthickness=0,
            )
            r.pack(fill="x", anchor="w")
            ToolTip(r, tmpl["description"])

        r_mix = tk.Radiobutton(
            content, text="\u2728 Mix All Templates",
            variable=self.tmpl_var, value=MIX_ALL_TEMPLATE_IDX,
            command=self._on_template_changed,
            bg=COLORS["bg_card"], fg=COLORS["accent_yellow"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["accent_yellow"],
            font=("Segoe UI", 9, "bold"), anchor="w", highlightthickness=0,
        )
        r_mix.pack(fill="x", anchor="w")
        ToolTip(r_mix, "Generate from ALL templates, merge & deduplicate.")

        # Template preview
        self.tmpl_preview = tk.Label(
            content, text="Mode: Full Cartesian Product",
            font=FONTS["mono_sm"], bg=COLORS["input_bg"],
            fg=COLORS["accent_green"], anchor="w", justify="left",
            padx=8, pady=4, wraplength=380,
        )
        self.tmpl_preview.pack(fill="x", pady=(6, 0))

        # Rule toggle
        self.rules_var = tk.BooleanVar(value=True)
        rules_chk = tk.Checkbutton(
            content, text="Apply intelligent filtering rules",
            variable=self.rules_var,
            command=lambda: self.state.dispatch(Action.TOGGLE_RULES),
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
            selectcolor=COLORS["input_bg"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["text_primary"],
            font=FONTS["small"], anchor="w", highlightthickness=0,
        )
        rules_chk.pack(fill="x", anchor="w", pady=(4, 0))
        ToolTip(rules_chk, "Remove redundant/invalid operator combinations\n"
                           "(e.g., filetype: + ext: in same query)")

    def _build_gen_controls(self, parent):
        """Generation count + button at sidebar bottom."""
        gen_frame = tk.Frame(
            parent, bg=COLORS["bg_card"], padx=10, pady=8,
            highlightthickness=1, highlightbackground=COLORS["border"],
        )
        gen_frame.pack(fill="x", padx=4, pady=(4, 4))

        row = tk.Frame(gen_frame, bg=COLORS["bg_card"])
        row.pack(fill="x")

        tk.Label(
            row, text="Count:", font=FONTS["body"],
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
        ).pack(side="left")

        self.gen_count_var = tk.StringVar(value="100")
        self.gen_entry = tk.Entry(
            row, textvariable=self.gen_count_var, width=10,
            bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            insertbackground=COLORS["accent_green"],
            font=FONTS["mono"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent_green"],
        )
        self.gen_entry.pack(side="left", padx=(6, 0))

        make_small_button(
            row, "MAX", self._set_max_count,
            style="yellow", tooltip="Set to maximum",
        ).pack(side="left", padx=(6, 0))

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            gen_frame, variable=self.progress_var, maximum=100,
        )
        # Hidden by default

    def _build_center(self):
        """Center area: Live Preview (top) + Results (bottom)."""
        center = tk.Frame(self.main_pane, bg=COLORS["bg_dark"])
        self.main_pane.add(center, minsize=500)

        # Vertical split: live preview + results
        center_pane = tk.PanedWindow(
            center, orient="vertical",
            bg=COLORS["bg_dark"], sashwidth=5,
            sashrelief="flat", borderwidth=0,
        )
        center_pane.pack(fill="both", expand=True)

        self._build_live_preview(center_pane)
        self._build_results_panel(center_pane)

    def _build_live_preview(self, parent):
        """Live preview pane showing what will be generated."""
        preview_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        parent.add(preview_frame, minsize=120, height=180)

        # Header
        hdr = tk.Frame(preview_frame, bg=COLORS["bg_dark"], pady=4, padx=4)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="\u26A1 Live Preview",
            font=FONTS["heading"], bg=COLORS["bg_dark"],
            fg=COLORS["live_green"],
        ).pack(side="left")

        self.preview_info = tk.Label(
            hdr, text="Shows sample queries that will be generated",
            font=FONTS["small"], bg=COLORS["bg_dark"],
            fg=COLORS["text_muted"],
        )
        self.preview_info.pack(side="left", padx=(10, 0))

        make_small_button(
            hdr, "\u21BB Refresh", self._refresh_preview,
            style="green", tooltip="Refresh preview",
        ).pack(side="right")

        # Preview text area
        self.preview_text = tk.Text(
            preview_frame,
            bg=COLORS["preview_bg"], fg=COLORS["accent_green"],
            font=FONTS["mono_sm"], relief="flat",
            borderwidth=0, highlightthickness=1,
            highlightbackground=COLORS["border"],
            padx=10, pady=6, wrap="none", state="disabled",
            height=6,
        )
        self.preview_text.pack(fill="both", expand=True, padx=4)
        self.preview_text.tag_configure(
            "operator", foreground=COLORS["accent_yellow"],
        )
        self.preview_text.tag_configure(
            "keyword", foreground=COLORS["accent_blue"],
        )
        self.preview_text.tag_configure(
            "sample_num", foreground=COLORS["text_muted"],
        )

    def _build_results_panel(self, parent):
        """Results panel: interactive data grid with search, copy, export."""
        results_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        parent.add(results_frame, minsize=250)

        # Header with counter
        hdr = tk.Frame(results_frame, bg=COLORS["bg_dark"], pady=4, padx=4)
        hdr.pack(fill="x")

        tk.Label(
            hdr, text="\u2263 Results",
            font=FONTS["heading"], bg=COLORS["bg_dark"],
            fg=COLORS["text_primary"],
        ).pack(side="left")

        self.result_count_label = tk.Label(
            hdr, text="0 dorks",
            font=FONTS["counter_sm"], bg=COLORS["bg_dark"],
            fg=COLORS["accent_yellow"],
        )
        self.result_count_label.pack(side="left", padx=(12, 0))

        self.result_stats_label = tk.Label(
            hdr, text="",
            font=FONTS["small"], bg=COLORS["bg_dark"],
            fg=COLORS["text_muted"],
        )
        self.result_stats_label.pack(side="left", padx=(8, 0))

        # Search/filter bar
        search_frame = tk.Frame(
            results_frame, bg=COLORS["bg_card"], padx=8, pady=5,
            highlightthickness=1, highlightbackground=COLORS["border"],
        )
        search_frame.pack(fill="x", padx=4)

        tk.Label(
            search_frame, text="\U0001F50D",
            font=FONTS["body"], bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"],
        ).pack(side="left")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        self.search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            bg=COLORS["input_bg"], fg=COLORS["input_fg"],
            insertbackground=COLORS["accent_green"],
            font=FONTS["mono"], relief="flat",
            highlightthickness=1, highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent_green"],
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(6, 6))
        ToolTip(self.search_entry, "Filter results (case-insensitive)")

        make_small_button(
            search_frame, "A\u2193Z", self._sort_results,
            style="blue", tooltip="Sort alphabetically",
        ).pack(side="left", padx=2)
        make_small_button(
            search_frame, "\u21C5", self._shuffle_results,
            style="blue", tooltip="Shuffle",
        ).pack(side="left", padx=2)
        make_small_button(
            search_frame, "Clear", self._clear_results,
            style="danger", tooltip="Clear results",
        ).pack(side="left", padx=2)

        # Results text area
        text_frame = tk.Frame(results_frame, bg=COLORS["bg_dark"])
        text_frame.pack(fill="both", expand=True, padx=4, pady=(4, 0))

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

        self.output_text.tag_configure(
            "lineno", foreground=COLORS["text_muted"],
        )
        self.output_text.tag_configure(
            "dork", foreground=COLORS["input_fg"],
        )
        self.output_text.tag_configure(
            "highlight",
            background=COLORS["highlight_bg"], foreground="#ffffff",
        )
        self.output_text.tag_configure(
            "op_highlight", foreground=COLORS["accent_yellow"],
        )

        out_scroll = tk.Scrollbar(
            text_frame, command=self.output_text.yview,
            bg=COLORS["scrollbar_bg"], troughcolor=COLORS["bg_dark"],
            activebackground=COLORS["scrollbar_fg"],
        )
        out_scroll.pack(side="right", fill="y")
        self.output_text.configure(yscrollcommand=out_scroll.set)

        h_scroll = tk.Scrollbar(
            results_frame, orient="horizontal",
            command=self.output_text.xview,
            bg=COLORS["scrollbar_bg"], troughcolor=COLORS["bg_dark"],
            activebackground=COLORS["scrollbar_fg"],
        )
        h_scroll.pack(fill="x", padx=4)
        self.output_text.configure(xscrollcommand=h_scroll.set)

        # Action buttons bar
        btn_bar = tk.Frame(
            results_frame, bg=COLORS["bg_card"], padx=10, pady=6,
            highlightthickness=1, highlightbackground=COLORS["border"],
        )
        btn_bar.pack(fill="x", padx=4, pady=(4, 4))

        make_button(
            btn_bar, "\u2398 Copy Selected", self._copy_selected,
            style="blue", tooltip="Copy selected text",
        ).pack(side="left", padx=(0, 4))
        make_button(
            btn_bar, "\u29C9 Copy All", self._copy_all,
            style="blue", tooltip="Copy all dorks to clipboard",
        ).pack(side="left", padx=(0, 4))

        # Export buttons
        export_frame = tk.Frame(btn_bar, bg=COLORS["bg_card"])
        export_frame.pack(side="right")

        make_button(
            export_frame, "\u21E9 TXT",
            lambda: self._export("txt"), style="green",
            tooltip="Export as plain text",
        ).pack(side="left", padx=2)
        make_button(
            export_frame, "\u21E9 CSV",
            lambda: self._export("csv"), style="green",
            tooltip="Export as CSV",
        ).pack(side="left", padx=2)
        make_button(
            export_frame, "\u21E9 JSON",
            lambda: self._export("json"), style="green",
            tooltip="Export as JSON",
        ).pack(side="left", padx=2)

    # ── Default Initialization ──

    def _init_defaults(self):
        """Initialize default boxes from data module."""
        for box_def in DEFAULT_BOXES:
            self.state.dispatch(
                Action.ADD_BOX,
                name=box_def["name"],
                entries=list(box_def["content"]),
                enabled=box_def["enabled"],
            )
        self._rebuild_box_widgets()
        self._update_stats()
        self._refresh_preview()

    # ── State Listeners ──

    def _on_boxes_changed(self):
        self._rebuild_box_widgets()
        self._update_stats()
        self._refresh_preview()

    def _on_stats_changed(self):
        self._update_stats()
        self._refresh_preview()

    def _on_results_changed(self):
        results = self.state.results
        self._display_dorks(results.filtered_dorks)
        count = len(results.filtered_dorks)
        total = len(results.all_dorks)
        if results.search_term and count != total:
            self.result_count_label.configure(
                text=f"{format_number(count)} / {format_number(total)} dorks",
            )
        else:
            self.result_count_label.configure(
                text=f"{format_number(count)} dorks",
            )

        # Show stats
        stats_parts = []
        if results.total_filtered > 0:
            stats_parts.append(f"{results.total_filtered} filtered by rules")
        if results.warnings:
            stats_parts.append(" | ".join(results.warnings))
        self.result_stats_label.configure(text=" | ".join(stats_parts))

    # ── Widget Rebuilding ──

    def _rebuild_box_widgets(self):
        """Rebuild box widgets to match current state."""
        current_uids = {b.uid for b in self.state.boxes}
        widget_uids = set(self.box_widgets.keys())

        # Remove widgets for deleted boxes
        for uid in widget_uids - current_uids:
            self.box_widgets[uid].destroy()
            del self.box_widgets[uid]

        # Create widgets for new boxes
        for box_state in self.state.boxes:
            if box_state.uid not in self.box_widgets:
                w = OperatorBoxWidget(
                    self, self.box_scroll.inner_frame, box_state,
                )
                self.box_widgets[box_state.uid] = w

        # Reorder
        for w in self.box_widgets.values():
            w.frame.pack_forget()
        for box_state in self.state.boxes:
            if box_state.uid in self.box_widgets:
                self.box_widgets[box_state.uid].frame.pack(
                    fill="x", padx=4, pady=3,
                )

    # ── Stats ──

    def _update_stats(self):
        total_boxes = self.state.box_count
        active_boxes = self.state.active_box_count

        self.stat_boxes_label.configure(
            text=f"Boxes: {active_boxes}/{total_boxes}",
        )
        self.box_count_label.configure(
            text=f"({total_boxes}/{MAX_BOXES})",
        )

        # Calculate total possible
        total = self._calc_total()
        self.stat_total_label.configure(
            text=f"Possible: {format_number(total)}",
        )

    def _calc_total(self):
        input_data = self._build_input(count_only=True)
        return self.engine.calculate_total(input_data)

    def _build_input(self, count_only=False):
        """Build a DorkGeneratorInput from current state."""
        entries = self.state.active_entries
        gen = self.state.generation

        if gen.mode == "template":
            idx = gen.active_template_idx
            tmpl = self.templates[idx] if idx is not None and 0 <= idx < len(self.templates) else None
            return DorkGeneratorInput(
                box_entries=entries,
                mode="template",
                template=tmpl,
                requested_count=gen.requested_count if not count_only else 1,
                apply_rules=gen.apply_rules,
            )
        elif gen.mode == "mix_all":
            return DorkGeneratorInput(
                box_entries=entries,
                mode="mix_all",
                templates_all=self.templates,
                requested_count=gen.requested_count if not count_only else 1,
                apply_rules=gen.apply_rules,
            )
        else:
            return DorkGeneratorInput(
                box_entries=entries,
                mode="cartesian",
                requested_count=gen.requested_count if not count_only else 1,
                apply_rules=gen.apply_rules,
            )

    # ── Live Preview ──

    def _refresh_preview(self):
        """Generate a small sample for the live preview."""
        try:
            entries = self.state.active_entries
            if not entries or all(not v for v in entries.values()):
                self._set_preview_text("(Add entries to boxes to see preview)")
                return

            # Generate a small sample (up to 10)
            input_data = self._build_input()
            input_data.requested_count = 10
            input_data.shuffle = True
            input_data.apply_rules = self.state.generation.apply_rules

            result = self.engine.generate(input_data)
            if not result.dorks:
                self._set_preview_text("(No valid combinations with current settings)")
                return

            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")

            for i, dork in enumerate(result.dorks[:10], 1):
                self.preview_text.insert("end", f"  {i:>2}. ", "sample_num")
                # Highlight operators in the dork
                self._insert_highlighted_dork(self.preview_text, dork)
                self.preview_text.insert("end", "\n")

            total = self._calc_total()
            self.preview_info.configure(
                text=f"Sample of {len(result.dorks)} / {format_number(total)} possible",
            )
            self.preview_text.configure(state="disabled")

        except Exception:
            self._set_preview_text("(Preview unavailable)")

    def _insert_highlighted_dork(self, text_widget, dork):
        """Insert a dork string with operator highlighting."""
        parts = dork.split()
        for j, part in enumerate(parts):
            if j > 0:
                text_widget.insert("end", " ")
            if ":" in part and not part.startswith('"'):
                colon_idx = part.index(":")
                op = part[:colon_idx + 1]
                val = part[colon_idx + 1:]
                text_widget.insert("end", op, "operator")
                text_widget.insert("end", val, "keyword")
            elif part.startswith('"') and part.endswith('"'):
                text_widget.insert("end", part, "keyword")
            else:
                text_widget.insert("end", part)

    def _set_preview_text(self, msg):
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", msg)
        self.preview_text.configure(state="disabled")
        self.preview_info.configure(text="")

    # ── Template ──

    def _on_template_changed(self):
        val = self.tmpl_var.get()
        self.state.dispatch(Action.SET_TEMPLATE, idx=val)
        self._update_template_preview()

    def _update_template_preview(self):
        idx = self.state.generation.active_template_idx
        mode = self.state.generation.mode

        if mode == "mix_all":
            lines = [
                "Mode: Mix All Templates",
                "Generates from every template, merges & deduplicates.",
            ]
            for i, tmpl in enumerate(self.templates):
                quoted = set(tmpl.get("quoted", []))
                parts = []
                for seg in tmpl["segments"]:
                    seg_parts = []
                    for bn in seg:
                        display = f"({bn})"
                        if bn in quoted:
                            display = f'"({bn})"'
                        seg_parts.append(display)
                    parts.append("+".join(seg_parts))
                lines.append(f"  T{i + 1}: {'  '.join(parts)}")
            self.tmpl_preview.configure(text="\n".join(lines))
            self.tmpl_accordion.set_badge("Mix All")

        elif mode == "template" and idx is not None and 0 <= idx < len(self.templates):
            tmpl = self.templates[idx]
            quoted = set(tmpl.get("quoted", []))
            parts = []
            for seg in tmpl["segments"]:
                seg_parts = []
                for bn in seg:
                    display = f"({bn})"
                    if bn in quoted:
                        display = f'"({bn})"'
                    seg_parts.append(display)
                parts.append("+".join(seg_parts))
            pattern_str = "  ".join(parts)
            self.tmpl_preview.configure(
                text=f"Pattern: {pattern_str}\n{tmpl['description']}",
            )
            self.tmpl_accordion.set_badge(tmpl["short"])
        else:
            self.tmpl_preview.configure(
                text="Mode: Full Cartesian Product of all enabled boxes",
            )
            self.tmpl_accordion.set_badge("Cartesian")

    # ── Generation ──

    def _generate(self):
        """Main generation action, delegated entirely to DorkGenerator."""
        try:
            requested = int(
                self.gen_count_var.get().strip().replace(",", "")
            )
            if requested <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid Input", "Enter a valid positive number.")
            return

        self.state.dispatch(Action.SET_COUNT, count=requested)

        input_data = self._build_input()
        input_data.requested_count = requested

        # Validate
        ok, msg = self.engine.validate_input(input_data)
        if not ok:
            messagebox.showerror("Validation Error", msg)
            return

        total = self.engine.calculate_total(input_data)
        if total == 0:
            messagebox.showwarning("No Combinations", "No entries in active boxes.")
            return

        if requested > total:
            result = messagebox.askyesno(
                "Exceeds Maximum",
                f"Requested {format_number(requested)} but only "
                f"{format_number(total)} unique exist.\n\n"
                f"Generate all {format_number(total)}?",
            )
            if not result:
                return
            input_data.requested_count = total

        if input_data.requested_count > HUGE_REQUEST_THRESHOLD:
            result = messagebox.askyesno(
                "Large Generation",
                f"Generating {format_number(input_data.requested_count)} "
                f"dorks may take a moment.\n\nContinue?",
            )
            if not result:
                return

        # Show progress
        self.progress.pack(fill="x", pady=(4, 0))
        self.progress_var.set(0)
        self.state.dispatch(Action.SET_GENERATING, value=True)
        self.root.update_idletasks()

        def progress_cb(done, total_req):
            pct = (done / max(total_req, 1)) * 100
            self.progress_var.set(pct)
            self.root.update_idletasks()

        try:
            result = self.engine.generate(input_data, progress_cb)
            self.state.dispatch(
                Action.SET_RESULTS,
                dorks=result.dorks,
                total_possible=result.total_possible,
                total_generated=result.total_generated,
                total_filtered=result.total_filtered,
                warnings=result.warnings,
            )
            self.progress_var.set(100)
            self.root.after(800, lambda: self.progress.pack_forget())

        except Exception as e:
            messagebox.showerror("Generation Error", str(e))
            self.progress.pack_forget()
            self.state.dispatch(Action.SET_GENERATING, value=False)

    # ── Results Display ──

    def _display_dorks(self, dorks):
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")

        if not dorks:
            self.output_text.configure(state="disabled")
            return

        pad = len(str(len(dorks)))
        for i, dork in enumerate(dorks, 1):
            line_num = f"{i:>{pad}}  "
            self.output_text.insert("end", line_num, "lineno")
            self.output_text.insert("end", dork + "\n", "dork")

        self.output_text.configure(state="disabled")

        if self.search_var.get().strip():
            self._highlight_search()

    def _highlight_search(self):
        term = self.search_var.get().strip()
        if not term:
            return
        self.output_text.tag_remove("highlight", "1.0", "end")
        start = "1.0"
        while True:
            pos = self.output_text.search(
                term, start, stopindex="end", nocase=True,
            )
            if not pos:
                break
            end_pos = f"{pos}+{len(term)}c"
            self.output_text.tag_add("highlight", pos, end_pos)
            start = end_pos

    # ── Actions ──

    def _add_box(self):
        if self.state.box_count >= MAX_BOXES:
            messagebox.showwarning("Limit", f"Maximum {MAX_BOXES} boxes.")
            return
        self.state.dispatch(Action.ADD_BOX)

    def _set_max_count(self):
        total = self._calc_total()
        self.gen_count_var.set(str(total))

    def _on_search(self):
        self.state.dispatch(
            Action.SET_SEARCH, term=self.search_var.get(),
        )

    def _sort_results(self):
        self.state.dispatch(Action.SORT_RESULTS)

    def _shuffle_results(self):
        self.state.dispatch(Action.SHUFFLE_RESULTS)

    def _clear_results(self):
        self.state.dispatch(Action.CLEAR_RESULTS)
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
        dorks = self.state.results.filtered_dorks
        if not dorks:
            messagebox.showinfo("Empty", "No dorks to copy.")
            return
        text = "\n".join(dorks)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._flash_status(f"Copied {format_number(len(dorks))} dorks!")

    def _flash_status(self, msg):
        self.result_count_label.configure(text=msg, fg=COLORS["success"])
        count = len(self.state.results.filtered_dorks)
        self.root.after(
            2000,
            lambda: self.result_count_label.configure(
                text=f"{format_number(count)} dorks",
                fg=COLORS["accent_yellow"],
            ),
        )

    def _export(self, fmt):
        dorks = self.state.results.filtered_dorks
        if not dorks:
            messagebox.showinfo("Empty", "No dorks to export.")
            return

        ext_map = {
            "txt": ("Text Files", "*.txt"),
            "csv": ("CSV Files", "*.csv"),
            "json": ("JSON Files", "*.json"),
        }
        filetypes = [ext_map[fmt], ("All Files", "*.*")]
        filepath = filedialog.asksaveasfilename(
            defaultextension=f".{fmt}",
            filetypes=filetypes,
            initialfile=f"dorkforge_export.{fmt}",
            title=f"Export as {fmt.upper()}",
        )
        if not filepath:
            return
        try:
            if fmt == "txt":
                ExportEngine.export_txt(dorks, filepath)
            elif fmt == "csv":
                ExportEngine.export_csv(dorks, filepath)
            elif fmt == "json":
                ExportEngine.export_json(dorks, filepath)
            self._flash_status(f"Exported to {fmt.upper()}!")
            messagebox.showinfo(
                "Export Complete",
                f"Exported {format_number(len(dorks))} dorks to:\n{filepath}",
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed:\n{str(e)}")

    # ── Session Management ──

    def _new_session(self):
        if messagebox.askyesno("New Session", "Reset all boxes to defaults?"):
            self.box_widgets.clear()
            # Clear children of scroll frame
            for w in self.box_scroll.inner_frame.winfo_children():
                w.destroy()

            self.state.dispatch(Action.CLEAR_RESULTS)
            # Rebuild from defaults
            self.state._boxes = []
            self.state._next_uid = 0
            for box_def in DEFAULT_BOXES:
                self.state.dispatch(
                    Action.ADD_BOX,
                    name=box_def["name"],
                    entries=list(box_def["content"]),
                    enabled=box_def["enabled"],
                )
            self.tmpl_var.set(-1)
            self._on_template_changed()
            self.gen_count_var.set("100")
            self.search_var.set("")

    def _save_session(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            initialfile="dorkforge_session.json",
            title="Save Session",
        )
        if not filepath:
            return
        try:
            data = self.state.to_dict()
            data["templates"] = self.templates
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._flash_status("Session saved!")
        except Exception as e:
            messagebox.showerror("Save Error", str(e))

    def _load_session(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Load Session",
        )
        if not filepath:
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Clear current widgets
            for w in self.box_widgets.values():
                w.destroy()
            self.box_widgets.clear()
            for w in self.box_scroll.inner_frame.winfo_children():
                w.destroy()

            self.state.dispatch(Action.CLEAR_RESULTS)
            self.state.dispatch(
                Action.LOAD_SESSION,
                boxes=data.get("boxes", []),
                generation=data.get("generation"),
            )
            if "templates" in data:
                self.templates = data["templates"]
            self.search_var.set("")
            self._flash_status("Session loaded!")
        except Exception as e:
            messagebox.showerror("Load Error", str(e))
