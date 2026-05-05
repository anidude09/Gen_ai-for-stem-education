"""engine.py - PaddleOCR singleton, core OCR, and tiled OCR for large images."""

from __future__ import annotations

import threading
import cv2
import numpy as np


# PaddleOCR singleton (lazy, thread-safe)──────

_PADDLE_OCR = None
_PADDLE_OCR_LOCK = threading.Lock()


def get_paddle_ocr():
    global _PADDLE_OCR
    if _PADDLE_OCR is not None:
        return _PADDLE_OCR

    with _PADDLE_OCR_LOCK:
        if _PADDLE_OCR is not None:
            return _PADDLE_OCR

        print("[construction_ocr] Loading PaddleOCR models …")
        try:
            import os
            import logging
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            # Suppress PaddlePaddle C++ (GLOG) warnings — must be set before paddle import
            os.environ.setdefault("GLOG_minloglevel", "2")
            os.environ.setdefault("GLOG_logtostderr", "0")
            # Suppress Python-level ppocr logger
            ppocr_logger = logging.getLogger("ppocr")
            ppocr_logger.setLevel(logging.ERROR)
            ppocr_logger.propagate = False
            logging.getLogger("ppocr.utils.utility").setLevel(logging.ERROR)
            
            # Check if GPU is available via PaddlePaddle
            use_gpu = False
            try:
                import paddle
                cuda_compiled = paddle.device.is_compiled_with_cuda()
                gpu_count = paddle.device.cuda.device_count() if cuda_compiled else 0
                use_gpu = cuda_compiled and gpu_count > 0
                if use_gpu:
                    print(f"[construction_ocr] PaddlePaddle GPU detected: {paddle.device.get_device()} ({gpu_count} device(s))")
                else:
                    print("[construction_ocr] PaddlePaddle CPU only (no CUDA or no GPU found)")
            except Exception:
                print("[construction_ocr] Could not detect PaddlePaddle device, defaulting to CPU")
            
            from paddleocr import PaddleOCR
            _PADDLE_OCR = PaddleOCR(
                use_gpu=use_gpu,
                use_textline_orientation=True,
                lang="en",
                ocr_version="PP-OCRv4",
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                show_log=False,
            )
            print(f"[construction_ocr] PaddleOCR ready ({'GPU' if use_gpu else 'CPU'})")
        except Exception as _e:
            print(f"[construction_ocr] PaddleOCR init failed: {_e}")
            _PADDLE_OCR = None

    return _PADDLE_OCR


# Configuration

OCR_MIN_CONFIDENCE = 0.30
TILE_SIZE     = 4000
TILE_OVERLAP  = 200
TILE_THRESHOLD = 4000


def run_paddle_ocr(img_bgr: np.ndarray) -> list[tuple]:
    ocr = get_paddle_ocr()
    if ocr is None:
        print("[construction_ocr] PaddleOCR not available")
        return []

    try:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    except Exception:
        img_rgb = img_bgr

    results = []
    try:
        # Check if using PaddleOCR 3.x (PaddleX wrapper) or 2.x natively
        if hasattr(ocr, "predict"):
            pages = ocr.predict(img_rgb)
        else:
            pages = ocr.ocr(img_rgb, cls=False)

        for page in pages:
            if not page:
                continue
            
            # Handle PaddleOCR 2.x API output: page is a list of lines [ [quad_points], (text, score) ]
            if isinstance(page, list):
                for line in page:
                    if not line or len(line) < 2: continue
                    quad = line[0]
                    text = line[1][0]
                    conf = line[1][1]
                    
                    if float(conf) < OCR_MIN_CONFIDENCE or not str(text).strip():
                        continue
                        
                    pts = [[float(p[0]), float(p[1])] for p in quad]
                    results.append((pts, str(text).strip(), float(conf)))
                continue

            # Handle PaddleOCR 3.x API output (PaddleX objects/dicts)
            try:
                if hasattr(page, "rec_texts"):
                    quads  = page.dt_polys
                    texts  = page.rec_texts
                    scores = page.rec_scores
                else:
                    quads  = page["dt_polys"]
                    texts  = page["rec_texts"]
                    scores = page["rec_scores"]

                for quad, text, conf in zip(quads, texts, scores):
                    conf = float(conf)
                    text = str(text).strip()
                    if conf < OCR_MIN_CONFIDENCE or not text:
                        continue
                    pts = [[float(p[0]), float(p[1])] for p in quad]
                    results.append((pts, text, conf))
            except Exception as e:
                print(f"[construction_ocr] OCR page parse error: {e}")
                
    except Exception as e:
        print(f"[construction_ocr] PaddleOCR processing error: {e}")
        
    return results


def box_iou(box_a: tuple, box_b: tuple) -> float:
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def run_paddle_ocr_tiled(img_bgr: np.ndarray) -> list[tuple]:
    h, w = img_bgr.shape[:2]

    if max(h, w) <= TILE_THRESHOLD:
        return run_paddle_ocr(img_bgr)

    step = TILE_SIZE - TILE_OVERLAP
    all_results = []
    tile_count = 0

    for y_off in range(0, h, step):
        for x_off in range(0, w, step):
            x2 = min(x_off + TILE_SIZE, w)
            y2 = min(y_off + TILE_SIZE, h)
            tile = img_bgr[y_off:y2, x_off:x2]

            tile_results = run_paddle_ocr(tile)
            tile_count += 1

            for pts, text, conf in tile_results:
                global_pts = [[p[0] + x_off, p[1] + y_off] for p in pts]
                all_results.append((global_pts, text, conf))

    print(f"[construction_ocr] Tiled OCR: {tile_count} tiles, {len(all_results)} raw detections")

    if not all_results:
        return all_results

    # Dedup: keep higher-confidence boxes, discard overlapping lower-confidence
    all_results.sort(key=lambda r: r[2], reverse=True)
    keep = []
    for pts, text, conf in all_results:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        bbox = (min(xs), min(ys), max(xs), max(ys))

        is_dup = False
        for k_pts, k_text, k_conf in keep:
            k_xs = [p[0] for p in k_pts]
            k_ys = [p[1] for p in k_pts]
            k_bbox = (min(k_xs), min(k_ys), max(k_xs), max(k_ys))

            if box_iou(bbox, k_bbox) > 0.50:
                is_dup = True
                break

        if not is_dup:
            keep.append((pts, text, conf))

    print(f"[construction_ocr] After tile dedup: {len(keep)} unique detections")
    return keep
