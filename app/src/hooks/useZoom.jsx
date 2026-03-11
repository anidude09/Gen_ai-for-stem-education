// useZoom — zoom state with keyboard shortcuts (Ctrl +/-/0) and mouse wheel support

import { useState, useEffect } from "react";

export default function useZoom({ min = 1, max = 3, step = 0.25 }) {
  const [zoom, setZoom] = useState(1);

  const clamp = (v) => Math.min(Math.max(v, min), max);

  const zoomIn = () => setZoom((z) => clamp(Number((z + step).toFixed(2))));
  const zoomOut = () => setZoom((z) => clamp(Number((z - step).toFixed(2))));
  const setZoomExact = (v) => setZoom(clamp(Number(v)));

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === "+" || e.key === "=") {
          e.preventDefault();
          zoomIn();
        } else if (e.key === "-") {
          e.preventDefault();
          zoomOut();
        } else if (e.key === "0") {
          e.preventDefault();
          setZoomExact(1);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleWheel = (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = -e.deltaY;
      const factor = delta > 0 ? 1 + step : 1 - step;
      setZoom((z) => clamp(Math.round(z * factor * 100) / 100));
    }
  };

  return { zoom, zoomIn, zoomOut, handleWheel };
}
