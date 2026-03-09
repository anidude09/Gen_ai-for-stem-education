/**
 * useLogout.js
 *
 * This custom React hook returns a memoized logout function.
 * - Sends a logout request to the backend API with the current session ID.
 * - Clears user-related state (user info, session ID, and uploaded image) on logout.
 * - Ensures the function reference is stable with useCallback for performance.
 */


import { useCallback } from "react";
import { logActivity } from "../utils/activityLogger";
import { API_BASE_URL } from "../config";

export default function useLogout(sessionId, setUser, setSessionId, setImageUrl) {
  return useCallback(async () => {
    if (!sessionId) return;

    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      logActivity({
        sessionId,
        eventType: "logout_manual",
      });
    } catch (err) {
      console.error("Logout error:", err);
    }

    setUser(null);
    setSessionId(null);
    setImageUrl(null);

    // Clear session storage to prevent auto-login on refresh
    sessionStorage.removeItem("drawingAppUser");
    sessionStorage.removeItem("drawingAppSessionId");
  }, [sessionId, setUser, setSessionId, setImageUrl]);
}
