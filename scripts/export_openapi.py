import json
import subprocess
from pathlib import Path

from stepg_api.main import app


def main() -> None:
    schema = app.openapi()
    output_path = Path(__file__).parent.parent / "docs" / "api" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    new_content = json.dumps(schema, sort_keys=True, indent=2) + "\n"

    if output_path.exists() and output_path.read_text(encoding="utf-8") == new_content:
        return

    output_path.write_text(new_content, encoding="utf-8")
    # noqa rationale: list args (no shell injection), git resolved via PATH (portable across dev envs)
    subprocess.run(["git", "add", str(output_path)], check=True)  # noqa: S603, S607


if __name__ == "__main__":
    main()
