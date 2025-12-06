/**
 * Page.jsx
 *
 * This component displays a single page image and highlights a specific circle on it.
 * - Reads query parameters `image` (page image URL) and `circle` (circle text to highlight)
 * - Loads the image and calculates scale info for proper overlays
 * - Sends the image to the backend detection API to get all circles
 * - Finds the circle that matches the target text and highlights it
 * - Supports zooming via buttons and mouse wheel
 */


import { useState, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import ZoomControls from "./ZoomControls";
import useZoom from "../hooks/useZoom";
import "../styles/zoom.css";
import ImageUploader from "./ImageUploader"; // Ensure this is imported if we use it directly here or nearby

function Page() {
  const [searchParams] = useSearchParams();
  const targetCircleText = searchParams.get("circle");
  const pageImage = searchParams.get("image");

  const [highlightCircle, setHighlightCircle] = useState(null);
  const [imageInfo, setImageInfo] = useState(null);
  
  const imgRef = useRef(null);
  const wrapperRef = useRef(null);

  const { zoom, zoomIn, zoomOut, handleWheel } = useZoom({ min: 1, max: 3, step: 0.25 });



  const handleImageLoad = () => {
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
  };

  useEffect(() => {
    if (!pageImage || !targetCircleText) {
      setHighlightCircle(null);
      return;
    }

    const detect = async () => {
      try {
        const blob = await fetch(pageImage).then((res) => res.blob());
        const formData = new FormData();
        formData.append("file", blob, "page.png");

        const resp = await fetch("http://localhost:8001/detect/", {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) throw new Error(`Detection failed: ${await resp.text()}`);

        const data = await resp.json();
        const circles = data.circles || [];

        const targetCircle = circles.find(
          (c) =>
            c.circle_text &&
            c.circle_text.trim().toLowerCase() === targetCircleText.trim().toLowerCase()
        );

        setHighlightCircle(targetCircle || null);
      } catch (err) {
        console.error("Detection error:", err);
        setHighlightCircle(null);
      }
    };

    detect();
  }, [pageImage, targetCircleText]);

  const getScaledCircle = () => {
    if (!highlightCircle || !imageInfo) return null;

    return {
      cx: highlightCircle.x * imageInfo.scaleX,
      cy: highlightCircle.y * imageInfo.scaleY,
      r: highlightCircle.r * Math.min(imageInfo.scaleX, imageInfo.scaleY),
    };
  };

  const scaledCircle = getScaledCircle();

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <ZoomControls zoom={zoom} zoomIn={zoomIn} zoomOut={zoomOut} />

      {pageImage && (
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
              src={pageImage}
              alt="Page"
              onLoad={handleImageLoad}
              style={{
                width: imageInfo ? imageInfo.clientWidth : "100%",
                height: imageInfo ? imageInfo.clientHeight : "auto",
                display: "block",
                userSelect: "none",
              }}
              onError={(e) => {
                console.error("Image failed to load:", pageImage);
                e.target.alt = "Failed to load image";
              }}
            />

            {/* Circle overlay */}
            {scaledCircle && (
              <svg
                width={imageInfo?.clientWidth || 0}
                height={imageInfo?.clientHeight || 0}
                style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none" }}
              >
                <circle
                  cx={scaledCircle.cx}
                  cy={scaledCircle.cy}
                  r={scaledCircle.r}
                  stroke="blue"
                  strokeWidth="3"
                  fill="none"
                />
              </svg>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Page;