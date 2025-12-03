/**
 * LoginForm.jsx
 *
 * This component renders a login form where a user enters their name and email.
 * - On submit, it sends the credentials to the backend login API.
 * - If successful, it stores the user info and session ID in the parent state.
 * - Handles loading state and displays error messages if login fails.
 */


import { useState } from "react";
import "../styles/LoginForm.css";
import { logActivity } from "../utils/activityLogger";

function LoginForm({ setUser, setSessionId }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("http://localhost:8001/auth/login", {
        method: "POST",
        body: new URLSearchParams({ name, email }),
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const data = await response.json();

      if (response.ok && data.session_id) {
        setUser({ name, email });
        setSessionId(data.session_id);

        // Log a successful login associated with the newly created session
        logActivity({
          sessionId: data.session_id,
          eventType: "login_success",
          eventData: { name, email },
          user: { name, email },
        });
      } else {
        setError(data.message || "Login failed. Please try again.");
      }
    } catch (err) {
      console.error("Login error:", err);
      setError("Network error. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <h2>Login</h2>
      <form onSubmit={handleSubmit} className="login-form">
        <input
          type="text"
          placeholder="Enter Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          disabled={loading}
        />
        <input
          type="email"
          placeholder="Enter Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={loading}
        />
        {error && <div className="error-message" style={{color: 'red', margin: '10px 0'}}>{error}</div>}
        <button type="submit" disabled={loading}>
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>
    </div>
  );
}

export default LoginForm;