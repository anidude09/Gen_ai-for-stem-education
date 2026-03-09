import { useState, useRef, useEffect, useMemo } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ImageUploader from "./components/ImageUploader";
import ImageCanvas from "./components/ImageCanvas";
import LoginForm from "./components/Loginform";
import Page from "./components/Page";
import VLMPanel from "./components/VLMPanel";
import useLogout from "./hooks/useLogout";
import useautoLogout from "./hooks/useautoLogout";
import useZoom from "./hooks/useZoom";
import { API_BASE_URL } from "./config";
import "./styles/App.css";

function MainPage() {
  // Workspace views state dictionary
  // Keys are "main" or "detail". We store all detection arrays and layout info here.
  const [views, setViews] = useState({
    main: {
      imageUrl: null,
      rawCircles: [],
      rawTexts: [],
      circles: [],
      texts: [],
      selectedShape: null,
      loaded: false,
      error: null,
      imageInfo: null,
    },
    detail: {
      imageUrl: null,
      pageLabel: null,
      targetCircleText: null,
      rawCircles: [],
      rawTexts: [],
      circles: [],
      texts: [],
      selectedShape: null,
      loaded: false,
      error: null,
      imageInfo: null,
    }
  });

  // Which "tab" is active in the workspace: "main" or "detail"
  const [activeView, setActiveView] = useState("main");

  // Helper to update a single view's state
  const updateView = (viewName, updates) => {
    setViews((prev) => ({
      ...prev,
      [viewName]: { ...prev[viewName], ...updates },
    }));
  };

  // We expose a setter for the main imageUrl to stick with the existing ImageUploader contract
  const setImageUrl = (url) => updateView("main", { imageUrl: url });

  // Helper to check if a specific view is currently valid and ready for operations
  const isViewValid = (viewStr) => Boolean(views[viewStr]);

  const [user, setUser] = useState(() => {
    try {
      const saved = sessionStorage.getItem("drawingAppUser");
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      console.warn("Failed to parse user session", e);
      return null;
    }
  });

  const [sessionId, setSessionId] = useState(() => {
    try {
      return sessionStorage.getItem("drawingAppSessionId") || null;
    } catch (e) {
      return null;
    }
  });

  // VLM (GPT-4o Vision) side-panel state
  const [vlmResult, setVlmResult] = useState(null);
  const [vlmLoading, setVlmLoading] = useState(false);
  const [vlmMode, setVlmMode] = useState(null); // "full" | "region"
  const [vlmPanelOpen, setVlmPanelOpen] = useState(true); // Toggle for right panel

  // VLM label → drawing text linking
  const [highlightedTextBox, setHighlightedTextBox] = useState(null); // {id, category}

  const imgRef = useRef(null);
  const detailImgRef = useRef(null);

  // Shared logout hook
  const handleLogout = useLogout(sessionId, setUser, setSessionId, setImageUrl);

  // Auto logout (inactivity + tab close)
  useautoLogout(sessionId, handleLogout, 50 * 10 * 1000);

  // Zoom state - now managed at App level to put controls in header
  const { zoom, zoomIn, zoomOut, handleWheel } = useZoom({ min: 1, max: 3, step: 0.25 });

  /**
   * handleVlmDetect — called by ImageCanvas when the user clicks Detect or
   * Detect in Selection.  Fires in parallel with the CV pipeline so the canvas
   * overlays appear promptly while GPT-4o thinks in the background.
   *
   * @param {Blob}  imageBlob  — the raw image file blob
   * @param {Object|null} cropParams — {x, y, w, h} in natural image pixels, or null for full image
   */
  const handleVlmDetect = async (imageBlob, cropParams = null) => {
    setVlmResult(null);
    setVlmLoading(true);
    setVlmMode(cropParams ? "region" : "full");

    const formData = new FormData();
    formData.append("file", imageBlob, "image.png");
    if (sessionId) formData.append("session_id", sessionId);
    if (cropParams) {
      formData.append("x", String(Math.round(cropParams.x)));
      formData.append("y", String(Math.round(cropParams.y)));
      formData.append("w", String(Math.round(cropParams.w)));
      formData.append("h", String(Math.round(cropParams.h)));
    }

    try {
      const res = await fetch(`${API_BASE_URL}/vlm/analyze`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`VLM HTTP ${res.status}: ${await res.text()}`);
      const data = await res.json();
      setVlmResult(data);
    } catch (err) {
      console.error("VLM analysis error:", err);
      setVlmResult({
        mode: cropParams ? "region" : "full",
        drawing_type: "Error",
        summary: [`VLM analysis failed: ${err.message}`],
        text_labels: [],
        detail_circles: [],
        symbols: [],
        student_tip: "",
      });
    } finally {
      setVlmLoading(false);
    }
  };

  // Handle navigation from a circle to a specific page (e.g., A5.1)
  const handleNavigateToPage = (pageImageUrl, pageNumber, circleText) => {
    console.log("Opening detail sheet from MainPage:", {
      pageImageUrl,
      pageNumber,
      circleText,
    });

    updateView("detail", {
      imageUrl: pageImageUrl,
      pageLabel: pageNumber,
      targetCircleText: circleText || null,
      loaded: false,
      error: null,
      rawCircles: [],
      rawTexts: [],
      circles: [],
      texts: [],
      selectedShape: null,
      imageInfo: null,
    });

    setActiveView("detail");
  };

  // ── VLM label → PaddleOCR text matching ──────────────────────────────────
  // Build a set of VLM label texts that have a matching PaddleOCR text box
  const matchableLabels = useMemo(() => {
    const vlmLabels = vlmResult?.text_labels || [];
    const ocrTexts = views[activeView]?.rawTexts || [];
    if (!vlmLabels.length || !ocrTexts.length) return new Set();

    const matchable = new Set();
    for (const label of vlmLabels) {
      const vlmText = (label.text || "").toUpperCase().trim();
      if (!vlmText) continue;
      for (const ocr of ocrTexts) {
        const ocrText = (ocr.text || "").toUpperCase().trim();
        if (!ocrText) continue;
        // Exact match or one contains the other
        if (ocrText === vlmText || ocrText.includes(vlmText) || vlmText.includes(ocrText)) {
          matchable.add(vlmText);
          break;
        }
      }
    }
    return matchable;
  }, [vlmResult, views, activeView]);

  // When user clicks a VLM label, find matching PaddleOCR text box
  const handleVlmLabelClick = (labelText, category) => {
    const target = (labelText || "").toUpperCase().trim();
    if (!target) return;

    const ocrTexts = views[activeView]?.rawTexts || [];

    // 1. Exact match
    let match = ocrTexts.find(t => (t.text || "").toUpperCase().trim() === target);

    // 2. OCR text contains VLM label
    if (!match) {
      match = ocrTexts.find(t => (t.text || "").toUpperCase().trim().includes(target));
    }

    // 3. VLM label contains OCR text
    if (!match) {
      match = ocrTexts.find(t => {
        const ocrText = (t.text || "").toUpperCase().trim();
        return ocrText.length >= 2 && target.includes(ocrText);
      });
    }

    if (match) {
      const currentImageInfo = views[activeView]?.imageInfo;
      // Scale to display coordinates
      const scaled = {
        ...match,
        x1: match.x1 * (currentImageInfo?.scaleX || 1),
        y1: match.y1 * (currentImageInfo?.scaleY || 1),
        x2: match.x2 * (currentImageInfo?.scaleX || 1),
        y2: match.y2 * (currentImageInfo?.scaleY || 1),
      };
      setHighlightedTextBox({ ...scaled, category });

      // Auto-clear highlight after 4 seconds
      setTimeout(() => setHighlightedTextBox(null), 4000);
    } else {
      console.log(`[VLM] No PaddleOCR match for "${labelText}"`);
      setHighlightedTextBox(null);
    }
  };

  // When the detail image + its layout info are ready and we know the
  // target circle text, automatically run detection and highlight circles.
  useEffect(() => {
    const detail = views.detail;
    const shouldDetect = detail.imageUrl && detail.imageInfo && detail.targetCircleText;
    if (!shouldDetect) return;

    const detectDetail = async () => {
      try {
        const blob = await fetch(detail.imageUrl).then((res) => res.blob());
        const formData = new FormData();
        formData.append("file", blob, "detail.png");

        const resp = await fetch(`${API_BASE_URL}/detect/`, {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) throw new Error(`Detection failed: ${await resp.text()}`);

        const data = await resp.json();
        const rawArray = data.circles || [];

        const scaledCircles = rawArray.map((c) => ({
          ...c,
          x: c.x * detail.imageInfo.scaleX,
          y: c.y * detail.imageInfo.scaleY,
          r: c.r * Math.min(detail.imageInfo.scaleX, detail.imageInfo.scaleY),
        }));

        // Only keep circles matching the target circle_text
        const targetLower = detail.targetCircleText.trim().toLowerCase();
        const matched = scaledCircles.filter(
          (c) =>
            c.circle_text &&
            typeof c.circle_text === "string" &&
            c.circle_text.trim().toLowerCase() === targetLower
        );

        updateView("detail", {
          rawCircles: rawArray,
          rawTexts: [],
          circles: matched,
          texts: []
        });
      } catch (err) {
        console.error("Detail detection error:", err);
        updateView("detail", { error: `Failed to detect on detail page: ${err.message}` });
      }
    };

    detectDetail();
  }, [views.detail.imageUrl, views.detail.imageInfo, views.detail.targetCircleText]);

  return (
    <div className="container">
      <header className="app-header" style={{ justifyContent: "flex-start", gap: "20px" }}>
        <h1 className="heading" style={{ textAlign: "left", margin: 0 }}>Generative AI for STEM Education</h1>

        {user && (
          <button onClick={handleLogout} className="logout-button" style={{ marginLeft: "auto", position: "static" }}>
            Logout
          </button>
        )}
      </header>

      <div
        className="app-body"
        style={{
          display: "grid",
          gridTemplateColumns: `180px 1fr ${user && vlmPanelOpen ? "340px" : "0px"}`,
          gridTemplateRows: "1fr",
          overflow: "hidden",
          transition: "grid-template-columns 0.3s ease"
        }}
      >
        <aside className="sidebar">
          <h2 className="sidebar-title">Workspace</h2>

          <div
            className={`sidebar-item ${activeView === "main" ? "active" : ""}`}
            onClick={() => views.main.imageUrl && setActiveView("main")}
            style={{ opacity: views.main.imageUrl ? 1 : 0.5, pointerEvents: views.main.imageUrl ? "auto" : "none" }}
          >
            <span className="sidebar-item-title">Main Sheet</span>
            {views.main.imageInfo ? (
              <span className="sidebar-item-details">
                {views.main.imageInfo.naturalWidth} x {views.main.imageInfo.naturalHeight} px
              </span>
            ) : (
              <span className="sidebar-item-details">No image loaded</span>
            )}
          </div>

          {views.detail.imageUrl && (
            <div
              className={`sidebar-item ${activeView === "detail" ? "active" : ""}`}
              onClick={() => setActiveView("detail")}
            >
              <span className="sidebar-item-title">
                Page {views.detail.pageLabel || "Detail"}
              </span>
              {views.detail.imageInfo && (
                <span className="sidebar-item-details">
                  {views.detail.imageInfo.naturalWidth} x {views.detail.imageInfo.naturalHeight} px
                </span>
              )}
            </div>
          )}

          {/* Upload Button - Moved to Sidebar */}
          {user && (
            <div style={{ marginTop: "12px" }}>
              <ImageUploader
                setImageUrl={(url) => setImageUrl(url)}
                resetStates={() => {
                  updateView("main", {
                    loaded: false,
                    error: null,
                    rawCircles: [],
                    rawTexts: [],
                    circles: [],
                    texts: [],
                    selectedShape: null,
                    imageInfo: null,
                  });
                }}
              />
            </div>
          )}

          {/* Instructions - Moved to sidebar bottom */}
          {activeView === "main" && views.main.imageUrl && (
            <div className="instructions-panel sidebar-instructions">
              <h3>How to Use</h3>
              <ol>
                <li><strong>Detect</strong> to find text/callouts.</li>
                <li><strong>Select region</strong> for focused search.</li>
                <li>Click text for AI explanations.</li>
                <li>Click red circles to navigate.</li>
              </ol>
            </div>
          )}
        </aside>

        <main className="main-content">
          {!user ? (
            <LoginForm setUser={setUser} setSessionId={setSessionId} />
          ) : (
            <>
              {Object.values(views).map((v, i) => v.error && <div key={i} className="error">{v.error}</div>)}

              {/* Main sheet view */}
              {activeView === "main" && views.main.imageUrl && (
                <div className="image-area">
                  <ImageCanvas
                    imageUrl={views.main.imageUrl}
                    imgRef={imgRef}
                    setLoaded={(v) => updateView("main", { loaded: v })}
                    setError={(v) => updateView("main", { error: v })}
                    setImageInfo={(v) => updateView("main", { imageInfo: v })}
                    setCircles={(v) => updateView("main", { circles: v })}
                    setTexts={(v) => updateView("main", { texts: v })}
                    setRawCircles={(v) => updateView("main", { rawCircles: v })}
                    setRawTexts={(v) => updateView("main", { rawTexts: v })}
                    loaded={views.main.loaded}
                    imageInfo={views.main.imageInfo}
                    circles={views.main.circles}
                    texts={views.main.texts}
                    setSelectedShape={(v) => updateView("main", { selectedShape: v })}
                    selectedShape={views.main.selectedShape}
                    sessionId={sessionId}
                    onNavigateToPage={handleNavigateToPage}
                    zoom={zoom}
                    zoomIn={zoomIn}
                    zoomOut={zoomOut}
                    handleWheel={handleWheel}
                    onVlmDetect={handleVlmDetect}
                    highlightedTextBox={highlightedTextBox}
                    vlmResult={vlmResult}
                  />
                </div>
              )}

              {/* Detail sheet view (navigated page) */}
              {activeView === "detail" && views.detail.imageUrl && (
                <div className="image-area">
                  <ImageCanvas
                    imageUrl={views.detail.imageUrl}
                    imgRef={detailImgRef}
                    setLoaded={(v) => updateView("detail", { loaded: v })}
                    setError={(v) => updateView("detail", { error: v })}
                    setImageInfo={(v) => updateView("detail", { imageInfo: v })}
                    setCircles={(v) => updateView("detail", { circles: v })}
                    setTexts={(v) => updateView("detail", { texts: v })}
                    setRawCircles={(v) => updateView("detail", { rawCircles: v })}
                    setRawTexts={(v) => updateView("detail", { rawTexts: v })}
                    loaded={views.detail.loaded}
                    imageInfo={views.detail.imageInfo}
                    circles={views.detail.circles}
                    texts={views.detail.texts}
                    setSelectedShape={(v) => updateView("detail", { selectedShape: v })}
                    selectedShape={views.detail.selectedShape}
                    sessionId={sessionId}
                    onNavigateToPage={handleNavigateToPage}
                    zoom={zoom}
                    zoomIn={zoomIn}
                    zoomOut={zoomOut}
                    handleWheel={handleWheel}
                    highlightCircleText={views.detail.targetCircleText}
                    hideControls
                  />
                </div>
              )}
            </>
          )}
        </main>

        {/* VLM right panel toggle button */}
        {user && (
          <button
            onClick={() => setVlmPanelOpen(!vlmPanelOpen)}
            style={{
              position: "fixed",
              right: vlmPanelOpen ? "340px" : "0",
              top: "50%",
              transform: "translateY(-50%)",
              zIndex: 3000,
              background: "#3b82f6",
              color: "white",
              border: "none",
              padding: "16px 8px",
              cursor: "pointer",
              borderRadius: "8px 0 0 8px",
              transition: "right 0.3s ease",
              boxShadow: "-2px 0 8px rgba(0,0,0,0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            title={vlmPanelOpen ? "Close AI Panel" : "Open AI Panel"}
          >
            {vlmPanelOpen ? "▶" : "◀"}
          </button>
        )}

        {/* VLM right panel — conditionally hidden via CSS Grid but kept in DOM for state */}
        {user && (
          <VLMPanel
            vlmResult={vlmResult}
            vlmLoading={vlmLoading}
            vlmMode={vlmMode}
            onLabelClick={handleVlmLabelClick}
            matchableLabels={matchableLabels}
            onCircleNavigate={(pageRef, circleNumber) => {
              const imagePath = `/images/${pageRef}.png`;
              handleNavigateToPage(imagePath, pageRef, circleNumber);
            }}
            isOpen={vlmPanelOpen}
            onToggle={() => setVlmPanelOpen(!vlmPanelOpen)}
          />
        )}

      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainPage />} />
        <Route path="/page" element={<Page />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
