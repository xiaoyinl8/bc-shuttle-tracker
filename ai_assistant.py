"""Shared AI assistant logic and rendering for BC Shuttle Tracker."""

import json
import os
import re
from datetime import datetime
from typing import Any

import streamlit as st
from openai import OpenAI
from streamlit.errors import StreamlitSecretNotFoundError

from shuttle_simulation import (
    build_eta_prediction,
    get_stop_arrivals,
    initialize_simulation_state,
)


COMM_AVE_SERVICE_SCHEDULE = {
    "weekday": [
        {
            "start": "07:00",
            "end": "17:00",
            "service_name": "Comm. Ave. Direct",
            "headway": "Every 7-10 Minutes",
            "notes": "Direct service runs the outer Commonwealth Ave stops only.",
        },
        {
            "start": "17:00",
            "end": "23:59",
            "service_name": "Comm. Ave. All Stops",
            "headway": "Every 10-15 Minutes",
            "notes": "Evening service returns to the full all-stops loop.",
        },
        {
            "start": "00:00",
            "end": "02:00",
            "service_name": "Comm. Ave. All Stops",
            "headway": "Every 10-15 Minutes",
            "notes": "Late-night weekday service continues after midnight on the full loop.",
        },
    ],
    "weekend": [
        {
            "start": "08:00",
            "end": "11:30",
            "service_name": "Comm. Ave. Direct",
            "headway": "Every 30 Minutes",
            "notes": "Morning weekend service is direct and much less frequent.",
        },
        {
            "start": "11:30",
            "end": "23:59",
            "service_name": "Comm. Ave. All Stops",
            "headway": "Every 10-15 Minutes",
            "notes": "Weekend daytime and evening service uses the full all-stops loop.",
        },
        {
            "start": "00:00",
            "end": "02:00",
            "service_name": "Comm. Ave. All Stops",
            "headway": "Every 10-15 Minutes",
            "notes": "Late-night weekend service continues after midnight on the full loop.",
        },
    ],
    "source_note": "Imported from Comm Ave updated 11.25.24 PDF schedule.",
}


def _ensure_state() -> None:
    if "route_definitions" not in st.session_state:
        initialize_simulation_state()
    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []
    if "ai_user_profile" not in st.session_state:
        st.session_state.ai_user_profile = {
            "prefers_early": False,
            "avoids_crowded": False,
            "risk_tolerance": "balanced",
            "max_wait_minutes": 12,
            "preferred_routes": [],
            "recent_goals": [],
        }


def _reset_ai_memory() -> None:
    st.session_state.ai_chat_history = []
    st.session_state.ai_user_profile = {
        "prefers_early": False,
        "avoids_crowded": False,
        "risk_tolerance": "balanced",
        "max_wait_minutes": 12,
        "preferred_routes": [],
        "recent_goals": [],
    }


def _get_configured_api_key() -> str:
    try:
        secret_key = st.secrets.get("OPENAI_API_KEY", "")
    except StreamlitSecretNotFoundError:
        secret_key = ""
    return secret_key or os.getenv("OPENAI_API_KEY", "")


def _confidence_label(confidence: int) -> str:
    if confidence >= 80:
        return "high"
    if confidence >= 60:
        return "medium"
    return "low"


def _capacity_label(capacity_pct: int) -> str:
    if capacity_pct >= 85:
        return "crowded"
    if capacity_pct >= 60:
        return "moderate"
    return "light"


def _minutes_since_midnight(now: datetime) -> int:
    return now.hour * 60 + now.minute


def _parse_time_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _find_active_comm_ave_service(now: datetime) -> dict[str, Any] | None:
    service_day = "weekday" if now.weekday() < 5 else "weekend"
    current_minutes = _minutes_since_midnight(now)
    windows = COMM_AVE_SERVICE_SCHEDULE[service_day]

    for window in windows:
        start = _parse_time_to_minutes(window["start"])
        end = _parse_time_to_minutes(window["end"])
        if start <= end:
            in_window = start <= current_minutes <= end
        else:
            in_window = current_minutes >= start or current_minutes <= end
        if in_window:
            return {"service_day": service_day, **window}
    return None


def _remember_goal(user_input: str) -> None:
    lowered = user_input.lower()
    matched_stop = next(
        (stop for stop in st.session_state.stops if stop.lower() in lowered),
        None,
    )
    if not matched_stop:
        return

    goals = st.session_state.ai_user_profile["recent_goals"]
    if matched_stop in goals:
        goals.remove(matched_stop)
    goals.append(matched_stop)
    st.session_state.ai_user_profile["recent_goals"] = goals[-5:]


def _update_user_profile_from_message(user_input: str) -> None:
    lowered = user_input.lower()
    profile = st.session_state.ai_user_profile

    if any(term in lowered for term in ["early", "on time", "dont want to be late", "don't want to be late", "make it on time"]):
        profile["prefers_early"] = True
        profile["risk_tolerance"] = "low"

    if any(term in lowered for term in ["not crowded", "less crowded", "avoid crowded", "seat", "seats", "empty bus"]):
        profile["avoids_crowded"] = True

    if any(term in lowered for term in ["fastest", "quickest", "soonest", "asap", "hurry"]):
        profile["risk_tolerance"] = "time_sensitive"

    wait_match = re.search(r"(\d+)\s*(minute|min)\b", lowered)
    if wait_match and any(term in lowered for term in ["wait", "waiting", "within", "max"]):
        profile["max_wait_minutes"] = max(1, min(30, int(wait_match.group(1))))

    for route_name in st.session_state.route_definitions:
        route_key = route_name.lower()
        if "comm" in lowered and "comm ave all stops" not in profile["preferred_routes"]:
            profile["preferred_routes"].append("Comm Ave All Stops")
        elif "newton" in lowered and "Newton Campus Express" not in profile["preferred_routes"]:
            profile["preferred_routes"].append("Newton Campus Express")
        elif route_key in lowered and route_name not in profile["preferred_routes"]:
            profile["preferred_routes"].append(route_name)

    profile["preferred_routes"] = profile["preferred_routes"][-3:]
    _remember_goal(user_input)


def _build_suggested_questions() -> list[str]:
    profile = st.session_state.ai_user_profile
    selected_stop = st.session_state.user_stop
    suggestions: list[str] = []

    if not st.session_state.ai_chat_history:
        suggestions.append(f"When is the next shuttle to {selected_stop}?")
        suggestions.append(f"Which shuttle should I take from {selected_stop} if I want the lowest-risk option?")

        if profile["avoids_crowded"]:
            suggestions.append("I prefer less crowded buses. Which option should I wait for?")
        else:
            suggestions.append("I want the fastest option right now. What do you recommend?")

        if profile["recent_goals"]:
            suggestions.append(
                f"Help me get to {profile['recent_goals'][-1]} with the best shuttle choice."
            )
        else:
            suggestions.append("What if I leave 5 minutes later?")
    else:
        last_assistant = next(
            (msg for msg in reversed(st.session_state.ai_chat_history) if msg["role"] == "assistant"),
            None,
        )
        structured = last_assistant.get("structured_data", {}) if last_assistant else {}
        follow_up_question = structured.get("follow_up_question") if isinstance(structured, dict) else None
        if follow_up_question:
            suggestions.append(str(follow_up_question))

        if profile["avoids_crowded"]:
            suggestions.append("Can you compare the least crowded option with the fastest one?")
        else:
            suggestions.append("Can you compare the best option with the next alternative?")

        if profile["prefers_early"]:
            suggestions.append("Which option gives me the best chance of arriving early?")
        else:
            suggestions.append("What if I wait 10 more minutes?")

        suggestions.append("How confident are you in that recommendation?")

        if selected_stop:
            suggestions.append(f"Would your recommendation change if I started from {selected_stop}?")

    deduped: list[str] = []
    for suggestion in suggestions:
        if suggestion and suggestion not in deduped:
            deduped.append(suggestion)
    return deduped[:4]


def _render_suggested_questions(section_key: str) -> str | None:
    suggestions = _build_suggested_questions()
    if not suggestions:
        return None

    label = "Suggested starters" if not st.session_state.ai_chat_history else "Keep exploring"
    st.caption(label)
    columns = st.columns(2, gap="small")
    chosen: str | None = None
    for idx, question in enumerate(suggestions):
        with columns[idx % 2]:
            if st.button(
                question,
                key=f"{section_key}_suggestion_{idx}",
                use_container_width=True,
            ):
                chosen = question
    return chosen


def _submit_user_message(user_input: str, api_key: str) -> str | None:
    clean_input = user_input.strip()
    if not clean_input:
        return None

    _update_user_profile_from_message(clean_input)
    st.session_state.ai_chat_history.append({"role": "user", "content": clean_input})
    try:
        _process_ai_response(api_key)
    except Exception as exc:
        st.session_state.ai_chat_history.pop()
        return str(exc)
    return None


def _build_context_payload() -> dict[str, Any]:
    selected = st.session_state.user_stop
    now = datetime.now()
    eta = build_eta_prediction(selected)
    arrivals = get_stop_arrivals(selected)
    recent_feedback = st.session_state.feedback_history[-5:]
    active_comm_ave_service = _find_active_comm_ave_service(now)

    active_alerts = []
    for shuttle_id, shuttle in st.session_state.shuttle_data.items():
        delay = shuttle.get("delay_minutes", 0)
        if abs(delay) >= 5:
            active_alerts.append(
                {
                    "shuttle_id": shuttle_id,
                    "label": shuttle["label"],
                    "route": shuttle["route"],
                    "delay_minutes": delay,
                }
            )

    best = eta["best_match"]
    alternatives = []
    for arrival in eta["alternatives"]:
        alternatives.append(
            {
                "shuttle_id": arrival["shuttle_id"],
                "label": arrival["label"],
                "route": arrival["route"],
                "eta_minutes": arrival["eta_minutes"],
                "capacity_pct": arrival["capacity_pct"],
                "capacity_label": _capacity_label(arrival["capacity_pct"]),
                "delay_minutes": arrival["delay_minutes"],
                "tradeoff_hint": (
                    "less crowded but slower"
                    if best and arrival["capacity_pct"] < best["capacity_pct"] and arrival["eta_minutes"] > best["eta_minutes"]
                    else "faster but more crowded"
                    if best and arrival["capacity_pct"] > best["capacity_pct"] and arrival["eta_minutes"] < best["eta_minutes"]
                    else "viable backup option"
                ),
            }
        )

    what_if_options = []
    if best:
        what_if_options.append(
            {
                "scenario": "Leave now",
                "outcome": f"Best current option is {best['label']} on {best['route']} in about {eta['min']}-{eta['max']} min.",
            }
        )
        if alternatives:
            alt = alternatives[0]
            delta = alt["eta_minutes"] - best["eta_minutes"]
            what_if_options.append(
                {
                    "scenario": "Wait for the next reasonable alternative",
                    "outcome": f"{alt['label']} arrives about {abs(delta)} min {'later' if delta >= 0 else 'earlier'} with {alt['capacity_label']} crowding.",
                }
            )
        if st.session_state.ai_user_profile["avoids_crowded"]:
            less_crowded = next(
                (item for item in [best, *eta["alternatives"]] if item["capacity_pct"] <= 55),
                None,
            )
            if less_crowded:
                what_if_options.append(
                    {
                        "scenario": "Choose a less crowded ride",
                        "outcome": f"{less_crowded['label']} looks lighter at about {less_crowded['capacity_pct']}% full.",
                    }
                )

    return {
        "current_time": now.strftime("%I:%M %p"),
        "current_day_type": "weekday" if now.weekday() < 5 else "weekend",
        "selected_stop": selected,
        "user_profile": st.session_state.ai_user_profile,
        "prediction": {
            "min_eta": eta["min"],
            "max_eta": eta["max"],
            "confidence": eta["confidence"],
            "confidence_label": _confidence_label(eta["confidence"]),
            "best_match": best,
            "alternatives": alternatives,
        },
        "arrivals": arrivals[:4],
        "route_summaries": [
            {
                "route": route_name,
                "service_days": route["service_days"],
                "service_window": route["service_window"],
                "headway": route["headway"],
            }
            for route_name, route in st.session_state.route_definitions.items()
        ],
        "service_schedule_reference": {
            "comm_ave": COMM_AVE_SERVICE_SCHEDULE,
            "active_comm_ave_service": active_comm_ave_service,
        },
        "all_stops": [
            {"name": stop_name, "routes": stop["routes"]}
            for stop_name, stop in st.session_state.stops.items()
        ],
        "recent_feedback": recent_feedback,
        "active_alerts": active_alerts,
        "what_if_options": what_if_options,
    }


_SYSTEM_PROMPT = """\
You are the BC Shuttle Decision Assistant for Boston College.

You do more than answer questions. You help riders decide what to do next using live shuttle data,
predicted arrival windows, confidence scores, route alternatives, active delay alerts, and user preferences.

Rules:
- Ground every answer in the provided JSON context.
- Recommend a concrete action when the user seems to need a decision.
- Explain why using ETA, delay, crowding, route type, and confidence.
- Use the service_schedule_reference data when reasoning about time-of-day frequency, likely service pattern, and whether Comm. Ave. Direct or Comm. Ave. All Stops is expected to be running.
- Be transparent about uncertainty. Never present weak predictions as certain.
- Personalize recommendations when user preferences are available.
- Offer at least one alternative when there is a meaningful tradeoff.
- Support what-if reasoning when relevant.
- Keep the tone practical, calm, and student-friendly.
- If information is missing, say that clearly.

Shuttle IDs for delay updates:
- comm-1 = Comm Ave 1
- comm-2 = Comm Ave 2
- newton-1 = Newton Express 1
- newton-2 = Newton Express 2

Respond with a single valid JSON object and no extra text. Use this schema:
{
  "intent": "arrival_check|decision_help|delay_report|schedule|capacity|other",
  "summary": "2-3 sentence rider-facing summary",
  "recommended_option": {
    "action": "short recommendation",
    "route": "route name or null",
    "bus": "bus label or null",
    "eta_minutes": 0,
    "reasoning": ["reason 1", "reason 2"]
  },
  "confidence": {
    "score": 0,
    "label": "high|medium|low",
    "explanation": "plain language explanation"
  },
  "alternatives": [
    {"action": "backup recommendation", "tradeoff": "brief tradeoff"}
  ],
  "what_if_options": [
    {"scenario": "what if case", "outcome": "expected outcome"}
  ],
  "proactive_alert": "optional short alert or null",
  "follow_up_question": "optional follow-up or null",
  "delay_update": {
    "shuttle_id": "comm-1",
    "delay_minutes": 0
  }
}

Only set delay_update when the user explicitly reports or clears a delay. Otherwise set it to null.\
"""


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _normalize_delay_update(payload: dict[str, Any]) -> dict[str, Any] | None:
    delay_data = payload.get("delay_update")
    if not isinstance(delay_data, dict):
        return None

    shuttle_id = delay_data.get("shuttle_id", "")
    delay_minutes = delay_data.get("delay_minutes", 0)
    if shuttle_id not in st.session_state.shuttle_data:
        return None

    try:
        return {"shuttle_id": shuttle_id, "delay_minutes": int(delay_minutes)}
    except (TypeError, ValueError):
        return None


def _format_list(items: list[str], heading: str) -> str:
    if not items:
        return ""
    body = "\n".join(f"- {item}" for item in items[:3] if item)
    if not body:
        return ""
    return f"**{heading}**\n{body}"


def _render_structured_reply(payload: dict[str, Any]) -> str:
    sections = []
    summary = payload.get("summary", "").strip()
    if summary:
        sections.append(summary)

    recommendation = payload.get("recommended_option") or {}
    action = recommendation.get("action")
    route = recommendation.get("route")
    bus = recommendation.get("bus")
    eta_minutes = recommendation.get("eta_minutes")
    reasoning = recommendation.get("reasoning") or []
    rec_line = action or "Check the live arrivals before heading out."
    details = []
    if bus:
        details.append(str(bus))
    if route:
        details.append(str(route))
    if isinstance(eta_minutes, int) and eta_minutes > 0:
        details.append(f"about {eta_minutes} min")
    if details:
        rec_line += " " + " | ".join(details)
    sections.append(f"**Recommendation**\n{rec_line}")

    reasoning_block = _format_list([str(item) for item in reasoning], "Why")
    if reasoning_block:
        sections.append(reasoning_block)

    confidence = payload.get("confidence") or {}
    confidence_score = confidence.get("score")
    confidence_label = confidence.get("label")
    confidence_explanation = confidence.get("explanation")
    if confidence_score is not None or confidence_explanation:
        label_text = f"{confidence_label.title()} confidence" if isinstance(confidence_label, str) else "Confidence"
        if isinstance(confidence_score, int):
            label_text += f" ({confidence_score}%)"
        conf_text = label_text
        if confidence_explanation:
            conf_text += f"\n{confidence_explanation}"
        sections.append(f"**Uncertainty**\n{conf_text}")

    alternatives = payload.get("alternatives") or []
    alt_lines = []
    for item in alternatives[:2]:
        if not isinstance(item, dict):
            continue
        action_text = item.get("action")
        tradeoff = item.get("tradeoff")
        if action_text and tradeoff:
            alt_lines.append(f"{action_text} ({tradeoff})")
        elif action_text:
            alt_lines.append(str(action_text))
    alt_block = _format_list(alt_lines, "Alternatives")
    if alt_block:
        sections.append(alt_block)

    what_if = payload.get("what_if_options") or []
    what_if_lines = []
    for item in what_if[:2]:
        if not isinstance(item, dict):
            continue
        scenario = item.get("scenario")
        outcome = item.get("outcome")
        if scenario and outcome:
            what_if_lines.append(f"{scenario}: {outcome}")
    what_if_block = _format_list(what_if_lines, "What If")
    if what_if_block:
        sections.append(what_if_block)

    proactive = payload.get("proactive_alert")
    if proactive:
        sections.append(f"**Heads Up**\n{proactive}")

    follow_up = payload.get("follow_up_question")
    if follow_up:
        sections.append(f"**Follow-Up**\n{follow_up}")

    return "\n\n".join(section for section in sections if section).strip()


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
    context_payload = _build_context_payload()
    system_msg = _SYSTEM_PROMPT + "\n\nLIVE_CONTEXT_JSON:\n" + json.dumps(context_payload, indent=2)

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
            response_format={"type": "json_object"},
        )
    raw = response.choices[0].message.content
    payload = _extract_json_object(raw)
    delay_data = _normalize_delay_update(payload)
    clean = _render_structured_reply(payload)

    delay_applied = None
    if delay_data:
        shuttle_id = delay_data["shuttle_id"]
        delay_minutes = delay_data["delay_minutes"]
        if shuttle_id in st.session_state.shuttle_data:
            _apply_delay(shuttle_id, delay_minutes)
            delay_applied = {"shuttle_id": shuttle_id, "delay_minutes": delay_minutes}

    record: dict[str, Any] = {"role": "assistant", "content": clean, "structured_data": payload}
    if delay_applied:
        record["delay_applied"] = delay_applied
    st.session_state.ai_chat_history.append(record)


def ensure_ai_state() -> None:
    _ensure_state()


def get_configured_api_key() -> str:
    return _get_configured_api_key()


def process_embedded_ai_message(user_input: str, user_api_key: str = "") -> str | None:
    """Process one AI message server-side for the embedded map assistant.

    Returns an error string when processing fails, otherwise None.
    """
    _ensure_state()
    api_key = user_api_key.strip() or _get_configured_api_key()
    if not api_key:
        return "Enter your OpenAI API key in the AI panel to enable chat."

    _update_user_profile_from_message(user_input)
    st.session_state.ai_chat_history.append({"role": "user", "content": user_input})
    try:
        _process_ai_response(api_key)
    except Exception as exc:
        st.session_state.ai_chat_history.pop()
        return str(exc)
    return None


# ── Standalone full-page rendering (pages/AI_Assistant.py) ──────────────────

def render_ai_assistant_page() -> None:
    _ensure_state()
    api_key = _get_configured_api_key()

    st.title("🤖 AI Shuttle Assistant")
    st.caption("Ask for the best shuttle, tradeoffs, confidence, or delay reports — the AI now tries to make a recommendation, not just answer.")

    with st.sidebar:
        st.header("AI Configuration")
        if api_key:
            st.success("Server-side OpenAI key detected.")
        else:
            st.warning("No server-side OpenAI key found. Add OPENAI_API_KEY to .streamlit/secrets.toml.")
        st.divider()

        if st.button("🗑️ Clear Chat History"):
            _reset_ai_memory()
            st.rerun()

        st.markdown("**💡 Try asking:**")
        st.caption("Which shuttle should I take if I need to get to Newton soon but want a seat?")
        st.caption("I hate crowded buses and can wait up to 10 minutes. What do you recommend?")
        st.caption("What if I leave 5 minutes later?")
        st.caption("The Newton express is running 10 minutes late.")
        st.caption("Comm Ave 1 is back on time.")

    if not api_key:
        st.info("Add OPENAI_API_KEY to .streamlit/secrets.toml to enable AI chat.")
        return

    selected_suggestion = _render_suggested_questions("page")
    if selected_suggestion:
        error = _submit_user_message(selected_suggestion, api_key)
        if error:
            st.error(f"OpenAI error: {error}")
        st.rerun()

    for msg in st.session_state.ai_chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            _render_delay_badge(msg)

    user_input = st.chat_input("Ask about shuttles or report a delay…")
    if not user_input:
        return

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        st.session_state.ai_chat_history.append({"role": "user", "content": user_input})
        _update_user_profile_from_message(user_input)
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
    api_key = _get_configured_api_key()

    st.markdown(
        """
        <div style="
            background:#1e293b;
            border:1px solid #334155;
            border-radius:18px;
            padding:16px 16px 14px;
            margin:10px 0 14px 0;
            box-shadow:0 14px 30px rgba(15,23,42,.16);
        ">
          <div style="font-size:15px;font-weight:800;color:#f8fafc;letter-spacing:-0.01em;">
            🤖 AI Shuttle Assistant
          </div>
          <div style="margin-top:6px;font-size:12px;line-height:1.45;color:#94a3b8;">
            Ask about arrivals, delays, and crowding using the app's server-side OpenAI key.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_status, col_clear = st.columns([6, 1])
    with col_status:
        if api_key:
            st.caption("Using the app's server-side OpenAI key.")
        else:
            st.caption("Add OPENAI_API_KEY to `.streamlit/secrets.toml` to enable AI chat.")
    with col_clear:
        if st.button("🗑️", key="clear_chat_panel", help="Clear chat history"):
            _reset_ai_memory()
            st.rerun()

    stop_names = sorted(st.session_state.stops.keys())
    current_stop = st.session_state.user_stop
    embedded_stop = st.session_state.get("embedded_user_stop")
    if embedded_stop not in stop_names or embedded_stop != current_stop:
        st.session_state.embedded_user_stop = current_stop
    st.caption("Your stop")
    selected_stop = st.selectbox(
        "Your stop",
        stop_names,
        key="embedded_user_stop",
        label_visibility="collapsed",
    )
    if selected_stop != st.session_state.user_stop:
        st.session_state.user_stop = selected_stop
        st.rerun()

    if not api_key:
        with st.container(height=380):
            st.caption("Try asking")
            _render_suggested_questions("panel_disabled")
        return

    selected_suggestion = _render_suggested_questions("panel")
    if selected_suggestion:
        error = _submit_user_message(selected_suggestion, api_key)
        if error:
            st.error(f"OpenAI error: {error}")
        st.rerun()

    # Scrollable chat history
    st.caption("Conversation")
    chat_container = st.container(height=520)
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
        error = _submit_user_message(user_input, api_key)
        if error:
            st.error(f"OpenAI error: {error}")
            return
        st.rerun()
