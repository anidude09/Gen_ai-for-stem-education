/**
 * ShapeOverlay.jsx
 *
 * This component renders an SVG overlay on top of an image to visually highlight
 * detected circles and text regions. Each shape is clickable, allowing users
 * to select a shape and view detailed information via a popup.
 */


import React from "react";

function ShapeOverlay({ imageInfo, circles, texts, selection, setSelectedShape }) {
  const handleShapeClick = (e, shape) => {
    e.preventDefault();
    e.stopPropagation();
    console.log("Shape clicked:", shape); 
    setSelectedShape(shape);
  };

  return (
    <svg
      className="overlay-svg"
      width={imageInfo.clientWidth}
      height={imageInfo.clientHeight}
      viewBox={`0 0 ${imageInfo.clientWidth} ${imageInfo.clientHeight}`}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        pointerEvents: "auto",
        zIndex: 10,
        transformOrigin: "0 0",
      }}
    >
      {circles.map((c) => (
        <circle
          key={`circle-${c.id}`}
          cx={c.x}
          cy={c.y}
          r={c.r}
          fill="rgba(255, 0, 0, 0.22)"
          stroke="red"
          strokeWidth="2"
          onClick={(e) => handleShapeClick(e, c)}
          style={{ cursor: "pointer", pointerEvents: "all" }}
        />
      ))}

      {texts.map((t) => (
        <rect
          key={`text-${t.id}`}
          x={t.x1}
          y={t.y1}
          width={t.x2 - t.x1}
          height={t.y2 - t.y1}
          fill="rgba(0,255,0,0.18)"
          stroke="green"
          strokeWidth="2"
          onClick={(e) => handleShapeClick(e, t)}
          style={{ cursor: "pointer", pointerEvents: "all" }}
        />
      ))}

      {selection && (
        <rect
          x={selection.x1}
          y={selection.y1}
          width={selection.x2 - selection.x1}
          height={selection.y2 - selection.y1}
          fill="rgba(0, 120, 255, 0.12)"
          stroke="#0078ff"
          strokeWidth="2"
          strokeDasharray="6 4"
          pointerEvents="none"
        />
      )}
    </svg>
  );
}

export default ShapeOverlay;
