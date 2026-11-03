"""Writes the API contract (OpenAPI) to openapi.json, the versioned single source of truth.

    python scripts/export_openapi.py          writes openapi.json
    python scripts/export_openapi.py --check  fails if openapi.json is not up to date

It never connects to the real database: the app is imported with an in-memory SQLite.
The front generates its types and client from this file (npm run gen:api).
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "openapi.json"

# Before importing the app: never touch Neon, never send emails, never call the AI provider
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["EMAIL_BACKEND"] = "memory"
os.environ.setdefault("SECRET_KEY", "solo-para-exportar-el-contrato-no-es-una-clave-real")
sys.path.insert(0, str(ROOT))


def current_contract() -> str:
    from main import app

    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    contract = current_contract()
    if "--check" in sys.argv:
        saved = CONTRACT.read_text(encoding="utf-8") if CONTRACT.exists() else ""
        if saved != contract:
            print("openapi.json está desactualizado: corre python scripts/export_openapi.py")
            return 1
        print("openapi.json está al día")
        return 0
    CONTRACT.write_text(contract, encoding="utf-8", newline="\n")
    print(f"Contrato escrito en {CONTRACT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
