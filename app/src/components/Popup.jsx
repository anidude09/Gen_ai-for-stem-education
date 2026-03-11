// Popup — shows info for a selected shape (circle navigation or LLM text explanation)

import { useState, useEffect } from "react";
import { logActivity } from "../utils/activityLogger";
import { API_BASE_URL } from "../config";

function Popup({ selectedShape, onClose, zoom = 1, onNavigateToPage, sessionId, vlmResult }) {
  const [info, setInfo] = useState(null);


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
    if (!selectedShape || selectedShape.r) return;
    setInfo("Loading...");

    if (sessionId) {
      logActivity({
        sessionId,
        eventType: "text_explanation_requested",
        eventData: { text: selectedShape.text || "Unlabeled text" },
      });
    }

    fetch(`${API_BASE_URL}/llm-images/explain_with_images`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content: selectedShape.text || "Unlabeled text",
        drawing_context: vlmResult ? {
          drawing_type: vlmResult.drawing_type,
          summary: vlmResult.summary,
          text_labels: vlmResult.text_labels,
        } : null,
      }),
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


  const handleRedirect = (e, pageNumber, circleText) => {
    e.preventDefault();
    e.stopPropagation();

    if (!pageNumber || !onNavigateToPage) return;

    const imagePath = `/images/${pageNumber}.png`;

    if (sessionId) {
      logActivity({
        sessionId,
        eventType: "circle_navigate_to_page",
        eventData: {
          page_number: pageNumber,
          circle_text: circleText,
        },
      });
    }

    onNavigateToPage(imagePath, pageNumber, circleText);
    onClose();
  };

  // Position popup near the shape, counter-scale so text stays readable

  const rawLeft = selectedShape.r
    ? selectedShape.x + selectedShape.r + 10
    : selectedShape.x2 + 10;

  const rawTop = selectedShape.r
    ? selectedShape.y - selectedShape.r / 2
    : selectedShape.y1;

  // Use page_number if available, otherwise try parsing circle_text as page ref
  let navPage = selectedShape.page_number;
  if (!navPage && selectedShape.circle_text && /^[A-Z]\d+(\.\d+)?$/i.test(selectedShape.circle_text)) {
    navPage = selectedShape.circle_text.toUpperCase();
  }

  return (
    <div
      className="popup-box"
      onClick={(e) => e.stopPropagation()}
      style={{
        position: "absolute",
        left: `${rawLeft}px`,
        top: `${rawTop}px`,
        zIndex: 1001,
        transform: `scale(${1 / zoom})`,
        transformOrigin: "top left",


        backgroundColor: "rgba(30, 41, 59, 0.85)", // Dark slate
        border: "1px solid rgba(255, 255, 255, 0.2)",
        borderRadius: "12px",
        padding: "16px",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
        minWidth: "320px",
        maxWidth: "420px",
        backdropFilter: "blur(12px)",
        color: "#f1f5f9", // Light text
        fontSize: "14px",
      }}
    >
      {selectedShape.r ? (
        <div>
          <h4 style={{ marginTop: 0, marginBottom: "12px", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "8px" }}>
            Circle Information
          </h4>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {navPage ? (
              <li style={{ marginBottom: "8px" }}>
                <strong style={{ color: "#94a3b8" }}>Page:</strong> {navPage}
              </li>
            ) : (
              <li style={{ marginBottom: "8px", color: "#cbd5e1" }}>
                No page reference detected.
              </li>
            )}
            {selectedShape.circle_text && (
              <li style={{ marginBottom: "12px" }}>
                <strong style={{ color: "#94a3b8" }}>Detail:</strong> {selectedShape.circle_text}
              </li>
            )}

            {navPage && (
              <li>
                <button
                  style={{
                    cursor: "pointer",
                    color: "white",
                    backgroundColor: "rgba(59, 130, 246, 0.8)",
                    border: "none",
                    padding: "8px 16px",
                    borderRadius: "6px",
                    width: "100%",
                    transition: "background 0.2s",
                  }}
                  onMouseOver={(e) => (e.target.style.backgroundColor = "rgba(37, 99, 235, 1)")}
                  onMouseOut={(e) => (e.target.style.backgroundColor = "rgba(59, 130, 246, 0.8)")}
                  onClick={(e) =>
                    handleRedirect(
                      e,
                      navPage,
                      selectedShape.circle_text
                    )
                  }
                >
                  Go to Page {navPage}
                </button>
              </li>
            )}
          </ul>



          <button
            onClick={onClose}
            style={{
              marginTop: "12px",
              padding: "6px 12px",
              backgroundColor: "transparent",
              color: "#94a3b8",
              border: "1px solid rgba(148, 163, 184, 0.3)",
              borderRadius: "6px",
              cursor: "pointer",
              width: "100%",
            }}
            onMouseOver={(e) => {
              e.target.style.borderColor = "#cbd5e1";
              e.target.style.color = "#f1f5f9";
            }}
            onMouseOut={(e) => {
              e.target.style.borderColor = "rgba(148, 163, 184, 0.3)";
              e.target.style.color = "#94a3b8";
            }}
          >
            Close
          </button>
        </div>
      ) : (
        <div>
          <h4 style={{ marginTop: 0, marginBottom: "12px", borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "8px" }}>
            Explanation
          </h4>
          <p style={{ marginBottom: "12px", fontSize: "1.1em" }}>
            <strong style={{ color: "#60a5fa" }}>{selectedShape.text || "Text"}</strong>
          </p>

          {typeof info === "string" ? (
            <div style={{ padding: "20px", textAlign: "center", color: "#cbd5e1" }}>
              {info === "Loading..." ? (
                <span>Thinking...</span>
              ) : (
                <span>{info || "Click to generate info"}</span>
              )}
            </div>
          ) : info ? (
            <div style={{ maxHeight: "300px", overflowY: "auto", paddingRight: "4px" }}>
              {Array.isArray(info.summary) && info.summary.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <strong style={{ color: "#94a3b8", display: "block", marginBottom: "4px" }}>Summary</strong>
                  <ul style={{ marginTop: 0, paddingLeft: "20px", color: "#e2e8f0" }}>
                    {info.summary.map((item, idx) => (
                      <li key={idx} style={{ marginBottom: "4px" }}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {Array.isArray(info.key_terms) && info.key_terms.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <strong style={{ color: "#94a3b8", display: "block", marginBottom: "4px" }}>Key Terms</strong>
                  <ul style={{ marginTop: 0, paddingLeft: "20px", color: "#e2e8f0" }}>
                    {info.key_terms.map((t, idx) => (
                      <li key={idx} style={{ marginBottom: "4px" }}>
                        <span style={{ color: "#f8fafc", fontWeight: 500 }}>{t.term}</span>: <span style={{ color: "#cbd5e1" }}>{t.definition}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {Array.isArray(info.unit_conversions) && info.unit_conversions.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <strong style={{ color: "#94a3b8", display: "block", marginBottom: "4px" }}>Conversions</strong>
                  <ul style={{ marginTop: 0, paddingLeft: "20px", color: "#e2e8f0" }}>
                    {info.unit_conversions.map((u, idx) => (
                      <li key={idx}>
                        {u.original} → {u.si}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {Array.isArray(info.images) && info.images.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <strong style={{ color: "#94a3b8", display: "block", marginBottom: "4px" }}>Visual References</strong>
                  <div
                    style={{
                      display: "flex",
                      gap: "10px",
                      marginTop: "8px",
                      overflowX: "auto",
                      paddingBottom: "8px",
                    }}
                  >
                    {info.images.map((img, idx) => (
                      <a
                        key={idx}
                        href={img.page_url || img.image_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ textDecoration: "none", color: "inherit", flex: "0 0 auto" }}
                      >
                        <figure style={{ margin: 0, maxWidth: "120px" }}>
                          <img
                            src={img.thumbnail_url || img.image_url}
                            alt={img.title || "Related image"}
                            style={{
                              width: "120px",
                              height: "90px",
                              borderRadius: "6px",
                              objectFit: "cover",
                              border: "1px solid rgba(255,255,255,0.1)",
                            }}
                          />
                        </figure>
                      </a>
                    ))}
                  </div>
                </div>

              )}


              {info.context && (
                <div style={{ marginTop: "16px", borderTop: "1px solid rgba(255,255,255,0.1)", paddingTop: "12px" }}>
                  <details style={{ cursor: "pointer" }}>
                    <summary style={{ color: "#94a3b8", fontSize: "0.9em", userSelect: "none" }}>
                      Show Source Context
                    </summary>
                    <div
                      style={{
                        marginTop: "8px",
                        padding: "8px",
                        backgroundColor: "rgba(0,0,0,0.2)",
                        borderRadius: "6px",
                        fontSize: "0.85em",
                        color: "#cbd5e1",
                        whiteSpace: "pre-wrap",
                        maxHeight: "200px",
                        overflowY: "auto"
                      }}
                    >
                      {info.context}
                    </div>
                  </details>
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: "#cbd5e1" }}>Click to generate info</p>
          )}

          <button
            onClick={onClose}
            style={{
              marginTop: "16px",
              padding: "8px 16px",
              backgroundColor: "rgba(255,255,255,0.1)",
              color: "#f1f5f9",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              width: "100%",
              transition: "background 0.2s",
            }}
            onMouseOver={(e) => (e.target.style.backgroundColor = "rgba(255,255,255,0.2)")}
            onMouseOut={(e) => (e.target.style.backgroundColor = "rgba(255,255,255,0.1)")}
          >
            Close
          </button>
        </div>
      )
      }
    </div >
  );
}

export default Popup;

