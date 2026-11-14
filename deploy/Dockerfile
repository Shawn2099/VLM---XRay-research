# Offline image for CXR-LLaVA v2, built on the PyTorch/CUDA image already
# present on icccserver.  No internet access is needed or used.
#
# Build:  docker build --pull=false -t cxr-llava:1.5 /home/iccc/cxr-llava/deploy

FROM quay.io/jupyter/pytorch-notebook:cuda12-python-3.11

USER root
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

# Wheels are vendored so the build works on a host with no PyPI access.
COPY wheels/ /tmp/wheels/
RUN pip install --no-index --find-links=/tmp/wheels \
        transformers==4.36.2 \
        tokenizers==0.15.2 \
        huggingface-hub==0.25.2 \
        safetensors==0.4.5 \
        sentencepiece==0.2.0 \
        protobuf==4.25.2 \
        pydicom==2.4.4 \
        python-gdcm==3.0.24.1 \
        numpy==1.26.4 \
        pillow==10.4.0 \
        fastapi==0.115.0 \
        uvicorn==0.30.6 \
        python-multipart==0.0.9 \
        pydantic==2.9.2 \
    && rm -rf /tmp/wheels \
    && python -c "import transformers, torch; print('transformers', transformers.__version__, 'torch', torch.__version__)"

WORKDIR /opt/cxr
COPY app.py smoke_test.py make_test_dicom.py ui.html /opt/cxr/
COPY samples/ /opt/cxr/samples/

# The model code is loaded with trust_remote_code=True, which copies the
# custom module into HF_MODULES_CACHE.  /tmp stays writable even if the
# container is later run with --read-only.
ENV MODEL_DIR=/models/cxr-llava \
    HF_HOME=/tmp/hf \
    HF_MODULES_CACHE=/tmp/hf/modules \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    PYTHONUNBUFFERED=1

USER jovyan
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# Bind 0.0.0.0 inside the container; the host publishes it on 127.0.0.1 only.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
