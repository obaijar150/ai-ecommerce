#!/usr/bin/env python
import json
from pathlib import Path


def validate_synthetic(path: Path) -> bool:
    data = json.load(path.open())
    assert "interactions" in data
    assert "items" in data
    assert len(data["items"]) > 0
    for _k, item in data["items"].items():
        assert "text" in item and item["text"]
    assert len(data["interactions"]) > 0
    for i in data["interactions"][:5]:
        assert "user_id" in i and "item_id" in i
    return True


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        validate_synthetic(Path(p))
    print("ok")
