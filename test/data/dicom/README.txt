OpenI / Indiana University chest X-ray subset
==============================================

Source: NLM Open-i, https://openi.nlm.nih.gov/faq
Mirror: https://huggingface.co/datasets/Shrey-1329/cxiu_hf_dataset
Content: 120 frontal/lateral chest radiographs (512x624 JPEG) with the
FINDINGS section of the corresponding radiology report.
Access: public, no registration.
Use: research and engineering tests only; not for clinical decisions.

The original OpenI archive was unavailable ("under maintenance") when this
subset was fetched on 2026-11-14; the HF mirror is a conversion of the same
public collection (6,060 image/report pairs).

DICOM test files
----------------
test_cxr_16bit.dcm, test_cxr_mono1.dcm, test_cxr_nowindow.dcm
    Synthetic 12-bit DICOMs generated from the CC0 sample in
    deploy/samples/chest_xray_pa.png by deploy/make_test_dicom.py.

The remaining *.dcm files are from the pydicom-data repository
(https://github.com/pydicom/pydicom-data, MIT licence) and are used only to
exercise compressed transfer syntaxes:
    693_J2KR.dcm / 693_J2KI.dcm   JPEG 2000 lossless / lossy
    JPEG-LL.dcm                   JPEG lossless
    emri_small_jpeg_ls_lossless.dcm  JPEG-LS lossless (multi-frame)
    liver_rle.dcm                 RLE (multi-frame)
    OBXXXX1A_2frame.dcm           uncompressed, 2 frames
    SC_rgb.dcm                    RGB colour (expected to be rejected)
    emri_small.dcm                uncompressed grayscale (multi-frame)

extra/ contains the hand-made edge cases:
    signed.dcm       PixelRepresentation=1, negative values
    zerowindow.dcm   WindowCenter=WindowWidth=0
    nopreamble.dcm   128-byte preamble + DICM removed
    nopixels.dcm     metadata only, no PixelData
    norows.dcm       PixelData but no Rows/Columns
    badheader.dcm    Modality contains CRLF + a fake header
    bit8.dcm         8-bit pixels (fluoroscopy-style)
    rescale.dcm      RescaleSlope=0.5, RescaleIntercept=-100
    vlut_04.dcm      VOI LUT sequence (pydicom-data)
    mlut_18.dcm      modality LUT sequence (pydicom-data)
    JLSL_16_15_1_1F.dcm  single-frame JPEG-LS (pydicom-data)
    SC_rgb_32bit.dcm     32-bit RGB (expected to be rejected)
