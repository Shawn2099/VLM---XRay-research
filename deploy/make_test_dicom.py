"""Create synthetic 16-bit chest X-ray DICOMs from the bundled CC0 sample.

Used to exercise the DICOM path without patient data:

    docker run --rm -v /tmp:/data cxr-llava:1.1 \
        python /opt/cxr/make_test_dicom.py

Writes /tmp/test_cxr_16bit.dcm, /tmp/test_cxr_mono1.dcm and
/tmp/test_cxr_nowindow.dcm.
"""

from __future__ import annotations

import os

import numpy as np
import pydicom
from PIL import Image
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, SecondaryCaptureImageStorage, generate_uid

SAMPLE = os.environ.get("SAMPLE_IMAGE", "/opt/cxr/samples/chest_xray_pa.png")
OUT_DIR = os.environ.get("OUT_DIR", "/tmp")


def make_dataset(path: str, pixels: np.ndarray, photometric: str, windowed: bool) -> None:
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = SecondaryCaptureImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = generate_uid()

    ds = FileDataset(path, {}, file_meta=meta, preamble=b"\0" * 128)
    ds.SOPClassUID = SecondaryCaptureImageStorage
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.FrameOfReferenceUID = generate_uid()
    ds.PatientName = "TEST^PUBLIC"
    ds.PatientID = "CC0-TEST"
    ds.PatientBirthDate = ""
    ds.StudyDate = "20261114"
    ds.StudyTime = "120000"
    ds.Modality = "CR"
    ds.BodyPartExamined = "CHEST"
    ds.ViewPosition = "PA"
    ds.SeriesNumber = 1
    ds.InstanceNumber = 1
    ds.Rows, ds.Columns = pixels.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = photometric
    ds.BitsAllocated = 16
    ds.BitsStored = 12
    ds.HighBit = 11
    ds.PixelRepresentation = 0
    ds.RescaleIntercept = 0
    ds.RescaleSlope = 1
    if windowed:
        ds.WindowCenter = 2048
        ds.WindowWidth = 4096
    ds.PixelData = pixels.astype("<u2").tobytes()
    ds.save_as(path, write_like_original=False)


def main() -> None:
    image = Image.open(SAMPLE).convert("L")
    pixels = np.asarray(image, dtype=np.uint16)
    # Scale the 8-bit sample into a 12-bit range, like a real CR image.
    pixels = (pixels.astype(np.uint32) * 4095 // 255).astype(np.uint16)

    os.makedirs(OUT_DIR, exist_ok=True)
    make_dataset(os.path.join(OUT_DIR, "test_cxr_16bit.dcm"), pixels, "MONOCHROME2", True)
    make_dataset(
        os.path.join(OUT_DIR, "test_cxr_mono1.dcm"),
        (4095 - pixels).astype(np.uint16),
        "MONOCHROME1",
        True,
    )
    make_dataset(
        os.path.join(OUT_DIR, "test_cxr_nowindow.dcm"), pixels, "MONOCHROME2", False
    )

    for name in ("test_cxr_16bit.dcm", "test_cxr_mono1.dcm", "test_cxr_nowindow.dcm"):
        path = os.path.join(OUT_DIR, name)
        print(f"{path}  {os.path.getsize(path)} bytes")
    print("OK")


if __name__ == "__main__":
    main()
