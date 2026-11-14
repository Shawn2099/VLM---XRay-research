#!/usr/bin/env bash
# Build and start the CXR-LLaVA service on icccserver.  No internet is needed:
# the base image is already on the host and all Python wheels are vendored.
set -euo pipefail

ROOT="${1:-/home/iccc/cxr-llava}"
MODEL_DIR="$ROOT/model"
DEPLOY_DIR="$ROOT/deploy"
IMAGE="cxr-llava:1.5"
NAME="cxr-llava"
PORT="${PORT:-8000}"
BIND_IP="${BIND_IP:-127.0.0.1}"          # 127.0.0.1 = tunnel only, 0.0.0.0 = LAN
REQUIRE_KEY="${REQUIRE_KEY:-0}"          # 1 = generate/use deploy/api.key
KEY_FILE="$DEPLOY_DIR/api.key"
BASE_IMAGE="quay.io/jupyter/pytorch-notebook:cuda12-python-3.11"

die() { echo "ERROR: $*" >&2; exit 1; }

[ -d "$MODEL_DIR" ] || die "model directory not found: $MODEL_DIR"
for f in model-00001-of-00003.safetensors model-00002-of-00003.safetensors \
         model-00003-of-00003.safetensors config.json CXR_LLAVA_HF.py \
         VisualTransformer.py tokenizer.model; do
    [ -f "$MODEL_DIR/$f" ] || die "missing $MODEL_DIR/$f"
done

docker image inspect "$BASE_IMAGE" >/dev/null 2>&1 \
    || die "base image not present locally and this host has no internet: $BASE_IMAGE"

CXR_API_KEY="${CXR_API_KEY:-}"
if [ "$REQUIRE_KEY" = "1" ]; then
    command -v openssl >/dev/null 2>&1 || die "openssl not found; cannot generate an API key"
    if [ ! -s "$KEY_FILE" ]; then
        umask 077
        openssl rand -hex 24 > "$KEY_FILE"
    fi
    chmod 600 "$KEY_FILE"
    CXR_API_KEY="$(cat "$KEY_FILE")"
fi

if [ "$BIND_IP" != "127.0.0.1" ] && [ -z "$CXR_API_KEY" ]; then
    die "refusing to expose $BIND_IP without an API key; set REQUIRE_KEY=1"
fi

echo "== building $IMAGE (offline)"
docker build --pull=false --network=none -t "$IMAGE" "$DEPLOY_DIR"

echo "== import preflight (catches torch/transformers incompatibility early)"
docker run --rm "$IMAGE" python -c \
    "import torch, transformers, tokenizers, numpy, PIL, fastapi, pydicom, gdcm; \
     print('imports OK: transformers', transformers.__version__, '| torch', torch.__version__, \
           '| tokenizers', tokenizers.__version__, '| numpy', numpy.__version__, \
           '| pydicom', pydicom.__version__)"

echo "== starting $NAME on $BIND_IP:$PORT"
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" \
    --restart unless-stopped \
    --gpus all \
    --security-opt no-new-privileges \
    --cap-drop ALL \
    --tmpfs /tmp:rw,size=2g,mode=1777 \
    -v "$MODEL_DIR":/models/cxr-llava:ro \
    -p "$BIND_IP":"$PORT":8000 \
    -e MODEL_DIR=/models/cxr-llava \
    -e CXR_API_KEY="$CXR_API_KEY" \
    -e CXR_CORS_ORIGINS="${CXR_CORS_ORIGINS:-*}" \
    "$IMAGE" >/dev/null

case "$BIND_IP" in
    0.0.0.0|127.0.0.1) HEALTH_HOST=127.0.0.1 ;;
    *)                  HEALTH_HOST="$BIND_IP" ;;
esac

echo "== waiting for health (first load reads 13 GiB and takes a few minutes)"
for _ in $(seq 1 90); do
    if curl -fsS "http://$HEALTH_HOST:$PORT/health" >/tmp/cxr_health.json 2>/dev/null; then
        cat /tmp/cxr_health.json
        echo
        if [ "$BIND_IP" = "0.0.0.0" ]; then
            LAN_IP="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i=="src") {print $(i+1); exit}}')"
            [ -n "$LAN_IP" ] || LAN_IP="$(hostname -I | awk '{print $1}')"
            echo "READY: UI http://$LAN_IP:$PORT/  |  API http://$LAN_IP:$PORT/"
        else
            echo "READY: http://127.0.0.1:$PORT (loopback; use ./tunnel.ps1 from Windows)"
        fi
        if [ -n "$CXR_API_KEY" ]; then
            echo "API key: $CXR_API_KEY"
            echo "         stored in $KEY_FILE (chmod 600)"
        fi
        exit 0
    fi
    sleep 5
done

echo "== container did not become healthy; last 80 log lines:" >&2
docker logs --tail 80 "$NAME" >&2 || true
exit 1
