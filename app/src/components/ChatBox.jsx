/**
 * ChatBox.jsx
 * 
 * A small search/chat box component that allows users to search for construction terms
 * without needing to find them on using the same LLM API to get explanations,
 * RAG context, and dictionary images.
 */

import { useState } from "react";

function ChatBox({ sessionId }) {
    const [query, setQuery] = useState("");
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);

    // Helper handling image URLs for both Vite (5173) and FastAPI (8001)
    const getBaseUrl = () => {
        const isDev = window.location.port === "5173";
        return isDev ? "http://127.0.0.1:8001" : "";
    };

    const getImageUrl = (path) => {
        if (!path) return null;
        if (path.startsWith("http")) return path;
        return `${getBaseUrl()}${path}`;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        setResult(null);

        try {
            const response = await fetch(`${getBaseUrl()}/llm-images/explain_with_images`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content: query.trim() }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log("ChatBox received data:", data);
            setResult(data);
            setIsExpanded(true);
        } catch (error) {
            console.error("ChatBox fetch error:", error);
            setResult({ error: "Failed to get explanation. Please try again." });
        } finally {
            setLoading(false);
        }
    };

    const handleClear = () => {
        setQuery("");
        setResult(null);
        setIsExpanded(false);
    };



    return (
        <div className="chatbox-container">
            <div
                className="chatbox-header"
                onClick={() => setIsExpanded(!isExpanded)}
            >
                <span className="chatbox-icon">💬</span>
                <span className="chatbox-title">Term Search</span>
                <span className="chatbox-toggle">{isExpanded ? "▼" : "▲"}</span>
            </div>

            <div className={`chatbox-content ${isExpanded ? "expanded" : ""}`}>
                <form onSubmit={handleSubmit} className="chatbox-form">
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Search a term (e.g., SOFFIT)"
                        className="chatbox-input"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        className="chatbox-submit"
                        disabled={loading || !query.trim()}
                    >
                        {loading ? "..." : "→"}
                    </button>
                </form>

                {result && (
                    <div className="chatbox-result">
                        {result.error ? (
                            <div className="chatbox-error">{result.error}</div>
                        ) : (
                            <>
                                {/* Dictionary Image */}
                                {result.dict_image && (
                                    <div className="chatbox-dict-image">
                                        <img
                                            src={getImageUrl(result.dict_image)}
                                            alt={query}
                                            onError={(e) => {
                                                console.error("Failed to load image:", e.target.src);
                                                e.target.style.display = 'none';
                                            }}
                                        />
                                    </div>
                                )}

                                {/* Summary */}
                                {Array.isArray(result.summary) && result.summary.length > 0 && (
                                    <div className="chatbox-section">
                                        <strong>Summary</strong>
                                        <ul>
                                            {result.summary.map((item, idx) => (
                                                <li key={idx}>{item}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Key Terms */}
                                {Array.isArray(result.key_terms) && result.key_terms.length > 0 && (
                                    <div className="chatbox-section">
                                        <strong>Key Terms</strong>
                                        <ul>
                                            {result.key_terms.map((t, idx) => (
                                                <li key={idx}>
                                                    <span className="term-name">{t.term}</span>: {t.definition}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Context (collapsible) */}
                                {result.context && (
                                    <details className="chatbox-context">
                                        <summary>Source Context</summary>
                                        <div className="context-content">{result.context}</div>
                                    </details>
                                )}

                                {/* Google Images */}
                                {Array.isArray(result.images) && result.images.length > 0 && (
                                    <div className="chatbox-images">
                                        <strong>Visual References</strong>
                                        <div className="image-row">
                                            {result.images.slice(0, 3).map((img, idx) => (
                                                <a
                                                    key={idx}
                                                    href={img.page_url || img.image_url}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                >
                                                    <img
                                                        src={img.thumbnail_url || img.image_url}
                                                        alt={img.title || "Reference"}
                                                    />
                                                </a>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </>
                        )}

                        <button onClick={handleClear} className="chatbox-clear">
                            Clear
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

export default ChatBox;
