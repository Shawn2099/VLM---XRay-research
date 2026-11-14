"""Load MedGemma 1.5 4B and generate one report, without HTTP.

    docker run --rm --gpus all \
        -v /home/iccc/models/medgemma-1.5-4b-it:/models/medgemma-1.5-4b-it:ro \
        medgemma:1.0 python /opt/medgemma/smoke_test.py
"""

from __future__ import annotations

import os
import sys
import time

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL_DIR = os.environ.get("MODEL_DIR", "/models/medgemma-1.5-4b-it")
SAMPLE = os.environ.get("SAMPLE_IMAGE", "/opt/medgemma/samples/chest_xray_pa.png")
PROMPT = (
    "You are an expert radiologist. Analyze this chest X-ray and write a "
    "structured report.\n\nFindings: describe the lungs, pleura, heart, "
    "mediastinum and bones. Explicitly state whether atelectasis, cardiomegaly, "
    "consolidation, pulmonary edema, pleural effusion or pneumothorax is "
    "present.\nImpression: one or two sentences summarising the important "
    "findings."
)


def main() -> int:
    print(f"torch={torch.__version__} cuda={torch.cuda.is_available()}", flush=True)
    if not torch.cuda.is_available():
        print("FAIL: CUDA not available", flush=True)
        return 2

    started = time.time()
    processor = AutoProcessor.from_pretrained(MODEL_DIR)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_DIR, torch_dtype=torch.bfloat16
    ).to("cuda").eval()
    print(
        f"loaded in {time.time() - started:.1f}s device={model.device} "
        f"dtype={next(model.parameters()).dtype} "
        f"vram={torch.cuda.memory_allocated() / 2**30:.2f} GiB",
        flush=True,
    )

    image = Image.open(SAMPLE).convert("RGB")
    width, height = image.size
    if max(width, height) > 1024:
        scale = 1024 / max(width, height)
        image = image.resize((int(width * scale), int(height * scale)))

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": PROMPT},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = {
        key: (value.to("cuda") if torch.is_tensor(value) else value)
        for key, value in inputs.items()
    }
    if "pixel_values" in inputs:
        inputs["pixel_values"] = inputs["pixel_values"].to(torch.bfloat16)
    input_length = inputs["input_ids"].shape[-1]

    started = time.time()
    with torch.inference_mode():
        output = model.generate(
            **inputs, max_new_tokens=512, do_sample=False
        )
    decode = getattr(processor, "decode", None) or processor.tokenizer.decode
    text = decode(output[0][input_length:], skip_special_tokens=True).strip()
    print(f"inference in {time.time() - started:.1f}s", flush=True)
    print("--- report ---", flush=True)
    print(text, flush=True)
    print("--- end ---", flush=True)

    if not text:
        print("FAIL: empty report", flush=True)
        return 3
    print("PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
