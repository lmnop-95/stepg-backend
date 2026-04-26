import json
import sys
from pathlib import Path

from stepg_api.main import app


def main() -> int:
    schema = app.openapi()
    output_path = Path(__file__).parent.parent / "docs" / "api" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_content = json.dumps(schema, sort_keys=True, indent=2) + "\n"

    if output_path.exists() and output_path.read_text(encoding="utf-8") == new_content:
        return 0

    output_path.write_text(new_content, encoding="utf-8")
    print(
        f"Updated {output_path.relative_to(Path.cwd())} — re-stage and commit again.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
