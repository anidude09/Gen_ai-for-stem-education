// useLogout — logout hook: calls backend, clears session state


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
    // Clear session storage
    sessionStorage.removeItem("drawingAppUser");
    sessionStorage.removeItem("drawingAppSessionId");
  }, [sessionId, setUser, setSessionId, setImageUrl]);
}
