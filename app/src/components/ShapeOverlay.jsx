// ShapeOverlay — SVG overlay for detected circles, text boxes, and selection region

import React from "react";

// Category-colour mapping (matches VLMPanel.jsx)
const CATEGORY_COLORS = {
  room_name: { stroke: "#3b82f6", fill: "rgba(59,130,246,0.25)" },
  dimension: { stroke: "#a855f7", fill: "rgba(168,85,247,0.25)" },
  annotation: { stroke: "#22c55e", fill: "rgba(34,197,94,0.25)" },
  abbreviation: { stroke: "#fbbf24", fill: "rgba(251,191,36,0.25)" },
  symbol: { stroke: "#ef4444", fill: "rgba(239,68,68,0.25)" },
  reference: { stroke: "#14b8a6", fill: "rgba(20,184,166,0.25)" },
  material: { stroke: "#f97316", fill: "rgba(249,115,22,0.25)" },
  other: { stroke: "#64748b", fill: "rgba(100,116,139,0.25)" },
};

function ShapeOverlay({ imageInfo, circles, texts, selection, onShapeClick, highlightCircleText, highlightedTextBox }) {
  const handleShapeClick = (e, shape) => {
    e.preventDefault();
    e.stopPropagation();
    if (shape.r) {
      console.log("Circle clicked. OCR debug:", {
        page_number: shape.page_number,
        circle_text: shape.circle_text,
        raw_texts_top: shape.raw_texts_top,
        raw_texts_bottom: shape.raw_texts_bottom,
      });
    }
    if (onShapeClick) {
      onShapeClick(shape);
    }
  };

  // Determine if a circle is the highlighted target
  const isCircleHighlighted = (c) => {
    if (!highlightCircleText || !c.circle_text) return false;
    return (
      c.circle_text.trim().toLowerCase() ===
      highlightCircleText.trim().toLowerCase()
    );
  };

  // Determine if a text box is the VLM-linked highlight
  const isTextHighlighted = (t) => {
    if (!highlightedTextBox) return false;
    return t.id === highlightedTextBox.id;
  };

  // Get category color for highlighted text box
  const getHighlightColor = () => {
    if (!highlightedTextBox) return CATEGORY_COLORS.other;
    const cat = (highlightedTextBox.category || "other").toLowerCase();
    return CATEGORY_COLORS[cat] || CATEGORY_COLORS.other;
  };

  // Filter out text boxes that fall inside any detected circle
  const isTextInsideCircle = (t) => {
    const textCx = (t.x1 + t.x2) / 2;
    const textCy = (t.y1 + t.y2) / 2;
    for (const c of circles) {
      const dx = textCx - c.x;
      const dy = textCy - c.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      // Text center is within 1.3× circle radius → inside or very close
      if (dist < c.r * 1.3) return true;
    }
    return false;
  };

  const visibleTexts = texts.filter(t => !isTextInsideCircle(t));
  const hlColor = getHighlightColor();

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
      <defs>
        {/* Mask cuts a hole in the dark wash for the selection region */}
        {selection && (
          <mask id="selection-mask">
            <rect x="0" y="0" width={imageInfo.clientWidth} height={imageInfo.clientHeight} fill="white" />
            <rect
              x={selection.x1}
              y={selection.y1}
              width={selection.x2 - selection.x1}
              height={selection.y2 - selection.y1}
              fill="black"
            />
          </mask>
        )}
      </defs>

      {/* Dark wash over image except the selected area */}
      {selection && (
        <rect
          x="0"
          y="0"
          width={imageInfo.clientWidth}
          height={imageInfo.clientHeight}
          fill="rgba(0, 0, 0, 0.45)"
          mask="url(#selection-mask)"
          style={{ pointerEvents: "none" }}
        />
      )}

      {/* Target circle highlight */}
      {circles.filter(isCircleHighlighted).map((c) => (
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
        const hl = isCircleHighlighted(c);
        return (
          <circle
            key={`circle-${c.id}`}
            cx={c.x}
            cy={c.y}
            r={c.r}
            fill={hl ? "rgba(59, 130, 246, 0.28)" : "rgba(255, 140, 50, 0.15)"}
            stroke={hl ? "#2563eb" : "#f97316"}
            strokeWidth={hl ? "3" : "1.5"}
            onClick={(e) => handleShapeClick(e, c)}
            style={{ cursor: "pointer", pointerEvents: "all" }}
          />
        );
      })}

      {/* VLM-linked text highlight */}
      {highlightedTextBox && visibleTexts.filter(isTextHighlighted).map((t) => (
        <rect
          key={`text-highlight-${t.id}`}
          x={t.x1 - 4}
          y={t.y1 - 4}
          width={t.x2 - t.x1 + 8}
          height={t.y2 - t.y1 + 8}
          fill="none"
          stroke={hlColor.stroke}
          strokeWidth="3"
          rx="3"
          className="text-highlight-pulse"
          style={{ pointerEvents: "none" }}
        />
      ))}

      {visibleTexts.map((t) => {
        const hl = isTextHighlighted(t);
        return (
          <rect
            key={`text-${t.id}`}
            x={t.x1}
            y={t.y1}
            width={t.x2 - t.x1}
            height={t.y2 - t.y1}
            fill={hl ? hlColor.fill : "rgba(0,200,0,0.08)"}
            stroke={hl ? hlColor.stroke : "rgba(0,180,0,0.45)"}
            strokeWidth={hl ? "3" : "1"}
            rx={hl ? "2" : "0"}
            onClick={(e) => handleShapeClick(e, t)}
            style={{ cursor: "pointer", pointerEvents: "all" }}
          />
        );
      })}

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
