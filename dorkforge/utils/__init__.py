"""
DorkForge - Styling & Utilities
=================================

Centralized color palette, font definitions, and shared utility functions.
All visual constants are defined here so themes can be changed in one place.
"""

# ─────────────────────────────────────────────
# Color Palette
# ─────────────────────────────────────────────
COLORS = {
    "bg_dark":       "#1a1a2e",
    "bg_medium":     "#16213e",
    "bg_light":      "#0f3460",
    "bg_card":       "#1e2a4a",
    "bg_sidebar":    "#141c30",
    "accent":        "#e94560",
    "accent_hover":  "#ff6b81",
    "accent_green":  "#00d2d3",
    "accent_yellow": "#feca57",
    "accent_blue":   "#54a0ff",
    "accent_purple": "#a55eea",
    "text_primary":  "#eaf0fb",
    "text_secondary":"#8899aa",
    "text_muted":    "#556677",
    "border":        "#2a3a5e",
    "border_light":  "#3a4a6e",
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
    "highlight_bg":  "#2a4a8e",
    "hover_row":     "#1e3a6e",
    "selected_row":  "#2a4a7e",
    "preview_bg":    "#0a1628",
    "live_green":    "#00ff88",
}

# ─────────────────────────────────────────────
# Font Definitions
# ─────────────────────────────────────────────
FONTS = {
    "title":       ("Segoe UI", 16, "bold"),
    "subtitle":    ("Segoe UI", 12),
    "heading":     ("Segoe UI", 11, "bold"),
    "heading_sm":  ("Segoe UI", 10, "bold"),
    "body":        ("Segoe UI", 10),
    "small":       ("Segoe UI", 9),
    "tiny":        ("Segoe UI", 8),
    "mono":        ("Consolas", 10),
    "mono_sm":     ("Consolas", 9),
    "mono_lg":     ("Consolas", 11),
    "counter":     ("Segoe UI", 20, "bold"),
    "counter_sm":  ("Segoe UI", 14, "bold"),
    "btn":         ("Segoe UI", 10, "bold"),
    "btn_sm":      ("Segoe UI", 9),
    "section":     ("Segoe UI", 10, "bold"),
    "badge":       ("Segoe UI", 8, "bold"),
}

# ─────────────────────────────────────────────
# Style Presets for Buttons
# ─────────────────────────────────────────────
BUTTON_STYLES = {
    "accent":  (COLORS["accent"], COLORS["accent_hover"], "#ffffff"),
    "green":   (COLORS["accent_green"], "#33e0e0", COLORS["bg_dark"]),
    "blue":    (COLORS["accent_blue"], "#7ab8ff", "#ffffff"),
    "yellow":  (COLORS["accent_yellow"], "#ffe07a", COLORS["bg_dark"]),
    "purple":  (COLORS["accent_purple"], "#c084fc", "#ffffff"),
    "muted":   (COLORS["border"], COLORS["bg_light"], COLORS["text_primary"]),
    "danger":  (COLORS["error"], "#ff6b6b", "#ffffff"),
    "success": (COLORS["success"], "#34d399", "#ffffff"),
}


def format_number(n):
    """Format a number with thousands separators."""
    return f"{n:,}"
