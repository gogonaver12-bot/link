#!/usr/bin/env bash
# 하루 1회 실행: 성과수집 -> AI 피드백/새 대본 -> 아직 안 만든 대본 렌더 -> 업로드
set -e
cd "$(dirname "$0")"
[ -f client_secret.json ] && [ -f uploads.json ] && python upload.py --stats || true
python feedback.py --n "${N:-3}"
for s in scripts/*.json; do
  id=$(basename "$s" .json)
  [ -f "out/$id.mp4" ] && continue
  python make_short.py "$s"
  [ -f client_secret.json ] && python upload.py "out/$id.mp4" ${PRIVATE:+--private}
done
