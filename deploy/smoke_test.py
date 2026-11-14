"""Load the model and generate one report, without the HTTP layer.

Run inside the built image:

    docker run --rm --gpus all \
        -v /home/iccc/cxr-llava/model:/models/cxr-llava:ro \
        cxr-llava:1.5 python /opt/cxr/smoke_test.py

Exit code 0 means the model loaded and produced non-empty text.  Any
compatibility problem with the pinned torch/transformers pair shows up here
first, with a full traceback.
"""

from __future__ import annotations

import os
import sys
import time

import torch
from PIL import Image
from transformers import AutoModel


def main() -> int:
    model_dir = os.environ.get("MODEL_DIR", "/models/cxr-llava")
    image_path = os.environ.get("SAMPLE_IMAGE", "/opt/cxr/samples/chest_xray_pa.png")

    print(f"torch={torch.__version__} cuda={torch.cuda.is_available()}", flush=True)
    if not torch.cuda.is_available():
        print("FAIL: CUDA not available", flush=True)
        return 2

    started = time.time()
    model = AutoModel.from_pretrained(model_dir, trust_remote_code=True)
    model = model.to("cuda").eval()
    torch.set_grad_enabled(False)
    load_s = time.time() - started
    print(
        f"loaded in {load_s:.1f}s device={model.device} "
        f"dtype={next(model.parameters()).dtype} "
        f"vram={torch.cuda.memory_allocated() / 2**30:.2f} GiB",
        flush=True,
    )

    image = Image.open(image_path)
    print(f"image={image_path} mode={image.mode} size={image.size}", flush=True)

    started = time.time()
    text = model.write_radiologic_report(image)
    infer_s = time.time() - started
    print(f"inference in {infer_s:.1f}s", flush=True)
    print("--- report ---", flush=True)
    print(text, flush=True)
    print("--- end ---", flush=True)

    if not text or not text.strip():
        print("FAIL: empty report", flush=True)
        return 3
    print("PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
