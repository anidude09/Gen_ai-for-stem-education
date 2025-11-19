import { useState, useRef } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ImageUploader from "./components/ImageUploader";
import ImageCanvas from "./components/ImageCanvas";
import LoginForm from "./components/Loginform";
import Page from "./components/Page";
import useLogout from "./hooks/useLogout";
import useautoLogout from "./hooks/useautoLogout";
import "./styles/App.css";

function MainPage() {
  const [imageUrl, setImageUrl] = useState(null);
  const [rawCircles, setRawCircles] = useState([]);
  const [rawTexts, setRawTexts] = useState([]);
  const [circles, setCircles] = useState([]);
  const [texts, setTexts] = useState([]);
  const [selectedShape, setSelectedShape] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(null);
  const [imageInfo, setImageInfo] = useState(null);

  const [user, setUser] = useState(null);
  const [sessionId, setSessionId] = useState(null);

  const imgRef = useRef(null);

  // Shared logout hook
  const handleLogout = useLogout(sessionId, setUser, setSessionId, setImageUrl);

  // Auto logout (inactivity + tab close)
  useautoLogout(sessionId, handleLogout,  50 * 10 * 1000);

  return (
    <div className="container">
      <header className="app-header">
        <h1 className="heading">Generative AI for STEM Education</h1>
        {user && (
          <button onClick={handleLogout} className="logout-button">
            Logout
          </button>
        )}
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <h2 className="sidebar-title">Workspace</h2>
          <p className="sidebar-subtitle">
            placeholder
          </p>
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
                  }}
                />
                {error && <div className="error">{error}</div>}
              </div>

              {imageUrl && (
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
                  />
                </div>
              )}

              {selectedShape && (
                <div
                  style={{
                    position: "fixed",
                    top: 0,
                    left: 0,
                    width: "100%",
                    height: "100%",
                    zIndex: 999,
                  }}
                  onClick={() => setSelectedShape(null)}
                />
              )}
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
