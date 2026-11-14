"""How much do lateral views cost the verifier?

Uses cached probabilities plus a mirror-symmetry score (no model inference), and
recomputes per-finding AUC on increasingly frontal subsets. If AUC rises with the
filter, the gate failure is partly a data problem, not only a model problem.

    python -m trustmed.eval.lateral_sensitivity --probs data_trustmed/probs_ensemble.json
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "test" / "data" / "openi500"
CUTS = [(-1.0, "all"), (0.2, "sym>0.2"), (0.4, "sym>0.4"), (0.55, "sym>0.55"), (0.7, "sym>0.7")]


def symmetry(path: pathlib.Path) -> float:
    array = np.asarray(Image.open(path).convert("L").resize((224, 224)), dtype=np.float32)
    array = (array - array.mean()) / (array.std() + 1e-6)
    return float((array * array[:, ::-1]).mean())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probs", required=True)
    args = parser.parse_args()

    dump = json.loads(pathlib.Path(args.probs).read_text(encoding="utf-8"))
    scores = {}
    for record_id in dump:
        path = next((DATA / f"{record_id}{ext}" for ext in (".png", ".jpg")
                     if (DATA / f"{record_id}{ext}").is_file()), None)
        if path:
            scores[record_id] = symmetry(path)

    labels = sorted({label for record in dump.values() for label in record["probs"]})
    header = f"{'finding':<28}" + "".join(f"{name:>10}" for _, name in CUTS) + f"{'n(all)':>8}"
    print(header)
    print("-" * len(header))

    for label in labels:
        row = f"{label:<28}"
        n_all = 0
        for cut, _ in CUTS:
            y, p = [], []
            for record_id, record in dump.items():
                if scores.get(record_id, -1) < cut:
                    continue
                y.append(int(record["labels"].get(label, 0)))
                p.append(float(record["probs"].get(label, 0.0)))
            n_all = max(n_all, len(y))
            if len(set(y)) < 2 or sum(y) < 5:
                row += f"{'—':>10}"
            else:
                row += f"{roc_auc_score(y, p):>10.3f}"
        print(row + f"{n_all:>8}")

    counts = {name: sum(1 for v in scores.values() if v >= cut) for cut, name in CUTS}
    print("\nimages kept:", counts)


if __name__ == "__main__":
    main()
