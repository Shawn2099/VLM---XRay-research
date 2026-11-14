#!/usr/bin/env bash
# Switch the active chest-X-ray backend on host port 8000.
# Only one model runs at a time: both need most of the 24 GB vGPU.
#
#   bash /home/iccc/switch.sh cxr       # ECOFRI/CXR-LLAVA-v2  (cxr-llava:1.5)
#   bash /home/iccc/switch.sh medgemma  # google/medgemma-1.5-4b-it (medgemma:1.0)
set -euo pipefail

TARGET="${1:-cxr}"
ROOT="/home/iccc"
KEY_FILE="$ROOT/cxr-llava/deploy/api.key"
HOST_PORT="${HOST_PORT:-8000}"

die() { echo "ERROR: $*" >&2; exit 1; }

[ -s "$KEY_FILE" ] || die "API key not found: $KEY_FILE"
KEY="$(cat "$KEY_FILE")"

case "$TARGET" in
    cxr)
        IMAGE="cxr-llava:1.5"
        NAME="cxr-llava"
        MODEL_HOST="$ROOT/cxr-llava/model"
        MODEL_CONT="/models/cxr-llava"
        CONTAINER_PORT=8000
        ;;
    medgemma)
        IMAGE="medgemma:1.0"
        NAME="medgemma"
        MODEL_HOST="$ROOT/models/medgemma-1.5-4b-it"
        MODEL_CONT="/models/medgemma-1.5-4b-it"
        CONTAINER_PORT=8001
        ;;
    *)
        die "usage: $0 {cxr|medgemma}"
        ;;
esac

[ -d "$MODEL_HOST" ] || die "model directory not found: $MODEL_HOST"
docker image inspect "$IMAGE" >/dev/null 2>&1 || die "image not found: $IMAGE"

echo "== stopping active backend"
docker rm -f cxr-llava medgemma >/dev/null 2>&1 || true

echo "== starting $NAME ($IMAGE) -> 0.0.0.0:$HOST_PORT"
docker run -d --name "$NAME" \
    --restart unless-stopped \
    --gpus all \
    --security-opt no-new-privileges \
    --cap-drop ALL \
    --tmpfs /tmp:rw,size=2g,mode=1777 \
    -v "$MODEL_HOST":"$MODEL_CONT":ro \
    -p "$HOST_PORT":"$CONTAINER_PORT" \
    -e MODEL_DIR="$MODEL_CONT" \
    -e CXR_API_KEY="$KEY" \
    -e CXR_CORS_ORIGINS="${CXR_CORS_ORIGINS:-*}" \
    "$IMAGE" >/dev/null

echo "== waiting for health (model load can take a minute)"
for _ in $(seq 1 120); do
    if curl -fsS "http://127.0.0.1:$HOST_PORT/health" >/tmp/active_health.json 2>/dev/null; then
        cat /tmp/active_health.json
        echo
        echo "ACTIVE: $TARGET"
        curl -fsS "http://127.0.0.1:$HOST_PORT/config" 2>/dev/null || true
        echo
        exit 0
    fi
    sleep 2
done

echo "== backend did not become healthy; last logs:" >&2
docker logs --tail 100 "$NAME" >&2 || true
exit 1
