"""Edge-case tests for the deployed CXR-LLaVA API.

Checks image formats, 16-bit rejection, corrupt input, DICOM handling, API-key
enforcement and error codes. Expects a running service and an API key.

  python test/edge_cases.py --api-key KEY --dicom-dir test/data/dicom
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import tempfile
from pathlib import Path

import requests
from PIL import Image, ImageStat

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CASES: list[tuple[str, str, int]] = []


def make_image(tmp: Path, name: str, mode: str, size: tuple[int, int], fmt: str) -> Path:
    path = tmp / name
    if mode == "I;16":
        image = Image.new("I;16", size)
        pixels = image.load()
        for x in range(0, size[0], 7):
            for y in range(0, size[1], 7):
                pixels[x, y] = (x * 37 + y * 91) % 65535
    else:
        image = Image.new(mode, size)
        pixels = image.load()
        for x in range(0, size[0], 5):
            for y in range(0, size[1], 5):
                value = (x * 13 + y * 29) % 256
                if mode == "RGB":
                    pixels[x, y] = (value, 255 - value, (value * 2) % 256)
                elif mode == "RGBA":
                    pixels[x, y] = (value, 255 - value, (value * 2) % 256, 255)
                elif mode == "P":
                    pixels[x, y] = value
                else:
                    pixels[x, y] = value
    image.save(path, format=fmt)
    return path


def post(base, key, path, endpoint="report", data=None, content_type="image/png"):
    headers = {"X-API-Key": key} if key else {}
    with path.open("rb") as handle:
        return requests.post(
            f"{base}/{endpoint}",
            headers=headers,
            files={"file": (path.name, handle, content_type)},
            data=data or {},
            timeout=300,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://10.10.10.28:8000")
    parser.add_argument("--api-key", default=os.environ.get("CXR_API_KEY", ""))
    parser.add_argument("--dicom-dir", default="test/data/dicom")
    parser.add_argument("--skip-report", action="store_true",
                        help="only exercise /preview and errors (faster)")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("pass --api-key or set CXR_API_KEY")

    results = []

    def check(name, response, expected):
        ok = response.status_code == expected
        detail = ""
        if "json" in (response.headers.get("content-type") or ""):
            try:
                body = response.json()
                if isinstance(body, dict) and body.get("detail"):
                    detail = str(body["detail"])[:120]
            except ValueError:
                pass
        elif response.status_code >= 400:
            detail = response.text[:80]
        detail = detail.encode("ascii", "ignore").decode()
        results.append((name, response.status_code, expected, ok, detail))
        print(f"{'PASS' if ok else 'FAIL'}  {name}: HTTP {response.status_code} "
              f"(expected {expected}) {detail}")

    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp)

        gray = make_image(tmp, "gray.png", "L", (512, 512), "PNG")
        rgb = make_image(tmp, "rgb.jpg", "RGB", (512, 512), "JPEG")
        rgba = make_image(tmp, "rgba.png", "RGBA", (512, 512), "PNG")
        palette = make_image(tmp, "palette.png", "P", (512, 512), "PNG")
        sixteen = make_image(tmp, "16bit.png", "I;16", (512, 512), "PNG")
        tiny = make_image(tmp, "tiny.png", "L", (8, 8), "PNG")
        large = make_image(tmp, "large.png", "L", (8000, 8000), "PNG")
        exif_path = tmp / "exif.jpg"
        exif_image = Image.new("RGB", (320, 160), (20, 40, 60))
        exif = exif_image.getexif()
        exif[274] = 6  # rotate 90 CW on display
        exif_image.save(exif_path, exif=exif)
        huge = tmp / "huge.bin"
        huge.write_bytes(b"\0" * (45 * 1024 * 1024))
        corrupt = tmp / "corrupt.png"
        corrupt.write_bytes(b"not an image at all")
        empty = tmp / "empty.png"
        empty.write_bytes(b"")

        if not args.skip_report:
            check("grayscale PNG report", post(args.base_url, args.api_key, gray), 200)
            check("RGB JPEG report", post(args.base_url, args.api_key, rgb), 200)
            check("RGBA PNG report", post(args.base_url, args.api_key, rgba), 200)
            check("palette PNG report", post(args.base_url, args.api_key, palette), 200)
            check("tiny 8x8 report", post(args.base_url, args.api_key, tiny), 200)

        check("16-bit PNG rejected", post(args.base_url, args.api_key, sixteen), 422)
        check("corrupt file rejected", post(args.base_url, args.api_key, corrupt), 400)
        check("empty file rejected", post(args.base_url, args.api_key, empty), 400)
        check("large 64 MP rejected", post(args.base_url, args.api_key, large), 413)
        check("oversized 45 MB body rejected", post(args.base_url, args.api_key, huge), 413)
        check("PNG with octet-stream type accepted",
              post(args.base_url, args.api_key, gray,
                   content_type="application/octet-stream"), 200)
        check("preview 16-bit PNG rejected",
              post(args.base_url, args.api_key, sixteen, "preview"), 422)
        exif_response = post(args.base_url, args.api_key, exif_path, "preview",
                             content_type="image/jpeg")
        check("EXIF-oriented JPEG accepted", exif_response, 200)
        if exif_response.ok:
            width = exif_response.headers.get("x-image-width")
            height = exif_response.headers.get("x-image-height")
            applied = width == "160" and height == "320"
            results.append(("EXIF orientation applied", 0, 1, applied,
                            f"{width}x{height}"))
            print(f"       {'PASS' if applied else 'FAIL'}  EXIF orientation: "
                  f"{width}x{height} (expected 160x320)")
        check("no API key rejected", post(args.base_url, "", gray), 401)
        check("wrong API key rejected", post(args.base_url, "wrong", gray), 401)
        check("empty question rejected",
              post(args.base_url, args.api_key, gray, "ask", {"question": "  "}), 422)
        check("missing question rejected",
              post(args.base_url, args.api_key, gray, "ask"), 422)

        for path, expected in (("/docs", 404), ("/openapi.json", 404)):
            response = requests.get(args.base_url + path, timeout=10)
            check(f"{path} disabled", response, expected)

        response = requests.get(args.base_url + "/report", timeout=10)
        check("GET /report rejected", response, 405)
        response = requests.get(args.base_url + "/does-not-exist", timeout=10)
        check("unknown route rejected", response, 404)

        response = requests.options(
            args.base_url + "/report",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
            },
            timeout=10,
        )
        check("CORS preflight", response, 200)
        print(f"       allow-origin: {response.headers.get('access-control-allow-origin')}")

        preview = post(args.base_url, args.api_key, gray, "preview")
        check("preview PNG", preview, 200)
        if preview.ok:
            image = Image.open(io.BytesIO(preview.content))
            print(f"       preview {image.size} {image.mode}; "
                  f"source={preview.headers.get('x-image-source')}")

        dicom_dir = Path(args.dicom_dir)
        for path in sorted(dicom_dir.glob("*.dcm")) if dicom_dir.is_dir() else []:
            # The colour test file is expected to be rejected: the model is
            # grayscale-only.
            # Colour and multi-frame files are expected to be rejected: the
            # model is grayscale-only and a multi-frame study is ambiguous.
            multi_frame = (
                "OBXXXX1A_2frame", "emri_small", "emri_small_jpeg_ls_lossless",
                "liver_rle",
            )
            expected = 422 if path.name.startswith(
                ("SC_rgb", "nopixels", "norows") + multi_frame
            ) else 200
            preview = post(args.base_url, args.api_key, path, "preview",
                           content_type="application/dicom")
            check(f"DICOM preview {path.name}", preview, expected)
            if preview.ok:
                print(f"       source={preview.headers.get('x-image-source')} "
                      f"photo={preview.headers.get('x-dicom-photometric')} "
                      f"bits={preview.headers.get('x-dicom-bitsstored')} "
                      f"window={preview.headers.get('x-dicom-window')}")
                decoded = Image.open(io.BytesIO(preview.content)).convert("L")
                deviation = ImageStat.Stat(decoded).stddev[0]
                blank = deviation < 2.0
                results.append((f"{path.name} preview non-blank", 0, 1, not blank,
                                f"stddev={deviation:.1f}"))
                print(f"       {'PASS' if not blank else 'FAIL'}  preview non-blank "
                      f"(stddev {deviation:.1f})")
            if not args.skip_report:
                check(f"DICOM report {path.name}", post(
                    args.base_url, args.api_key, path, "report",
                    {"temperature": "0", "top_p": "1"},
                    content_type="application/dicom"), expected)
            if preview.ok and path.name == "badheader.dcm":
                hijack = preview.headers.get("X-Evil")
                modality = preview.headers.get("x-dicom-modality", "")
                clean = hijack is None and "\r" not in modality and "\n" not in modality
                results.append(("DICOM header injection blocked", 0, 1, clean,
                                f"x-evil={hijack!r} modality={modality!r}"))
                print(f"       {'PASS' if clean else 'FAIL'}  header injection blocked "
                      f"(x-evil={hijack!r}, modality={modality!r})")

    passed = sum(1 for item in results if item[3])
    print(f"\n{passed}/{len(results)} checks passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
