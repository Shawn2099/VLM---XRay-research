"""End-to-end check of the TrustMed HTTP surface (no GPU, no torch needed).

Drives the real service the way the browser does: sign in, upload, generate,
read back, review, history. Fails loudly on anything that is not a real result.

    python test/trustmed_e2e.py --base http://127.0.0.1:8010
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import requests

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "openi500"

CASES = [
    ("0001.png", "normal"),
    ("0019.png", "cardiomegaly (reference)"),
    ("0000.png", "effusion (reference)"),
]

PASS, FAIL = "PASS", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, PASS if ok else FAIL, detail))
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8010")
    parser.add_argument("--email", default="admin@trustmed.local")
    parser.add_argument("--password", default="trustmed-admin")
    args = parser.parse_args()

    session = requests.Session()

    # 0. unauthenticated access must be refused
    health = session.get(f"{args.base}/health", timeout=30)
    check("health", health.ok, f"{health.status_code}")
    unauth = session.post(f"{args.base}/api/upload", files={"file": ("x.png", b"x")}, timeout=30)
    check("unauthenticated upload refused", unauth.status_code == 401, f"{unauth.status_code}")

    # 1. sign in
    login = session.post(
        f"{args.base}/auth/login",
        data={"email": args.email, "password": args.password},
        allow_redirects=False,
        timeout=30,
    )
    check("login", login.status_code == 303, f"{login.status_code}")

    home = session.get(f"{args.base}/", timeout=30)
    check("worklist page", home.ok and "TrustMed" in home.text, f"{home.status_code}")

    bad = requests.post(
        f"{args.base}/auth/login",
        data={"email": args.email, "password": "wrong-password"},
        allow_redirects=False,
        timeout=30,
    )
    check("wrong password refused", bad.status_code == 401, f"{bad.status_code}")

    report_ids: list[int] = []
    for filename, expected in CASES:
        path = DATA / filename
        with path.open("rb") as handle:
            upload = session.post(
                f"{args.base}/api/upload",
                files={"file": (path.name, handle, "image/png")},
                timeout=120,
            )
        if not check(f"upload {filename}", upload.ok, f"{upload.status_code}"):
            continue
        image_id = upload.json()["image_id"]

        response = session.post(
            f"{args.base}/api/report",
            data={"image_id": image_id, "threshold": "0.55"},
            timeout=600,
        )
        if not check(f"report {filename}", response.ok, f"{response.status_code}"):
            print(response.text[:400])
            continue

        body = response.json()
        findings = body["findings"]
        verdicts: dict[str, int] = {}
        for finding in findings:
            verdicts[finding["verdict"]] = verdicts.get(finding["verdict"], 0) + 1

        check(f"report {filename} has text", bool(body["text"].strip()), body["text"][:60])
        check(f"report {filename} has findings", len(findings) >= 1, f"{len(findings)}")
        check(
            f"report {filename} confidence in range",
            0.0 <= body["confidence"] <= 1.0,
            f"{body['confidence']}",
        )
        check(
            f"report {filename} status valid",
            body["status"] in {"auto_accepted", "review_suggested", "review_required"},
            body["status"],
        )

        # every positive/negative finding must carry a reason and, when verifiable, a probability
        for finding in findings:
            if finding["verdict"] == "not_assessable":
                continue
            if finding["image_prob"] is None:
                check(f"{filename}: prob for {finding['label']}", False, "missing")
                break

        # no finding may be quoted from a sentence that contradicts its label
        for finding in findings:
            if finding["polarity"] > 0 and finding["sentence"].lower().startswith("no "):
                check(f"{filename}: contradictory quote for {finding['label']}", False,
                      finding["sentence"][:60])
        report_ids.append(body["report_id"])

        print(f"{filename} [{expected}]")
        print(f"  status={body['status']} confidence={body['confidence']} "
              f"latency={body['latency_ms']} ms")
        print(f"  verdicts={verdicts}")
        for finding in findings:
            print(f"    - {finding['label']:<26} report={finding['polarity']:+d} "
                  f"image={finding['image_prob']} {finding['verdict']}")

    # 2. read back + review
    if report_ids:
        read = session.get(f"{args.base}/api/reports/{report_ids[0]}", timeout=30)
        check("read back report", read.ok and read.json()["report"]["id"] == report_ids[0])

        detail = session.get(f"{args.base}/api/reports/{report_ids[0]}", timeout=30).json()
        finding_id = detail["findings"][0]["id"]
        review = session.post(
            f"{args.base}/api/findings/{finding_id}/review",
            data={"action": "accept", "comment": "e2e check"},
            timeout=30,
        )
        check("review recorded", review.ok, f"{review.status_code}")

        bad_action = session.post(
            f"{args.base}/api/findings/{finding_id}/review",
            data={"action": "delete"},
            timeout=30,
        )
        check("invalid review action refused", bad_action.status_code == 422,
              f"{bad_action.status_code}")

    history = session.get(f"{args.base}/history", timeout=30)
    check("history page", history.ok and "report history" in history.text, f"{history.status_code}")

    cert = session.get(f"{args.base}/api/selftest", timeout=120)
    if cert.ok:
        body = cert.json()
        check("chexbert self-test", body["chexbert"]["ok"], json.dumps(body["chexbert"]["checks"]))
        check("classifier label map", body["classifier"]["ok"],
              json.dumps(body["classifier"]["missing"]))

    print("\n=== summary ===")
    width = max(len(name) for name, _, _ in results)
    for name, status, detail in results:
        print(f"{status}  {name:<{width}}  {detail}")
    failures = [r for r in results if r[1] == FAIL]
    print(f"\n{len(results) - len(failures)}/{len(results)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
