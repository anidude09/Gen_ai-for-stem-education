import { useState, useRef, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ImageUploader from "./components/ImageUploader";
import ImageCanvas from "./components/ImageCanvas";
import LoginForm from "./components/Loginform";
import AgentChatPanel from "./components/AgentChatPanel";
import { scaleCircles, scaleTexts } from "./utils/scaleShapes";
import useLogout from "./hooks/useLogout";
import useautoLogout from "./hooks/useautoLogout";
import useZoom from "./hooks/useZoom";
import { API_BASE_URL } from "./config";
import "./styles/App.css";

const CHAT_WIDTH = 480;

function emptyViewData() {
  return {
    rawCircles: [], rawTexts: [],
    circles: [], texts: [],
    selectedShape: null,
    loaded: false, error: null, imageInfo: null,
  };
}

function MainPage() {
  const [views, setViews] = useState({
    main: { imageUrl: null, ...emptyViewData() },
    pages: {},  // key (pageLabel) → { imageUrl, pageLabel, targetCircleText, ...emptyViewData() }
  });

  // activeView is "main" or a pageLabel string
  const [activeView, setActiveView] = useState("main");

  const currentView = activeView === "main" ? views.main : (views.pages[activeView] || null);

  const updateView = (key, updates) => {
    if (key === "main") {
      setViews(prev => ({ ...prev, main: { ...prev.main, ...updates } }));
    } else {
      setViews(prev => ({
        ...prev,
        pages: { ...prev.pages, [key]: { ...prev.pages[key], ...updates } },
      }));
    }
  };

  // New image upload — clear all pages and reset
  const setImageUrl = (url) => {
    setViews({ main: { imageUrl: url, ...emptyViewData() }, pages: {} });
    setActiveView("main");
  };

  const [user, setUser] = useState(() => {
    try {
      const saved = sessionStorage.getItem("drawingAppUser");
      return saved ? JSON.parse(saved) : null;
    } catch (e) { return null; }
  });

  const [sessionId, setSessionId] = useState(() => {
    try { return sessionStorage.getItem("drawingAppSessionId") || null; }
    catch (e) { return null; }
  });

  const [chatPanelOpen, setChatPanelOpen] = useState(true);
  const chatPanelRef = useRef(null);
  const [pageSessionId, setPageSessionId] = useState(() => crypto.randomUUID());
  const [globalContextStatus, setGlobalContextStatus] = useState("idle");
  const [globalVlmResult, setGlobalVlmResult] = useState(null);
  const contextBuiltForRef = useRef(null);
  const contextBuiltPagesRef = useRef(new Set());
  const detectedPagesRef = useRef(new Set());

  // Reset session ONLY when a new main image is uploaded
  useEffect(() => {
    if (!views.main.imageUrl) return;
    const newId = crypto.randomUUID();
    setPageSessionId(newId);
    setGlobalContextStatus("idle");
    setGlobalVlmResult(null);
    contextBuiltForRef.current = null;
    contextBuiltPagesRef.current = new Set();
    detectedPagesRef.current = new Set();
  }, [views.main.imageUrl]);

  // Build VLM context for the main image once per session
  useEffect(() => {
    const imageUrl = views.main.imageUrl;
    if (!imageUrl) return;
    if (contextBuiltForRef.current === pageSessionId) return;
    contextBuiltForRef.current = pageSessionId;
    setGlobalContextStatus("loading");

    const buildContext = async () => {
      try {
        const blob = await fetch(imageUrl).then(r => r.blob());
        const formData = new FormData();
        formData.append("file", blob, "image.png");
        formData.append("page_session_id", pageSessionId);
        formData.append("page_label", "Main Drawing");

        const res = await fetch(`${API_BASE_URL}/chat/context`, { method: "POST", body: formData });
        if (res.ok) {
          const data = await res.json();
          setGlobalContextStatus("ready");
          if (data.analysis) {
            try {
              setGlobalVlmResult(typeof data.analysis === "string" ? JSON.parse(data.analysis) : data.analysis);
            } catch (e) {
              console.warn("Could not parse VLM analysis", e);
            }
          }
        } else {
          setGlobalContextStatus("error");
        }
      } catch (err) {
        setGlobalContextStatus("error");
        console.error("[Agent] Global context error:", err);
      }
    };
    buildContext();
  }, [pageSessionId]);

  // Append VLM context for each newly visited page into the same session
  useEffect(() => {
    for (const [key, page] of Object.entries(views.pages)) {
      if (page.imageUrl && !contextBuiltPagesRef.current.has(key)) {
        contextBuiltPagesRef.current.add(key);
        const buildPageContext = async () => {
          try {
            const formData = new FormData();
            formData.append("page_session_id", pageSessionId);
            formData.append("page_label", page.pageLabel || key);
            // Server-hosted pages: pass path so backend reads from disk (no upload)
            if (!page.imageUrl.startsWith("blob:")) {
              const pathname = page.imageUrl.startsWith("/") ? page.imageUrl : new URL(page.imageUrl).pathname;
              formData.append("server_image_path", pathname);
            } else {
              const blob = await fetch(page.imageUrl).then(r => r.blob());
              formData.append("file", blob, "image.png");
            }
            await fetch(`${API_BASE_URL}/chat/context`, { method: "POST", body: formData });
            console.log(`[Agent] Context appended for page: ${key}`);
          } catch (err) {
            console.error(`[Agent] Failed to build context for page ${key}:`, err);
          }
        };
        buildPageContext();
      }
    }
  }, [views.pages, pageSessionId]);

  // Auto-detect circles on newly visited pages once imageInfo is available
  useEffect(() => {
    for (const [key, page] of Object.entries(views.pages)) {
      if (
        page.imageInfo &&
        page.targetCircleText &&
        !detectedPagesRef.current.has(key) &&
        page.rawCircles.length === 0
      ) {
        detectedPagesRef.current.add(key);
        const detectPage = async () => {
          try {
            const formData = new FormData();
            formData.append("circles_only", "true");
            formData.append("page_session_id", pageSessionId);
            formData.append("page_label", page.pageLabel || key);
            // Server-hosted pages: pass path so backend uses cache or reads from disk
            if (!page.imageUrl.startsWith("blob:")) {
              const pathname = page.imageUrl.startsWith("/") ? page.imageUrl : new URL(page.imageUrl).pathname;
              formData.append("server_image_path", pathname);
            } else {
              const blob = await fetch(page.imageUrl).then(res => res.blob());
              formData.append("file", blob, "detail.png");
            }

            const resp = await fetch(`${API_BASE_URL}/detect/`, { method: "POST", body: formData });
            if (!resp.ok) throw new Error(`Detection failed: ${await resp.text()}`);

            const data = await resp.json();
            const rawArray = data.circles || [];
            const rawTexts = data.texts || [];

            updateView(key, {
              rawCircles: rawArray,
              rawTexts: rawTexts,
              circles: scaleCircles(rawArray, page.imageInfo),
              texts: scaleTexts(rawTexts, page.imageInfo),
            });
          } catch (err) {
            console.error(`Detail detection error for ${key}:`, err);
            updateView(key, { error: `Failed to detect on page ${key}: ${err.message}` });
          }
        };
        detectPage();
      }
    }
  }, [views.pages]);

  const imgRef = useRef(null);
  const pageImgRef = useRef(null);

  const handleLogout = useLogout(sessionId, setUser, setSessionId, setImageUrl);
  useautoLogout(sessionId, handleLogout, 50 * 10 * 1000);

  const { zoom, zoomIn, zoomOut, handleWheel } = useZoom({ min: 1, max: 3, step: 0.25 });

  const handleAgentDraw = (drawData) => {
    const { rectangles, circles } = drawData;
    if (!currentView?.imageInfo) return;

    updateView(activeView, {
      circles: scaleCircles(circles || [], currentView.imageInfo).map(c => ({ ...c, circle_text: c.label || "" })),
      texts: scaleTexts(rectangles || [], currentView.imageInfo).map(t => ({ ...t, text: t.label || "" })),
      rawCircles: circles,
      rawTexts: rectangles,
    });
  };

  const handleNavigateToPage = (pageImageUrl, pageNumber, circleText) => {
    const key = pageNumber || pageImageUrl;
    setViews(prev => {
      if (prev.pages[key]) return prev;  // already visited, just switch
      return {
        ...prev,
        pages: {
          ...prev.pages,
          [key]: {
            imageUrl: pageImageUrl,
            pageLabel: pageNumber,
            targetCircleText: circleText || null,
            ...emptyViewData(),
          },
        },
      };
    });
    setActiveView(key);
  };

  const allErrors = [
    views.main.error,
    ...Object.values(views.pages).map(p => p.error),
  ].filter(Boolean);

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
          gridTemplateColumns: `180px 1fr ${(user && chatPanelOpen) ? `${CHAT_WIDTH}px` : "0px"}`,
          gridTemplateRows: "1fr",
          overflow: "hidden",
          transition: "grid-template-columns 0.3s ease",
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

          {Object.entries(views.pages).map(([key, page]) => (
            <div
              key={key}
              className={`sidebar-item ${activeView === key ? "active" : ""}`}
              onClick={() => setActiveView(key)}
            >
              <span className="sidebar-item-title">Page {page.pageLabel || key}</span>
              {page.imageInfo && (
                <span className="sidebar-item-details">
                  {page.imageInfo.naturalWidth} x {page.imageInfo.naturalHeight} px
                </span>
              )}
            </div>
          ))}

          {user && (
            <div style={{ marginTop: "12px" }}>
              <ImageUploader setImageUrl={setImageUrl} resetStates={() => {}} />
            </div>
          )}

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
              {allErrors.map((err, i) => <div key={i} className="error">{err}</div>)}

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
                    vlmResult={globalVlmResult}
                  />
                </div>
              )}

              {activeView !== "main" && views.pages[activeView] && (
                <div className="image-area">
                  <ImageCanvas
                    imageUrl={views.pages[activeView].imageUrl}
                    imgRef={pageImgRef}
                    setLoaded={(v) => updateView(activeView, { loaded: v })}
                    setError={(v) => updateView(activeView, { error: v })}
                    setImageInfo={(v) => updateView(activeView, { imageInfo: v })}
                    setCircles={(v) => updateView(activeView, { circles: v })}
                    setTexts={(v) => updateView(activeView, { texts: v })}
                    setRawCircles={(v) => updateView(activeView, { rawCircles: v })}
                    setRawTexts={(v) => updateView(activeView, { rawTexts: v })}
                    loaded={views.pages[activeView].loaded}
                    imageInfo={views.pages[activeView].imageInfo}
                    circles={views.pages[activeView].circles}
                    texts={views.pages[activeView].texts}
                    setSelectedShape={(v) => updateView(activeView, { selectedShape: v })}
                    selectedShape={views.pages[activeView].selectedShape}
                    sessionId={sessionId}
                    onNavigateToPage={handleNavigateToPage}
                    zoom={zoom}
                    zoomIn={zoomIn}
                    zoomOut={zoomOut}
                    handleWheel={handleWheel}
                    highlightCircleText={views.pages[activeView].targetCircleText}
                    vlmResult={globalVlmResult}
                  />
                </div>
              )}
            </>
          )}
        </main>

        {user && (
          <button
            onClick={() => setChatPanelOpen(!chatPanelOpen)}
            style={{
              position: "fixed",
              right: chatPanelOpen ? `${CHAT_WIDTH}px` : "0",
              top: "60%",
              transform: "translateY(-50%)",
              zIndex: 3000,
              background: "#10b981",
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
            title={chatPanelOpen ? "Close Assistant" : "Chat with Assistant"}
          >
            {chatPanelOpen ? "▶" : "💬"}
          </button>
        )}

        {user && chatPanelOpen && (
          <AgentChatPanel
            ref={chatPanelRef}
            isOpen={chatPanelOpen}
            imageUrl={currentView?.imageUrl}
            pageSessionId={pageSessionId}
            globalContextStatus={globalContextStatus}
            globalVlmResult={globalVlmResult}
            onAgentDraw={handleAgentDraw}
            onNavigateToPage={handleNavigateToPage}
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
      </Routes>
    </BrowserRouter>
  );
}

export default App;
