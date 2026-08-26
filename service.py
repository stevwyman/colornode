# service.py – DDColor colorization microservice for RootNode

from __future__ import annotations

import logging
import os
import threading

import cv2
import numpy as np
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from huggingface_hub import PyTorchModelHubMixin

from ddcolor import ColorizationPipeline, DDColor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_HOME = os.getenv("DDCOLOR_HOME", "/app/.ddcolor")
MODEL_NAME = os.getenv("DDCOLOR_MODEL", "piddnad/ddcolor_paper_tiny")
INPUT_SIZE = int(os.getenv("DDCOLOR_INPUT_SIZE", "512"))
JPEG_QUALITY = int(os.getenv("DDCOLOR_JPEG_QUALITY", "92"))

os.environ.setdefault("HF_HOME", MODEL_HOME)
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", MODEL_HOME)
os.makedirs(MODEL_HOME, exist_ok=True)

app = FastAPI(title="ColorNode-Service")


class DDColorHF(DDColor, PyTorchModelHubMixin):
    def __init__(self, config=None, **kwargs):
        if isinstance(config, dict):
            kwargs = {**config, **kwargs}
        super().__init__(**kwargs)


_lock = threading.Lock()
_colorizer: ColorizationPipeline | None = None
_loaded_model_name: str | None = None


def _hub_id(name: str) -> str:
    if os.path.isdir(name) or "/" in name:
        return name
    return f"piddnad/{name}"


def get_colorizer() -> ColorizationPipeline:
    """Load DDColor once; weights are cached under DDCOLOR_HOME."""
    global _colorizer, _loaded_model_name
    with _lock:
        if _colorizer is None:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            hub_id = _hub_id(MODEL_NAME)
            logger.info("Lade DDColor-Modell %s auf %s …", hub_id, device)
            model = DDColorHF.from_pretrained(hub_id, cache_dir=MODEL_HOME)
            model = model.to(device)
            model.eval()
            _colorizer = ColorizationPipeline(
                model, input_size=INPUT_SIZE, device=device
            )
            _loaded_model_name = hub_id
            logger.info("DDColor bereit.")
        return _colorizer


def _to_cv2_image(file_bytes: bytes) -> np.ndarray:
    np_arr = np.frombuffer(file_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Bild konnte nicht dekodiert werden.")
    return img


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": _hub_id(MODEL_NAME),
        "ready": _colorizer is not None,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
    }


@app.post("/colorize")
@app.post("/api/v1/colorize")
def colorize(file: UploadFile = File(...)):
    """
    Colorize a black-and-white (or faded) photo.

    Returns JPEG bytes. The original is never stored.
    """
    logger.info("Empfange Datei: %s", file.filename)
    try:
        contents = file.file.read()
        img = _to_cv2_image(contents)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Bild-Lese-Fehler: {exc}") from exc

    try:
        colorizer = get_colorizer()
        image_out = colorizer.process(img)
        ok, encoded = cv2.imencode(
            ".jpg",
            image_out,
            [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
        )
        if not ok:
            raise RuntimeError("JPEG-Kodierung fehlgeschlagen.")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("DDColor-Fehler")
        raise HTTPException(status_code=500, detail=f"DDColor-Fehler: {exc}") from exc

    logger.info("Kolorisierung erfolgreich (%s Bytes).", len(encoded))
    return Response(
        content=encoded.tobytes(),
        media_type="image/jpeg",
        headers={
            "X-ColorNode-Model": _loaded_model_name or _hub_id(MODEL_NAME),
        },
    )
