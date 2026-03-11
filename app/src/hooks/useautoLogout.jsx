/**
 * useAutoLogout.js
 *
 * This custom React hook automatically logs out a user after a period of inactivity.
 * - Tracks user activity (mouse movement, clicks, key presses, scrolling).
 * - Resets the inactivity timer on any interaction.
 * - Calls the provided handleLogout function if the user is inactive for the specified timeout.
 * - On page close/refresh, sends a best-effort beacon to the backend but does NOT
 *   clear sessionStorage, so a simple page refresh keeps the user logged in.
 */

import { useEffect } from "react";
import { logActivity } from "../utils/activityLogger";
import { API_BASE_URL } from "../config";

export default function useAutoLogout(sessionId, handleLogout, timeout) {
  useEffect(() => {
    if (!sessionId) return;

    let timer;

    const resetTimer = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        console.log("Auto logout: inactive for 5 mins");
        logActivity({
          sessionId,
          eventType: "logout_auto_inactivity",
        });
        handleLogout();
      }, timeout);
    };

    window.addEventListener("mousemove", resetTimer);
    window.addEventListener("keydown", resetTimer);
    window.addEventListener("click", resetTimer);
    window.addEventListener("scroll", resetTimer);

    // On page close/refresh: notify the backend but do NOT clear session storage.
    // navigator.sendBeacon is fire-and-forget — it works even during page unload.
    // This way, refreshing the page keeps the user logged in.
    const handleUnload = () => {
      navigator.sendBeacon(
        `${API_BASE_URL}/auth/logout`,
        new Blob(
          [JSON.stringify({ session_id: sessionId })],
          { type: "application/json" }
        )
      );
    };
    window.addEventListener("beforeunload", handleUnload);

    resetTimer();

    return () => {
      clearTimeout(timer);
      window.removeEventListener("mousemove", resetTimer);
      window.removeEventListener("keydown", resetTimer);
      window.removeEventListener("click", resetTimer);
      window.removeEventListener("scroll", resetTimer);
      window.removeEventListener("beforeunload", handleUnload);
    };
  }, [sessionId, handleLogout, timeout]);
}
