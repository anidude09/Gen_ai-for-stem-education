/**
 * Popup.jsx
 *
 * This component displays a popup box with information about a selected shape (circle or text).
 * - For circles: shows page number and circle text, with a button to navigate to the corresponding page.
 * - For text: fetches additional info from the LLM backend and displays it.
 * - Supports zoomed image coordinates without scaling the popup itself.
 * - Provides a close button to dismiss the popup.
 */


import { useState, useEffect } from "react";
import { logActivity } from "../utils/activityLogger";

function Popup({ selectedShape, onClose, zoom = 1, onNavigateToPage, sessionId }) {
  const [info, setInfo] = useState(null);

  // Log whenever a popup is opened for a selected shape
  useEffect(() => {
    if (!selectedShape || !sessionId) return;

    const isCircle = Boolean(selectedShape.r);
    logActivity({
      sessionId,
      eventType: isCircle ? "circle_popup_opened" : "text_popup_opened",
      eventData: selectedShape,
    });
  }, [selectedShape, sessionId]);

  useEffect(() => {
    // Only fetch explanation + images when a TEXT selection is active
    if (!selectedShape || selectedShape.r) return;
    setInfo("Loading...");

    if (sessionId) {
      logActivity({
        sessionId,
        eventType: "text_explanation_requested",
        eventData: { text: selectedShape.text || "Unlabeled text" },
      });
    }

    fetch("http://localhost:8001/llm-images/explain_with_images", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: selectedShape.text || "Unlabeled text" }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => setInfo(data))
      .catch((error) => {
        console.error("LLM+image fetch error:", error);
        setInfo("Error generating info");
      });
  }, [selectedShape, sessionId]);

  if (!selectedShape) return null;

  // ✅ Apply zoom only to coordinates, not to popup size
  const left =
    (selectedShape.r
      ? selectedShape.x + selectedShape.r + 10
      : selectedShape.x2 + 10) * zoom;

  const top =
    (selectedShape.r
      ? selectedShape.y - selectedShape.r / 2
      : selectedShape.y1) * zoom;

  // Redirect handler
  const handleRedirect = (e, pageNumber, circleText) => {
    e.preventDefault();
    e.stopPropagation();

    console.log("Go to page button clicked", {
      pageNumber,
      circleText,
      hasNavigateHandler: !!onNavigateToPage,
    });

    if (!pageNumber) {
      console.log("Missing navigation data:", { pageNumber });
      return;
    }

    const pageImageUrl = `/images/${pageNumber}.png`;

    if (sessionId) {
      logActivity({
        sessionId,
        eventType: "navigate_to_page",
        eventData: {
          pageNumber,
          circleText,
          pageImageUrl,
        },
      });
    }

    if (onNavigateToPage) {
      // Let the parent (MainPage) handle switching tabs / images.
      onNavigateToPage(pageImageUrl, pageNumber, circleText);
    } else {
      // Fallback: direct navigation if no handler is provided.
      let targetUrl = `/page?image=${encodeURIComponent(pageImageUrl)}`;
      if (circleText) {
        targetUrl += `&circle=${encodeURIComponent(circleText)}`;
      }
      console.log("Fallback navigation to detail page:", {
        targetUrl,
        pageImageUrl,
        circleText,
      });
      window.location.href = targetUrl;
    }

    onClose();
  };

  return (
    <div
      className="popup-box"
      onClick={(e) => e.stopPropagation()}
      style={{
        position: "absolute",
        left: `${left}px`,
        top: `${top}px`,
        zIndex: 1001,
        // Glassy / frosted card
        backgroundColor: "rgba(255, 255, 255, 0.7)",
        border: "1px solid rgba(255, 255, 255, 0.4)",
        borderRadius: "8px",
        padding: "10px",
        boxShadow: "0 4px 20px rgba(0,0,0,0.25)",
        minWidth: "320px",
        maxWidth: "420px",
        backdropFilter: "blur(8px)",
        color: "#000",
      }}
    >
      {selectedShape.r ? (
        <div>
          <h4>Circle Information</h4>
          {selectedShape.page_number ? (
            <ul style={{ listStyle: "none", padding: 0 }}>
              <li style={{ marginBottom: "8px" }}>
                <strong>Page Number:</strong> {selectedShape.page_number}
              </li>
              {selectedShape.circle_text && (
                <li>
                  <strong>Circle Text:</strong> {selectedShape.circle_text}
                </li>
              )}
              <li style={{ marginTop: "5px" }}>
                <button
                  style={{
                    cursor: "pointer",
                    color: "white",
                    backgroundColor: "#007bff",
                    border: "none",
                    padding: "5px 10px",
                    borderRadius: "4px",
                  }}
                  onClick={(e) =>
                    handleRedirect(
                      e,
                      selectedShape.page_number,
                      selectedShape.circle_text
                    )
                  }
                >
                  Go to page {selectedShape.page_number}
                </button>
              </li>
            </ul>
          ) : (
            <p>No page number available for navigation.</p>
          )}

          {/* Debug: show raw OCR tokens for this circle */}
          {(selectedShape.raw_texts_top || selectedShape.raw_texts_bottom) && (
            <div style={{ marginTop: "10px", fontSize: "0.8rem" }}>
              <strong>OCR Debug:</strong>
              {Array.isArray(selectedShape.raw_texts_top) &&
                selectedShape.raw_texts_top.length > 0 && (
                  <div>
                    <em>Top (circle) text:</em>{" "}
                    {selectedShape.raw_texts_top.join(" | ")}
                  </div>
                )}
              {Array.isArray(selectedShape.raw_texts_bottom) &&
                selectedShape.raw_texts_bottom.length > 0 && (
                  <div>
                    <em>Bottom (page) text:</em>{" "}
                    {selectedShape.raw_texts_bottom.join(" | ")}
                  </div>
                )}
            </div>
          )}

          <button
            onClick={onClose}
            style={{
              marginTop: "10px",
              padding: "5px 10px",
              backgroundColor: "#6c757d",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Close
          </button>
        </div>
      ) : (
        <div>
          <h4>Detected Text</h4>
          <p>
            <strong>Text:</strong> {selectedShape.text || "Text"}
          </p>

          {typeof info === "string" ? (
            <p>
              <strong>Info:</strong> {info || "Click to generate info"}
            </p>
          ) : info ? (
            <div>
              {Array.isArray(info.summary) && info.summary.length > 0 && (
                <div style={{ marginBottom: "8px" }}>
                  <strong>Summary:</strong>
                  <ul style={{ marginTop: "6px" }}>
                    {info.summary.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {Array.isArray(info.key_terms) && info.key_terms.length > 0 && (
                <div style={{ marginBottom: "8px" }}>
                  <strong>Key Terms:</strong>
                  <ul style={{ marginTop: "6px" }}>
                    {info.key_terms.map((t, idx) => (
                      <li key={idx}>
                        <em>{t.term}</em>: {t.definition}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {Array.isArray(info.unit_conversions) && info.unit_conversions.length > 0 && (
                <div style={{ marginBottom: "8px" }}>
                  <strong>Unit Conversions:</strong>
                  <ul style={{ marginTop: "6px" }}>
                    {info.unit_conversions.map((u, idx) => (
                      <li key={idx}>
                        {u.original} → {u.si}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {Array.isArray(info.images) && info.images.length > 0 && (
                <div style={{ marginBottom: "8px" }}>
                  <strong>Related images:</strong>
                  <div
                    style={{
                      display: "flex",
                      gap: "8px",
                      marginTop: "6px",
                      flexWrap: "nowrap",
                      overflowX: "auto",
                    }}
                  >
                    {info.images.map((img, idx) => (
                      <a
                        key={idx}
                        href={img.page_url || img.image_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ textDecoration: "none", color: "inherit" }}
                      >
                        <figure
                          style={{
                            margin: 0,
                            textAlign: "center",
                            maxWidth: "120px",
                          }}
                        >
                          <img
                            src={img.thumbnail_url || img.image_url}
                            alt={img.title || "Related construction image"}
                            style={{
                              maxWidth: "120px",
                              maxHeight: "120px",
                              borderRadius: "4px",
                              objectFit: "cover",
                              border: "1px solid #ddd",
                            }}
                          />
                          <figcaption
                            style={{ fontSize: "0.75rem", marginTop: "4px" }}
                          >
                            {img.title
                              ? img.title.slice(0, 50)
                              : img.source}
                          </figcaption>
                        </figure>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {info.clarifying_question && (
                <div style={{ marginTop: "6px", fontStyle: "italic" }}>
                  {info.clarifying_question}
                </div>
              )}
            </div>
          ) : (
            <p>Click to generate info</p>
          )}

          <button
            onClick={onClose}
            style={{
              marginTop: "10px",
              padding: "5px 10px",
              backgroundColor: "#6c757d",
              color: "white",
              border: "none",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Close
          </button>
        </div>
      )}
    </div>
  );
}

export default Popup;

