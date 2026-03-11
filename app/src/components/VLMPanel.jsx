/**
 * VLMPanel.jsx
 *
 * Right-side panel showing GPT-4o Vision analysis results.
 * Kept minimal — plain text, no heavy visuals.
 */

import React from "react";

// Simple category colors for label text
const CAT_COLORS = {
    room_name: "#93c5fd",
    dimension: "#c4b5fd",
    annotation: "#86efac",
    abbreviation: "#fde68a",
    symbol: "#fca5a5",
    reference: "#5eead4",
    material: "#fdba74",
    other: "#94a3b8",
};

export default function VLMPanel({ vlmResult, vlmLoading, vlmMode, onLabelClick, matchableLabels, onCircleNavigate, isOpen, onToggle }) {
    const panelStyle = {
        width: "340px",
        height: "100%",
        background: "rgba(15, 23, 42, 0.95)",
        borderLeft: "1px solid rgba(255,255,255,0.07)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        fontFamily: "inherit",
    };

    const headerStyle = {
        padding: "14px 16px 12px",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
        fontWeight: 600,
        fontSize: "13px",
        color: "#f1f5f9",
        flexShrink: 0,
    };

    const bodyStyle = {
        flex: 1,
        overflowY: "auto",
        padding: "16px",
        color: "#cbd5e1",
        fontSize: "13px",
        lineHeight: 1.7,
    };

    // ── Idle ────────────────────────────────────────────
    if (!vlmLoading && !vlmResult) {
        return (
            <aside style={panelStyle}>
                <div style={headerStyle}>AI Analysis</div>
                <div style={{ ...bodyStyle, color: "#475569", textAlign: "center", paddingTop: "40px" }}>
                    Click <strong>Detect</strong> or <strong>Detect in selection</strong> to analyze the drawing.
                </div>
            </aside>
        );
    }

    // ── Loading ────────────────────────────────────────
    if (vlmLoading) {
        return (
            <aside style={panelStyle}>
                <div style={headerStyle}>
                    AI Analysis
                    <span style={{ marginLeft: "8px", fontWeight: 400, fontSize: "11px", color: "#60a5fa" }}>
                        Analyzing...
                    </span>
                </div>
                <div style={{ ...bodyStyle, color: "#475569" }}>
                    GPT-4o is analyzing the {vlmMode === "region" ? "selected region" : "full drawing"}. This may take a few seconds.
                </div>
            </aside>
        );
    }

    // ── Result ─────────────────────────────────────────
    const {
        drawing_type,
        summary = [],
        text_labels = [],
        detail_circles = [],
        symbols = [],
        student_tip,
    } = vlmResult;

    return (
        <aside style={panelStyle}>
            <div style={headerStyle}>
                AI Analysis
                {vlmMode && (
                    <span style={{ marginLeft: "8px", fontWeight: 400, fontSize: "11px", color: "#94a3b8" }}>
                        ({vlmMode === "region" ? "Region" : "Full"})
                    </span>
                )}
            </div>

            <div style={bodyStyle}>

                {/* Drawing Type */}
                {drawing_type && (
                    <div style={{ marginBottom: "16px" }}>
                        <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Drawing Type
                        </div>
                        <div style={{ color: "#f1f5f9", fontWeight: 600 }}>{drawing_type}</div>
                    </div>
                )}

                {/* Summary */}
                {summary.length > 0 && (
                    <div style={{ marginBottom: "16px" }}>
                        <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Summary
                        </div>
                        <ul style={{ margin: 0, paddingLeft: "16px" }}>
                            {summary.map((s, i) => (
                                <li key={i} style={{ marginBottom: "4px" }}>{s}</li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Text Labels */}
                {text_labels.length > 0 && (
                    <div style={{ marginBottom: "16px" }}>
                        <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Labels ({text_labels.length})
                        </div>
                        {text_labels.map((label, i) => {
                            const cat = (label.category || "other").toLowerCase();
                            const color = CAT_COLORS[cat] || CAT_COLORS.other;
                            const isMatchable = matchableLabels && matchableLabels.has(label.text?.toUpperCase());
                            return (
                                <div
                                    key={i}
                                    onClick={() => isMatchable && onLabelClick && onLabelClick(label.text, cat)}
                                    style={{
                                        padding: "6px 0",
                                        borderBottom: "1px solid rgba(255,255,255,0.05)",
                                        cursor: isMatchable ? "pointer" : "default",
                                        opacity: isMatchable ? 1 : 0.7,
                                    }}
                                >
                                    <span style={{ color, fontWeight: 600 }}>{label.text}</span>
                                    <span style={{ color: "#64748b", fontSize: "11px", marginLeft: "6px" }}>{cat.replace("_", " ")}</span>
                                    {label.explanation && (
                                        <div style={{ color: "#94a3b8", fontSize: "12px", marginTop: "2px" }}>{label.explanation}</div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Detail Circles */}
                {detail_circles.length > 0 && (
                    <div style={{ marginBottom: "16px" }}>
                        <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Detail Circles ({detail_circles.length})
                        </div>
                        {detail_circles.map((dc, i) => {
                            const hasPage = Boolean(dc.page_reference);
                            return (
                                <div
                                    key={i}
                                    onClick={() => hasPage && onCircleNavigate && onCircleNavigate(dc.page_reference, dc.number)}
                                    style={{
                                        padding: "6px 0",
                                        borderBottom: "1px solid rgba(255,255,255,0.05)",
                                        cursor: hasPage ? "pointer" : "default",
                                    }}
                                >
                                    <span style={{ fontWeight: 600, color: "#fb923c" }}>{dc.number}</span>
                                    {dc.page_reference && <span style={{ color: "#94a3b8", marginLeft: "6px" }}>→ {dc.page_reference}</span>}
                                    {dc.meaning && <div style={{ color: "#94a3b8", fontSize: "12px", marginTop: "2px" }}>{dc.meaning}</div>}
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Symbols */}
                {symbols.length > 0 && (
                    <div style={{ marginBottom: "16px" }}>
                        <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Symbols ({symbols.length})
                        </div>
                        {symbols.map((sym, i) => (
                            <div key={i} style={{ padding: "4px 0", fontSize: "12px" }}>
                                <span style={{ fontWeight: 600, color: "#f1f5f9" }}>{sym.type}</span>
                                {sym.description && <span style={{ color: "#94a3b8" }}> — {sym.description}</span>}
                            </div>
                        ))}
                    </div>
                )}

                {/* Student Tip */}
                {student_tip && (
                    <div style={{ padding: "10px 12px", borderLeft: "2px solid #fbbf24", background: "rgba(251,191,36,0.06)", borderRadius: "4px" }}>
                        <div style={{ fontSize: "11px", color: "#fbbf24", marginBottom: "4px", fontWeight: 600 }}>Tip</div>
                        <div style={{ color: "#fde68a", fontSize: "12px", lineHeight: 1.6 }}>{student_tip}</div>
                    </div>
                )}

            </div>
        </aside>
    );
}
