"""Shared AI assistant logic and rendering for BC Shuttle Tracker."""

import json
import re
from datetime import datetime

import streamlit as st
from openai import OpenAI

from shuttle_simulation import get_stop_arrivals, initialize_simulation_state


def _ensure_state() -> None:
    if "route_definitions" not in st.session_state:
        initialize_simulation_state()
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []


def _get_shuttle_context() -> str:
    lines = [f"Current time: {datetime.now().strftime('%I:%M %p')}", ""]

    lines.append("=== LIVE SHUTTLE STATUS ===")
    for shuttle_id, shuttle in st.session_state.shuttle_data.items():
        delay = shuttle.get("delay_minutes", 0)
        delay_str = f" (+{delay} min delay)" if delay > 0 else (" (running early)" if delay < 0 else " (on time)")
        dwell = shuttle.get("dwell_seconds_remaining", 0)
        status = (
            f"boarding at {shuttle['current_stop']}"
            if dwell > 0
            else f"traveling from {shuttle['current_stop']} toward {shuttle['next_stop']}"
        )
        lines.append(
            f"- {shuttle_id} ({shuttle['label']}), route: {shuttle['route']}, "
            f"status: {status}, capacity: {shuttle['capacity_pct']}%{delay_str}"
        )

    lines += ["", "=== ROUTE SCHEDULES ==="]
    for route_name, route in st.session_state.route_definitions.items():
        lines.append(f"- {route_name}: {route['service_days']}, {route['service_window']}, {route['headway']}")

    lines += ["", "=== UPCOMING ARRIVALS AT SELECTED STOP ==="]
    selected = st.session_state.user_stop
    lines.append(f"Selected stop: {selected}")
    arrivals = get_stop_arrivals(selected)
    if arrivals:
        for a in arrivals[:4]:
            lines.append(
                f"  - {a['label']} ({a['route']}): {a['eta_minutes']} min away, "
                f"capacity {a['capacity_pct']}%, {'on time' if a['on_time'] else 'delayed'}"
            )
    else:
        lines.append("  No arrivals found for this stop.")

    lines += ["", "=== ALL STOPS ==="]
    for stop_name, stop in st.session_state.stops.items():
        lines.append(f"- {stop_name}: served by {', '.join(stop['routes'])}")

    return "\n".join(lines)


_SYSTEM_PROMPT = """\
You are the BC Shuttle Tracker AI assistant for Boston College. \
Help students and staff with real-time shuttle information.

You have access to live shuttle data injected below. Always use that data when answering.

Capabilities:
- Answer questions about next arrivals, ETAs, capacity, and delays
- Accept delay reports from users and update the system
- Summarize the shuttle schedule

Shuttle IDs for updates:
  comm-1   = Comm Ave 1
  comm-2   = Comm Ave 2
  newton-1 = Newton Express 1
  newton-2 = Newton Express 2

When a user reports a delay (e.g. "the comm ave bus is 10 minutes late") or clears one \
("back on time"), include at the very end of your message — after all human-readable text — \
a machine-readable block EXACTLY like this with no surrounding whitespace:
<delay_update>{"shuttle_id": "SHUTTLE_ID", "delay_minutes": NUMBER}</delay_update>

Use delay_minutes 0 when clearing a delay. Do not include this block unless the user is \
explicitly reporting or clearing a delay. Be friendly, concise, and accurate.\
"""


def _parse_delay_update(text: str) -> tuple[str, dict | None]:
    match = re.search(r"<delay_update>(.*?)</delay_update>", text, re.DOTALL)
    if not match:
        return text, None
    try:
        data = json.loads(match.group(1).strip())
        return text[: match.start()].rstrip(), data
    except (json.JSONDecodeError, ValueError):
        return text, None


def _apply_delay(shuttle_id: str, delay_minutes: int) -> str:
    shuttle = st.session_state.shuttle_data[shuttle_id]
    shuttle["delay_minutes"] = delay_minutes
    shuttle["on_time"] = delay_minutes == 0
    label = shuttle["label"]
    if delay_minutes == 0:
        msg = f"AI chat cleared delay for {label} — now on time"
    else:
        direction = "late" if delay_minutes > 0 else "early"
        msg = f"AI chat updated {label}: {abs(delay_minutes)} min {direction}"
    st.session_state.recent_updates.append({
        "time": datetime.now().strftime("%I:%M %p"),
        "message": msg,
    })
    if delay_minutes != 0:
        st.session_state.system_alerts.append({
            "message": f"⚠️ {label} is running {abs(delay_minutes)} min {'late' if delay_minutes > 0 else 'early'} (reported via AI chat)"
        })
    return label


def _render_delay_badge(msg: dict) -> None:
    if msg.get("delay_applied"):
        d = msg["delay_applied"]
        shuttle = st.session_state.shuttle_data.get(d["shuttle_id"], {})
        label = shuttle.get("label", d["shuttle_id"])
        mins = d["delay_minutes"]
        if mins == 0:
            st.success(f"✅ Delay cleared for {label} — marked on time")
        else:
            st.warning(
                f"⚠️ Applied to tracker: {label} {'+' if mins > 0 else ''}{mins} min"
            )


def _process_ai_response(api_key: str) -> None:
    """Call OpenAI using the current chat history and append the assistant response."""
    live_context = _get_shuttle_context()
    system_msg = _SYSTEM_PROMPT + "\n\n" + live_context

    messages = [{"role": "system", "content": system_msg}]
    for msg in st.session_state.ai_chat_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    client = OpenAI(api_key=api_key)
    with st.spinner("Thinking…"):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=600,
        )
    raw = response.choices[0].message.content
    clean, delay_data = _parse_delay_update(raw)

    delay_applied = None
    if delay_data:
        shuttle_id = delay_data.get("shuttle_id", "")
        delay_minutes = int(delay_data.get("delay_minutes", 0))
        if shuttle_id in st.session_state.shuttle_data:
            _apply_delay(shuttle_id, delay_minutes)
            delay_applied = {"shuttle_id": shuttle_id, "delay_minutes": delay_minutes}

    record: dict = {"role": "assistant", "content": clean}
    if delay_applied:
        record["delay_applied"] = delay_applied
    st.session_state.ai_chat_history.append(record)


# ── Standalone full-page rendering (pages/AI_Assistant.py) ──────────────────

def render_ai_assistant_page() -> None:
    _ensure_state()

    st.title("🤖 AI Shuttle Assistant")
    st.caption("Ask about arrivals, capacity, or report a delay — the AI reads live shuttle data automatically.")

    with st.sidebar:
        st.header("🔑 OpenAI API Key")
        api_key = st.text_input(
            "Enter your OpenAI API key",
            type="password",
            key="openai_api_key",
            placeholder="sk-...",
            help="Stored only in your browser session, never logged.",
        )
        st.caption("Key is stored only in this session.")
        st.divider()

        if st.button("🗑️ Clear Chat History"):
            st.session_state.ai_chat_history = []
            st.rerun()

        st.markdown("**💡 Try asking:**")
        st.caption("When's the next shuttle to Conte Forum?")
        st.caption("The Newton express is running 10 minutes late.")
        st.caption("How crowded is the Comm Ave shuttle right now?")
        st.caption("Summarize today's shuttle schedule.")
        st.caption("Comm Ave 1 is back on time.")

    if not api_key:
        st.info("Enter your OpenAI API key in the sidebar to start.")
        return

    for msg in st.session_state.ai_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            _render_delay_badge(msg)

    user_input = st.chat_input("Ask about shuttles or report a delay…")
    if not user_input:
        return

    st.session_state.ai_chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        try:
            _process_ai_response(api_key)
        except Exception as exc:
            st.error(f"OpenAI error: {exc}")
            st.session_state.ai_chat_history.pop()
            return
        last = st.session_state.ai_chat_history[-1]
        st.markdown(last["content"])
        _render_delay_badge(last)


# ── Inline panel rendering (embedded in map_page.py) ────────────────────────

def render_ai_assistant_panel() -> None:
    """Render AI assistant as a compact panel for embedding inside a column."""
    _ensure_state()

    st.markdown("### 🤖 AI Assistant")

    col_key, col_clear = st.columns([4, 1])
    with col_key:
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            key="openai_api_key",
            placeholder="sk-... (session only)",
            label_visibility="collapsed",
        )
    with col_clear:
        if st.button("🗑️", key="clear_chat_panel", help="Clear chat history"):
            st.session_state.ai_chat_history = []
            st.rerun()

    if not api_key:
        st.caption("Enter your OpenAI API key above to start chatting.")
        with st.container(height=380):
            st.markdown("**💡 Try asking:**")
            st.caption("When's the next shuttle to Conte Forum?")
            st.caption("The Newton express is running 10 minutes late.")
            st.caption("How crowded is the Comm Ave shuttle right now?")
            st.caption("Summarize today's shuttle schedule.")
            st.caption("Comm Ave 1 is back on time.")
        return

    # Scrollable chat history
    chat_container = st.container(height=420)
    with chat_container:
        if not st.session_state.ai_chat_history:
            st.caption("No messages yet — ask something below!")
        for msg in st.session_state.ai_chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                _render_delay_badge(msg)

    # Input form (st.chat_input pins to page bottom, so use a form here)
    with st.form("ai_panel_form", clear_on_submit=True, border=False):
        user_input = st.text_input(
            "Message",
            placeholder="Ask about shuttles or report a delay…",
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send ➤", use_container_width=True)

    if submitted and user_input.strip():
        st.session_state.ai_chat_history.append({"role": "user", "content": user_input.strip()})
        try:
            _process_ai_response(api_key)
        except Exception as exc:
            st.error(f"OpenAI error: {exc}")
            st.session_state.ai_chat_history.pop()
            return
        st.rerun()
