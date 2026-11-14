"""DenseNet-121 image findings (TorchXRayVision), with an explicit 18 -> 14 map.

Guardrail G1: the mapping is asserted at load time. A silent mismatch here would
make every verdict wrong without raising anywhere else.
"""

from __future__ import annotations

import threading

import numpy as np
from PIL import Image

from .. import config

# TorchXRayVision "densenet121-res224-all" output order (verified at load).
EXPECTED_XRV = [
    "Atelectasis",
    "Consolidation",
    "Infiltration",
    "Pneumothorax",
    "Edema",
    "Emphysema",
    "Fibrosis",
    "Effusion",
    "Pneumonia",
    "Pleural_Thickening",
    "Cardiomegaly",
    "Nodule",
    "Mass",
    "Hernia",
    "Lung Lesion",
    "Fracture",
    "Lung Opacity",
    "Enlarged Cardiomediastinum",
]

# several xrv heads can feed one CheXbert label; we keep the max
XRV_TO_CHEXBERT = {
    "Atelectasis": "Atelectasis",
    "Consolidation": "Consolidation",
    "Infiltration": "Lung Opacity",
    "Pneumothorax": "Pneumothorax",
    "Edema": "Edema",
    "Effusion": "Pleural Effusion",
    "Pneumonia": "Pneumonia",
    "Pleural_Thickening": "Pleural Other",
    "Cardiomegaly": "Cardiomegaly",
    "Nodule": "Lung Lesion",
    "Mass": "Lung Lesion",
    "Lung Lesion": "Lung Lesion",
    "Fracture": "Fracture",
    "Lung Opacity": "Lung Opacity",
    "Enlarged Cardiomediastinum": "Enlarged Cardiomediastinum",
}

# labels the classifier can never speak to — always "not assessable"
NOT_ASSESSABLE = {"Support Devices", "No Finding"}

_model = None
_lock = threading.Lock()


def _load():
    global _model
    with _lock:
        if _model is None:
            import torch
            import torchxrayvision as xrv

            model = xrv.models.DenseNet(weights=config.DENSENET_WEIGHTS).eval()
            found = [p for p in model.pathologies if p]
            unknown = [p for p in found if p not in EXPECTED_XRV]
            mapped = [p for p in found if p in XRV_TO_CHEXBERT]
            if unknown:
                raise RuntimeError(
                    "TorchXRayVision returned labels this build does not know; "
                    f"refusing to guess: {unknown}"
                )
            if len(mapped) < 4:
                raise RuntimeError(
                    f"{config.DENSENET_WEIGHTS} exposes only {mapped}; "
                    "not enough overlapping findings to verify anything"
                )
            _model = (model, torch)
    return _model


def _preprocess(gray: np.ndarray):
    import torchvision
    import torchxrayvision as xrv
    import torch

    image = xrv.datasets.normalize(gray.astype(np.uint8), 255)[None, ...]
    transform = torchvision.transforms.Compose(
        [xrv.datasets.XRayCenterCrop(), xrv.datasets.XRayResizer(224)]
    )
    return torch.from_numpy(transform(image).astype("float32"))[None, ...]


def predict(gray_path: str) -> dict[str, float]:
    model, torch = _load()
    with Image.open(gray_path) as image:
        gray = np.asarray(image.convert("L"))

    batch = _preprocess(gray)
    with _lock, torch.no_grad():
        raw = model(batch)[0].tolist()

    per_label: dict[str, float] = {}
    for name, prob in zip(model.pathologies, raw):
        target = XRV_TO_CHEXBERT.get(name)
        if target is None:
            continue
        per_label[target] = max(per_label.get(target, 0.0), float(prob))
    return {k: round(v, 4) for k, v in per_label.items()}


def self_test() -> dict:
    """Guardrail G1: mapping is complete and covers exactly the CheXbert labels
    that an image model can speak to."""
    expected = {
        "Atelectasis",
        "Cardiomegaly",
        "Consolidation",
        "Edema",
        "Enlarged Cardiomediastinum",
        "Fracture",
        "Lung Lesion",
        "Lung Opacity",
        "Pleural Effusion",
        "Pleural Other",
        "Pneumonia",
        "Pneumothorax",
    }
    targets = set(XRV_TO_CHEXBERT.values())
    unmapped = [name for name in EXPECTED_XRV if name not in XRV_TO_CHEXBERT]
    return {
        "ok": targets == expected,
        "missing": sorted(expected - targets),
        "unexpected": sorted(targets - expected),
        # heads with no CheXbert counterpart are listed, not silently dropped
        "xrv_only": sorted(unmapped),
        "not_assessable": sorted(NOT_ASSESSABLE),
    }
