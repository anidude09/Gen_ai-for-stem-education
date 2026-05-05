import React, { useState, useRef, useEffect, forwardRef, useImperativeHandle } from "react";
import { API_BASE_URL } from "../config";

const AgentChatPanel = forwardRef(({ isOpen, imageUrl, pageSessionId, globalContextStatus, globalVlmResult, onAgentDraw, onNavigateToPage }, ref) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    // Reset chat when the page session context changes (User uploaded new image)
    useEffect(() => {
        setMessages([]);
    }, [pageSessionId]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useImperativeHandle(ref, () => ({
        submitMessage: (text, displayLabel) => {
            processMessage(text, displayLabel);
        }
    }));

    const processMessage = async (userText, displayLabel = null) => {
        if (!userText.trim() || !imageUrl || isLoading) return;
        // displayLabel is the short text shown in the chat, userText is the full prompt sent to the agent
        const shownText = displayLabel || userText;
        const newMsgList = [...messages, { role: "user", text: shownText }];
        setMessages(newMsgList);
        setIsLoading(true);

        // Add a placeholder for AI response
        setMessages([...newMsgList, { role: "agent", text: "", tool_calls: [] }]);

        try {
            const blob = await fetch(imageUrl).then(res => res.blob());
            const formData = new FormData();
            formData.append("file", blob, "image.png");
            formData.append("message", userText);
            formData.append("page_session_id", pageSessionId);

            const response = await fetch(`${API_BASE_URL}/chat/`, {
                method: "POST",
                body: formData,
            });

            if (!response.body) throw new Error("No readable stream from server");

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            
            let currentAssistantText = "";
            let currentToolCalls = [];

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const dataStr = line.replace("data: ", "").trim();
                        if (dataStr === "[DONE]") break;
                        if (!dataStr) continue;
                        
                        try {
                            const data = JSON.parse(dataStr);
                            
                            if (data.type === "text") {
                                currentAssistantText += data.content;
                            } else if (data.type === "tool_start") {
                                currentToolCalls.push({ name: data.name, status: "running" });
                            } else if (data.type === "tool_end") {
                                // Find the running instance and mark it done
                                const tc = currentToolCalls.slice().reverse().find(t => t.name === data.name && t.status === "running");
                                if (tc) {
                                    tc.status = "done";
                                }
                            } else if (data.type === "error") {
                                currentAssistantText += `\n[Error: ${data.content}]`;
                            } else if (data.type === "draw_shapes") {
                                if (onAgentDraw) {
                                    onAgentDraw(data.data);
                                }
                            }

                            setMessages(prev => {
                                const copy = [...prev];
                                copy[copy.length - 1] = { 
                                    role: "agent", 
                                    text: currentAssistantText,
                                    tool_calls: [...currentToolCalls]
                                };
                                return copy;
                            });
                        } catch (err) {
                            console.warn("Failed to parse SSE JSON", err, dataStr);
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Chat error:", error);
            setMessages(prev => {
                const copy = [...prev];
                copy[copy.length - 1].text += "\n[Connection Error]";
                return copy;
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleSend = async (e) => {
        e.preventDefault();
        const userText = input.trim();
        setInput("");
        await processMessage(userText);
    };

    const panelStyle = {
        width: "480px",
        height: "100%",
        background: "rgba(15, 23, 42, 0.95)",
        borderLeft: "1px solid rgba(255,255,255,0.07)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        fontFamily: "inherit",
    };

    if (!isOpen) return null;

    return (
        <aside style={panelStyle}>
            <div style={{ padding: "14px 16px 12px", borderBottom: "1px solid rgba(255,255,255,0.07)", fontWeight: 600, fontSize: "15px", color: "#f1f5f9", flexShrink: 0 }}>
                Interactive Plan Assistant
            </div>

            <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "16px" }}>
                {/* Global context status banner */}
                {globalContextStatus && globalContextStatus !== "idle" && (
                    <div style={{
                        padding: "8px 12px",
                        borderRadius: "6px",
                        fontSize: "12px",
                        fontStyle: "italic",
                        textAlign: "center",
                        background: globalContextStatus === "loading" ? "rgba(59,130,246,0.15)" :
                                    globalContextStatus === "ready" ? "rgba(16,185,129,0.15)" :
                                    "rgba(239,68,68,0.15)",
                        color: globalContextStatus === "loading" ? "#93c5fd" :
                               globalContextStatus === "ready" ? "#6ee7b7" :
                               "#fca5a5",
                    }}>
                        {globalContextStatus === "loading" && "⚙️ Building Global Drawing Context..."}
                        {globalContextStatus === "ready" && "✅ Agent has full drawing context"}
                        {globalContextStatus === "error" && "⚠️ Context build failed — agent will still work"}
                    </div>
                )}

                {globalVlmResult && (
                    <div style={{
                        background: "#334155",
                        color: "#f1f5f9",
                        padding: "12px",
                        borderRadius: "8px",
                        fontSize: "14px",
                        lineHeight: "1.5"
                    }}>
                        <div style={{ fontWeight: 600, color: "#60a5fa", marginBottom: "8px" }}>
                            {globalVlmResult.drawing_type || "Drawing Analysis"}
                        </div>
                        {Array.isArray(globalVlmResult.summary) && (
                            <ul style={{ margin: "0 0 12px 0", paddingLeft: "20px" }}>
                                {globalVlmResult.summary.map((point, idx) => (
                                    <li key={idx} style={{ marginBottom: "4px" }}>{point}</li>
                                ))}
                            </ul>
                        )}
                        {Array.isArray(globalVlmResult.text_labels) && globalVlmResult.text_labels.length > 0 && (
                            <div style={{ marginBottom: "12px" }}>
                                <div style={{ fontWeight: 600, color: "#94a3b8", marginBottom: "4px" }}>Key Labels:</div>
                                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                                    {globalVlmResult.text_labels.map((label, idx) => (
                                        <div
                                            key={idx}
                                            onClick={() => {
                                                if (ref.current) {
                                                    ref.current.submitMessage(`What does '${label.text}' mean?`);
                                                }
                                            }}
                                            style={{
                                                background: "rgba(59,130,246,0.2)",
                                                border: "1px solid rgba(59,130,246,0.4)",
                                                borderRadius: "4px",
                                                padding: "2px 6px",
                                                cursor: "pointer",
                                                fontSize: "12px"
                                            }}
                                            title={label.category}
                                        >
                                            {label.text}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {Array.isArray(globalVlmResult.detail_circles) && globalVlmResult.detail_circles.length > 0 && (
                            <div>
                                <div style={{ fontWeight: 600, color: "#94a3b8", marginBottom: "4px" }}>Detail References:</div>
                                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                                    {globalVlmResult.detail_circles.map((circle, idx) => (
                                        <div
                                            key={idx}
                                            onClick={() => {
                                                if (circle.page && onNavigateToPage) {
                                                    onNavigateToPage(`/images/${circle.page}.png`, circle.page, circle.text);
                                                }
                                            }}
                                            style={{
                                                background: "rgba(239,68,68,0.2)",
                                                border: "1px solid rgba(239,68,68,0.4)",
                                                borderRadius: "4px",
                                                padding: "2px 6px",
                                                cursor: circle.page ? "pointer" : "default",
                                                fontSize: "12px"
                                            }}
                                            title={`Page ${circle.page}`}
                                        >
                                            {circle.text}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {messages.length === 0 && !globalVlmResult && (
                    <div style={{ color: "#475569", textAlign: "center", paddingTop: "40px", fontSize: "14px" }}>
                        Ask me about this drawing. I can find symbols, read text, search Google for images, or look up RSMeans definitions. Click any detected text on the blueprint to ask about it!
                    </div>
                )}
                
                {messages.map((msg, i) => (
                    <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}>
                        
                        {/* Tool execution logs */}
                        {msg.role === "agent" && msg.tool_calls && msg.tool_calls.length > 0 && (
                            <div style={{ marginBottom: "8px", display: "flex", flexDirection: "column", gap: "4px" }}>
                                {msg.tool_calls.map((tc, j) => (
                                    <div key={j} style={{ fontSize: "12px", color: "#64748b", fontStyle: "italic" }}>
                                        {tc.status === "running" ? "⚙️ Running: " : "✅ Finished: "}
                                        {tc.name}
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Message bubble */}
                        {msg.text && (
                            <div style={{
                                background: msg.role === "user" ? "#3b82f6" : "#334155",
                                color: "#f1f5f9",
                                padding: "10px 14px",
                                borderRadius: "8px",
                                maxWidth: "90%",
                                fontSize: "14px",
                                lineHeight: "1.6",
                                whiteSpace: "pre-wrap"
                            }}>
                                {msg.text}
                            </div>
                        )}
                        {/* Loading pulse indicator */}
                        {msg.role === "agent" && !msg.text && isLoading && (
                            <div style={{ color: "#64748b", fontSize: "14px", fontStyle: "italic", marginTop: "4px" }}>
                                Thinking...
                            </div>
                        )}
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSend} style={{ padding: "12px", borderTop: "1px solid rgba(255,255,255,0.07)", display: "flex", gap: "8px" }}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={imageUrl ? "Ask the assistant..." : "Upload an image first"}
                    disabled={!imageUrl || isLoading}
                    style={{
                        flex: 1,
                        background: "rgba(255,255,255,0.05)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: "6px",
                        padding: "8px 12px",
                        color: "#fff",
                        fontSize: "14px",
                        outline: "none"
                    }}
                />
                <button 
                    type="submit" 
                    disabled={!imageUrl || isLoading || !input.trim()}
                    style={{
                        background: "#3b82f6",
                        color: "white",
                        border: "none",
                        borderRadius: "6px",
                        padding: "0 14px",
                        cursor: (!imageUrl || isLoading || !input.trim()) ? "not-allowed" : "pointer",
                        opacity: (!imageUrl || isLoading || !input.trim()) ? 0.5 : 1,
                        fontWeight: 600
                    }}
                >
                    Send
                </button>
            </form>
        </aside>
    );
});

export default AgentChatPanel;
