from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.llm import check_llm_status


def main() -> int:
    status = check_llm_status()
    provider = status.get("provider", "unknown")
    model = status.get("model", "unknown")
    print(f"Provider: {provider}")
    print(f"Model: {model}")
    print(f"Status: {status.get('status', 'unknown')}")
    print(status.get("message", ""))
    if provider == "ollama" and status.get("status") == "missing_model":
        print(f"Install it with: ollama pull {model}")
    return 0 if status.get("status") == "available" else 1


if __name__ == "__main__":
    raise SystemExit(main())
