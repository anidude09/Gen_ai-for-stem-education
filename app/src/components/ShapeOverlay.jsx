/**
 * ShapeOverlay.jsx
 *
 * This component renders an SVG overlay on top of an image to visually highlight
 * detected circles and text regions. Each shape is clickable, allowing users
 * to select a shape and view detailed information via a popup.
 */


import React from "react";

function ShapeOverlay({ imageInfo, circles, texts, selection, onShapeClick, highlightCircleText }) {
  const handleShapeClick = (e, shape) => {
    e.preventDefault();
    e.stopPropagation();
    // Extra debug logging for OCR results when clicking a circle
    if (shape.r) {
      console.log("Circle clicked. OCR debug:", {
        page_number: shape.page_number,
        circle_text: shape.circle_text,
        raw_texts_top: shape.raw_texts_top,
        raw_texts_bottom: shape.raw_texts_bottom,
      });
    } else {
      console.log("Text box clicked:", shape);
    }
    if (onShapeClick) {
      onShapeClick(shape);
    }
  };

  // Determine if a circle is the highlighted target
  const isHighlighted = (c) => {
    if (!highlightCircleText || !c.circle_text) return false;
    return (
      c.circle_text.trim().toLowerCase() ===
      highlightCircleText.trim().toLowerCase()
    );
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
      {/* Pulsing highlight ring behind the target circle */}
      {circles.filter(isHighlighted).map((c) => (
        <circle
          key={`highlight-${c.id}`}
          cx={c.x}
          cy={c.y}
          r={c.r + 6}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="4"
          className="circle-highlight-pulse"
          style={{ pointerEvents: "none" }}
        />
      ))}

      {circles.map((c) => {
        const hl = isHighlighted(c);
        return (
          <circle
            key={`circle-${c.id}`}
            cx={c.x}
            cy={c.y}
            r={c.r}
            fill={hl ? "rgba(59, 130, 246, 0.28)" : "rgba(255, 0, 0, 0.22)"}
            stroke={hl ? "#2563eb" : "red"}
            strokeWidth={hl ? "3" : "2"}
            onClick={(e) => handleShapeClick(e, c)}
            style={{ cursor: "pointer", pointerEvents: "all" }}
          />
        );
      })}

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
