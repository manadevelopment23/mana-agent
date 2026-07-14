from __future__ import annotations

from pathlib import Path

import streamlit as st

from mana_agent.ui.streamlit_helpers import (
    create_schedule,
    delete_schedule,
    find_mana_root,
    list_schedules,
    run_schedule_now,
    schedule_status,
    set_schedule_enabled,
)


def render(root: Path | None = None) -> None:
    root = root or find_mana_root()
    st.header("Cron Jobs")
    with st.form("create_schedule", clear_on_submit=True):
        name = st.text_input("Name", placeholder="Nightly repository analysis")
        cron = st.text_input("POSIX cron", value="0 2 * * *")
        action = st.selectbox("Action", ["analyze", "daily_report", "self_improvement", "custom"])
        command = st.text_input("Custom command", disabled=action != "custom")
        targets = st.multiselect("Deploy to", ["local", "github"], default=["local"])
        if st.form_submit_button("Create and deploy", type="primary"):
            try:
                schedule = create_schedule(
                    name=name,
                    action=action,
                    cron=cron,
                    targets=targets,
                    command=command or None,
                    root=root,
                )
                st.success(f"Created {schedule['id']}")
                st.json(schedule.get("deployment", {}))
            except ValueError as exc:
                st.error(str(exc))
    for schedule in list_schedules(root):
        with st.expander(f"{schedule['name']} · {schedule['cron']}"):
            st.json(schedule_status(schedule["id"], root))
            c1, c2, c3 = st.columns(3)
            if c1.button("Run now", key=f"cron_run_{schedule['id']}"):
                st.json(run_schedule_now(schedule["id"], root))
            if c2.button("Disable" if schedule["enabled"] else "Enable", key=f"cron_tog_{schedule['id']}"):
                set_schedule_enabled(schedule["id"], not schedule["enabled"], root)
                st.rerun()
            if c3.button("Remove", key=f"cron_rm_{schedule['id']}"):
                delete_schedule(schedule["id"], root)
                st.rerun()
