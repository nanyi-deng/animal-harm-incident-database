"""Generate the self-contained audit tool by injecting items JSON into the template.

Uses str.replace against a literal placeholder token, not re.sub -- avoids
the backslash-reinterpretation trap re.sub has with string replacements.

Run: python3 pipeline/generate_audit_tool.py
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
TEMPLATE = HERE / "audit_tool_template.html"
ITEMS = HERE / "audit_tool_items.json"
OUT = HERE / "gold_standard_audit_tool.html"


def main():
    items = json.loads(ITEMS.read_text(encoding="utf-8"))
    template = TEMPLATE.read_text(encoding="utf-8")
    items_json = json.dumps(items, ensure_ascii=False)
    html = template.replace("__ITEMS_JSON__", items_json)
    OUT.write_text(html, encoding="utf-8")
    print(f"Generated {OUT} ({len(html):,} bytes, {len(items)} items embedded)")


if __name__ == "__main__":
    main()
