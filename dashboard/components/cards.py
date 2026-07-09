"""Example card components (Grok Build).

These are illustrative; expand with st.container + metrics as needed.
"""
import streamlit as st
from typing import Any


def stat_card(label: str, value: Any, delta: str | None = None) -> None:
    """Simple metric card wrapper."""
    if delta:
        st.metric(label, value, delta)
    else:
        st.metric(label, value)
