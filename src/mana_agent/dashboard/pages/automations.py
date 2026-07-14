from __future__ import annotations

from pathlib import Path

import streamlit as st

from mana_agent.ui.streamlit_helpers import (
    append_automation_run,
    delete_schedule,
    find_mana_root,
    list_schedules,
    load_automations,
    save_automations,
    schedule_status,
    set_schedule_enabled,
    trigger_automation,
)


def render(root: Path | None = None) -> None:
    root = root or find_mana_root()
    st.header("Automations")
    cfg = load_automations(root)
    autos = cfg.get("automations", [])
    runs = cfg.get("runs", [])
    with st.form("new_auto", clear_on_submit=True):
        name = st.text_input("Name", value="Self-Improve on Verify")
        trigger = st.selectbox("Trigger", ["manual", "on_success", "interval"])
        action = st.selectbox("Action", ["self_improvement", "daily_report", "analyze", "noop"])
        enabled = st.checkbox("Enabled", value=True)
        if st.form_submit_button("Create / Update") and name:
            existing = [a for a in autos if a.get("name") != name]
            existing.append(
                {
                    "id": name.lower().replace(" ", "_"),
                    "name": name,
                    "trigger": trigger,
                    "action": action,
                    "enabled": enabled,
                }
            )
            cfg["automations"] = existing
            save_automations(cfg, root)
            st.success("Saved.")
            st.rerun()
    for a in autos:
        cols = st.columns([3, 1, 1, 1])
        cols[0].write(f"**{a.get('name')}** — {a.get('trigger')} → {a.get('action')}")
        if cols[1].button("Run", key=f"run_{a.get('id')}"):
            r = trigger_automation(a.get("action", "noop"), root=root)
            append_automation_run({"automation": a.get("name"), "result": r}, root)
            st.json(r)
        if cols[2].button("Toggle", key=f"tog_{a.get('id')}"):
            a["enabled"] = not a.get("enabled", True)
            save_automations(cfg, root)
            st.rerun()
        if cols[3].button("Del", key=f"del_{a.get('id')}"):
            cfg["automations"] = [x for x in autos if x.get("id") != a.get("id")]
            save_automations(cfg, root)
            st.rerun()
    st.subheader("Schedules")
    for schedule in list_schedules(root):
        with st.expander(f"{schedule['name']} · {schedule['cron']}"):
            st.json(schedule_status(schedule["id"], root))
            if st.button("Disable" if schedule["enabled"] else "Enable", key=f"sched_{schedule['id']}"):
                set_schedule_enabled(schedule["id"], not schedule["enabled"], root)
                st.rerun()
            if st.button("Remove", key=f"rm_{schedule['id']}"):
                delete_schedule(schedule["id"], root)
                st.rerun()
    st.subheader("Recent runs")
    for r in reversed(runs[-8:]):
        st.write(f"- {r.get('ts', '')}: {r.get('action') or r.get('automation')}")
