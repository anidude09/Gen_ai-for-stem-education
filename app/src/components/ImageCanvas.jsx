/**
 * ImageCanvas.jsx
 *
 * This component is responsible for:
 * - Displaying an uploaded image
 * - Sending the image to a backend for text/shape detection
 * - Scaling the returned coordinates to match the displayed image
 * - Rendering overlays for detected circles/texts
 * - Allowing zoom in/out (via buttons and scroll wheel)
 * - Showing a popup when a shape is selected
 */


import React, { useRef, useState } from "react";
import ShapeOverlay from "./ShapeOverlay";
import Popup from "./Popup";
import ZoomControls from "./ZoomControls";
import useZoom from "../hooks/useZoom";

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
}) {
  const wrapperRef = useRef(null);
  const { zoom, zoomIn, zoomOut, handleWheel } = useZoom({ min: 1, max: 3, step: 0.25 });
  const [isDetecting, setIsDetecting] = useState(false);

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

      const res = await fetch("http://localhost:8001/detect/", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);

      const data = await res.json();
      const rawCircles = data.circles || [];
      const rawTexts = data.texts || [];

      setRawCircles(rawCircles);
      setRawTexts(rawTexts);

      const scaledCircles = rawCircles.map((c) => ({
        ...c,
        x: c.x * imageInfo.scaleX,
        y: c.y * imageInfo.scaleY,
        r: c.r * Math.min(imageInfo.scaleX, imageInfo.scaleY),
      }));

      const scaledTexts = rawTexts.map((t) => ({
        ...t,
        x1: t.x1 * imageInfo.scaleX,
        y1: t.y1 * imageInfo.scaleY,
        x2: t.x2 * imageInfo.scaleX,
        y2: t.y2 * imageInfo.scaleY,
      }));

      setCircles(scaledCircles);
      setTexts(scaledTexts);
    } catch (err) {
      setError(`Failed to detect shapes: ${err.message}`);
      console.error(err);
    }
    finally {
      setIsDetecting(false);
    }
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <ZoomControls zoom={zoom} zoomIn={zoomIn} zoomOut={zoomOut} />

      <div style={{ margin: "8px 0" }}>
        <button
          onClick={runDetection}
          disabled={!imageInfo || isDetecting}
          className="detect-button"
          aria-busy={isDetecting ? "true" : "false"}
        >
          {isDetecting ? "Detecting..." : "Detect"}
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
        onWheel={handleWheel}
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
            <ShapeOverlay
              imageInfo={imageInfo}
              circles={circles}
              texts={texts}
              setSelectedShape={setSelectedShape}
            />
          )}
        </div>
      </div>

      {selectedShape && imageInfo && (
        <Popup selectedShape={selectedShape} onClose={() => setSelectedShape(null)} zoom={zoom} />
      )}
    </div>
  );
}

export default ImageCanvas;
