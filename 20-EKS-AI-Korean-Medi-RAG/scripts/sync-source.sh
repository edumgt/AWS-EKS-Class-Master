#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/AI-Korean-Medi-RAG"
  exit 1
fi

SRC_DIR="$(cd "$1" && pwd)"
CHAPTER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST_DIR="${CHAPTER_DIR}/source"

for required in api web scripts data requirements.txt; do
  if [[ ! -e "${SRC_DIR}/${required}" ]]; then
    echo "Missing ${required} in ${SRC_DIR}"
    exit 1
  fi
done

rm -rf "${DST_DIR}"
mkdir -p "${DST_DIR}"

cp -r "${SRC_DIR}/api" "${DST_DIR}/api"
cp -r "${SRC_DIR}/web" "${DST_DIR}/web"
cp -r "${SRC_DIR}/scripts" "${DST_DIR}/scripts"
cp -r "${SRC_DIR}/data" "${DST_DIR}/data"
cp "${SRC_DIR}/requirements.txt" "${DST_DIR}/requirements.txt"

echo "Synced AI-Korean-Medi-RAG source into ${DST_DIR}"
