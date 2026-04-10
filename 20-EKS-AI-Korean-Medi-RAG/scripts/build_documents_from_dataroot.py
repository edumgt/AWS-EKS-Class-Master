#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def clean_domain_name(name: str) -> str:
    return re.sub(r"^\d+\.", "", name).strip()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, help="DATA_ROOT path")
    parser.add_argument("--output", required=True, help="documents.jsonl output path")
    args = parser.parse_args()

    data_root = Path(args.data_root).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    source_root = data_root / "01.원천데이터"
    if not source_root.exists():
      raise SystemExit(f"[ERR] source root not found: {source_root}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8") as out:
        for domain_dir in sorted(path for path in source_root.iterdir() if path.is_dir()):
            domain_name = clean_domain_name(domain_dir.name)
            for txt_path in sorted(domain_dir.glob("*.txt")):
                text = clean_text(txt_path.read_text(encoding="utf-8", errors="ignore"))
                if not text:
                    continue

                row = {
                    "doc_id": txt_path.stem,
                    "domain_name": domain_name,
                    "source_spec": str(txt_path.relative_to(data_root)),
                    "creation_year": None,
                    "text": text,
                }
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1

    print(f"[OK] wrote {count} documents")
    print(f"[OK] output: {output_path}")


if __name__ == "__main__":
    main()
