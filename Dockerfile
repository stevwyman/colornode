# ==========================================
# Stage 1️⃣ Builder
# ==========================================
FROM registry.access.redhat.com/hi/python:3.14-builder AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER root
WORKDIR /app

COPY requirements.txt .

# Use BuildKit cache mount for pip to speed up Torch installs
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt && \
    /opt/venv/bin/pip uninstall -y opencv-python opencv-contrib-python || true && \
    /opt/venv/bin/pip install --force-reinstall opencv-python-headless

RUN mkdir -p /app/.ddcolor

# ==========================================
# Stage 2️⃣ Final (Rootless & Hardened)
# ==========================================
FROM registry.access.redhat.com/hi/python:3.14 AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DDCOLOR_HOME="/app/.ddcolor" \
    HF_HOME="/app/.ddcolor" \
    HUGGINGFACE_HUB_CACHE="/app/.ddcolor"

USER root
WORKDIR /app

# Copy the venv and set ownership to rootless user (1001)
COPY --from=builder --chown=1001:0 /opt/venv /opt/venv

# Ensure the rootless user has a writable directory for downloading ML models
COPY --from=builder --chown=1001:0 /app/.ddcolor /app/.ddcolor

# Copy application files (service + vendored DDColor inference code)
COPY --chown=1001:0 . .

# Switch to the non-root user
USER 1001

VOLUME /app/.ddcolor

# Execute uvicorn explicitly from the venv binary path
CMD ["/opt/venv/bin/uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8000"]
