/**
 * useAutoLogout.js
 *
 * This custom React hook automatically logs out a user after a period of inactivity.
 * - Tracks user activity (mouse movement, clicks, key presses, scrolling).
 * - Resets the inactivity timer on any interaction.
 * - Calls the provided handleLogout function if the user is inactive for the specified timeout.
 * - Also logs out the user when the window is closed or refreshed.
 */

import { useEffect } from "react";
import { logActivity } from "../utils/activityLogger";

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

    const handleUnload = () => handleLogout();
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
