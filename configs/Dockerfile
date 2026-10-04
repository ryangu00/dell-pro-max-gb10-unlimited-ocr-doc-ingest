# Equivalent of the recorded interactive image; not built in this cookbook.
FROM nvcr.io/nvidia/pytorch:25.10-py3
RUN pip uninstall -y torchao && \
    pip install transformers==4.57.1 pymupdf==1.27.2.2 addict easydict einops matplotlib
# Mount a prepared workspace at /ws; weights are not included in the image.
ENV MODEL_DIR=/ws/models/Unlimited-OCR
