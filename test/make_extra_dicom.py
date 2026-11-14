"""Create extra DICOM edge-case files for the API tests.

Run locally (pydicom 2.4.4 + numpy + Pillow):
    python test/make_extra_dicom.py

Writes into test/data/dicom/extra/:
    signed.dcm       PixelRepresentation=1, negative values
    zerowindow.dcm   WindowCenter=WindowWidth=0 (invalid VOI)
    nopreamble.dcm   128-byte preamble and DICM prefix removed
    nopixels.dcm     metadata only, no PixelData
    norows.dcm       PixelData but no Rows/Columns
"""

from __future__ import annotations

import pathlib

import numpy as np
import pydicom
from PIL import Image
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

ROOT = pathlib.Path(__file__).resolve().parent
BASE = ROOT / "data" / "dicom" / "test_cxr_16bit.dcm"
SAMPLE = ROOT.parent / "deploy" / "samples" / "chest_xray_pa.png"
OUT = ROOT / "data" / "dicom" / "extra"


def new_dataset(
    pixels: np.ndarray,
    signed: bool,
    window: tuple[int, int] | None,
    bits: int = 16,
    slope: float | None = None,
    intercept: float | None = None,
) -> FileDataset:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = generate_uid()

    ds = FileDataset("", {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    ds.PatientName = "TEST^PUBLIC"
    ds.PatientID = "CC0-TEST"
    ds.Modality = "CR"
    ds.BodyPartExamined = "CHEST"
    ds.Rows, ds.Columns = pixels.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 8 if bits == 8 else 16
    ds.BitsStored = bits
    ds.HighBit = bits - 1
    ds.PixelRepresentation = 1 if signed else 0
    if slope is not None:
        ds.RescaleSlope = slope
    if intercept is not None:
        ds.RescaleIntercept = intercept
    if window is not None:
        ds.WindowCenter, ds.WindowWidth = window
    if bits == 8:
        ds.PixelData = pixels.astype("<u1").tobytes()
    else:
        ds.PixelData = pixels.astype("<i2" if signed else "<u2").tobytes()
    return ds


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    image = Image.open(SAMPLE).convert("L").resize((512, 512))
    unsigned = (np.asarray(image, dtype=np.uint32) * 4095 // 255).astype(np.uint16)

    # Signed pixel data: CT-like range around zero.
    signed = (unsigned.astype(np.int32) - 1024).astype(np.int16)
    new_dataset(signed, signed=True, window=None).save_as(
        OUT / "signed.dcm", write_like_original=False
    )

    # Invalid window width must fall back to percentile scaling.
    new_dataset(unsigned, signed=False, window=(0, 0)).save_as(
        OUT / "zerowindow.dcm", write_like_original=False
    )

    # File-controlled tag value that would split a response header if echoed.
    bad_header = new_dataset(unsigned, signed=False, window=(2048, 4096))
    bad_header.Modality = "CR\r\nX-Evil: injected"
    bad_header.save_as(OUT / "badheader.dcm", write_like_original=False)

    # 8-bit pixels (fluoroscopy-style) and a modality LUT with slope/intercept.
    new_dataset((unsigned >> 4).astype(np.uint8), signed=False, window=None,
                bits=8).save_as(OUT / "bit8.dcm", write_like_original=False)
    new_dataset(unsigned, signed=False, window=None,
                slope=0.5, intercept=-100).save_as(
                    OUT / "rescale.dcm", write_like_original=False
                )

    base = pydicom.dcmread(BASE)
    raw = BASE.read_bytes()
    (OUT / "nopreamble.dcm").write_bytes(raw[132:])

    no_pixels = pydicom.dcmread(BASE)
    del no_pixels.PixelData
    no_pixels.save_as(OUT / "nopixels.dcm", write_like_original=False)

    no_rows = pydicom.dcmread(BASE)
    del no_rows.Rows
    del no_rows.Columns
    no_rows.save_as(OUT / "norows.dcm", write_like_original=False)

    for name in ("signed.dcm", "zerowindow.dcm", "nopreamble.dcm",
                 "nopixels.dcm", "norows.dcm", "badheader.dcm",
                 "bit8.dcm", "rescale.dcm"):
        path = OUT / name
        print(f"{path.name:16s} {path.stat().st_size:>8} bytes")
    print("base rows/cols:", base.Rows, base.Columns)


if __name__ == "__main__":
    main()
