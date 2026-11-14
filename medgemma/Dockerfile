# MedGemma 1.5 4B service — offline image.
#
# Build:  docker build --pull=false -t medgemma:1.0 /home/iccc/medgemma/deploy
# Run:    /home/iccc/switch.sh medgemma   (maps container :8001 -> host :8000)

FROM quay.io/jupyter/pytorch-notebook:cuda12-python-3.11

USER root
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY wheels/ /tmp/wheels/
RUN python -m venv --system-site-packages /opt/medgemma/venv \
    && /opt/medgemma/venv/bin/pip install --no-index --find-links=/tmp/wheels \
        transformers==4.51.3 \
        huggingface-hub==0.36.0 \
        tokenizers==0.21.4 \
        safetensors==0.8.0 \
        regex==2026.11.9 \
        jinja2==3.1.4 \
        pydicom==2.4.4 \
        python-gdcm==3.0.24.1 \
        numpy==2.0.2 \
        pillow==11.0.0 \
        fastapi==0.115.0 \
        starlette==0.38.6 \
        uvicorn==0.30.6 \
        python-multipart==0.0.9 \
        pydantic==2.14.3 \
    && rm -rf /tmp/wheels

ENV PATH=/opt/medgemma/venv/bin:$PATH
RUN python -c "import torch, transformers; from transformers import AutoProcessor, AutoModelForImageTextToText; print('transformers', transformers.__version__, 'torch', torch.__version__)"

WORKDIR /opt/medgemma
COPY app.py ui.html smoke_test.py /opt/medgemma/
COPY samples/ /opt/medgemma/samples/

ENV MODEL_DIR=/models/medgemma-1.5-4b-it \
    UI_PATH=/opt/medgemma/ui.html \
    HF_HOME=/tmp/hf \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false \
    PYTHONUNBUFFERED=1

USER jovyan
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD /opt/medgemma/venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=4)"

CMD ["/opt/medgemma/venv/bin/uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
