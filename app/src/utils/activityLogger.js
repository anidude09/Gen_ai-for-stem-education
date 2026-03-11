// activityLogger — sends user activity events to the backend for logging

import { API_BASE_URL } from "../config";

export async function logActivity({
  sessionId,
  eventType,
  eventData = {},
  user,
}) {
  if (!sessionId || !eventType) {
    return;
  }

  try {
    await fetch(`${API_BASE_URL}/activity/log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        event_type: eventType,
        event_data: eventData,
        user_name: user?.name,
        user_email: user?.email,
      }),
    });
  } catch (err) {
    // Logging failure should never break the UI
    console.error("Failed to log activity:", err);
  }
}


