// ImageCanvas — displays uploaded image, runs detection, renders shape overlays and popups

import React, { useRef, useState } from "react";
import ShapeOverlay from "./ShapeOverlay";
import Popup from "./Popup";
import ZoomControls from "./ZoomControls";
import { logActivity } from "../utils/activityLogger";
import { scaleCircles, scaleTexts } from "../utils/scaleShapes";
import { API_BASE_URL } from "../config";

function ImageCanvas({
  imageUrl,
  imgRef,
  setLoaded,
  setError,
  setImageInfo,
  setCircles,
  setTexts,
  setRawCircles,
  setRawTexts,
  loaded,
  imageInfo,
  circles,
  texts,
  setSelectedShape,
  selectedShape,
  sessionId,
  onNavigateToPage,
  zoom,
  zoomIn,
  zoomOut,
  highlightCircleText,
  vlmResult,
}) {
  const wrapperRef = useRef(null);

  const [isDetecting, setIsDetecting] = useState(false);
  const [selection, setSelection] = useState(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionStart, setSelectionStart] = useState(null);

  const handleImageLoad = async () => {
    if (!imgRef.current) return;

    const info = {
      naturalWidth: imgRef.current.naturalWidth,
      naturalHeight: imgRef.current.naturalHeight,
      clientWidth: imgRef.current.clientWidth,
      clientHeight: imgRef.current.clientHeight,
      scaleX: imgRef.current.clientWidth / imgRef.current.naturalWidth,
      scaleY: imgRef.current.clientHeight / imgRef.current.naturalHeight,
    };
    setImageInfo(info);
    setLoaded(true);
  };



  const runDetection = async () => {
    try {
      setError(null);
      setIsDetecting(true);
      if (!imageUrl || !imageInfo) {
        throw new Error("Image not ready. Please wait for it to load.");
      }

      const blob = await fetch(imageUrl).then((r) => r.blob());
      const formData = new FormData();
      formData.append("file", blob, "image.png");

      logActivity({
        sessionId,
        eventType: "detect_full_image_start",
        eventData: { imageUrl },
      });

      const res = await fetch(`${API_BASE_URL}/detect/`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);

      const data = await res.json();
      const rawCircles = data.circles || [];
      const rawTexts = data.texts || [];

      setRawCircles(rawCircles);
      setRawTexts(rawTexts);
      setCircles(scaleCircles(rawCircles, imageInfo));
      setTexts(scaleTexts(rawTexts, imageInfo));

      logActivity({
        sessionId,
        eventType: "detect_full_image_complete",
        eventData: {
          imageUrl,
          circlesCount: rawCircles.length,
          textsCount: rawTexts.length,
        },
      });
    } catch (err) {
      setError(`Failed to detect shapes: ${err.message}`);
      console.error(err);
    }
    finally {
      setIsDetecting(false);
    }
  };

  const runRegionDetection = async () => {
    try {
      setError(null);
      if (!imageUrl || !imageInfo) {
        throw new Error("Image not ready. Please wait for it to load.");
      }
      if (!selection) {
        throw new Error("No region selected. Drag on the image to select an area.");
      }

      const { x1, y1, x2, y2 } = selection;
      const widthClient = x2 - x1;
      const heightClient = y2 - y1;
      if (widthClient <= 0 || heightClient <= 0) {
        throw new Error("Selected region is too small.");
      }

      const x = Math.round(x1 / imageInfo.scaleX);
      const y = Math.round(y1 / imageInfo.scaleY);
      const w = Math.round(widthClient / imageInfo.scaleX);
      const h = Math.round(heightClient / imageInfo.scaleY);

      setIsDetecting(true);

      logActivity({
        sessionId,
        eventType: "detect_region_start",
        eventData: {
          imageUrl,
          selectionClient: { x1, y1, x2, y2 },
          selectionImage: { x, y, w, h },
        },
      });

      const blob = await fetch(imageUrl).then((r) => r.blob());
      const formData = new FormData();
      formData.append("file", blob, "image.png");
      formData.append("x", String(x));
      formData.append("y", String(y));
      formData.append("w", String(w));
      formData.append("h", String(h));

      const res = await fetch(`${API_BASE_URL}/detect/region-detect`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);

      const data = await res.json();
      const rawCircles = data.circles || [];
      const rawTexts = data.detections || [];

      setRawCircles(rawCircles);
      setRawTexts(rawTexts);
      setCircles(scaleCircles(rawCircles, imageInfo));
      setTexts(scaleTexts(rawTexts, imageInfo));

      logActivity({
        sessionId,
        eventType: "detect_region_complete",
        eventData: {
          imageUrl,
          selectionClient: { x1, y1, x2, y2 },
          regionCirclesCount: rawCircles.length,
          regionTextsCount: rawTexts.length,
        },
      });
    } catch (err) {
      setError(`Failed to detect in region: ${err.message}`);
      console.error(err);
    } finally {
      setIsDetecting(false);
      setSelection(null); // Clear selection so the dark overlay goes away
    }
  };

  const clientToImageCoords = (event) => {
    if (!wrapperRef.current) return null;
    const rect = wrapperRef.current.getBoundingClientRect();
    const x = (event.clientX - rect.left) / zoom;
    const y = (event.clientY - rect.top) / zoom;
    return { x, y };
  };

  const handleMouseDown = (event) => {
    if (!imageInfo) return;
    if (event.button !== 0) return; // left button only

    const coords = clientToImageCoords(event);
    if (!coords) return;

    const { x, y } = coords;
    const clampedX = Math.max(0, Math.min(x, imageInfo.clientWidth));
    const clampedY = Math.max(0, Math.min(y, imageInfo.clientHeight));

    setSelectionStart({ x: clampedX, y: clampedY });
    setSelection({ x1: clampedX, y1: clampedY, x2: clampedX, y2: clampedY });
    setIsSelecting(true);
  };

  const handleMouseMove = (event) => {
    if (!isSelecting || !selectionStart || !imageInfo) return;

    const coords = clientToImageCoords(event);
    if (!coords) return;

    const { x, y } = coords;
    const clampedX = Math.max(0, Math.min(x, imageInfo.clientWidth));
    const clampedY = Math.max(0, Math.min(y, imageInfo.clientHeight));

    const x1 = Math.min(selectionStart.x, clampedX);
    const y1 = Math.min(selectionStart.y, clampedY);
    const x2 = Math.max(selectionStart.x, clampedX);
    const y2 = Math.max(selectionStart.y, clampedY);

    setSelection({ x1, y1, x2, y2 });
  };

  const stopSelecting = () => {
    if (isSelecting) {
      setIsSelecting(false);
    }
  };

  const handleShapeSelected = (shape) => {
    setSelectedShape(shape);

    const isCircle = Boolean(shape.r);

    logActivity({
      sessionId,
      eventType: isCircle ? "circle_selected" : "text_selected",
      eventData: {
        shape,
        imageUrl,
      },
    });
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {imageUrl && (
        <ZoomControls zoom={zoom} zoomIn={zoomIn} zoomOut={zoomOut} />
      )}

      <div style={{ margin: "8px 0" }}>
          <button
            onClick={runDetection}
            disabled={!imageInfo || isDetecting}
            className="detect-button"
            aria-busy={isDetecting ? "true" : "false"}
          >
            {isDetecting ? "Detecting..." : "Detect"}
          </button>
          <button
            onClick={runRegionDetection}
            disabled={!imageInfo || !selection || isDetecting}
            className="detect-button"
            style={{ marginLeft: "8px" }}
            aria-busy={isDetecting ? "true" : "false"}
          >
            {isDetecting ? "Detecting..." : "Detect in selection"}
          </button>
        </div>

      {isDetecting && (
        <div className="loading-bar" role="status" aria-label="Detecting">
          <div className="loading-bar__indeterminate"></div>
        </div>
      )}

      <div
        className="image-container"
        style={{ position: "relative", display: "inline-block", overflow: "auto" }}
      // onWheel handled by parent if needed, or can be re-added here if we pass handleWheel prop
      >
        <div
          ref={wrapperRef}
          className="zoom-wrapper"
          style={{
            position: "relative",
            width: imageInfo ? imageInfo.clientWidth : "auto",
            height: imageInfo ? imageInfo.clientHeight : "auto",
            transform: `scale(${zoom})`,
            transformOrigin: "0 0",
            transition: "transform 120ms ease-out",
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={stopSelecting}
          onMouseLeave={stopSelecting}
        >
          <img
            ref={imgRef}
            src={imageUrl}
            alt="uploaded"
            onLoad={handleImageLoad}
            style={{
              width: imageInfo ? imageInfo.clientWidth : "100%",
              height: imageInfo ? imageInfo.clientHeight : "auto",
              display: "block",
              userSelect: "none",
            }}
          />
          {loaded && imageInfo && (
            <>
              <ShapeOverlay
                imageInfo={imageInfo}
                circles={circles}
                texts={texts}
                selection={selection}
                onShapeClick={handleShapeSelected}
                highlightCircleText={highlightCircleText}
              />
              {selectedShape && (
                <Popup
                  selectedShape={selectedShape}
                  onClose={() => setSelectedShape(null)}
                  zoom={zoom}
                  onNavigateToPage={onNavigateToPage}
                  sessionId={sessionId}
                  vlmResult={vlmResult}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ImageCanvas;
