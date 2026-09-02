"""Static V1/V2 boundary audit helper.

Usage from the backend root:
    python tools/audit_v1_v2.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "app"
V1_ROUTERS = {"auth", "billing", "export", "history", "industries", "invoice", "stripe_webhook", "upload"}

for path in sorted((ROOT / "models").glob("*.py")):
    if path.name != "__init__.py":
        print(f"V1_MODEL {path.relative_to(ROOT.parent)}")

for path in sorted((ROOT / "routers").glob("*.py")):
    if path.stem in V1_ROUTERS:
        for method, route in re.findall(r"@router\.(get|post|put|patch|delete)\(([^\n]+)", path.read_text(errors="ignore")):
            print(f"V1_ROUTE {method.upper()} {route.strip()}")

print("V2_SERVICE_RAW_DB_CHECK")
for path in sorted((ROOT / "services").rglob("*.py")):
    text = path.read_text(errors="ignore")
    if re.search(r"\bself\.db\.table\(", text):
        print(f"RAW_DB {path.relative_to(ROOT.parent)}")
