#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams


def normalize_collection_name(domain_name: str) -> str:
    s = (domain_name or "").strip().replace(" ", "_")
    s = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in s)
    return f"med_{s.lower()}" if s else "med_all"


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 120) -> list[str]:
    text = " ".join((text or "").split())
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def tokenize(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z가-힣]+", (text or "").lower())


def hashed_embedding(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    for token in tokenize(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "big") % dim
        sign = -1.0 if digest[4] % 2 else 1.0
        weight = 1.0 + (digest[5] / 255.0)
        vec[idx] += sign * weight

    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def iter_points(docs_path: Path, dim: int) -> Iterable[tuple[str, PointStruct]]:
    point_id = 1
    with docs_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            chunks = chunk_text(row.get("text", ""))
            domain_name = str(row.get("domain_name") or "unknown")
            collection_name = normalize_collection_name(domain_name)
            for chunk_idx, chunk in enumerate(chunks):
                payload = {
                    "doc_id": str(row.get("doc_id") or "unknown"),
                    "domain_name": domain_name,
                    "source_spec": row.get("source_spec"),
                    "creation_year": row.get("creation_year"),
                    "chunk_idx": chunk_idx,
                    "text": chunk,
                }
                yield collection_name, PointStruct(
                    id=point_id,
                    vector=hashed_embedding(chunk, dim),
                    payload=payload,
                )
                point_id += 1


def ensure_collection(client: QdrantClient, name: str, dim: int) -> None:
    collections = {c.name for c in client.get_collections().collections}
    if name in collections:
        return
    client.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", required=True, help="documents.jsonl path")
    parser.add_argument("--qdrant-url", default="http://localhost:6333", help="Qdrant URL")
    parser.add_argument("--dim", type=int, default=384, help="embedding dimension")
    parser.add_argument("--batch-size", type=int, default=64, help="upsert batch size")
    args = parser.parse_args()

    docs_path = Path(args.docs).expanduser().resolve()
    if not docs_path.exists():
        raise SystemExit(f"[ERR] documents file not found: {docs_path}")

    client = QdrantClient(url=args.qdrant_url)

    grouped: dict[str, list[PointStruct]] = {}
    counts: dict[str, int] = {}

    def flush(collection_name: str) -> None:
        points = grouped.get(collection_name) or []
        if not points:
            return
        ensure_collection(client, collection_name, args.dim)
        client.upsert(collection_name=collection_name, points=points, wait=True)
        counts[collection_name] = counts.get(collection_name, 0) + len(points)
        grouped[collection_name] = []

    for collection_name, point in iter_points(docs_path, args.dim):
        grouped.setdefault(collection_name, []).append(point)
        grouped.setdefault("med_all", []).append(
            PointStruct(id=10_000_000 + point.id, vector=point.vector, payload=point.payload)
        )
        if len(grouped[collection_name]) >= args.batch_size:
            flush(collection_name)
        if len(grouped["med_all"]) >= args.batch_size:
            flush("med_all")

    for collection_name in list(grouped):
        flush(collection_name)

    total = sum(counts.values())
    print(f"[OK] indexed total points: {total}")
    for name in sorted(counts):
        print(f"[OK] {name}: {counts[name]}")


if __name__ == "__main__":
    main()
