import { useState, useRef, useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ImageUploader from "./components/ImageUploader";
import ImageCanvas from "./components/ImageCanvas";
import LoginForm from "./components/Loginform";
import Page from "./components/Page";
import useLogout from "./hooks/useLogout";
import useautoLogout from "./hooks/useautoLogout";
import "./styles/App.css";

function MainPage() {
  // Main (uploaded) sheet state
  const [imageUrl, setImageUrl] = useState(null);
  const [rawCircles, setRawCircles] = useState([]);
  const [rawTexts, setRawTexts] = useState([]);
  const [circles, setCircles] = useState([]);
  const [texts, setTexts] = useState([]);
  const [selectedShape, setSelectedShape] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(null);
  const [imageInfo, setImageInfo] = useState(null);

  // Detail sheet (navigated-to page) state
  const [detailImageUrl, setDetailImageUrl] = useState(null);
  const [detailPageLabel, setDetailPageLabel] = useState(null);
  const [detailRawCircles, setDetailRawCircles] = useState([]);
  const [detailRawTexts, setDetailRawTexts] = useState([]);
  const [detailCircles, setDetailCircles] = useState([]);
  const [detailTexts, setDetailTexts] = useState([]);
  const [detailSelectedShape, setDetailSelectedShape] = useState(null);
  const [detailLoaded, setDetailLoaded] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [detailImageInfo, setDetailImageInfo] = useState(null);
  const [detailTargetCircleText, setDetailTargetCircleText] = useState(null);

  // Which "tab" is active in the workspace: "main" or "detail"
  const [activeView, setActiveView] = useState("main");

  const [user, setUser] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const imgRef = useRef(null);
  const detailImgRef = useRef(null);

  // Shared logout hook
  const handleLogout = useLogout(sessionId, setUser, setSessionId, setImageUrl);

  // Auto logout (inactivity + tab close)
  useautoLogout(sessionId, handleLogout,  50 * 10 * 1000);

  // Handle navigation from a circle to a specific page (e.g., A5.1)
  const handleNavigateToPage = (pageImageUrl, pageNumber, circleText) => {
    console.log("Opening detail sheet from MainPage:", {
      pageImageUrl,
      pageNumber,
      circleText,
    });

    setDetailPageLabel(pageNumber);
    setDetailImageUrl(pageImageUrl);
    setDetailTargetCircleText(circleText || null);
    setActiveView("detail");

    // Reset detail workspace state so detection can run fresh
    setDetailLoaded(false);
    setDetailError(null);
    setDetailRawCircles([]);
    setDetailRawTexts([]);
    setDetailCircles([]);
    setDetailTexts([]);
    setDetailSelectedShape(null);
    setDetailImageInfo(null);
  };

  // When the detail image + its layout info are ready and we know the
  // target circle text, automatically run detection and highlight circles.
  useEffect(() => {
    const shouldDetect =
      detailImageUrl && detailImageInfo && detailTargetCircleText;
    if (!shouldDetect) return;

    const detectDetail = async () => {
      try {
        const blob = await fetch(detailImageUrl).then((res) => res.blob());
        const formData = new FormData();
        formData.append("file", blob, "detail.png");

        const resp = await fetch("http://localhost:8001/detect/", {
          method: "POST",
          body: formData,
        });

        if (!resp.ok) throw new Error(`Detection failed: ${await resp.text()}`);

        const data = await resp.json();
        const rawCircles = data.circles || [];
        const rawTexts = data.texts || [];

        setDetailRawCircles(rawCircles);
        setDetailRawTexts(rawTexts);

        const scaledCircles = rawCircles.map((c) => ({
          ...c,
          x: c.x * detailImageInfo.scaleX,
          y: c.y * detailImageInfo.scaleY,
          r: c.r * Math.min(detailImageInfo.scaleX, detailImageInfo.scaleY),
        }));

        const scaledTexts = rawTexts.map((t) => ({
          ...t,
          x1: t.x1 * detailImageInfo.scaleX,
          y1: t.y1 * detailImageInfo.scaleY,
          x2: t.x2 * detailImageInfo.scaleX,
          y2: t.y2 * detailImageInfo.scaleY,
        }));

        setDetailCircles(scaledCircles);
        setDetailTexts(scaledTexts);

        // Auto-select the first circle whose circle_text matches
        const targetLower = detailTargetCircleText.trim().toLowerCase();
        const matched = scaledCircles.find(
          (c) =>
            c.circle_text &&
            typeof c.circle_text === "string" &&
            c.circle_text.trim().toLowerCase() === targetLower
        );
        if (matched) {
          setDetailSelectedShape(matched);
        }
      } catch (err) {
        console.error("Detail detection error:", err);
        setDetailError(`Failed to detect on detail page: ${err.message}`);
      }
    };

    detectDetail();
  }, [detailImageUrl, detailImageInfo, detailTargetCircleText]);

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

      <div className="app-body">
        <aside className="sidebar">
          <h2 className="sidebar-title">Workspace</h2>
          
          <div 
            className={`sidebar-item ${activeView === "main" ? "active" : ""}`}
            onClick={() => imageUrl && setActiveView("main")}
            style={{ opacity: imageUrl ? 1 : 0.5, pointerEvents: imageUrl ? "auto" : "none" }}
          >
            <span className="sidebar-item-title">Main Sheet</span>
            {imageInfo ? (
               <span className="sidebar-item-details">
                 {imageInfo.naturalWidth} x {imageInfo.naturalHeight} px
               </span>
            ) : (
               <span className="sidebar-item-details">No image loaded</span>
            )}
          </div>

          {detailImageUrl && (
            <div 
              className={`sidebar-item ${activeView === "detail" ? "active" : ""}`}
              onClick={() => setActiveView("detail")}
            >
              <span className="sidebar-item-title">
                Page {detailPageLabel || "Detail"}
              </span>
              {detailImageInfo && (
                <span className="sidebar-item-details">
                  {detailImageInfo.naturalWidth} x {detailImageInfo.naturalHeight} px
                </span>
              )}
            </div>
          )}
        </aside>

        <main className="main-content">
          {!user ? (
            <LoginForm setUser={setUser} setSessionId={setSessionId} />
          ) : (
            <>
              <div className="uploader-row">
                <ImageUploader
                  setImageUrl={setImageUrl}
                  resetStates={() => {
                    setLoaded(false);
                    setError(null);
                    setRawCircles([]);
                    setRawTexts([]);
                    setCircles([]);
                    setTexts([]);
                    setSelectedShape(null);
                    setImageInfo(null); // Reset image info too
                  }}
                />
                {error && <div className="error">{error}</div>}
              </div>

              {/* Instructions Panel (Only shown when an image is loaded and we are in main view) */}
              {activeView === "main" && imageUrl && (
                <div className="instructions-panel">
                    <h3>How to Use</h3>
                    <ol>
                        <li>Use the <strong>Detect</strong> button to find text and callouts automatically.</li>
                        <li>Drag your mouse over a specific area and click <strong>Detect in selection</strong> for focused results.</li>
                        <li>Click on highlighted text to get AI-powered explanations.</li>
                        <li>Click on red callout circles to navigate to referenced detail pages.</li>
                    </ol>
                </div>
              )}

              {/* Main sheet view */}
              {activeView === "main" && imageUrl && (
                <div className="image-area">
                  <ImageCanvas
                    imageUrl={imageUrl}
                    imgRef={imgRef}
                    setLoaded={setLoaded}
                    setError={setError}
                    setImageInfo={setImageInfo}
                    setCircles={setCircles}
                    setTexts={setTexts}
                    setRawCircles={setRawCircles}
                    setRawTexts={setRawTexts}
                    loaded={loaded}
                    imageInfo={imageInfo}
                    circles={circles}
                    texts={texts}
                    setSelectedShape={setSelectedShape}
                    selectedShape={selectedShape}
                    sessionId={sessionId}
                    onNavigateToPage={handleNavigateToPage}
                  />
                </div>
              )}

              {/* Detail sheet view (navigated page) */}
              {activeView === "detail" && detailImageUrl && (
                <div className="image-area">
                  <ImageCanvas
                    imageUrl={detailImageUrl}
                    imgRef={detailImgRef}
                    setLoaded={setDetailLoaded}
                    setError={setDetailError}
                    setImageInfo={setDetailImageInfo}
                    setCircles={setDetailCircles}
                    setTexts={setDetailTexts}
                    setRawCircles={setDetailRawCircles}
                    setRawTexts={setDetailRawTexts}
                    loaded={detailLoaded}
                    imageInfo={detailImageInfo}
                    circles={detailCircles}
                    texts={detailTexts}
                    setSelectedShape={setDetailSelectedShape}
                    selectedShape={detailSelectedShape}
                    sessionId={sessionId}
                    onNavigateToPage={handleNavigateToPage}
                  />
                  {detailError && <div className="error">{detailError}</div>}
                </div>
              )}

              {/* Note: Previously we rendered full-screen invisible overlays here to */
              /* close popups on outside click. Those overlays were intercepting */
              /* clicks meant for the popup buttons (like "Go to page A7.1"). */
              /* They've been removed so click handlers fire correctly. */}
            </>
          )}
        </main>
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
