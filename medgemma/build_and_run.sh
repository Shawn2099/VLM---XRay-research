#!/usr/bin/env bash
# Build the MedGemma 1.5 4B image offline.  Running/switching is done by
# /home/iccc/switch.sh so both backends share the same host port.
set -euo pipefail

ROOT="${1:-/home/iccc/medgemma}"
DEPLOY_DIR="$ROOT/deploy"
IMAGE="medgemma:1.0"
BASE_IMAGE="quay.io/jupyter/pytorch-notebook:cuda12-python-3.11"

die() { echo "ERROR: $*" >&2; exit 1; }

[ -d "$DEPLOY_DIR" ] || die "deploy directory not found: $DEPLOY_DIR"
docker image inspect "$BASE_IMAGE" >/dev/null 2>&1 \
    || die "base image not present locally and this host has no internet: $BASE_IMAGE"

echo "== building $IMAGE (offline)"
docker build --pull=false --network=none -t "$IMAGE" "$DEPLOY_DIR"

echo "== import preflight"
docker run --rm --entrypoint /opt/medgemma/venv/bin/python "$IMAGE" -c \
    "import torch, transformers, pydicom, gdcm, fastapi, PIL; \
     from transformers import AutoProcessor, AutoModelForImageTextToText; \
     print('imports OK: transformers', transformers.__version__, '| torch', torch.__version__, \
           '| pydicom', pydicom.__version__)"

echo
echo "Image ready. Activate it with:  bash /home/iccc/switch.sh medgemma"
