#!/usr/bin/env python3
"""
Pure-Python i18n helper: extracts messages (like `makemessages -l fa`) and compiles .po -> .mo
No GNU gettext binaries required.

Limitations vs. Django:
- Template parsing is heuristic (handles {% trans %} and {% blocktrans %} basic cases).
- Python extraction handles common gettext names and literal strings.
- Context-aware plurals are kept simple.

Requires: polib
    pip install polib
"""

import os
import re
import ast
import sys
from pathlib import Path
import polib

# --- CONFIG ---
BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIRS = [BASE_DIR]  # where to scan
LOCALE_DIR = BASE_DIR / "locale"
LANG = "fa"
PO_PATH = LOCALE_DIR / LANG / "LC_MESSAGES" / "django.po"
MO_PATH = LOCALE_DIR / LANG / "LC_MESSAGES" / "django.mo"

# Directories/files to ignore while scanning
IGNORE_DIRS = {
    ".git", ".hg", ".svn", "__pycache__", "venv", ".venv", "env", ".env",
    "node_modules", "static", "media", "dist", "build", "migrations",
    "site-packages", ".pytest_cache", ".mypy_cache",
    "locale"  # don't scan locales for strings
}
IGNORE_FILE_EXT = {
    ".mo", ".po", ".pyc", ".pyo", ".min.js", ".map", ".svg", ".png",
    ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".pdf", ".zip", ".gz"
}

# --- Utilities ---

def iter_source_files():
    for root in SOURCE_DIRS:
        for dirpath, dirnames, filenames in os.walk(root):
            # prune ignored dirs
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in IGNORE_FILE_EXT:
                    continue
                full = Path(dirpath) / filename
                # only .py and template-like files
                if ext == ".py" or ext in {".html", ".txt"}:
                    yield full

def clean_blocktrans_text(s: str) -> str:
    """Remove template variables/tags from blocktrans body."""
    # Remove {{ ... }} and {% ... %}
    s = re.sub(r"\{\{.*?\}\}", "", s, flags=re.S)
    s = re.sub(r"\{%.+?%\}", "", s, flags=re.S)
    # Collapse whitespace
    s = " ".join(s.split())
    return s.strip()

# --- Python extractor via AST ---

GETTEXT_NAMES_1 = {"_", "gettext", "gettext_lazy", "ugettext", "ugettext_lazy"}
GETTEXT_NAMES_N = {"ngettext", "ungettext"}
GETTEXT_NAMES_P = {"pgettext"}           # pgettext(context, message)
GETTEXT_NAMES_NP = {"npgettext"}         # npgettext(context, singular, plural, n)

def extract_from_python(path: Path) -> set[str]:
    msgs = set()
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # try fallback encodings if needed
        try:
            src = path.read_text(encoding="utf-16")
        except Exception:
            return msgs

    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return msgs

    class V(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call):
            fn = node.func
            name = None
            if isinstance(fn, ast.Name):
                name = fn.id
            elif isinstance(fn, ast.Attribute):
                name = fn.attr

            def const_str(val):
                # Py3.8+ unified: strings are ast.Constant
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    return val.value
                return None

            if name in GETTEXT_NAMES_1 and node.args:
                s = const_str(node.args[0])
                if s:
                    msgs.add(s)

            elif name in GETTEXT_NAMES_N and len(node.args) >= 2:
                s = const_str(node.args[0])
                p = const_str(node.args[1])
                if s: msgs.add(s)
                if p: msgs.add(p)

            elif name in GETTEXT_NAMES_P and len(node.args) >= 2:
                # pgettext(context, message)
                m = const_str(node.args[1])
                if m: msgs.add(m)

            elif name in GETTEXT_NAMES_NP and len(node.args) >= 3:
                # npgettext(context, singular, plural, n)
                s = const_str(node.args[1])
                p = const_str(node.args[2])
                if s: msgs.add(s)
                if p: msgs.add(p)

            self.generic_visit(node)

    V().visit(tree)
    return msgs

# --- Template extractor via regex ---

# {% trans "Hello" %} or {% trans 'Hello' %}
TRANS_TAG_RE = re.compile(r"\{\%\s*trans\s+(['\"])(.+?)\1\s*\%\}", re.S)

# {% blocktrans %} ... {% endblocktrans %}
BLOCK_TRANS_RE = re.compile(r"\{\%\s*blocktrans.*?\%\}(.*?)\{\%\s*endblocktrans\s*\%\}", re.S)

def extract_from_template(path: Path) -> set[str]:
    msgs = set()
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            src = path.read_text(encoding="utf-16")
        except Exception:
            return msgs

    # {% trans "..." %}
    for m in TRANS_TAG_RE.finditer(src):
        msg = m.group(2).strip()
        if msg:
            msgs.add(msg)

    # {% blocktrans %}...{% endblocktrans %}
    for m in BLOCK_TRANS_RE.finditer(src):
        body = clean_blocktrans_text(m.group(1))
        if body:
            msgs.add(body)

    return msgs

# --- PO merging / compiling ---

def ensure_po():
    PO_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PO_PATH.exists():
        po = polib.POFile()
        po.metadata = {
            'Project-Id-Version': 'messages',
            'MIME-Version': '1.0',
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Transfer-Encoding': '8bit',
            'Language': LANG,
        }
        po.save(PO_PATH)

def update_po_with_messages(all_msgs: set[str]):
    po = polib.pofile(str(PO_PATH))
    existing_ids = {e.msgid for e in po}

    # Add new entries
    added = 0
    for msg in sorted(all_msgs):
        if msg not in existing_ids:
            entry = polib.POEntry(msgid=msg, msgstr="")
            po.append(entry)
            added += 1

    # Optionally mark removed entries obsolete (kept here)
    # If you want to mark missing ones as obsolete:
    # for e in list(po):
    #     if e.msgid not in all_msgs:
    #         e.obsolete = True

    if added:
        print(f"📝 Added {added} new msgids.")
    else:
        print("✅ No new msgids.")

    po.save(PO_PATH)
    return po

def compile_mo():
    po = polib.pofile(str(PO_PATH))
    po.save_as_mofile(str(MO_PATH))
    print(f"📦 Compiled -> {MO_PATH}")

# --- Main ---

def main():
    print("🔎 Scanning source for translatable strings...")
    all_msgs = set()
    for path in iter_source_files():
        ext = path.suffix.lower()
        if ext == ".py":
            all_msgs |= extract_from_python(path)
        elif ext in {".html", ".txt"}:
            all_msgs |= extract_from_template(path)

    print(f"Found {len(all_msgs)} unique msgids.")
    ensure_po()
    update_po_with_messages(all_msgs)
    compile_mo()
    print("✅ Done.")

if __name__ == "__main__":
    sys.exit(main())
