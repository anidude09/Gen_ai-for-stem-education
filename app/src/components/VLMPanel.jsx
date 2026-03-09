/**
 * VLMPanel.jsx
 *
 * Right-side panel that shows GPT-4o Vision analysis results.
 * Receives vlmResult, vlmLoading, and vlmMode as props from App.jsx.
 *
 * States:
 *   - idle:    panel placeholder ("Run Detect to get AI analysis")
 *   - loading: animated skeleton while GPT-4o is thinking
 *   - result:  structured display with Drawing Type, Summary, Labels, Circles, Symbols, Tip
 */

import React from "react";

// ─── Category colour mapping ─────────────────────────────────────────────────
const CATEGORY_COLORS = {
    room_name: { bg: "rgba(59,130,246,0.18)", border: "rgba(59,130,246,0.5)", text: "#93c5fd" },
    dimension: { bg: "rgba(168,85,247,0.18)", border: "rgba(168,85,247,0.5)", text: "#c4b5fd" },
    annotation: { bg: "rgba(34,197,94,0.18)", border: "rgba(34,197,94,0.5)", text: "#86efac" },
    abbreviation: { bg: "rgba(251,191,36,0.18)", border: "rgba(251,191,36,0.5)", text: "#fde68a" },
    symbol: { bg: "rgba(239,68,68,0.18)", border: "rgba(239,68,68,0.5)", text: "#fca5a5" },
    reference: { bg: "rgba(20,184,166,0.18)", border: "rgba(20,184,166,0.5)", text: "#5eead4" },
    material: { bg: "rgba(249,115,22,0.18)", border: "rgba(249,115,22,0.5)", text: "#fdba74" },
    other: { bg: "rgba(100,116,139,0.18)", border: "rgba(100,116,139,0.5)", text: "#94a3b8" },
};

function Badge({ label, color }) {
    return (
        <span
            style={{
                display: "inline-block",
                padding: "2px 8px",
                borderRadius: "9999px",
                fontSize: "11px",
                fontWeight: 600,
                textTransform: "uppercase",
                letterSpacing: "0.04em",
                background: color?.bg || "rgba(100,116,139,0.18)",
                border: `1px solid ${color?.border || "rgba(100,116,139,0.5)"}`,
                color: color?.text || "#94a3b8",
                marginLeft: "6px",
                verticalAlign: "middle",
            }}
        >
            {label}
        </span>
    );
}

// ─── Skeleton loader ──────────────────────────────────────────────────────────
function SkeletonLine({ width = "100%", height = "12px", mb = "8px" }) {
    return (
        <div
            style={{
                width,
                height,
                marginBottom: mb,
                borderRadius: "4px",
                background: "linear-gradient(90deg, rgba(255,255,255,0.06) 25%, rgba(255,255,255,0.12) 50%, rgba(255,255,255,0.06) 75%)",
                backgroundSize: "200% 100%",
                animation: "vlm-shimmer 1.5s infinite",
            }}
        />
    );
}

// ─── Section wrapper ──────────────────────────────────────────────────────────
function Section({ title, children, isEmpty }) {
    if (isEmpty) return null;
    return (
        <div style={{ marginBottom: "18px" }}>
            <div
                style={{
                    fontSize: "10px",
                    fontWeight: 700,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    color: "#64748b",
                    marginBottom: "8px",
                }}
            >
                {title}
            </div>
            {children}
        </div>
    );
}

// ─── Main component ───────────────────────────────────────────────────────────
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
        position: "relative",
    };

    const headerStyle = {
        padding: "14px 16px 12px",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
        display: "flex",
        alignItems: "center",
        gap: "10px",
        flexShrink: 0,
    };

    const bodyStyle = {
        flex: 1,
        overflowY: "auto",
        padding: "16px",
        color: "#e2e8f0",
        fontSize: "13px",
    };


    // ── Idle state ──────────────────────────────────────────────────────────────
    if (!vlmLoading && !vlmResult) {
        return (
            <aside style={panelStyle}>
                <div style={headerStyle}>
                    <span style={{ fontWeight: 600, fontSize: "13px", color: "#f1f5f9" }}>
                        VLM Output
                    </span>
                </div>
                <div
                    style={{
                        ...bodyStyle,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#475569",
                        textAlign: "center",
                        gap: "12px",
                    }}
                >
                    <div style={{ fontSize: "40px", opacity: 0.4 }}>🏗️</div>
                    <div style={{ fontSize: "13px", lineHeight: 1.6 }}>
                        Click <strong style={{ color: "#64748b" }}>Detect</strong> or{" "}
                        <strong style={{ color: "#64748b" }}>Detect in selection</strong>
                        <br />
                        to get a GPT-4o Vision analysis of the drawing.
                    </div>
                </div>
            </aside>
        );
    }

    // ── Loading state ───────────────────────────────────────────────────────────
    if (vlmLoading) {
        return (
            <aside style={panelStyle}>
                <div style={headerStyle}>
                    <span style={{ fontSize: "16px" }}>🤖</span>
                    <span style={{ fontWeight: 600, fontSize: "13px", color: "#f1f5f9" }}>
                        VLM Output
                    </span>
                    <span
                        style={{
                            marginLeft: "auto",
                            fontSize: "11px",
                            color: "#60a5fa",
                            animation: "vlm-shimmer 2s infinite",
                        }}
                    >
                        Analyzing...
                    </span>
                </div>
                <div style={bodyStyle}>
                    <SkeletonLine width="60%" height="14px" mb="14px" />
                    <SkeletonLine width="100%" mb="6px" />
                    <SkeletonLine width="90%" mb="6px" />
                    <SkeletonLine width="80%" mb="18px" />
                    <SkeletonLine width="50%" height="14px" mb="10px" />
                    <SkeletonLine width="100%" mb="6px" />
                    <SkeletonLine width="95%" mb="6px" />
                    <SkeletonLine width="75%" mb="18px" />
                    <SkeletonLine width="55%" height="14px" mb="10px" />
                    <SkeletonLine width="100%" mb="6px" />
                    <SkeletonLine width="88%" mb="6px" />
                    <SkeletonLine width="70%" mb="6px" />
                </div>
            </aside>
        );
    }

    // ── Result state ────────────────────────────────────────────────────────────
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

            {/* Header */}
            <div style={headerStyle}>
                <span style={{ fontWeight: 600, fontSize: "13px", color: "#f1f5f9" }}>
                    VLM Output
                </span>
                {vlmMode === "region" && (
                    <Badge label="Region" color={CATEGORY_COLORS.reference} />
                )}
                {vlmMode === "full" && (
                    <Badge label="Full" color={CATEGORY_COLORS.annotation} />
                )}
            </div>

            <div style={bodyStyle}>

                {/* Drawing Type */}
                {drawing_type && (
                    <Section title="Drawing Type">
                        <div
                            style={{
                                padding: "8px 12px",
                                background: "rgba(59,130,246,0.1)",
                                border: "1px solid rgba(59,130,246,0.25)",
                                borderRadius: "8px",
                                color: "#93c5fd",
                                fontWeight: 600,
                                fontSize: "14px",
                            }}
                        >
                            {drawing_type}
                        </div>
                    </Section>
                )}

                {/* Summary */}
                <Section title="Summary" isEmpty={summary.length === 0}>
                    <ul style={{ margin: 0, paddingLeft: "18px", color: "#cbd5e1", lineHeight: 1.7 }}>
                        {summary.map((bullet, i) => (
                            <li key={i} style={{ marginBottom: "4px" }}>{bullet}</li>
                        ))}
                    </ul>
                </Section>

                {/* Text Labels */}
                <Section title={`Labels Found (${text_labels.length})`} isEmpty={text_labels.length === 0}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        {text_labels.map((label, i) => {
                            const cat = (label.category || "other").toLowerCase();
                            const color = CATEGORY_COLORS[cat] || CATEGORY_COLORS.other;
                            const isMatchable = matchableLabels && matchableLabels.has(label.text?.toUpperCase());
                            return (
                                <div
                                    key={i}
                                    className="vlm-label-row"
                                    onClick={() => isMatchable && onLabelClick && onLabelClick(label.text, cat)}
                                    style={{
                                        padding: "7px 10px",
                                        borderRadius: "6px",
                                        background: color.bg,
                                        border: `1px solid ${color.border}`,
                                        transition: "background 0.15s",
                                        cursor: isMatchable ? "pointer" : "default",
                                        opacity: isMatchable ? 1 : 0.7,
                                    }}
                                >
                                    <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "3px" }}>
                                        <span style={{ fontWeight: 600, color: "#f8fafc", fontSize: "13px" }}>
                                            {label.text}
                                        </span>
                                        <Badge label={cat.replace("_", " ")} color={color} />
                                        {isMatchable && (
                                            <span title="Click to highlight on drawing" style={{ marginLeft: "auto", fontSize: "13px", cursor: "pointer" }}>
                                                📍
                                            </span>
                                        )}
                                    </div>
                                    {label.explanation && (
                                        <div style={{ color: "#94a3b8", fontSize: "12px", lineHeight: 1.5 }}>
                                            {label.explanation}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </Section>

                {/* Detail Circles */}
                <Section title={`Detail Circles (${detail_circles.length})`} isEmpty={detail_circles.length === 0}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        {detail_circles.map((dc, i) => {
                            const hasPage = Boolean(dc.page_reference);
                            return (
                                <div
                                    key={i}
                                    onClick={() => hasPage && onCircleNavigate && onCircleNavigate(dc.page_reference, dc.number)}
                                    style={{
                                        padding: "7px 10px",
                                        borderRadius: "6px",
                                        background: "rgba(249,115,22,0.1)",
                                        border: "1px solid rgba(249,115,22,0.3)",
                                        cursor: hasPage ? "pointer" : "default",
                                        transition: "background 0.15s",
                                    }}
                                >
                                    <div style={{ display: "flex", alignItems: "center" }}>
                                        <span style={{ fontWeight: 700, color: "#fb923c" }}>
                                            {dc.number}
                                        </span>
                                        {dc.page_reference && (
                                            <span style={{ color: "#94a3b8", marginLeft: "6px" }}>
                                                → {dc.page_reference}
                                            </span>
                                        )}
                                        {hasPage && (
                                            <span title="Click to navigate to page" style={{ marginLeft: "auto", fontSize: "13px" }}>
                                                🔗
                                            </span>
                                        )}
                                    </div>
                                    {dc.meaning && (
                                        <div style={{ color: "#94a3b8", fontSize: "12px", marginTop: "3px" }}>
                                            {dc.meaning}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </Section>

                {/* Symbols */}
                <Section title={`Symbols (${symbols.length})`} isEmpty={symbols.length === 0}>
                    <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                        {symbols.map((sym, i) => (
                            <div key={i} style={{ display: "flex", gap: "8px", color: "#cbd5e1", fontSize: "12px" }}>
                                <span style={{ color: "#fbbf24", flexShrink: 0 }}>◆</span>
                                <span>
                                    <strong style={{ color: "#f1f5f9" }}>{sym.type}</strong>
                                    {sym.description && ` — ${sym.description}`}
                                </span>
                            </div>
                        ))}
                    </div>
                </Section>

                {/* Student Tip */}
                {student_tip && (
                    <div
                        style={{
                            marginTop: "4px",
                            padding: "10px 12px",
                            borderRadius: "8px",
                            background: "rgba(251,191,36,0.08)",
                            border: "1px solid rgba(251,191,36,0.25)",
                            borderLeft: "3px solid #fbbf24",
                        }}
                    >
                        <div
                            style={{
                                fontSize: "10px",
                                fontWeight: 700,
                                textTransform: "uppercase",
                                letterSpacing: "0.1em",
                                color: "#fbbf24",
                                marginBottom: "5px",
                            }}
                        >
                            💡 Student Tip
                        </div>
                        <div style={{ color: "#fde68a", fontSize: "12px", lineHeight: 1.6 }}>
                            {student_tip}
                        </div>
                    </div>
                )}

            </div>
        </aside>
    );
}
