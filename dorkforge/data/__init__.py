"""
DorkForge - Default Data Sets
==============================

Contains structured default data for operators, keywords (grouped by
sub-category), file types, and combination templates. This data is
decoupled from UI and engine, making it easy to extend.
"""

# ─────────────────────────────────────────────
# Google Dork Operators
# ─────────────────────────────────────────────
OPERATORS = {
    "Search Operators": {
        "description": "Core Google search operators for targeting content",
        "items": [
            {"value": "intitle:", "label": "intitle:", "description": "Page title contains term"},
            {"value": "allintitle:", "label": "allintitle:", "description": "Title contains ALL terms"},
            {"value": "inurl:", "label": "inurl:", "description": "URL contains term"},
            {"value": "allinurl:", "label": "allinurl:", "description": "URL contains ALL terms"},
            {"value": "intext:", "label": "intext:", "description": "Body text contains term"},
            {"value": "allintext:", "label": "allintext:", "description": "Body contains ALL terms"},
            {"value": "site:", "label": "site:", "description": "Restrict to specific domain"},
        ],
    },
    "File & Cache Operators": {
        "description": "Operators for file types and cached content",
        "items": [
            {"value": "filetype:", "label": "filetype:", "description": "Specific file extension"},
            {"value": "ext:", "label": "ext:", "description": "File extension (alias for filetype)"},
            {"value": "cache:", "label": "cache:", "description": "Google cached version of page"},
        ],
    },
    "Advanced Operators": {
        "description": "Specialized operators for advanced searches",
        "items": [
            {"value": "link:", "label": "link:", "description": "Pages linking to URL"},
            {"value": "related:", "label": "related:", "description": "Pages similar to URL"},
            {"value": "info:", "label": "info:", "description": "Information about URL"},
            {"value": "define:", "label": "define:", "description": "Definition of term"},
        ],
    },
}

# ─────────────────────────────────────────────
# Keywords (grouped by category)
# ─────────────────────────────────────────────
KEYWORDS = {
    "Credentials": {
        "description": "Terms related to authentication and credentials",
        "items": [
            "login", "password", "username", "admin", "auth",
            "credential", "passwd", "secret", "token", "api_key",
            "apikey", "access_token", "private_key", "ssh_key",
        ],
    },
    "Documents & Data": {
        "description": "Terms for finding exposed documents",
        "items": [
            "confidential", "internal", "private", "restricted",
            "budget", "salary", "invoice", "report", "backup",
            "database", "dump", "export", "spreadsheet",
        ],
    },
    "Infrastructure": {
        "description": "Terms for finding exposed infrastructure",
        "items": [
            "dashboard", "admin panel", "control panel", "cpanel",
            "phpmyadmin", "webmail", "server-status", "server-info",
            "index of", "parent directory", "directory listing",
        ],
    },
    "Configuration": {
        "description": "Terms for finding configuration files",
        "items": [
            "config", "configuration", "setup", "install",
            "env", ".env", "wp-config", "database.yml",
            "settings", "application.properties",
        ],
    },
    "Error Pages": {
        "description": "Terms for finding error/debug pages",
        "items": [
            "error", "warning", "exception", "stack trace",
            "debug", "traceback", "fatal error", "syntax error",
            "mysql error", "sql syntax",
        ],
    },
}

# ─────────────────────────────────────────────
# File Types (grouped by category)
# ─────────────────────────────────────────────
FILE_TYPES = {
    "Documents": {
        "description": "Common document formats",
        "items": ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "odt", "rtf"],
    },
    "Web Files": {
        "description": "Web application files",
        "items": ["php", "asp", "aspx", "jsp", "html", "htm", "xml", "json"],
    },
    "Data Files": {
        "description": "Data and database files",
        "items": ["sql", "csv", "log", "txt", "bak", "db", "mdb", "sqlite"],
    },
    "Configuration": {
        "description": "Configuration files",
        "items": ["conf", "cfg", "ini", "yml", "yaml", "env", "properties", "xml"],
    },
    "Archives": {
        "description": "Compressed and archive files",
        "items": ["zip", "tar", "gz", "rar", "7z", "bz2"],
    },
}

# ─────────────────────────────────────────────
# Operator Rules (for intelligent combinations)
# ─────────────────────────────────────────────
OPERATOR_RULES = {
    # Mutually exclusive operators (cannot appear together)
    "mutually_exclusive": [
        {"filetype:", "ext:"},
        {"intitle:", "allintitle:"},
        {"inurl:", "allinurl:"},
        {"intext:", "allintext:"},
    ],
    # Operators that don't make sense together
    "conflicting_pairs": [
        ("intitle:", "inurl:"),   # same keyword rarely in both title and url
    ],
    # Operators that require a value (not standalone)
    "requires_value": [
        "intitle:", "allintitle:", "inurl:", "allinurl:",
        "intext:", "allintext:", "site:", "filetype:", "ext:",
        "cache:", "link:", "related:", "info:", "define:",
    ],
    # Operators that take a domain/URL, not a keyword
    "domain_operators": ["site:", "cache:", "link:", "related:", "info:"],
    # File type operators
    "filetype_operators": ["filetype:", "ext:"],
}

# ─────────────────────────────────────────────
# Combination Templates
# ─────────────────────────────────────────────
DEFAULT_TEMPLATES = [
    {
        "name": "Operator + Keyword",
        "short": "T1: Op+Kw  Op+Param",
        "description": "(operator)(keyword) (operator)(parameter)\n"
                       "Example: intitle:login intitle:admin.php",
        "segments": [
            ["Search Operator", "Keyword"],
            ["Search Operator", "Page Parameters"],
        ],
        "quoted": [],
    },
    {
        "name": "Site + Keyword, Filetype + Page",
        "short": "T2: Site+Kw  File+Page",
        "description": "(operator)(keyword) (page type)(parameter)\n"
                       "Example: site:example.com login filetype:php admin",
        "segments": [
            ["Search Operator", "Keyword"],
            ["Page Type", "Page Parameters"],
        ],
        "quoted": [],
    },
    {
        "name": "Quoted Keywords",
        "short": 'T3: "Kw"  "Param"',
        "description": '"(keyword)" "(parameter)"\n'
                       'Example: "login" "admin.php"',
        "segments": [
            ["Keyword"],
            ["Page Parameters"],
        ],
        "quoted": ["Keyword", "Page Parameters"],
    },
    {
        "name": "Quoted Keyword + Filetype",
        "short": 'T4: "Kw"  File+Page',
        "description": '"(keyword)" (filetype)(page type)\n'
                       'Example: "admin panel" filetype:php login',
        "segments": [
            ["Keyword"],
            ["Page Type", "Page Parameters"],
        ],
        "quoted": ["Keyword"],
    },
]

# ─────────────────────────────────────────────
# Default Box Configuration
# ─────────────────────────────────────────────
DEFAULT_BOXES = [
    {
        "name": "Search Operator",
        "content": ["site:example.com", "intitle:", "inurl:", "intext:"],
        "enabled": True,
    },
    {
        "name": "Keyword",
        "content": ["login", "admin panel", "dashboard"],
        "enabled": True,
    },
    {
        "name": "Page Type",
        "content": ["filetype:php", "filetype:asp", "filetype:html"],
        "enabled": True,
    },
    {
        "name": "Page Parameters",
        "content": ["admin.php", "login.asp", "index.html"],
        "enabled": True,
    },
]

# ─────────────────────────────────────────────
# Application Constants
# ─────────────────────────────────────────────
APP_TITLE = "DorkForge"
APP_VERSION = "2.0.0"
MIN_BOXES = 2
MAX_BOXES = 20
HUGE_REQUEST_THRESHOLD = 100_000
MIX_ALL_TEMPLATE_IDX = -2
