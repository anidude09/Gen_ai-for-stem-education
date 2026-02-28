"""
paddleocr_test.py

Smoke test for PaddleOCR on a construction drawing.
Uses tile-based OCR for high resolution images to maintain text quality
while keeping memory usage low (~400 MB per tile).

Install first:
    pip install paddlepaddle paddleocr

Usage:
    python experiments/paddleocr_test.py [path/to/image.png]
    python experiments/paddleocr_test.py "Images/page_7 (1).png"
"""

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image


# ── Config ────────────────────────────────────────────────────────────────────
TILE_SIZE    = 4000   # each tile is TILE_SIZE x TILE_SIZE pixels
TILE_OVERLAP = 200    # px overlap between tiles to avoid splitting text
MIN_CONF     = 0.30   # discard detections below 30% confidence
IOU_THRESH   = 0.50   # NMS threshold — merge duplicate boxes from overlaps


def _iou(box_a, box_b):
    """Intersection-over-Union for two (x_min,y_min,x_max,y_max) boxes."""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0, xb - xa) * max(0, yb - ya)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def _nms(detections):
    """Simple NMS: given overlapping boxes from adjacent tiles, keep the
    higher-confidence one when IoU > IOU_THRESH."""
    if not detections:
        return detections
    # Sort by confidence descending
    dets = sorted(detections, key=lambda d: d[2], reverse=True)
    keep = []
    for det in dets:
        bbox = det[3]  # (x_min, y_min, x_max, y_max)
        is_dup = False
        for kept in keep:
            if _iou(bbox, kept[3]) > IOU_THRESH:
                is_dup = True
                break
        if not is_dup:
            keep.append(det)
    return keep


def generate_tiles(img: Image.Image, tile_size=TILE_SIZE, overlap=TILE_OVERLAP):
    """Yield (crop, x_offset, y_offset) for each tile of the image."""
    w, h = img.size
    step = tile_size - overlap
    for y in range(0, h, step):
        for x in range(0, w, step):
            x2 = min(x + tile_size, w)
            y2 = min(y + tile_size, h)
            crop = img.crop((x, y, x2, y2))
            yield crop, x, y


def find_test_image() -> Path:
    data_dir = Path(__file__).parent.parent / "data"
    pngs = list(data_dir.rglob("*.png"))
    if pngs:
        return pngs[0]
    raise FileNotFoundError(
        "No PNG found in data/. Provide an image path as argument:\n"
        "  python"
    )


def main():
    # ── Image ────────────────────────────────────────────────────────────────
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
    else:
        img_path = str(find_test_image())

    img = Image.open(img_path)
    w, h = img.size
    print(f"\n[PaddleOCR] Input image: {img_path}  ({w}x{h})")

    # Decide: tile or whole-image
    needs_tiling = max(w, h) > TILE_SIZE
    if needs_tiling:
        tiles = list(generate_tiles(img))
        print(f"[PaddleOCR] Image is large — splitting into {len(tiles)} overlapping {TILE_SIZE}x{TILE_SIZE} tiles")
    else:
        print(f"[PaddleOCR] Image fits in a single tile — no splitting needed")

    # ── Load PaddleOCR ───────────────────────────────────────────────────────
    print("[PaddleOCR] Loading models ...")
    t0 = time.time()

    from paddleocr import PaddleOCR
    ocr = PaddleOCR(
        use_textline_orientation=True,
        lang="en",
        ocr_version="PP-OCRv4",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
    )
    print(f"[PaddleOCR] Models loaded in {time.time()-t0:.1f}s")

    # ── Run OCR ──────────────────────────────────────────────────────────────
    print("[PaddleOCR] Running OCR ...")
    t0 = time.time()
    raw_detections = []  # (quad_global, text, conf, bbox_global)

    if needs_tiling:
        for idx, (crop, x_off, y_off) in enumerate(tiles):
            # Save tile to temp file (PaddleOCR expects a path or numpy array)
            crop_np = np.array(crop)
            result = list(ocr.predict(crop_np))

            tile_count = 0
            for page in result:
                if page is None:
                    continue
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
                        if conf < MIN_CONF or not text:
                            continue
                        # Offset quad coordinates to global image space
                        pts = [[float(p[0]) + x_off, float(p[1]) + y_off] for p in quad]
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        bbox = (min(xs), min(ys), max(xs), max(ys))
                        raw_detections.append((pts, text, conf, bbox))
                        tile_count += 1
                except Exception as e:
                    print(f"  [warn] tile {idx}: {e}")

            print(f"  tile {idx+1}/{len(tiles)}  offset=({x_off},{y_off})  found {tile_count} texts")
    else:
        # Single image — no tiling
        img_np = np.array(img)
        result = list(ocr.predict(img_np))
        for page in result:
            if page is None:
                continue
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
                    if conf < MIN_CONF or not text:
                        continue
                    pts = [[float(p[0]), float(p[1])] for p in quad]
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    bbox = (min(xs), min(ys), max(xs), max(ys))
                    raw_detections.append((pts, text, conf, bbox))
            except Exception as e:
                print(f"  [warn] {e}")

    elapsed = time.time() - t0

    # ── NMS to remove duplicates from tile overlaps ──────────────────────────
    if needs_tiling:
        before = len(raw_detections)
        detections = _nms(raw_detections)
        print(f"[PaddleOCR] NMS: {before} raw → {len(detections)} unique detections")
    else:
        detections = raw_detections

    print(f"[PaddleOCR] Detected {len(detections)} text regions in {elapsed:.1f}s")

    # ── Print results ─────────────────────────────────────────────────────────
    print("\n" + "="*70)
    print(f"{'#':<4} {'TEXT':<35} {'CONF':>6}  BBOX (x_min,y_min,x_max,y_max)")
    print("="*70)

    total_high_conf = 0
    for i, (pts, text, conf, bbox) in enumerate(detections):
        x_min, y_min, x_max, y_max = [int(v) for v in bbox]
        conf_pct = conf * 100
        flag = "✓" if conf > 0.8 else " "
        print(f"{i:<4} {text[:35]:<35} {conf_pct:>5.1f}%  ({x_min},{y_min},{x_max},{y_max}) {flag}")
        if conf > 0.8:
            total_high_conf += 1

    print("="*70)
    print(f"Total: {len(detections)} regions  |  High confidence (>80%): {total_high_conf}")

    if detections:
        confs = [d[2] for d in detections]
        print(f"Avg confidence: {sum(confs)/len(confs)*100:.1f}%")
        print(f"Min confidence: {min(confs)*100:.1f}%")
        print(f"Max confidence: {max(confs)*100:.1f}%")

    print(f"\n[PaddleOCR] Done. Total inference time: {elapsed:.1f}s")

    # ── Save annotated image with bounding boxes ─────────────────────────────
    from PIL import ImageDraw, ImageFont

    # Work on original full-res image
    annotated = img.copy().convert("RGB")
    draw = ImageDraw.Draw(annotated)

    # Try to use a readable font size proportional to image
    font_size = max(14, min(w, h) // 80)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
    except (OSError, IOError):
        font = ImageFont.load_default()

    for pts, text, conf, bbox in detections:
        x_min, y_min, x_max, y_max = [int(v) for v in bbox]
        # Green for high confidence, orange for lower
        color = (0, 200, 0) if conf > 0.8 else (255, 165, 0)
        draw.rectangle([x_min, y_min, x_max, y_max], outline=color, width=3)
        # Label with text and confidence
        label = f"{text[:25]} ({conf*100:.0f}%)"
        # Draw label background
        left, top, right, bottom = draw.textbbox((x_min, y_min - font_size - 4), label, font=font)
        draw.rectangle([left - 1, top - 1, right + 1, bottom + 1], fill=color)
        draw.text((x_min, y_min - font_size - 4), label, fill="black", font=font)

    input_stem = Path(img_path).stem
    out_path = str(Path(__file__).parent / f"paddleocr_output_{input_stem}.png")
    annotated.save(out_path)
    print(f"[PaddleOCR] Annotated image saved to: {out_path}")


if __name__ == "__main__":
    main()
