"""Mana Agent Web Dashboard (Grok Build - Streamlit MVP).

Entry point for the optional web UI.

Run:
    streamlit run dashboard/app.py
    # or after CLI integration:
    mana-agent dashboard

Design:
- Read-only first (safe).
- Reuses existing .mana/ artifacts, renderers, and multi-agent concepts.
- Sidebar navigation.
- "Powered by mana-agent multi-agent runtime" branding.
- Lazy / optional: core package does not require streamlit.

Grok Build rules followed:
- Inspect + small focused files.
- No changes to CLI core, multi_agent, routing, or decision layer.
- Graceful if optional deps missing (handled in CLI wrapper later).
- Model-driven philosophy preserved (dashboard visualizes decisions/traces).

Future: full multipage + mutation approval gates + live triggers.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import streamlit as st
except ImportError as e:
    print("ERROR: streamlit is required to run the dashboard.", file=sys.stderr)
    print("pip install 'mana-agent[dashboard]'", file=sys.stderr)
    raise SystemExit(1) from e

# Lazy import of helpers (never at top of core)
try:
    from mana_agent.ui.streamlit_helpers import (
        find_mana_root,
        get_index_stats,
        get_last_analysis_summary,
        load_recent_traces,
        load_taskboard_state,
    )
except Exception as e:  # pragma: no cover - dashboard optional
    st.error(f"Failed to load mana-agent helpers: {e}")
    st.stop()

st.set_page_config(
    page_title="Mana Agent Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Branding / Header ---
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
      <span style="font-size:28px">🧠</span>
      <div>
        <h1 style="margin:0">Mana Agent</h1>
        <div style="color:#888;font-size:0.9rem">Web Dashboard • Powered by multi-agent runtime</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

root = find_mana_root()
st.caption(f"Repository root: `{root}`")

# --- Sidebar ---
st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Overview",
        "Chat",
        "Reports",
        "Taskboard & Traces",
        "Metrics",
        "Automations",
    ],
    index=0,
)

st.sidebar.divider()
st.sidebar.caption("Grok Build MVP • Read-only first")
if st.sidebar.button("Refresh data"):
    st.rerun()

# --- Page content ---
if page == "Overview":
    st.header("Project Overview")

    col1, col2, col3 = st.columns(3)
    idx = get_index_stats(root)
    col1.metric("Index Ready", "✅" if idx.get("ready") else "❌", idx.get("chunks", 0))
    col2.metric("Chunks", idx.get("chunks", 0))
    col3.metric("Root", str(root.name))

    st.subheader("Last Analysis")
    analysis = get_last_analysis_summary(root)
    if analysis.get("type") == "md":
        st.markdown(analysis.get("preview", "")[:1500])
        st.caption(f"Source: {analysis.get('path')}")
    elif analysis.get("type") == "json":
        st.json(analysis.get("data", {}))
    else:
        st.info(analysis.get("message", "No analysis yet."))

    st.subheader("Quick Actions (safe)")
    if st.button("Run Analysis (read-only mode)"):
        st.info("This would invoke `mana-agent analyze` via the existing service layer.\n"
                "In a later iteration this calls the approved path only.")
        # Future: subprocess or lazy service call returning artifacts.

    if st.button("Open Chat in terminal"):
        st.code("mana-agent chat --root-dir " + str(root), language="bash")

elif page == "Chat":
    st.header("Interactive Chat (embedded)")
    st.caption("MVP: The real chat experience lives in the CLI TUI. "
               "This area will later embed AskAgent / chat session via the runtime.")
    prompt = st.text_input("Ask something about the repo (preview)")
    if prompt:
        st.write("**You:**", prompt)
        st.info("Dashboard chat integration will reuse the existing AskService / MainAgent "
                "with model decision layer. (Not executed in this read-only MVP.)")

elif page == "Reports":
    st.header("Reports & Artifacts")
    st.tabs(["Mermaid", "HTML", "JSON", "Markdown"])

    # Placeholder content - in real impl load from .mana or docs/analyze
    st.subheader("Example Mermaid (from analysis)")
    st.code(
        "graph TD\n  A[User] -->|chat| B[MainAgent]\n  B --> C[Taskboard]\n",
        language="mermaid",
    )
    st.caption("Real reports will render using existing renderers/html_report + st components.")

elif page == "Taskboard & Traces":
    st.header("Live Taskboard & Traces")

    tb = load_taskboard_state(root)
    st.json(tb, expanded=False)

    st.subheader("Recent Traces (last entries)")
    traces = load_recent_traces(root, limit=3)
    if traces:
        for t in traces[:6]:
            with st.expander(f"{t.get('_file', 'trace')} - {t.get('kind', t.get('event', 'event'))}"):
                st.json(t)
    else:
        st.write("No traces found under .mana/traces/")

elif page == "Metrics":
    st.header("Metrics")
    st.caption("Token usage, success rates, and session stats (mock + real telemetry later).")

    c1, c2, c3 = st.columns(3)
    c1.metric("Sessions (today)", "42", "+3")
    c2.metric("Avg Tokens / turn", "1.2k")
    c3.metric("Success rate", "94%")

    st.line_chart({"tokens": [1200, 800, 1500, 900, 1100]})

elif page == "Automations":
    st.header("Automations")
    st.write("GitHub Actions templates and self-improvement jobs will appear here.")
    st.info("See Phase 3. Example trigger buttons will call scheduler / self_improvement safely.")

st.divider()
st.caption("© mana-agent • All decisions go through the validated model decision layer. No fallbacks.")
