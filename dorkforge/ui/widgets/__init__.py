"""
DorkForge - Reusable UI Widgets
=================================

Custom tkinter widgets used across the application.
"""

import tkinter as tk
from dorkforge.utils import COLORS, FONTS, BUTTON_STYLES


# ─────────────────────────────────────────────
# Tooltip
# ─────────────────────────────────────────────
class ToolTip:
    """Hover tooltip for any widget."""

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
            font=FONTS["small"], padx=8, pady=4,
        )
        label.pack()

    def _hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ─────────────────────────────────────────────
# Styled Button
# ─────────────────────────────────────────────
def make_button(parent, text, command, style="accent", width=None,
                tooltip=None, font_key="btn"):
    """Create a styled button with hover effects."""
    bg, hover_bg, fg = BUTTON_STYLES.get(style, BUTTON_STYLES["accent"])
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=hover_bg, activeforeground=fg,
        font=FONTS[font_key], relief="flat", cursor="hand2",
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
    """Create a small button."""
    bg, hover_bg, fg = BUTTON_STYLES.get(style, BUTTON_STYLES["muted"])
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


def make_icon_button(parent, text, command, style="muted", tooltip=None,
                     padx=4, pady=2):
    """Create an icon-sized button."""
    bg, hover_bg, fg = BUTTON_STYLES.get(style, BUTTON_STYLES["muted"])
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=hover_bg, activeforeground=fg,
        font=FONTS["tiny"], relief="flat", cursor="hand2",
        padx=padx, pady=pady, borderwidth=0, highlightthickness=0,
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    if tooltip:
        ToolTip(btn, tooltip)
    return btn


# ─────────────────────────────────────────────
# Scrollable Frame
# ─────────────────────────────────────────────
class ScrollableFrame(tk.Frame):
    """A frame with a vertical scrollbar."""

    def __init__(self, parent, bg=None, **kwargs):
        bg = bg or COLORS["bg_medium"]
        super().__init__(parent, bg=bg, **kwargs)

        self.canvas = tk.Canvas(
            self, bg=bg, highlightthickness=0, borderwidth=0,
        )
        self.scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview,
            bg=COLORS["scrollbar_bg"], troughcolor=bg,
            activebackground=COLORS["scrollbar_fg"],
        )
        self.inner_frame = tk.Frame(self.canvas, bg=bg)

        self.inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor="nw",
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)
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
# Collapsible Accordion Section
# ─────────────────────────────────────────────
class AccordionSection(tk.Frame):
    """A collapsible section with a header and expandable content area.

    Reduces cognitive load by letting users expand only what they need.
    """

    def __init__(self, parent, title, bg=None, accent_color=None,
                 initially_expanded=False, badge_text=None, **kwargs):
        bg = bg or COLORS["bg_card"]
        self._accent = accent_color or COLORS["accent_green"]
        super().__init__(parent, bg=bg, highlightthickness=1,
                         highlightbackground=COLORS["border"], **kwargs)

        self._expanded = initially_expanded

        # Header
        self._header = tk.Frame(self, bg=bg, cursor="hand2")
        self._header.pack(fill="x", padx=8, pady=(6, 2))

        # Arrow indicator
        self._arrow = tk.Label(
            self._header,
            text="\u25BC" if self._expanded else "\u25B6",
            font=FONTS["small"], bg=bg, fg=self._accent,
        )
        self._arrow.pack(side="left", padx=(0, 6))

        # Title
        self._title_label = tk.Label(
            self._header, text=title,
            font=FONTS["section"], bg=bg, fg=self._accent,
        )
        self._title_label.pack(side="left")

        # Badge (item count, etc.)
        if badge_text:
            self._badge = tk.Label(
                self._header, text=badge_text,
                font=FONTS["badge"], bg=COLORS["border"],
                fg=COLORS["text_primary"], padx=6, pady=1,
            )
            self._badge.pack(side="left", padx=(8, 0))
        else:
            self._badge = None

        # Content area
        self._content = tk.Frame(self, bg=bg)
        if self._expanded:
            self._content.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        # Bind click to toggle
        for widget in (self._header, self._arrow, self._title_label):
            widget.bind("<Button-1>", lambda e: self.toggle())

    @property
    def content(self):
        """The inner frame where child widgets go."""
        return self._content

    @property
    def expanded(self):
        return self._expanded

    def toggle(self):
        """Toggle expanded/collapsed state."""
        if self._expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self):
        self._expanded = True
        self._arrow.configure(text="\u25BC")
        self._content.pack(fill="both", expand=True, padx=8, pady=(0, 6))

    def collapse(self):
        self._expanded = False
        self._arrow.configure(text="\u25B6")
        self._content.pack_forget()

    def set_badge(self, text):
        """Update the badge text."""
        if self._badge:
            self._badge.configure(text=text)
        else:
            self._badge = tk.Label(
                self._header, text=text,
                font=FONTS["badge"], bg=COLORS["border"],
                fg=COLORS["text_primary"], padx=6, pady=1,
            )
            self._badge.pack(side="left", padx=(8, 0))


# ─────────────────────────────────────────────
# StatusBadge
# ─────────────────────────────────────────────
class StatusBadge(tk.Label):
    """A small colored badge showing status text."""

    def __init__(self, parent, text="", style="enabled", **kwargs):
        styles = {
            "enabled":  (COLORS["tag_enabled"], COLORS["bg_dark"]),
            "disabled": (COLORS["tag_disabled"], "#ffffff"),
            "warning":  (COLORS["warning"], COLORS["bg_dark"]),
            "success":  (COLORS["success"], "#ffffff"),
            "info":     (COLORS["accent_blue"], "#ffffff"),
        }
        bg, fg = styles.get(style, styles["enabled"])
        super().__init__(
            parent, text=text,
            font=FONTS["badge"], bg=bg, fg=fg,
            padx=6, pady=1, **kwargs,
        )

    def set_style(self, text, style="enabled"):
        styles = {
            "enabled":  (COLORS["tag_enabled"], COLORS["bg_dark"]),
            "disabled": (COLORS["tag_disabled"], "#ffffff"),
            "warning":  (COLORS["warning"], COLORS["bg_dark"]),
            "success":  (COLORS["success"], "#ffffff"),
            "info":     (COLORS["accent_blue"], "#ffffff"),
        }
        bg, fg = styles.get(style, styles["enabled"])
        self.configure(text=text, bg=bg, fg=fg)
