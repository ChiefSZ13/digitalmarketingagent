from pathlib import Path
import json

from marketing_agent.main import create_app


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / "packages" / "contracts" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(create_app().openapi(), indent=2), encoding="utf-8")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()

