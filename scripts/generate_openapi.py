"""Generate docs/openapi.json from current Flask routes.

Usage:
    python scripts/generate_openapi.py
    python scripts/generate_openapi.py --output docs/openapi.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main():
    parser = argparse.ArgumentParser(description="Generate OpenAPI spec from Flask routes")
    parser.add_argument("--output", default="docs/openapi.json", help="Output path")
    args = parser.parse_args()

    from app import create_app
    from app.presentation.api.openapi_setup import build_spec

    app = create_app()
    spec = build_spec(app)
    spec_dict = spec.to_dict()

    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec_dict, indent=2, sort_keys=True, ensure_ascii=False))
    print(f"OpenAPI spec written to {output_path}")
    print(f"Paths: {len(spec_dict.get('paths', {}))}")


if __name__ == "__main__":
    main()
