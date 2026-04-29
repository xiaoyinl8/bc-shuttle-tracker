import json
import os
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components
from streamlit.errors import StreamlitSecretNotFoundError

from ai_assistant import ensure_ai_state
from interaction_ui import apply_shared_styles
from shuttle_simulation import (
    STOP_CAPACITY_DELTA,
    build_eta_prediction,
    display_stop_name,
    get_stop_arrivals,
    initialize_simulation_state,
    update_shuttle_positions,
)


st.set_page_config(
    page_title="BC Shuttle Tracker",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_shared_styles()


def apply_fullscreen_shell_styles() -> None:
    st.markdown(
        """
        <style>
        #MainMenu,
        header,
        header[data-testid="stHeader"],
        [data-testid="stHeader"],
        [data-testid="stAppHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="collapsedControl"],
        footer {
          display:none !important;
          height:0 !important;
          min-height:0 !important;
          visibility:hidden !important;
        }
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
          margin:0 !important;
          padding:0 !important;
          height:100dvh !important;
          overflow:hidden !important;
        }
        .stMain,
        .stMainBlockContainer,
        .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="block-container"] {
          margin:0 !important;
          padding:0 !important;
          max-width:100% !important;
        }
        section[data-testid="stMain"] {
          top:0 !important;
          padding-top:0 !important;
        }
        section[data-testid="stMain"] > div {
          padding-top:0 !important;
          margin-top:0 !important;
        }
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stMain"] > div {
          padding-top:0 !important;
          margin-top:0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_app_state() -> None:
    initialize_simulation_state()



def _sync_selected_stop_from_query() -> None:
    selected_from_query = st.query_params.get("selected_stop")
    if selected_from_query and selected_from_query in st.session_state.stops:
        st.session_state.user_stop = selected_from_query



def show_onboarding() -> None:
    apply_fullscreen_shell_styles()
    st.markdown(
        """
        <style>
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
          margin: 0 !important;
          padding: 0 !important;
          height: 100vh;
          overflow: hidden !important;
        }
        .stMainBlockContainer,
        .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"],
        [data-testid="block-container"] {
          max-width: 100% !important;
          padding: 0 !important;
          margin: 0 !important;
        }
        @keyframes gradientShift {
          0%   { background-position: 0% 50%; }
          50%  { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        .welcome-shell {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px 24px 96px;
          background: linear-gradient(135deg, #f8fbff 0%, #eef4ff 35%, #e8f0fe 65%, #f0f9ff 100%);
          background-size: 300% 300%;
          animation: gradientShift 10s ease infinite;
        }
        .welcome-card {
          width: min(1120px, 100%);
          background: rgba(255,255,255,0.92);
          border: 1px solid rgba(191,219,254,0.95);
          border-radius: 28px;
          box-shadow: 0 24px 60px rgba(37,99,235,0.10);
          padding: 26px 28px 22px;
        }
        .welcome-kicker {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 8px 14px;
          border-radius: 999px;
          background: #dbeafe;
          color: #1d4ed8;
          font-size: 0.88rem;
          font-weight: 700;
        }
        .welcome-title {
          margin-top: 14px;
          font-size: clamp(2.1rem, 3.5vw, 3.5rem);
          line-height: 1.02;
          letter-spacing: -0.04em;
          color: #0f172a;
          font-weight: 900;
        }
        .welcome-subtitle {
          margin-top: 10px;
          max-width: 760px;
          color: #334155;
          font-size: 1rem;
          line-height: 1.5;
        }
        .welcome-grid {
          margin-top: 18px;
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
        }
        .welcome-panel {
          border-radius: 22px;
          padding: 15px 15px 14px;
          min-height: 150px;
          transition: transform 0.22s ease, box-shadow 0.22s ease;
          cursor: default;
        }
        .welcome-panel:hover {
          transform: translateY(-4px);
          box-shadow: 0 14px 32px rgba(29,78,216,0.13);
        }
        .welcome-panel h3 {
          margin: 0 0 8px 0;
          color: #0f172a;
          font-size: 1rem;
          font-weight: 800;
          letter-spacing: -0.02em;
        }
        .welcome-panel ul {
          margin: 0;
          padding-left: 18px;
          color: #334155;
          line-height: 1.5;
          font-size: 0.92rem;
        }
        .welcome-panel li + li {
          margin-top: 4px;
        }
        .welcome-panel.map { background: #ecfdf5; }
        .welcome-panel.ai { background: #eff6ff; }
        .welcome-panel.profile { background: #fff7ed; }
        .welcome-footer {
          margin-top: 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 18px;
          padding-top: 14px;
          border-top: 1px solid #dbeafe;
        }
        .welcome-note {
          color: #475569;
          font-size: 0.92rem;
          line-height: 1.45;
          max-width: 700px;
        }
        .welcome-note strong {
          color: #0f172a;
        }
        div.stButton {
          position: fixed;
          left: 50%;
          bottom: 24px;
          transform: translateX(-50%);
          width: min(320px, calc(100vw - 32px));
          margin: 0;
          z-index: 10;
        }
        div.stButton > button[kind="primary"] {
          width: 100%;
          border-radius: 999px;
          padding: 0.85rem 1.2rem;
          font-weight: 800;
          font-size: 1rem;
          box-shadow: 0 14px 30px rgba(37,99,235,0.22);
        }
        @media (max-width: 900px) {
          html, body, .stApp {
            overflow: auto !important;
          }
          .welcome-shell {
            min-height: auto;
            padding: 18px;
          }
          .welcome-card {
            padding: 24px 20px 22px;
          }
          .welcome-grid {
            grid-template-columns: 1fr;
          }
          .welcome-footer {
            flex-direction: column;
            align-items: stretch;
          }
          div.stButton {
            position: static;
            transform: none;
            width: 100%;
            margin: 18px auto 0;
          }
        }
        </style>
        <div class="welcome-shell">
          <div class="welcome-card">
            <div class="welcome-kicker">🚌 BC Shuttle Tracker</div>
            <div class="welcome-title">Find the right shuttle faster.</div>
            <div class="welcome-subtitle">
              Live map predictions, location-aware suggestions, and an AI assistant all in one screen so riders can decide where to board and when to leave.
            </div>
            <div class="welcome-grid">
              <div class="welcome-panel map">
                <h3>Live Map</h3>
                <ul>
                  <li>Watch shuttles move around campus in real time.</li>
                  <li>Tap a stop to change your destination instantly.</li>
                  <li>Use route focus cards to simplify the map.</li>
                </ul>
              </div>
              <div class="welcome-panel ai">
                <h3>AI Assistant</h3>
                <ul>
                  <li>Ask which shuttle is best from your current stop.</li>
                  <li>Compare ETA, crowding, and risk in plain language.</li>
                  <li>Get suggestions that react to your selected stop.</li>
                </ul>
              </div>
              <div class="welcome-panel profile">
                <h3>Rider Profile</h3>
                <ul>
                  <li>Add your timing style and crowding preference.</li>
                  <li>Upload your class schedule for better advice.</li>
                  <li>Help the AI tailor suggestions to your habits.</li>
                </ul>
              </div>
            </div>
            <div class="welcome-footer">
              <div class="welcome-note">
                <strong>Everything important is meant to be visible immediately.</strong>
                Open the live map to start, then use the built-in guide for a short walkthrough of the interface.
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("🚀 Open Live Map", type="primary"):
        st.session_state.has_seen_onboarding = True
        st.rerun()


def build_map_payload(selected_stop: str) -> dict:
    destination_stop = st.session_state.get("destination_stop", "Conte Forum")
    if destination_stop not in st.session_state.stops:
        destination_stop = selected_stop
    routes = {}
    for route_name, route in st.session_state.route_definitions.items():
        ordered_stops = sorted(
            route["metrics"]["stop_progress"].items(),
            key=lambda item: item[1],
        )
        routes[route_name] = {
            "color": route["color"],
            "marker_color": route.get("marker_color", route["color"]),
            "path": route["path"],
            "stops": route["stops"],
            "segment_lengths": route["metrics"]["segment_lengths"],
            "cumulative": route["metrics"]["cumulative"],
            "total_length": route["metrics"]["total_length"],
            "stop_progress": route["metrics"]["stop_progress"],
            "ordered_stop_names": [name for name, _ in ordered_stops],
            "service_days": route["service_days"],
            "service_window": route["service_window"],
            "headway": route["headway"],
        }

    shuttles = []
    for shuttle_id, shuttle in st.session_state.shuttle_data.items():
        route_def = st.session_state.route_definitions[shuttle["route"]]
        shuttles.append(
            {
                "id": shuttle_id,
                "label": shuttle["label"],
                "route": shuttle["route"],
                "progress": shuttle["progress"],
                "speed_mph": shuttle["speed_mph"],
                "capacity": shuttle["capacity"],
                "capacity_pct": shuttle["capacity_pct"],
                "current_stop": shuttle["current_stop"],
                "next_stop": shuttle["next_stop"],
                "dwell_seconds_remaining": shuttle.get("dwell_seconds_remaining", 0.0),
                "delay_minutes": shuttle.get("delay_minutes", 0),
                "is_express": shuttle.get("is_express", False),
                # Embed marker color directly so JS never needs a route lookup
                "marker_color": route_def.get("marker_color", route_def["color"]),
            }
        )

    return {
        "selected_stop": selected_stop,
        "destination_stop": destination_stop,
        "selected_coords": st.session_state.stops[selected_stop],
        "destination_coords": st.session_state.stops[destination_stop],
        "selected_route_filter": st.session_state.selected_route_filter,
        "routes": routes,
        "shuttles": shuttles,
    }


def _stop_option_label(stop_name: str) -> str:
    routes = st.session_state.stops[stop_name]["routes"]
    if len(routes) == 1:
        return f"{display_stop_name(stop_name)} — {routes[0]}"
    return f"{display_stop_name(stop_name)} — {', '.join(routes)}"


def _capacity_label(capacity_pct: int) -> str:
    if capacity_pct >= 85:
        return "Very Crowded"
    if capacity_pct >= 60:
        return "Moderate"
    return "Light"


def _capacity_visual_html(capacity_pct: int) -> str:
    highlighted = max(1, min(5, round(capacity_pct / 20)))
    filled = "#1d4ed8"
    faded = "#c7d2fe"
    people = []
    for index in range(5):
        color = filled if index < highlighted else faded
        x = 6 + index * 22
        people.append(
            f"""
            <g transform="translate({x}, 2)">
              <circle cx="8" cy="6" r="5" fill="{color}"></circle>
              <rect x="5" y="12" width="6" height="13" rx="3" fill="{color}"></rect>
              <rect x="0" y="13" width="4" height="12" rx="2" fill="{color}"></rect>
              <rect x="12" y="13" width="4" height="12" rx="2" fill="{color}"></rect>
              <rect x="4" y="24" width="4" height="12" rx="2" fill="{color}"></rect>
              <rect x="8" y="24" width="4" height="12" rx="2" fill="{color}"></rect>
            </g>
            """
        )

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 125 40" width="125" height="40" aria-hidden="true">{"".join(people)}</svg>'
    svg_src = f"data:image/svg+xml;utf8,{quote(svg)}"

    return (
        f'<div style="display:flex;align-items:center;gap:1rem;flex-wrap:wrap;margin-top:0.9rem;">'
        f'<div style="display:flex;align-items:flex-end;">'
        f'<img src="{svg_src}" alt="{_capacity_label(capacity_pct)} crowd graphic" class="capacity-anim" style="width:125px;height:40px;display:block;" />'
        f"</div>"
        f'<div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:{filled};">{_capacity_label(capacity_pct)}</div>'
        f'<div style="color:#6b7280;">Crowd level predicted from current vehicle data</div>'
        f"</div>"
        f"</div>"
    )


def render_arrival_schedule(selected_stop: str) -> None:
    eta = build_eta_prediction(selected_stop)
    arrivals = get_stop_arrivals(selected_stop)
    display_selected_stop = display_stop_name(selected_stop)

    st.markdown("## Shuttle Schedule")
    st.caption("AI-predicted arrivals for your selected stop, starting with the next bus and followed by upcoming service on each route.")

    if not arrivals:
        st.info("No predicted shuttle arrivals are available for this stop yet.")
        return

    best = eta["best_match"]
    if best:
        delay = best.get("delay_minutes", 0)
        if delay > 0:
            delay_badge = f'<span style="background:#fef2f2;color:#b91c1c;font-weight:700;padding:2px 10px;border-radius:999px;font-size:0.85rem;border:1px solid #fecaca;">⚠️ +{delay} min delay</span>'
        elif delay < 0:
            delay_badge = f'<span style="background:#f0fdf4;color:#15803d;font-weight:700;padding:2px 10px;border-radius:999px;font-size:0.85rem;border:1px solid #bbf7d0;">⏰ Running {abs(delay)} min early</span>'
        else:
            delay_badge = '<span style="background:#f0fdf4;color:#15803d;font-weight:700;padding:2px 10px;border-radius:999px;font-size:0.85rem;border:1px solid #bbf7d0;">✅ On time</span>'
        express_badge = '<span style="background:#f5f3ff;color:#6d28d9;font-weight:700;padding:2px 10px;border-radius:999px;font-size:0.85rem;border:1px solid #ddd6fe;">🚀 Express</span>' if best.get("is_express") else ""
        st.markdown("### Next Shuttle")
        st.markdown(
            f"""
            <div class="status-card">
                <div style="font-size:0.95rem;color:#6b7280;">Predicted Arrival</div>
                <div style="font-size:2.8rem;font-weight:700;line-height:1;margin:0.5rem 0 0.5rem 0;">{eta['min']}-{eta['max']} min</div>
                <div style="margin-bottom:0.6rem;display:flex;gap:0.4rem;flex-wrap:wrap;">{delay_badge}{express_badge}</div>
                <div style="font-weight:700;">{best['label']}</div>
                <div>Route: <span style="color:{best['route_color']};font-weight:700;">{best['route']}</span></div>
                <div>{'Currently boarding at' if '(boarding)' in best['next_stop'] else 'Heading to'} {display_stop_name(best['next_stop'])}</div>
                <div>{best['capacity']} • {best['capacity_pct']}% occupied</div>
                {_capacity_visual_html(best['capacity_pct'])}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Following Buses")
    for arrival in arrivals:
        status_text = (
            "Boarding now"
            if "(boarding)" in arrival["next_stop"]
            else f"Next stop: {display_stop_name(arrival['next_stop'])}"
        )
        delay = arrival.get("delay_minutes", 0)
        if delay > 0:
            arrival_delay_badge = f'<span style="background:#fef2f2;color:#b91c1c;font-weight:700;font-size:0.8rem;padding:1px 8px;border-radius:999px;border:1px solid #fecaca;">⚠️ +{delay} min delay</span>'
        elif delay < 0:
            arrival_delay_badge = f'<span style="background:#f0fdf4;color:#15803d;font-weight:700;font-size:0.8rem;padding:1px 8px;border-radius:999px;border:1px solid #bbf7d0;">⏰ {abs(delay)} min early</span>'
        else:
            arrival_delay_badge = ""
        arrival_express_badge = '<span style="background:#f5f3ff;color:#6d28d9;font-weight:700;font-size:0.8rem;padding:1px 8px;border-radius:999px;border:1px solid #ddd6fe;">🚀 Express</span>' if arrival.get("is_express") else ""
        badges_html = " &nbsp;".join(b for b in [arrival_delay_badge, arrival_express_badge] if b)
        badges_div = f'<div style="margin-top:0.3rem;">{badges_html}</div>' if badges_html else ""
        card_html = (
            '<div class="status-card">'
            '<div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">'
            '<div>'
            f'<div style="font-weight:700;font-size:1.05rem;">{arrival["label"]}</div>'
            f'<div style="color:{arrival["route_color"]};font-weight:700;margin-top:0.2rem;">{arrival["route"]}</div>'
            f'<div style="color:#4b5563;margin-top:0.45rem;">{status_text}</div>'
            f'<div style="color:#4b5563;">Capacity: {arrival["capacity"]} ({arrival["capacity_pct"]}%)</div>'
        )
        card_html += badges_div + _capacity_visual_html(arrival["capacity_pct"])
        card_html += (
            '</div>'
            '<div style="text-align:right;">'
            f'<div style="font-size:1.8rem;font-weight:700;line-height:1;">{arrival["eta_minutes"]} min</div>'
            f'<div style="color:#6b7280;margin-top:0.35rem;">to {display_selected_stop}</div>'
            '</div>'
            '</div>'
            '</div>'
        )
        st.markdown(card_html, unsafe_allow_html=True)


def render_live_dashboard(selected_stop: str) -> None:
    payload = json.dumps(build_map_payload(selected_stop))
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      <style>
        html, body {{
          margin: 0;
          padding: 0;
          width: 100%;
          font-family: sans-serif;
          background: white;
        }}
        .live-shell {{
          display: grid;
          grid-template-columns: minmax(0, 2.1fr) minmax(320px, 1fr);
          gap: 24px;
          align-items: start;
        }}
        #map {{
          width: 100%;
          height: 560px;
          border-radius: 16px;
          overflow: hidden;
          border: 1px solid #e5e7eb;
        }}
        .panel {{
          padding: 4px 0;
        }}
        .panel h2 {{
          margin: 0 0 8px 0;
          font-size: 20px;
          color: #1f2937;
        }}
        .panel .subtle {{
          color: #6b7280;
          font-size: 14px;
          line-height: 1.5;
          margin-bottom: 18px;
        }}
        .card {{
          background: #f4f6fb;
          border-radius: 14px;
          padding: 14px 16px;
          margin-bottom: 14px;
          border-left: 6px solid #cbd5e1;
        }}
        .card .title {{
          font-weight: 700;
          font-size: 15px;
          color: #111827;
        }}
        .card .body {{
          color: #4b5563;
          margin-top: 6px;
          line-height: 1.45;
        }}
        .card .status {{
          font-weight: 700;
          font-size: 14px;
        }}
        .route-chip {{
          display: inline-block;
          color: white;
          border-radius: 999px;
          padding: 4px 10px;
          font-size: 12px;
          font-weight: 700;
          margin-right: 8px;
          margin-top: 8px;
        }}
        .route-filter {{
          width: 100%;
          text-align: left;
          border: 0;
          background: transparent;
          border-radius: 12px;
          padding: 10px 12px;
          cursor: pointer;
          transition: background 0.18s ease, transform 0.18s ease;
        }}
        .route-filter:hover {{
          background: rgba(15, 23, 42, 0.04);
        }}
        .route-filter.active {{
          background: rgba(15, 23, 42, 0.06);
          transform: translateX(2px);
        }}
        .bus-marker {{
          width: 34px;
          height: 34px;
          border-radius: 50%;
          border: 3px solid white;
          box-shadow: 0 3px 8px rgba(0,0,0,0.25);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 18px;
          color: white;
        }}
        .bus-marker.boarding {{
          transform: scale(1.08);
          box-shadow: 0 0 0 6px rgba(255,255,255,0.35), 0 3px 8px rgba(0,0,0,0.25);
        }}
        .boarding-pill {{
          background: rgba(17, 24, 39, 0.92);
          color: white;
          border-radius: 999px;
          padding: 4px 10px;
          font-size: 12px;
          font-weight: 700;
          white-space: nowrap;
          box-shadow: 0 3px 8px rgba(0,0,0,0.2);
        }}
        .legend {{
          background: white;
          padding: 10px 12px;
          border-radius: 10px;
          box-shadow: 0 4px 14px rgba(0,0,0,0.15);
          line-height: 1.4;
        }}
        .legend-dot {{
          display: inline-block;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          margin-right: 8px;
        }}
      </style>
    </head>
    <body>
      <div class="live-shell">
        <div id="map"></div>
        <div class="panel">
          <h2>Your Selected Stop</h2>
          <div class="card">
            <div class="title" id="stop-title"></div>
            <div class="body" id="service-meta"></div>
          </div>
          <h2>Routes</h2>
          <div class="card" id="route-info"></div>
        </div>
      </div>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <script>
        const payload = {payload};
        const displayStopName = (name) => name.replace(/^[A-Z]\\.\\s*/, '');
        const stopTitle = document.getElementById('stop-title');
        const serviceMeta = document.getElementById('service-meta');
        const routeInfo = document.getElementById('route-info');
        const map = L.map('map', {{ zoomControl: false, attributionControl: true }}).setView(
          [payload.selected_coords.lat, payload.selected_coords.lon],
          14
        );
        let activeRoute = payload.selected_route_filter !== 'All routes' ? payload.selected_route_filter : null;
        const routeLayers = {{}};

        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap &copy; CARTO'
        }}).addTo(map);

        const routeEntries = Object.entries(payload.routes);
        routeEntries.forEach(([routeName, route]) => {{
          const polyline = L.polyline(route.path, {{
            color: route.color,
            weight: 6,
            opacity: 0.9
          }}).addTo(map).bindTooltip(routeName);

          const stopMarkers = [];
          route.stops.forEach((stop) => {{
            const isSelected = stop.name === payload.selected_stop;
            const marker = L.circleMarker([stop.lat, stop.lon], {{
              radius: isSelected ? 9 : 6,
              color: 'white',
              weight: 2,
              fillColor: isSelected ? '#111827' : route.color,
              fillOpacity: 1
            }}).addTo(map).bindPopup(`<b>${{displayStopName(stop.name)}}</b><br>${{routeName}}`);
            stopMarkers.push(marker);
          }});

          routeLayers[routeName] = {{
            polyline,
            stopMarkers,
            bounds: L.latLngBounds(route.path),
          }};
        }});

        const legend = L.control({{ position: 'bottomleft' }});
        legend.onAdd = function() {{
          const div = L.DomUtil.create('div', 'legend');
          div.innerHTML = '<b>Routes</b><br>' + routeEntries.map(([name, route]) =>
            `<div style="margin-top:6px;"><span class="legend-dot" style="background:${{route.color}};"></span>${{name}}</div>`
          ).join('');
          return div;
        }};
        legend.addTo(map);

        function nearestStopProgress(route, name) {{
          return route.stop_progress[name];
        }}

        function nextStopName(route, progress, inclusive = true) {{
          for (const name of route.ordered_stop_names) {{
            if (inclusive) {{
              if (route.stop_progress[name] >= progress - 1e-6) return name;
            }} else if (route.stop_progress[name] > progress + 1e-6) {{
              return name;
            }}
          }}
          return route.ordered_stop_names[0];
        }}

        function crossedStop(currentProgress, nextProgress, stopProgress) {{
          if (currentProgress <= nextProgress) {{
            return stopProgress > currentProgress + 1e-6 && stopProgress <= nextProgress + 1e-6;
          }}
          return stopProgress > currentProgress + 1e-6 || stopProgress <= nextProgress + 1e-6;
        }}

        function positionAtProgress(route, progress) {{
          const target = ((progress % 1) + 1) % 1 * route.total_length;
          for (let i = 0; i < route.segment_lengths.length; i += 1) {{
            const startDistance = route.cumulative[i];
            const endDistance = route.cumulative[i + 1];
            const segmentLength = route.segment_lengths[i];
            if (target <= endDistance || i === route.segment_lengths.length - 1) {{
              const ratio = segmentLength === 0 ? 0 : (target - startDistance) / segmentLength;
              const start = route.path[i];
              const end = route.path[i + 1];
              return [
                start[0] + (end[0] - start[0]) * ratio,
                start[1] + (end[1] - start[1]) * ratio
              ];
            }}
          }}
          return route.path[route.path.length - 1];
        }}

        function stopDwellSeconds(name) {{
          if (name.startsWith('A.') || name.startsWith('G.') || name.startsWith('M.')) return 35;
          if (name.startsWith('D.') || name.startsWith('J.')) return 25;
          return 18;
        }}

        const shuttles = payload.shuttles.map((shuttle) => {{
          const route = payload.routes[shuttle.route];
          const marker = L.marker(positionAtProgress(route, shuttle.progress), {{
            icon: L.divIcon({{
              className: '',
              html: `<div class="bus-marker ${{shuttle.route==='Newton Campus Express'?'bus-color-newton':'bus-color-comm'}}">🚌</div>`,
              iconSize: [34, 34],
              iconAnchor: [17, 17]
            }})
          }}).addTo(map);
          const boardingBadge = L.marker(positionAtProgress(route, shuttle.progress), {{
            icon: L.divIcon({{
              className: '',
              html: '',
              iconSize: [90, 24],
              iconAnchor: [45, 34]
            }})
          }}).addTo(map);

          marker.bindTooltip(`${{shuttle.label}} • ${{shuttle.route}}`);
          return {{
            ...shuttle,
            marker,
            boardingBadge,
            lastFrame: performance.now()
          }};
        }});

        function applyRouteFilter() {{
          routeEntries.forEach(([routeName, route]) => {{
            const isActive = !activeRoute || activeRoute === routeName;
            const layers = routeLayers[routeName];
            layers.polyline.setStyle({{
              opacity: isActive ? 0.95 : 0,
              weight: activeRoute === routeName ? 8 : 6,
            }});
            if (activeRoute === routeName) {{
              layers.polyline.bringToFront();
            }}
            layers.stopMarkers.forEach((marker) => {{
              marker.setStyle({{
                opacity: isActive ? 1 : 0,
                fillOpacity: isActive ? 1 : 0,
              }});
            }});
          }});

          shuttles.forEach((shuttle) => {{
            const isActive = !activeRoute || activeRoute === shuttle.route;
            shuttle.marker.setOpacity(isActive ? 1 : 0);
            shuttle.boardingBadge.setOpacity(isActive && shuttle.dwell_seconds_remaining > 0 ? 1 : 0);
          }});
        }}

        function updateMarkerVisual(shuttle) {{
          const route = payload.routes[shuttle.route];
          const boarding = shuttle.dwell_seconds_remaining > 0;
          shuttle.marker.setIcon(L.divIcon({{
            className: '',
            html: `<div class="bus-marker ${{shuttle.route==='Newton Campus Express'?'bus-color-newton':'bus-color-comm'}} ${{boarding ? 'boarding' : ''}}">🚌</div>`,
            iconSize: [34, 34],
            iconAnchor: [17, 17]
          }}));

          if (boarding) {{
            shuttle.boardingBadge.setIcon(L.divIcon({{
              className: '',
              html: `<div class="boarding-pill">Boarding</div>`,
              iconSize: [90, 24],
              iconAnchor: [45, 34]
            }}));
            shuttle.boardingBadge.setOpacity(!activeRoute || activeRoute === shuttle.route ? 1 : 0);
          }} else {{
            shuttle.boardingBadge.setOpacity(0);
          }}
        }}

        function refreshPopup(shuttle) {{
          const delayText = shuttle.delay_minutes > 0
            ? `<br><span style="color:#dc2626;font-weight:700;">⚠️ Running ${{shuttle.delay_minutes}} min late</span>`
            : shuttle.delay_minutes < 0
              ? `<br><span style="color:#16a34a;font-weight:700;">⏰ Running ${{Math.abs(shuttle.delay_minutes)}} min early</span>`
              : '';
          const expressText = shuttle.is_express
            ? `<br><span style="color:#7c3aed;font-weight:700;">🚀 Express</span>`
            : '';
          shuttle.marker.bindPopup(
            `<b>${{shuttle.label}}</b><br>` +
            `Route: ${{shuttle.route}}<br>` +
            `Current stop: ${{displayStopName(shuttle.current_stop)}}<br>` +
            `Next stop: ${{displayStopName(shuttle.next_stop)}}<br>` +
            `Status: ${{shuttle.dwell_seconds_remaining > 0 ? 'Boarding passengers' : 'In service'}}<br>` +
            `Capacity: ${{shuttle.capacity}} (${{shuttle.capacity_pct}}%)` +
            delayText + expressText
          );
        }}

        function updateShuttleState(shuttle, deltaSeconds) {{
          const route = payload.routes[shuttle.route];
          if (shuttle.dwell_seconds_remaining > 0) {{
            shuttle.dwell_seconds_remaining = Math.max(0, shuttle.dwell_seconds_remaining - deltaSeconds);
          }} else {{
            const distanceFraction = (shuttle.speed_mph * deltaSeconds / 3600) / route.total_length;
            const nextStop = nextStopName(route, shuttle.progress, false);
            const nextStopProgress = nearestStopProgress(route, nextStop);
            const proposedProgress = (shuttle.progress + distanceFraction) % 1;
            if (crossedStop(shuttle.progress, proposedProgress, nextStopProgress)) {{
              shuttle.progress = nextStopProgress;
              shuttle.current_stop = nextStop;
              shuttle.next_stop = `${{nextStop}} (boarding)`;
              shuttle.dwell_seconds_remaining = stopDwellSeconds(nextStop);
            }} else {{
              shuttle.progress = proposedProgress;
              shuttle.next_stop = nextStopName(route, shuttle.progress, false);
            }}
          }}

          const ordered = route.ordered_stop_names;
          let nextName = nextStopName(route, shuttle.progress, shuttle.dwell_seconds_remaining > 0);
          const nextIndex = ordered.indexOf(nextName);
          const prevIndex = nextIndex > 0 ? nextIndex - 1 : ordered.length - 1;
          shuttle.current_stop = ordered[prevIndex];
          if (shuttle.dwell_seconds_remaining > 0) {{
            shuttle.current_stop = nextName;
            shuttle.next_stop = `${{nextName}} (boarding)`;
          }} else {{
            shuttle.next_stop = nextName;
          }}
        }}

        function animate(now) {{
          shuttles.forEach((shuttle) => {{
            const deltaSeconds = Math.min(1.5, (now - shuttle.lastFrame) / 1000);
            shuttle.lastFrame = now;
            updateShuttleState(shuttle, deltaSeconds);
            const position = positionAtProgress(payload.routes[shuttle.route], shuttle.progress);
            shuttle.marker.setLatLng(position);
            shuttle.boardingBadge.setLatLng(position);
            updateMarkerVisual(shuttle);
            refreshPopup(shuttle);
          }});
          requestAnimationFrame(animate);
        }}

        function arrivalsForSelectedStop() {{
          const stopName = payload.selected_stop;
          return shuttles
            .filter((shuttle) => payload.routes[shuttle.route].stop_progress[stopName] !== undefined)
            .map((shuttle) => {{
              const route = payload.routes[shuttle.route];
              const stopProgress = route.stop_progress[stopName];
              const progressDelta = (stopProgress - shuttle.progress + 1) % 1;
              const remainingMiles = progressDelta * route.total_length;
              const etaMinutes = Math.max(1, Math.round((remainingMiles / Math.max(shuttle.speed_mph, 1)) * 60));
              const adjustedEta = Math.max(1, etaMinutes + (shuttle.delay_minutes || 0));
              return {{
                shuttle,
                etaMinutes: adjustedEta
              }};
            }})
            .sort((a, b) => a.etaMinutes - b.etaMinutes);
        }}

        function renderSidePanel() {{
          const displayRouteName = activeRoute || Object.keys(payload.routes)[0];
          const primaryRoute = payload.routes[displayRouteName];
          stopTitle.textContent = displayStopName(payload.selected_stop);
          serviceMeta.textContent = `${{primaryRoute.service_days}} service: ${{primaryRoute.service_window}} (${{primaryRoute.headway}})`;
          const routeHtml = Object.entries(payload.routes).map(([routeName, route]) => {{
            const isActive = activeRoute === routeName;
            return `<div style="margin-bottom:12px;">
              <button class="route-filter ${{isActive ? 'active' : ''}}" data-route="${{routeName}}">
                <div class="route-chip" style="background:${{route.color}};">${{routeName}}</div>
                <div class="body">Stops on route: ${{route.ordered_stop_names.length}}</div>
                <div class="body">${{route.service_days}} • ${{route.headway}}</div>
              </button>
            </div>`;
          }}).join('');
          routeInfo.innerHTML = routeHtml;
        }}

        routeInfo.addEventListener('click', (event) => {{
          const button = event.target.closest('.route-filter');
          if (!button) return;
          const routeName = button.dataset.route;
          activeRoute = activeRoute === routeName ? null : routeName;
          if (activeRoute) {{
            map.fitBounds(routeLayers[activeRoute].bounds, {{ padding: [24, 24] }});
          }} else {{
            map.setView([payload.selected_coords.lat, payload.selected_coords.lon], 14);
          }}
          renderSidePanel();
          applyRouteFilter();
        }});

        shuttles.forEach((shuttle) => {{
          updateMarkerVisual(shuttle);
          refreshPopup(shuttle);
        }});
        renderSidePanel();
        applyRouteFilter();
        requestAnimationFrame(animate);
      </script>
    </body>
    </html>
    """
    components.html(html, height=640)


_AI_SYSTEM_PROMPT = (
    "You are the BC Shuttle Tracker AI assistant for Boston College. "
    "Help students and staff with real-time shuttle information. "
    "You have access to live shuttle data injected below. Always use that data when answering. "
    "Capabilities: answer questions about next arrivals, ETAs, capacity, and delays; "
    "accept delay reports from users and update the system; summarize the shuttle schedule. "
    "When the user has selected both an origin stop and destination stop, plan around that trip. "
    "Do not silently change the boarding stop. If recommending a bus from a nearby alternate stop, "
    "say that it requires walking to that stop first and include combined walk-plus-wait timing. "
    "For questions about the next bus from the selected stop, use selected-origin arrivals by default. "
    "When a structured class schedule JSON section is present, use it for class-aware suggestions "
    "and next-class planning instead of relying only on the raw schedule transcription. "
    "Use the provided current datetime in America/New_York for all schedule and 'today' reasoning. "
    "If the context says the destination is not set because it matches the origin, do not recommend "
    "boarding a shuttle for a trip. Ask the rider to choose a different destination first. "
    "Shuttle IDs: comm-1=Comm Ave 1, comm-2=Comm Ave 2, newton-1=Newton Express 1, newton-2=Newton Express 2. "
    "Decide the response format yourself. For questions asking which shuttle to take, what the rider should "
    "take right now, whether they should take a specific shuttle, or comparing fastest/most comfortable options, "
    "always use the structured JSON schema so the UI can render a formatted recommendation card. "
    "Use plain text only when the user asks a follow-up explanation, "
    "asks about prediction confidence or how certain you are, asks how you reasoned, asks a general custom question, "
    "or does not need an actionable shuttle card. Use structured JSON only when the answer should create "
    "a rider action card, such as a next-arrival check, route recommendation, comparison, schedule or "
    "capacity decision, what-if trip plan, or explicit delay update. If you use plain text, do not include "
    "JSON, markdown headings, or schema labels. "
    "When a structured response is useful, respond with one valid JSON object and no extra text. Use this schema: "
    "{"
    "\"summary\":\"2 short sentences\","
    "\"recommended_option\":{\"action\":\"short recommendation\",\"route\":\"route or null\",\"bus\":\"bus label or null\",\"eta_minutes\":0,\"reasoning\":[\"reason\"]},"
    "\"confidence\":{\"score\":0,\"label\":\"high|medium|low\",\"explanation\":\"plain-language explanation of how certain this prediction is\"},"
    "\"alternatives\":[{\"action\":\"backup option\",\"tradeoff\":\"brief tradeoff\"}],"
    "\"what_if_options\":[{\"scenario\":\"what if case\",\"outcome\":\"expected outcome\"}],"
    "\"proactive_alert\":\"short heads-up or null\","
    "\"follow_up_question\":\"optional next question or null\","
    "\"delay_update\":{\"shuttle_id\":\"comm-1\",\"delay_minutes\":0},"
    "\"capacity_update\":{\"shuttle_id\":\"comm-1\",\"capacity_pct\":50}"
    "}. "
    "For confidence.score, use a real 0-100 confidence score. Do not use 0 as a placeholder "
    "when label is high, medium, or low. "
    "Use JSON null for proactive_alert, follow_up_question, delay_update, and capacity_update when not applicable; never write phrases like 'none at this time'. "
    "Only set delay_update when the user explicitly reports or clears a delay; otherwise set it to null. "
    "Only set capacity_update when the user explicitly reports a capacity or crowding level for a shuttle; otherwise set it to null. "
    "Always return the full JSON schema — never return a bare partial object like {shuttle_id, delay_minutes} on its own. Always include at least a summary field. "
    "When the user reports a delay or early arrival for the next shuttle, set delay_update with the shuttle_id of that shuttle — this automatically updates ETAs for all stops on that route. "
    "The confidence score means how certain the prediction is — higher is more reliable, 90% means 90% certain. "
    "Labels: High >=80%, Medium >=60%, Low <60%. "
    "Factors that affect it: on-time status (base 88% on time, 68% if delayed), recent rider feedback, "
    "how far away the shuttle is (farther = less certain), size of reported delay, and whether it is an express route. "
    "Capacity labels: Crowded >=85% full, Moderate >=60% full, Light <60% full. "
    "Explain these when the user asks how confidence or capacity is calculated. "
    "For capacity questions, use plain text only — answer with the shuttle label, current capacity percentage, and crowding label (Light/Moderate/Very crowded). Do not use a structured JSON card for capacity-only questions. "
    "Always use the human-readable shuttle label (e.g. 'Comm Ave 1') in the 'bus' field — never use the internal shuttle ID (e.g. 'comm-1'). "
    "Be friendly, concise, explain the why, and include confidence for structured recommendations."
)


def _get_secret_value(*names: str) -> str:
    for name in names:
        try:
            value = st.secrets.get(name, "")
        except StreamlitSecretNotFoundError:
            value = ""
        if value:
            return str(value)
        env_value = os.getenv(name, "")
        if env_value:
            return env_value
    return ""


def _get_supabase_config() -> dict[str, str | bool]:
    url = _get_secret_value("SUPABASE_URL", "supabase_url")
    anon_key = _get_secret_value(
        "SUPABASE_ANON_KEY",
        "SUPABASE_KEY",
        "SUPABASE_PUBLIC_KEY",
        "supabase_anon_key",
        "supabase_key",
    )
    return {
        "url": url.rstrip("/"),
        "anonKey": anon_key,
        "enabled": bool(url and anon_key),
    }


def render_split_app(selected_stop: str, show_ai_panel: bool = True) -> None:  # noqa: PLR0915 (long but intentional)
    TOTAL_H = 900   # iframe needs real render space; CSS below removes its wrapper from page flow
    payload = build_map_payload(selected_stop)
    ensure_ai_state()
    # Inject data as JSON into a separate <script> block so the HTML template
    # stays a plain (non-f-string) string and can never be corrupted by the data.
    payload_json      = json.dumps(payload)
    system_prompt_json = json.dumps(_AI_SYSTEM_PROMPT)
    init_time         = json.dumps(st.session_state.simulation_last_updated.strftime("%I:%M:%S %p"))
    from ai_assistant import get_configured_api_key  # noqa: PLC0415
    _resolved_api_key = get_configured_api_key()
    ai_server_configured = json.dumps(bool(_resolved_api_key))
    ai_api_key_json = json.dumps(_resolved_api_key)
    show_ai_panel_json = json.dumps(show_ai_panel)
    ai_chat_history_json = json.dumps(st.session_state.ai_chat_history)
    embedded_ai_error_json = json.dumps(st.session_state.get("embedded_ai_error", ""))
    supabase_config_json = json.dumps(_get_supabase_config())
    destination_stop = payload["destination_stop"]
    stop_options = "".join(
        '<option value="{v}"{sel}>{v}</option>'.format(
            v=name,
            sel=" selected" if name == selected_stop else "",
        )
        for name in sorted(st.session_state.stops.keys())
    )
    destination_options = "".join(
        '<option value="{v}"{sel}>{v}</option>'.format(
            v=name,
            sel=" selected" if name == destination_stop else "",
        )
        for name in sorted(st.session_state.stops.keys())
    )

    stop_cap_delta_json = json.dumps(STOP_CAPACITY_DELTA)
    # Data-only f-string — just numbers and pre-validated JSON blobs
    data_script = (
        f"<script>"
        f"var TOTAL_H={TOTAL_H};"
        f"var mapPayload={payload_json};"
        f"var STOP_CAP_DELTA={stop_cap_delta_json};"
        f"var SYSTEM_PROMPT={system_prompt_json};"
        f"var INIT_TIME={init_time};"
        f"var AI_SERVER_CONFIGURED={ai_server_configured};"
        f"var AI_API_KEY={ai_api_key_json};"
        f"var SHOW_AI_PANEL={show_ai_panel_json};"
        f"var AI_CHAT_HISTORY={ai_chat_history_json};"
        f"var EMBEDDED_AI_ERROR={embedded_ai_error_json};"
        f"var SUPABASE_CONFIG={supabase_config_json};"
        f"</script>"
    )

    # HTML template — raw string so JS regex backslashes are safe.
    html_template = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  * {box-sizing:border-box;margin:0;padding:0;}
  html,body {height:100%;overflow:hidden;background:#0f172a;color:#f1f5f9;
    font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}
  #app {display:flex;width:100%;overflow:hidden;}

  /* AI panel */
  #ai-panel {width:420px;min-width:260px;max-width:70%;position:relative;
    display:flex;flex-direction:column;background:#1e293b;border-right:1px solid #334155;overflow:hidden;}
  #ai-header {padding:12px 14px 10px;border-bottom:1px solid #334155;flex-shrink:0;
    background:linear-gradient(180deg,#1e3a5f 0%,#1e293b 100%);}
  #ai-title  {font-size:18px;font-weight:700;color:#f1f5f9;margin-bottom:8px;}
  #key-row   {display:flex;gap:6px;margin-bottom:7px;}
  #api-key-inp {flex:1;background:#0f172a;border:1px solid #334155;color:#f1f5f9;
    padding:7px 10px;border-radius:8px;font-size:12px;outline:none;}
  #api-key-inp::placeholder {color:#475569;}
  #api-key-inp:focus {border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.18);}
  #server-key-note {flex:1;font-size:11px;color:#4ade80;padding:7px 10px;border-radius:8px;
    background:#052e16;border:1px solid #166534;}
  #clear-btn {background:#374151;color:#9ca3af;border:none;padding:6px 10px;
    border-radius:6px;cursor:pointer;font-size:13px;flex-shrink:0;}
  #clear-btn:hover {background:#4b5563;color:#f1f5f9;}
  .stop-row  {display:flex;align-items:center;gap:6px;margin-top:6px;}
  .stop-lbl  {font-size:11px;color:#64748b;white-space:nowrap;width:74px;}
  #stop-sel, #dest-sel  {flex:1;min-width:0;background:#0f172a;border:1px solid #334155;color:#f1f5f9;
    padding:4px 8px;border-radius:6px;font-size:12px;outline:none;}
  #chat-box  {flex:1;min-height:0;overflow-y:auto;padding:10px 10px 286px;display:flex;flex-direction:column;gap:8px;scroll-behavior:smooth;}
  #chat-box::-webkit-scrollbar {width:4px;}
  #chat-box::-webkit-scrollbar-thumb {background:#334155;border-radius:2px;}
  .msg-user  {align-self:flex-end;background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff;padding:9px 13px;
    border-radius:16px 16px 3px 16px;max-width:88%;font-size:13px;line-height:1.5;word-wrap:break-word;
    box-shadow:0 2px 10px rgba(29,78,216,.35);}
  .msg-ai    {align-self:flex-start;background:#1e3a5f;color:#e2e8f0;padding:9px 13px;
    border-radius:16px 16px 16px 3px;max-width:88%;font-size:13px;line-height:1.5;word-wrap:break-word;
    box-shadow:0 2px 8px rgba(0,0,0,.22);}
  .msg-err   {align-self:center;background:#7f1d1d;color:#fca5a5;padding:6px 10px;
    border-radius:8px;font-size:12px;max-width:90%;}
  .ai-structured {display:flex;flex-direction:column;gap:9px;}
  .ai-section {border-top:1px solid rgba(148,163,184,.2);padding-top:8px;}
  .ai-section:first-child {border-top:none;padding-top:0;}
  .ai-section-title {font-size:10px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#93c5fd;margin-bottom:4px;}
  .ai-section-main {font-weight:800;color:#f8fafc;}
  .ai-section-detail {color:#cbd5e1;font-size:12px;margin-top:3px;}
  .ai-list {margin:5px 0 0 15px;color:#dbeafe;}
  .ai-list li {margin-top:3px;}
  .ai-pill-row {display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;}
  .ai-pill {display:inline-flex;align-items:center;padding:4px 8px;border-radius:999px;background:#0f172a;border:1px solid #334155;color:#bfdbfe;font-size:11px;font-weight:800;}
  .ai-alert {background:#422006;border:1px solid #f59e0b;color:#fde68a;border-radius:10px;padding:8px 10px;font-size:12px;}
  #ai-heads-up {display:none;}
  #suggestions {position:absolute;left:10px;right:10px;bottom:62px;z-index:20;padding:12px;
    border:1px solid rgba(96,165,250,.35);border-radius:16px;background:rgba(15,23,42,.84);
    box-shadow:0 14px 34px rgba(15,23,42,.28),inset 0 1px 0 rgba(255,255,255,.08);
    backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);max-height:220px;overflow-y:auto;}
  #suggestions:empty {display:none;}
  #suggestions::-webkit-scrollbar {width:4px;}
  #suggestions::-webkit-scrollbar-thumb {background:rgba(147,197,253,.45);border-radius:999px;}
  .suggest-label {font-size:10px;font-weight:900;color:#93c5fd;margin-bottom:8px;letter-spacing:.08em;text-transform:uppercase;}
  .suggest-grid {display:flex;flex-direction:column;gap:8px;}
  .suggest-chip {width:100%;border:1px solid rgba(147,197,253,.45);text-align:left;
    background:linear-gradient(180deg,rgba(30,64,175,.28),rgba(15,23,42,.92));color:#e0f2fe;
    padding:10px 12px;border-radius:12px;font-size:12px;line-height:1.32;cursor:pointer;
    box-shadow:0 6px 18px rgba(15,23,42,.2);
    transition:background .15s ease,transform .15s ease,color .15s ease,box-shadow .15s ease,border-color .15s ease;}
  .suggest-chip:hover {background:#2563eb;color:#fff;transform:translateX(3px);border-color:#93c5fd;box-shadow:0 8px 22px rgba(37,99,235,.35);}
  .delay-ok  {display:inline-block;margin-top:5px;padding:2px 8px;border-radius:999px;
    font-size:11px;font-weight:700;background:#d1fae5;color:#065f46;}
  .delay-warn{display:inline-block;margin-top:5px;padding:2px 8px;border-radius:999px;
    font-size:11px;font-weight:700;background:#fef3c7;color:#92400e;}
  #thinking  {align-self:flex-start;background:#1e3a5f;padding:10px 14px;
    border-radius:14px 14px 14px 3px;}
  .dot       {display:inline-block;width:7px;height:7px;background:#60a5fa;border-radius:50%;
    animation:wave 1.2s ease-in-out infinite;margin:0 2px;}
  .dot:nth-child(2){animation-delay:.15s;} .dot:nth-child(3){animation-delay:.3s;}
  @keyframes wave {0%,60%,100%{transform:translateY(0);}30%{transform:translateY(-6px);}}
  #input-row {padding:9px;border-top:1px solid #334155;display:flex;gap:6px;flex-shrink:0;}
  #user-inp  {flex:1;background:#0f172a;border:1px solid #334155;color:#f1f5f9;
    padding:8px 12px;border-radius:8px;font-size:13px;outline:none;}
  #user-inp:focus {border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.18);}
  #send-btn  {background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;border:none;padding:8px 14px;border-radius:8px;
    cursor:pointer;font-size:13px;font-weight:600;flex-shrink:0;transition:transform .15s ease,box-shadow .15s ease;}
  #send-btn:hover {background:linear-gradient(135deg,#60a5fa,#3b82f6);transform:translateY(-1px);box-shadow:0 4px 12px rgba(59,130,246,.4);}
  #send-btn:disabled {background:#374151;color:#6b7280;cursor:not-allowed;transform:none;box-shadow:none;}
  #upload-btn {background:#1e293b;color:#94a3b8;border:1px solid #334155;padding:8px 10px;
    border-radius:8px;cursor:pointer;font-size:15px;flex-shrink:0;line-height:1;}
  #upload-btn:hover {background:#334155;color:#f1f5f9;}
  #upload-btn:disabled {opacity:.4;cursor:not-allowed;}
  #schedule-badge {margin:0 9px 6px;padding:6px 10px;border-radius:8px;background:#0c2340;
    border:1px solid #1e40af;font-size:11px;color:#93c5fd;display:flex;align-items:center;gap:6px;}
  #schedule-badge .rm {cursor:pointer;color:#64748b;font-size:13px;margin-left:auto;}
  #schedule-badge .rm:hover {color:#f87171;}
  #profile-btn {display:inline-flex;align-items:center;gap:8px;background:#0f172a;border:1px solid #334155;color:#f1f5f9;
    padding:4px 10px 4px 4px;border-radius:999px;cursor:pointer;line-height:1;}
  #profile-btn:hover {background:#1f2937;}
  #profile-avatar {width:28px;height:28px;border-radius:50%;background:#2563eb;color:#fff;display:flex;align-items:center;justify-content:center;
    font-size:11px;font-weight:800;letter-spacing:.03em;}
  #profile-name {font-size:12px;font-weight:700;max-width:120px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
  #profile-modal-backdrop {position:fixed;inset:0;background:rgba(15,23,42,.48);display:none;align-items:flex-start;justify-content:flex-end;z-index:1400;}
  #profile-modal-backdrop.open {display:flex;}
  #profile-modal {width:min(360px, calc(100vw - 24px));max-height:calc(100vh - 24px);margin:12px 14px 0 0;background:rgba(255,255,255,0.92);color:#0f172a;border-radius:20px;
    box-shadow:0 24px 60px rgba(15,23,42,.28);overflow:hidden;border:1px solid rgba(191,219,254,0.8);display:flex;flex-direction:column;
    backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);}
  .profile-head {flex:0 0 auto;}
  .profile-head {padding:16px 18px 12px;border-bottom:1px solid #e2e8f0;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;}
  .profile-head h3 {font-size:18px;font-weight:900;letter-spacing:-.02em;}
  .profile-head p {font-size:12px;color:#64748b;line-height:1.45;margin-top:4px;}
  .profile-close {border:none;background:#eff6ff;color:#1d4ed8;border-radius:999px;width:30px;height:30px;cursor:pointer;font-size:16px;}
  .profile-body {padding:16px 18px 18px;display:flex;flex-direction:column;gap:14px;flex:1 1 auto;min-height:0;overflow-y:auto;}
  .profile-group {display:flex;flex-direction:column;gap:8px;}
  .profile-label {font-size:12px;font-weight:800;color:#334155;letter-spacing:.02em;}
  .profile-help {font-size:11px;color:#64748b;line-height:1.45;}
  .profile-sync {border:1px solid #dbeafe;background:#eff6ff;color:#1e3a8a;border-radius:10px;padding:8px 10px;font-size:11px;line-height:1.35;}
  .profile-sync.warn {border-color:#fed7aa;background:#fff7ed;color:#9a3412;}
  .profile-sync.ok {border-color:#bbf7d0;background:#f0fdf4;color:#166534;}
  .profile-input, .profile-select {width:100%;background:#f8fafc;border:1px solid #cbd5e1;border-radius:10px;padding:10px 12px;font-size:13px;color:#0f172a;outline:none;}
  .profile-input:focus, .profile-select:focus {border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.12);}
  .profile-options {display:flex;flex-wrap:wrap;gap:8px;}
  .profile-choice {position:relative;display:inline-flex;align-items:center;}
  .profile-choice input {position:absolute;opacity:0;pointer-events:none;}
  .profile-choice span {display:inline-flex;align-items:center;padding:8px 10px;border-radius:999px;border:1px solid #cbd5e1;background:#f8fafc;
    font-size:12px;font-weight:700;color:#334155;cursor:pointer;transition:all .15s ease;}
  .profile-choice input:checked + span {background:#dbeafe;border-color:#60a5fa;color:#1d4ed8;}
  .profile-actions {display:flex;gap:10px;justify-content:flex-end;padding-top:4px;}
  .profile-footer-actions {position:sticky;bottom:-18px;margin:0 -18px -18px;padding:12px 18px 14px;background:rgba(255,255,255,0.96);border-top:1px solid #e2e8f0;z-index:2;}
  .profile-save, .profile-secondary {border:none;border-radius:10px;padding:10px 14px;font-size:13px;font-weight:800;cursor:pointer;}
  .profile-save {background:#2563eb;color:#fff;}
  .profile-save:hover {background:#1d4ed8;}
  .profile-secondary {background:#eff6ff;color:#1d4ed8;}
  .profile-secondary:hover {background:#dbeafe;}
  .profile-delete {background:#fee2e2;color:#dc2626;border:none;border-radius:10px;
    padding:10px 14px;font-size:13px;font-weight:800;cursor:pointer;margin-right:auto;}
  .profile-delete:hover {background:#fecaca;}
  #upload-btn {background:#1e293b;border:1px solid #3b82f6;padding:7px 10px;
    border-radius:8px;cursor:pointer;font-size:12px;flex-shrink:0;line-height:1;
    color:#93c5fd;font-weight:700;display:flex;align-items:center;gap:4px;}
  #upload-btn:hover {background:#1e40af;color:#fff;}
  #upload-btn:disabled {opacity:.4;cursor:not-allowed;}
  #toast {position:fixed;bottom:28px;left:50%;transform:translateX(-50%) translateY(14px);
    padding:10px 22px;border-radius:999px;font-size:13px;font-weight:600;
    background:#1e293b;color:#f1f5f9;border:1px solid #334155;
    box-shadow:0 8px 24px rgba(0,0,0,.4);opacity:0;pointer-events:none;
    transition:opacity .2s ease,transform .2s ease;z-index:9999;white-space:nowrap;}
  #toast.show {opacity:1;transform:translateX(-50%) translateY(0);}
  #toast.t-success {background:#052e16;color:#4ade80;border-color:#166534;}
  #toast.t-warn    {background:#431407;color:#fdba74;border-color:#9a3412;}
  body.light-mode #toast {background:#ffffff;color:#0f172a;border-color:#e2e8f0;box-shadow:0 8px 24px rgba(0,0,0,.12);}
  body.light-mode #toast.t-success {background:#dcfce7;color:#15803d;border-color:#16a34a;}
  body.light-mode #toast.t-warn    {background:#fef3c7;color:#92400e;border-color:#d97706;}
  body.light-mode #upload-btn {background:#eff6ff;border-color:#3b82f6;color:#1d4ed8;}
  body.light-mode #upload-btn:hover {background:#dbeafe;color:#1e40af;}
  #theme-btn {background:none;border:1px solid #334155;font-size:15px;cursor:pointer;
    padding:4px 8px;border-radius:6px;color:#94a3b8;flex-shrink:0;margin-left:auto;line-height:1;}
  #theme-btn:hover {background:rgba(148,163,184,.12);color:#f1f5f9;}
  #guide-btn {background:none;border:1px solid #334155;font-size:12px;cursor:pointer;
    padding:6px 10px;border-radius:999px;color:#94a3b8;flex-shrink:0;font-weight:700;line-height:1;}
  #guide-btn:hover {background:rgba(148,163,184,.12);color:#f1f5f9;}

  /* ── Light mode overrides ─────────────────────────────────────────────── */
  body.light-mode {background:#f1f5f9;color:#0f172a;}
  body.light-mode #ai-panel {background:#ffffff;border-right-color:#cbd5e1;}
  body.light-mode #ai-header {border-bottom-color:#cbd5e1;background:linear-gradient(180deg,#eff6ff 0%,#ffffff 100%);}
  body.light-mode #ai-title {color:#0f172a;}
  body.light-mode #api-key-inp {background:#f8fafc;border-color:#cbd5e1;color:#0f172a;}
  body.light-mode #api-key-inp::placeholder {color:#94a3b8;}
  body.light-mode #server-key-note {background:#dcfce7;border-color:#16a34a;color:#15803d;}
  body.light-mode #clear-btn {background:#e2e8f0;color:#475569;}
  body.light-mode #clear-btn:hover {background:#cbd5e1;color:#0f172a;}
  body.light-mode .stop-lbl {color:#64748b;}
  body.light-mode #stop-sel, body.light-mode #dest-sel {background:#f8fafc;border-color:#cbd5e1;color:#0f172a;}
  body.light-mode #chat-box::-webkit-scrollbar-thumb {background:#cbd5e1;}
  body.light-mode .msg-ai {background:#dbeafe;color:#1e3a5f;}
  body.light-mode .ai-section {border-top-color:#bfdbfe;}
  body.light-mode .ai-section-title {color:#1d4ed8;}
  body.light-mode .ai-section-main {color:#0f172a;}
  body.light-mode .ai-section-detail, body.light-mode .ai-list {color:#334155;}
  body.light-mode .ai-pill {background:#eff6ff;border-color:#bfdbfe;color:#1d4ed8;}
  body.light-mode .ai-alert {background:#fffbeb;border-color:#f59e0b;color:#92400e;}
  body.light-mode #suggestions {background:rgba(255,255,255,.9);border-color:#bfdbfe;box-shadow:0 14px 34px rgba(37,99,235,.12),inset 0 1px 0 rgba(255,255,255,.9);}
  body.light-mode .suggest-label {color:#2563eb;}
  body.light-mode .suggest-chip {background:#f8fafc;border-color:#cbd5e1;color:#334155;}
  body.light-mode .suggest-chip:hover {background:#2563eb;color:#fff;border-color:#2563eb;transform:translateX(3px);box-shadow:0 6px 16px rgba(37,99,235,.28);}
  body.light-mode #thinking {background:#dbeafe;}
  body.light-mode .dot {background:#64748b;}
  body.light-mode #input-row {border-top-color:#cbd5e1;}
  body.light-mode #user-inp {background:#f8fafc;border-color:#cbd5e1;color:#0f172a;}
  body.light-mode #user-inp::placeholder {color:#94a3b8;}
  body.light-mode #send-btn:disabled {background:#e2e8f0;color:#94a3b8;}
  body.light-mode #upload-btn {background:#f1f5f9;border-color:#cbd5e1;color:#64748b;}
  body.light-mode #upload-btn:hover {background:#e2e8f0;color:#0f172a;}
  body.light-mode #schedule-badge {background:#dbeafe;border-color:#3b82f6;color:#1e40af;}
  body.light-mode #profile-btn {background:#ffffff;border-color:#cbd5e1;color:#0f172a;}
  body.light-mode #profile-btn:hover {background:#f8fafc;}
  body.light-mode #theme-btn {border-color:#cbd5e1;color:#64748b;}
  body.light-mode #theme-btn:hover {background:rgba(0,0,0,.06);color:#0f172a;}
  body.light-mode #guide-btn {border-color:#cbd5e1;color:#475569;}
  body.light-mode #guide-btn:hover {background:rgba(0,0,0,.06);color:#0f172a;}
  body.light-mode #drag-handle {background:#e2e8f0;border-color:#cbd5e1;}
  body.light-mode #drag-handle:hover,body.light-mode #drag-handle.dragging {background:#3b82f6;border-color:#3b82f6;}
  body.light-mode #drag-handle::after {color:#94a3b8;}
  body.light-mode #map-header {background:linear-gradient(180deg,#f0f6ff 0%,#ffffff 100%);border-bottom-color:#cbd5e1;}
  body.light-mode #map-header h2 {color:#0f172a;}
  body.light-mode #map-header span {color:#64748b;}
  body.light-mode #route-side {background:#f8fafc;color:#0f172a;border-left-color:#cbd5e1;}
  body.light-mode #route-side h3 {color:#0f172a;}
  body.light-mode .card {background:#ffffff;border-image:linear-gradient(180deg,#2563eb,#7c3aed) 1;}
  body.light-mode .card .title {color:#0f172a;}
  body.light-mode .card .body {color:#475569;}
  body.light-mode .stop-metric-value {color:#0f172a;}
  body.light-mode .stop-metric-label {color:#64748b;}
  body.light-mode .stop-metric-detail {color:#475569;}
  body.light-mode .stop-capacity-badge {background:#dbeafe;color:#1d4ed8;}
  body.light-mode .stop-inline-route {color:#1d4ed8;}
  body.light-mode .route-filter {box-shadow:0 2px 8px rgba(0,0,0,.08);}
  body.light-mode .route-filter:hover {box-shadow:0 8px 20px rgba(0,0,0,.12);}
  body.light-mode .route-filter.active {background:#dbeafe;box-shadow:0 0 0 3px rgba(37,99,235,.3),0 6px 20px rgba(37,99,235,.12);}
  body.light-mode .route-filter .route-title {color:#64748b;}
  body.light-mode .route-filter .route-stops {color:#1e293b;}
  body.light-mode .route-filter .route-action {color:#2563eb;}
  body.light-mode .route-filter.active .route-action {color:#1d4ed8;}

  /* ── Stop context bar (AI panel, below stop selector) ───────────────── */
  #stop-ctx {padding:9px 12px 10px;border-top:1px solid #334155;flex-shrink:0;
    background:#0c2340;border-left:3px solid #3b82f6;}
  #stop-ctx-name {font-size:13px;font-weight:900;color:#f1f5f9;letter-spacing:-.01em;}
  #stop-ctx-rows {margin-top:5px;display:flex;flex-direction:column;gap:3px;}
  .ctx-row {font-size:11px;color:#93c5fd;line-height:1.4;}
  .ctx-eta-val {font-weight:900;color:#f1f5f9;font-size:15px;}
  .ctx-cap-red {color:#ef4444;font-weight:700;}
  .ctx-cap-yel {color:#f59e0b;font-weight:700;}
  .ctx-cap-grn {color:#22c55e;font-weight:700;}
  body.light-mode #stop-ctx {background:#dbeafe;border-left-color:#2563eb;border-top-color:#cbd5e1;}
  body.light-mode #stop-ctx-name {color:#0f172a;}
  body.light-mode .ctx-row {color:#1d4ed8;}
  body.light-mode .ctx-eta-val {color:#0f172a;}

  /* ── You-are-here / geolocation ──────────────────────────────────────── */
  .user-dot {width:16px;height:16px;border-radius:50%;background:#3b82f6;
    border:2.5px solid #fff;box-shadow:0 2px 4px rgba(0,0,0,.3);
    animation:pulse-loc 2s infinite;}
  @keyframes pulse-loc {
    0%   {box-shadow:0 0 0 0   rgba(59,130,246,.6), 0 2px 4px rgba(0,0,0,.3);}
    70%  {box-shadow:0 0 0 10px rgba(59,130,246,0),  0 2px 4px rgba(0,0,0,.3);}
    100% {box-shadow:0 0 0 0   rgba(59,130,246,0),   0 2px 4px rgba(0,0,0,.3);}
  }
  #loc-banner {display:none;align-items:center;gap:8px;padding:7px 14px;
    background:#0c2340;border-bottom:1px solid #1d4ed8;font-size:12px;
    color:#93c5fd;flex-shrink:0;}
  #loc-banner b {color:#e2e8f0;}
  #map-wrap {position:relative;min-width:0;overflow:hidden;}
  #map-alert {position:absolute;top:14px;left:50%;transform:translateX(-50%);z-index:900;
    width:min(620px,calc(100% - 32px));display:none;align-items:flex-start;gap:10px;
    padding:12px 14px;border-radius:16px;background:rgba(255,251,235,.96);
    border:1px solid rgba(245,158,11,.75);color:#92400e;box-shadow:0 18px 40px rgba(15,23,42,.22);
    backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);}
  #map-alert.show {display:flex;}
  #map-alert .alert-dot {width:10px;height:10px;border-radius:50%;background:#f59e0b;box-shadow:0 0 0 4px rgba(245,158,11,.18);margin-top:4px;flex-shrink:0;}
  #map-alert .alert-body {min-width:0;font-size:13px;line-height:1.42;}
  #map-alert .alert-title {font-size:11px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#78350f;margin-bottom:2px;}
  #map-alert-close {border:none;background:rgba(146,64,14,.1);color:#78350f;border-radius:999px;width:24px;height:24px;cursor:pointer;
    font-size:16px;line-height:1;flex-shrink:0;margin-left:auto;}
  #map-alert-close:hover {background:rgba(146,64,14,.18);}
  .loc-dot {width:10px;height:10px;border-radius:50%;flex-shrink:0;display:inline-block;}
  .loc-dist {margin-left:auto;color:#64748b;font-size:11px;white-space:nowrap;}
  .loc-center-btn {margin-left:8px;background:#1d4ed8;color:#fff;border:none;padding:3px 9px;
    border-radius:5px;cursor:pointer;font-size:11px;flex-shrink:0;font-weight:600;}
  .loc-center-btn:hover {background:#2563eb;}
  #locate-btn {background:none;border:1px solid #334155;font-size:15px;cursor:pointer;
    padding:4px 8px;border-radius:6px;color:#94a3b8;flex-shrink:0;line-height:1;}
  #locate-btn:hover {background:rgba(148,163,184,.12);color:#f1f5f9;}
  #locate-btn.tracking {border-color:#3b82f6;color:#3b82f6;}
  body.light-mode #loc-banner {background:#dbeafe;border-bottom-color:#93c5fd;color:#1e40af;}
  body.light-mode #loc-banner b {color:#1e3a5f;}
  body.light-mode #map-alert {background:rgba(255,251,235,.96);}
  body.light-mode .loc-dist {color:#94a3b8;}
  body.light-mode #locate-btn {border-color:#cbd5e1;color:#64748b;}
  body.light-mode #locate-btn:hover {background:rgba(0,0,0,.06);color:#0f172a;}
  body.light-mode #locate-btn.tracking {border-color:#3b82f6;color:#2563eb;}

  /* Drag handle */
  #drag-handle {width:6px;flex-shrink:0;background:#1e293b;cursor:col-resize;
    display:flex;align-items:center;justify-content:center;
    border-left:1px solid #334155;border-right:1px solid #334155;user-select:none;}
  #drag-handle:hover,#drag-handle.dragging {background:#3b82f6;border-color:#3b82f6;}
  #drag-handle::after {content:'⋮';color:#475569;font-size:12px;}
  #drag-handle:hover::after,#drag-handle.dragging::after {color:#fff;}

  /* Map panel */
  #map-panel  {flex:1;display:flex;flex-direction:column;min-width:300px;overflow:hidden;}
  #map-header {padding:10px 16px;background:linear-gradient(180deg,#243554 0%,#1e293b 100%);border-bottom:1px solid #334155;
    display:flex;align-items:center;gap:12px;flex-shrink:0;height:44px;}
  #map-header h2 {font-size:18px;font-weight:700;color:#f1f5f9;}
  #map-header span {font-size:11px;color:#64748b;}
  #map-body   {display:grid;grid-template-columns:minmax(0,1fr) 300px;overflow:hidden;}
  #map        {width:100%;}
  #route-side {background:#1e293b;overflow-y:auto;padding:12px;
    font-family:sans-serif;font-size:12px;color:#f1f5f9;border-left:1px solid #334155;}
  #route-side::-webkit-scrollbar {width:4px;}
  #route-side::-webkit-scrollbar-thumb {background:#334155;border-radius:2px;}
  #route-side::-webkit-scrollbar-thumb:hover {background:#475569;}
  #route-side h3 {font-size:20px;margin:8px 0 6px;color:#f1f5f9;font-weight:800;letter-spacing:-.01em;}
  .card       {background:#0f172a;border-radius:14px;padding:14px 14px 13px;margin-bottom:10px;
    border-left:4px solid;border-image:linear-gradient(180deg,#3b82f6,#7c3aed) 1;}
  .card .title{font-weight:700;font-size:12px;color:#f1f5f9;}
  .card .body {color:#94a3b8;margin-top:3px;font-size:11px;line-height:1.4;}
  .stop-card {padding:14px 14px 12px;}
  .stop-card .title {font-size:12px;font-weight:900;line-height:1.18;letter-spacing:-.02em;word-break:break-word;}
  .stop-routes {display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;}
  .stop-route-pill {display:inline-flex;align-items:center;padding:5px 10px;border-radius:999px;
    color:#fff;font-size:9px;font-weight:800;letter-spacing:.01em;max-width:100%;line-height:1.2;}
  .stop-metric {margin-top:12px;padding-top:11px;border-top:1px solid rgba(148,163,184,.18);}
  .stop-metric-label {font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;}
  .stop-metric-value {margin-top:5px;font-size:18px;font-weight:900;color:#f1f5f9;line-height:1.02;letter-spacing:-.02em;}
  .stop-metric-detail {margin-top:5px;color:#94a3b8;font-size:10px;line-height:1.4;}
  .stop-capacity-badge {display:inline-flex;align-items:center;padding:5px 10px;border-radius:999px;
    background:#1e3a5f;color:#93c5fd;font-size:10px;font-weight:800;}
  .capacity-people {display:flex;gap:5px;align-items:flex-end;margin-top:10px;margin-bottom:8px;flex-wrap:wrap;}
  .capacity-person {position:relative;width:8px;height:20px;opacity:.26;transition:opacity .4s ease;}
  .capacity-person.active {opacity:1;}
  .capacity-person::before {content:'';position:absolute;left:1px;top:0;width:6px;height:6px;border-radius:50%;background:currentColor;}
  .capacity-person::after {content:'';position:absolute;left:2px;top:7px;width:4px;height:11px;border-radius:3px;background:currentColor;box-shadow:-3px 2px 0 0 currentColor,3px 2px 0 0 currentColor,-2px 10px 0 0 currentColor,2px 10px 0 0 currentColor;}
  .stop-inline-route {font-weight:800;color:#93c5fd;}
  .route-chip {display:inline-flex;align-items:center;gap:6px;color:#fff;border-radius:999px;padding:8px 14px;
    font-size:11px;font-weight:800;letter-spacing:.01em;margin-top:2px;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.25),inset 0 -1px 0 rgba(0,0,0,.15),0 2px 6px rgba(0,0,0,.2);}
  .route-top {min-width:0;}
  .route-chip {max-width:100%;white-space:nowrap;}
  .route-filter {width:100%;text-align:left;cursor:pointer;transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease, background .15s ease;
    border-left-width:4px;border-left-style:solid;border-top:none;border-right:none;border-bottom:none;box-shadow:0 4px 12px rgba(0,0,0,.3);}
  .route-filter:hover {transform:translateY(-2px);box-shadow:0 10px 24px rgba(0,0,0,.4);}
  .route-filter:focus-visible {outline:none;box-shadow:0 0 0 3px rgba(59,130,246,.4);}
  .route-filter.active {background:#1e3a5f;box-shadow:0 0 0 3px rgba(59,130,246,.55),0 6px 20px rgba(59,130,246,.2);}
  .route-filter .route-top {display:flex;align-items:flex-start;justify-content:space-between;gap:10px;}
  .route-filter .route-title {font-size:12px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#94a3b8;}
  .route-filter .route-stops {margin-top:10px;font-size:13px;font-weight:700;color:#e2e8f0;line-height:1.45;}
  .route-filter .route-action {margin-top:10px;font-size:11px;font-weight:700;color:#60a5fa;display:flex;align-items:center;gap:6px;}
  .route-filter.active .route-action {color:#93c5fd;}
  .legend     {background:#fff;color:#111827;padding:7px 9px;border-radius:7px;
    box-shadow:0 3px 10px rgba(0,0,0,.15);font-size:11px;line-height:1.5;}
  .legend-dot {display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;}
  .bus-hit {width:52px;height:52px;display:flex;align-items:center;justify-content:center;cursor:pointer;}
  .bus-marker {width:32px;height:32px;border-radius:50%;border:3px solid #fff;
    box-shadow:0 2px 6px rgba(0,0,0,.3);display:flex;align-items:center;
    justify-content:center;font-size:16px;cursor:pointer;}
  .bus-marker.boarding {box-shadow:0 0 0 5px rgba(255,255,255,.35),0 2px 6px rgba(0,0,0,.3);animation:none;}
  /* Per-route icon colors + pulse animations */
  @keyframes bus-pulse-comm {
    0%   {box-shadow:0 0 0 0 rgba(29,78,216,.55),0 2px 6px rgba(0,0,0,.3);}
    70%  {box-shadow:0 0 0 10px rgba(29,78,216,0),0 2px 6px rgba(0,0,0,.3);}
    100% {box-shadow:0 0 0 0 rgba(29,78,216,0),0 2px 6px rgba(0,0,0,.3);}
  }
  @keyframes bus-pulse-newton {
    0%   {box-shadow:0 0 0 0 rgba(139,0,0,.55),0 2px 6px rgba(0,0,0,.3);}
    70%  {box-shadow:0 0 0 10px rgba(139,0,0,0),0 2px 6px rgba(0,0,0,.3);}
    100% {box-shadow:0 0 0 0 rgba(139,0,0,0),0 2px 6px rgba(0,0,0,.3);}
  }
  .bus-color-comm   { background-color: #1d4ed8 !important; animation: bus-pulse-comm 1.8s infinite; }
  .bus-color-newton { background-color: #8b0000 !important; animation: bus-pulse-newton 1.8s infinite; }
  .boarding-pill {background:rgba(17,24,39,.9);color:#fff;border-radius:999px;
    padding:3px 8px;font-size:11px;font-weight:700;white-space:nowrap;}
  /* Floating map windows (stop info + shuttle info) */
  #stop-float, #shuttle-float {
    position:absolute;z-index:1000;
    background:rgba(15,23,42,0.93);border:1px solid #1e3a5f;
    border-radius:16px;padding:14px 15px 13px;
    box-shadow:0 8px 32px rgba(0,0,0,.45),0 0 0 1px rgba(59,130,246,.12);
    backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
    font-family:sans-serif;font-size:12px;color:#f1f5f9;
    min-width:220px;max-width:280px;pointer-events:auto;}
  #stop-float  {bottom:20px;left:16px;}
  #shuttle-float {top:16px;right:16px;}
  .float-head {display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:10px;}
  .float-title {font-size:13px;font-weight:900;color:#f1f5f9;letter-spacing:-.01em;line-height:1.2;word-break:break-word;}
  .float-close {background:none;border:none;cursor:pointer;color:#64748b;font-size:15px;
    line-height:1;padding:0;flex-shrink:0;margin-top:1px;}
  .float-close:hover {color:#f87171;}
  body.light-mode #stop-float, body.light-mode #shuttle-float {
    background:rgba(255,255,255,0.95);border-color:#bfdbfe;
    box-shadow:0 8px 32px rgba(15,23,42,.15),0 0 0 1px rgba(37,99,235,.1);color:#0f172a;}
  body.light-mode .float-title {color:#0f172a;}
  body.light-mode .float-close {color:#94a3b8;}
  body.light-mode .float-close:hover {color:#dc2626;}
  /* Override dark-mode inline colors for muted/primary text inside floats */
  body.light-mode #stop-float [style*="color:#94a3b8"],
  body.light-mode #shuttle-float [style*="color:#94a3b8"] {color:#374151 !important;}
  body.light-mode #stop-float [style*="color:#64748b"],
  body.light-mode #shuttle-float [style*="color:#64748b"] {color:#374151 !important;}
  body.light-mode #stop-float [style*="color:#f1f5f9"],
  body.light-mode #shuttle-float [style*="color:#f1f5f9"] {color:#0f172a !important;}
  body.light-mode #stop-float b[style*="color:#f1f5f9"],
  body.light-mode #shuttle-float b[style*="color:#f1f5f9"] {color:#0f172a !important;}

  /* Shuttle relevance highlighting when a stop is selected */
  .bus-marker.relevant {box-shadow:0 0 0 5px rgba(250,204,21,.75),0 2px 8px rgba(0,0,0,.4);
    transform:scale(1.12);transition:box-shadow .25s ease,transform .25s ease;animation:none;}
  .bus-marker.dim {opacity:1;transition:opacity .25s ease;}
  /* Location-based recommendation card */
  .loc-rec-best {background:#0a1f38 !important;}
  .loc-rec-badge {font-size:10px;font-weight:800;color:#60a5fa;margin-bottom:5px;letter-spacing:.04em;}
  .loc-rec-eta {font-size:22px;font-weight:900;color:#f1f5f9;line-height:1;}
  body.light-mode .loc-rec-best {background:#dbeafe !important;}
  body.light-mode .loc-rec-badge {color:#1d4ed8;}
  body.light-mode .loc-rec-eta {color:#0f172a;}

  /* Guided tour */
  #tour-overlay {position:fixed;inset:0;background:rgba(15,23,42,.45);display:none;z-index:2500;pointer-events:auto;}
  #tour-overlay.active {display:block;}
  #tour-highlight {position:fixed;border:3px solid #60a5fa;border-radius:18px;
    box-shadow:0 0 0 9999px rgba(15,23,42,.42), 0 20px 50px rgba(15,23,42,.35);
    display:none;z-index:2501;pointer-events:none;transition:all .2s ease;}
  #tour-highlight.active {display:block;}
  #tour-card {position:fixed;display:none;z-index:2502;width:min(360px, calc(100vw - 32px));
    background:#ffffff;color:#0f172a;border-radius:20px;padding:18px 18px 16px;
    box-shadow:0 24px 60px rgba(15,23,42,.28);border:1px solid #dbeafe;}
  #tour-card.active {display:block;}
  #tour-step {font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#2563eb;}
  #tour-title {margin-top:8px;font-size:20px;font-weight:900;letter-spacing:-.03em;color:#0f172a;}
  #tour-body {margin-top:10px;font-size:14px;line-height:1.55;color:#334155;}
  #tour-actions {display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:16px;}
  #tour-left-actions, #tour-right-actions {display:flex;align-items:center;gap:10px;}
  .tour-btn {border:none;border-radius:999px;padding:10px 14px;font-size:13px;font-weight:800;cursor:pointer;}
  .tour-btn.secondary {background:#eff6ff;color:#1d4ed8;}
  .tour-btn.secondary:hover {background:#dbeafe;}
  .tour-btn.primary {background:#2563eb;color:#fff;}
  .tour-btn.primary:hover {background:#1d4ed8;}
  .tour-btn.ghost {background:transparent;color:#64748b;padding:10px 8px;}
  .tour-btn.ghost:hover {color:#0f172a;}
  body.light-mode #tour-overlay {background:rgba(15,23,42,.32);}

  @media (max-height: 940px) {
    #ai-panel {width:380px;}
    #ai-header {padding:10px 12px 8px;}
    #ai-title {margin-bottom:6px;}
    #key-row {margin-bottom:6px;}
    #chat-box {padding:8px 8px 238px;gap:6px;}
    .msg-user, .msg-ai {font-size:12px;padding:7px 10px;}
    #suggestions {left:8px;right:8px;bottom:58px;padding:9px;border-radius:14px;max-height:178px;}
    .suggest-label {margin-bottom:6px;}
    .suggest-grid {gap:6px;}
    .suggest-chip {padding:6px 9px;font-size:11px;}
    #input-row {padding:8px;gap:5px;}
    #user-inp, #send-btn, #upload-btn {font-size:12px;}
    #map-header {padding:8px 12px;height:40px;gap:8px;}
    #map-header h2 {font-size:18px;}
    #map-header span {font-size:10px;}
    #loc-banner {padding:6px 12px;font-size:11px;}
    #map-body {grid-template-columns:minmax(0,1fr) 285px;}
    #route-side {padding:10px;font-size:11px;}
    #route-side h3 {font-size:18px;margin:6px 0 5px;}
    .card {padding:12px 12px 11px;margin-bottom:8px;border-radius:12px;}
    .card .title {font-size:11px;}
    .card .body {font-size:10px;}
    .loc-rec-eta {font-size:18px;}
    .stop-routes {margin-top:8px;gap:5px;}
    .stop-route-pill {padding:4px 8px;font-size:8px;}
    .stop-metric {margin-top:9px;padding-top:9px;}
    .stop-metric-label {font-size:9px;}
    .stop-metric-value {margin-top:4px;font-size:16px;}
    .stop-metric-detail {margin-top:4px;font-size:9px;}
    .stop-capacity-badge {padding:4px 8px;font-size:9px;}
    .capacity-people {gap:4px;margin-top:8px;margin-bottom:4px;}
    .capacity-person {width:7px;height:18px;}
    .capacity-person::before {width:5px;height:5px;}
    .capacity-person::after {top:6px;height:10px;}
    .route-chip {padding:6px 10px;font-size:10px;}
    .route-filter .route-stops {margin-top:8px;font-size:11px;}
    .route-filter .route-action {margin-top:8px;font-size:10px;}
    #profile-btn {padding:3px 8px 3px 3px;gap:6px;}
    #profile-avatar {width:24px;height:24px;font-size:10px;}
    #profile-name {font-size:11px;max-width:92px;}
    #guide-btn, #locate-btn, #theme-btn {padding:4px 7px;}
  }
</style>
</head>
<body>
<div id="app">

  <div id="ai-panel">
    <div id="ai-header">
      <div id="ai-title">🤖 AI Shuttle Assistant</div>
      <div id="key-row">
        <input id="api-key-inp" type="password" placeholder="Enter your OpenAI API key…"/>
        <button id="clear-btn" onclick="clearChat()" title="Clear chat">🗑️</button>
      </div>
      <div class="stop-row">
        <span class="stop-lbl">Your stop:</span>
        <select id="stop-sel" onchange="onStopChange(this.value)">STOP_OPTIONS_PLACEHOLDER</select>
      </div>
      <div class="stop-row">
        <span class="stop-lbl">Destination:</span>
        <select id="dest-sel" onchange="onDestinationChange(this.value)">DESTINATION_OPTIONS_PLACEHOLDER</select>
      </div>
    </div>
    <div id="stop-ctx">
      <div id="stop-ctx-name">Loading…</div>
      <div id="stop-ctx-rows"></div>
    </div>
    <div id="chat-box"></div>
    <div id="suggestions"></div>
    <input id="schedule-file" type="file" accept="image/*" style="display:none"/>
    <div id="schedule-badge" style="display:none">
      <span>📅</span><span id="schedule-label">Schedule loaded</span>
      <span class="rm" onclick="clearSchedule()" title="Remove schedule">✕</span>
    </div>
    <div id="input-row">
      <button id="upload-btn" title="Open rider profile" onclick="openProfileModal()">👤 Profile</button>
      <input id="user-inp" type="text" placeholder="Ask about shuttles or report a delay…"/>
      <button id="send-btn">Send ➤</button>
    </div>
  </div>

  <div id="drag-handle"></div>

  <div id="map-panel">
    <div id="map-header">
      <h2>🗺️ Live Shuttle Map</h2>
      <span id="map-ts"></span>
      <button id="profile-btn" onclick="openProfileModal()" title="Open profile">
        <span id="profile-avatar">BC</span>
        <span id="profile-name">Your profile</span>
      </button>
      <button id="guide-btn" onclick="startTour(true)" title="Replay guide">Guide</button>
      <button id="locate-btn" onclick="showMyLocation()" title="Show my location and set nearest stop">📍</button>
      <button id="theme-btn" onclick="toggleTheme()" title="Toggle light/dark mode">☀️</button>
    </div>
    <div id="loc-banner"></div>
    <div id="map-body">
      <div id="map-wrap">
        <div id="map-alert"></div>
        <div id="map" style="width:100%;"></div>
        <div id="stop-float" style="display:none;">
          <div class="float-head">
            <div id="stop-float-title" class="float-title"></div>
            <button class="float-close" onclick="closeStopSection()" title="Close">✕</button>
          </div>
          <div id="stop-float-routes"></div>
          <div id="stop-float-arrivals"></div>
        </div>
        <div id="shuttle-float" style="display:none;">
          <div class="float-head">
            <div id="shuttle-float-title" class="float-title"></div>
            <button class="float-close" onclick="closeShuttleFloat()" title="Close">✕</button>
          </div>
          <div id="shuttle-float-body"></div>
        </div>
      </div>
      <div id="route-side">
        <h3 id="loc-rec-title" style="display:none;">Stops Near You</h3>
        <div id="loc-rec" style="display:none;"></div>
        <h3>Routes</h3>
        <div id="route-info"></div>
      </div>
    </div>
  </div>

</div>
<div id="tour-overlay"></div>
<div id="tour-highlight"></div>
<div id="tour-card" role="dialog" aria-live="polite" aria-label="User guide">
  <div id="tour-step"></div>
  <div id="tour-title"></div>
  <div id="tour-body"></div>
  <div id="tour-actions">
    <div id="tour-left-actions">
      <button class="tour-btn ghost" onclick="stopTour()">Skip</button>
    </div>
    <div id="tour-right-actions">
      <button id="tour-back" class="tour-btn secondary" onclick="previousTourStep()">Back</button>
      <button id="tour-next" class="tour-btn primary" onclick="nextTourStep()">Next</button>
    </div>
  </div>
</div>
<div id="profile-modal-backdrop" onclick="handleProfileBackdrop(event)">
  <div id="profile-modal">
    <div class="profile-head">
      <div>
        <h3>Rider Profile</h3>
        <p>Tell the assistant a bit about you so its recommendations can feel more personal.</p>
      </div>
      <button class="profile-close" onclick="closeProfileModal()" title="Close profile">✕</button>
    </div>
    <div class="profile-body">
      <div id="profile-sync-status" class="profile-sync">Cloud sync status is checking...</div>
      <div class="profile-group">
        <label class="profile-label" for="profile-nickname">Nickname</label>
        <input id="profile-nickname" class="profile-input" type="text" placeholder="ex. Maya"/>
      </div>

      <div class="profile-group">
        <div class="profile-label">Timing style</div>
        <div class="profile-help">Would you rather leave early or leave more room to procrastinate?</div>
        <div class="profile-options">
          <label class="profile-choice"><input type="radio" name="timing-style" value="early"/><span>Leave early</span></label>
          <label class="profile-choice"><input type="radio" name="timing-style" value="balanced"/><span>Balanced</span></label>
          <label class="profile-choice"><input type="radio" name="timing-style" value="procrastinate"/><span>Procrastinate</span></label>
        </div>
      </div>

      <div class="profile-group">
        <div class="profile-label">Crowding preference</div>
        <div class="profile-options">
          <label class="profile-choice"><input type="radio" name="crowd-style" value="avoid_crowds"/><span>Avoid crowded buses</span></label>
          <label class="profile-choice"><input type="radio" name="crowd-style" value="balanced"/><span>No strong preference</span></label>
          <label class="profile-choice"><input type="radio" name="crowd-style" value="fastest"/><span>Fastest ride only</span></label>
        </div>
      </div>

      <div class="profile-group">
        <label class="profile-label" for="profile-max-wait">Maximum wait you are usually okay with</label>
        <select id="profile-max-wait" class="profile-select">
          <option value="5">5 minutes</option>
          <option value="10">10 minutes</option>
          <option value="15">15 minutes</option>
          <option value="20">20 minutes</option>
          <option value="30">30 minutes</option>
        </select>
      </div>

      <div class="profile-group">
        <label class="profile-label" for="profile-route">Preferred route</label>
        <select id="profile-route" class="profile-select">
          <option value="">No strong preference</option>
          <option value="Comm Ave All Stops">Comm Ave All Stops</option>
          <option value="Newton Campus Express">Newton Campus Express</option>
        </select>
      </div>

      <div class="profile-group">
        <div class="profile-label">Class schedule</div>
        <div class="profile-help">Upload an image so the assistant can help with class-specific shuttle planning.</div>
        <div id="profile-schedule-status" class="profile-help">No schedule uploaded yet.</div>
        <div class="profile-actions" style="justify-content:flex-start;padding-top:0;">
          <button class="profile-secondary" onclick="document.getElementById('schedule-file').click()">Upload schedule</button>
          <button class="profile-secondary" onclick="clearSchedule()">Remove schedule</button>
        </div>
      </div>

      <div class="profile-actions profile-footer-actions">
        <button class="profile-delete" onclick="deleteProfile()">🗑 Delete profile</button>
        <button class="profile-secondary" onclick="closeProfileModal()">Cancel</button>
        <button class="profile-save" onclick="saveProfile()">Save profile</button>
      </div>
    </div>
  </div>
</div>
<div id="toast"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
// ── helpers ──────────────────────────────────────────────────────────────────
function nearestStopProgress(route, name) { return route.stop_progress[name]; }
function nextStopName(route, progress, inclusive) {
  inclusive = (inclusive === undefined) ? true : inclusive;
  for (var i = 0; i < route.ordered_stop_names.length; i++) {
    var name = route.ordered_stop_names[i];
    if (inclusive) { if (route.stop_progress[name] >= progress - 1e-6) return name; }
    else if (route.stop_progress[name] > progress + 1e-6) return name;
  }
  return route.ordered_stop_names[0];
}
function crossedStop(cur, nxt, sp) {
  if (cur <= nxt) return sp > cur + 1e-6 && sp <= nxt + 1e-6;
  return sp > cur + 1e-6 || sp <= nxt + 1e-6;
}
function positionAtProgress(route, progress) {
  var target = ((progress % 1) + 1) % 1 * route.total_length;
  for (var i = 0; i < route.segment_lengths.length; i++) {
    if (target <= route.cumulative[i+1] || i === route.segment_lengths.length - 1) {
      var ratio = route.segment_lengths[i] === 0 ? 0
        : (target - route.cumulative[i]) / route.segment_lengths[i];
      var s = route.path[i], e = route.path[i+1];
      return [s[0]+(e[0]-s[0])*ratio, s[1]+(e[1]-s[1])*ratio];
    }
  }
  return route.path[route.path.length-1];
}
function stopDwell(name) {
  if (name.charAt(0)==='A'||name.charAt(0)==='G'||name.charAt(0)==='M') return 35;
  if (name.charAt(0)==='D'||name.charAt(0)==='J') return 25;
  return 18;
}
function projectedCapacityAtStop(shuttle, stopName) {
  // If a rider reported the capacity for this specific stop, use that directly
  if (shuttle._reported_cap_at && shuttle._reported_cap_at[stopName] !== undefined) {
    return shuttle._reported_cap_at[stopName];
  }
  var route = mapPayload.routes[shuttle.route];
  var targetProg = route.stop_progress[stopName];
  if (targetProg === undefined) return shuttle.capacity_pct;
  var deltaToTarget = (targetProg - shuttle.progress + 1) % 1;
  var projected = shuttle.capacity_pct;
  // Accumulate capacity changes for every stop the shuttle passes through
  // BEFORE reaching the target stop (excludes the target itself so we show
  // capacity as the bus arrives — before riders at that stop board/alight).
  Object.entries(route.stop_progress).forEach(function(entry) {
    var sName = entry[0], sProg = entry[1];
    var deltaToStop = (sProg - shuttle.progress + 1) % 1;
    if (deltaToStop > 0.001 && deltaToStop < deltaToTarget - 0.001) {
      projected += (STOP_CAP_DELTA[sName] || 0);
    }
  });
  return Math.max(5, Math.min(95, Math.round(projected)));
}

function arrivalsForStop(stopName) {
  return (shuttles||[])
    .filter(function(s){ return mapPayload.routes[s.route].stop_progress[stopName] !== undefined; })
    .map(function(s) {
      var route = mapPayload.routes[s.route];
      var sp    = route.stop_progress[stopName];
      var delta = (sp - s.progress + 1) % 1;
      var miles = delta * route.total_length;
      var eta   = Math.max(1, Math.round(miles / Math.max(s.speed_mph,1) * 60));
      // Project capacity accounting for boarding/alighting at intermediate stops
      var projCap = projectedCapacityAtStop(s, stopName);
      var shuttleAtStop = Object.assign({}, s, {
        capacity_pct: projCap,
        capacity: projCap >= 85 ? 'Full' : projCap >= 60 ? 'Medium' : 'Empty'
      });
      return {shuttle: shuttleAtStop, etaMinutes: Math.max(1, eta + (s.delay_minutes||0))};
    })
    .sort(function(a,b){ return a.etaMinutes - b.etaMinutes; });
}

function routeProgressDelta(routeName, fromStopName, toStopName) {
  var route = mapPayload.routes[routeName];
  if (!route || route.stop_progress[fromStopName] === undefined || route.stop_progress[toStopName] === undefined) return null;
  return (route.stop_progress[toStopName] - route.stop_progress[fromStopName] + 1) % 1;
}

function routeNamesForStop(stopName) {
  return routeEntries
    .filter(function(entry) { return entry[1].stop_progress[stopName] !== undefined; })
    .map(function(entry) { return entry[0]; });
}

function stopCoords(stopName) {
  for (var i = 0; i < routeEntries.length; i++) {
    var stops = routeEntries[i][1].stops;
    for (var j = 0; j < stops.length; j++) {
      if (stops[j].name === stopName) return [stops[j].lat, stops[j].lon];
    }
  }
  return [mapPayload.selected_coords.lat, mapPayload.selected_coords.lon];
}

function capacityPeopleHtml(capacityPct) {
  var filled = Math.max(1, Math.min(5, Math.round(capacityPct / 20)));
  var people = '';
  for (var i = 0; i < 5; i++) {
    people += '<span class="capacity-person'+(i < filled ? ' active' : '')+'" aria-hidden="true"></span>';
  }
  return '<div class="capacity-people" style="color:#2563eb;">'+people+'</div>';
}

// ── fit everything to the actual window height ────────────────────────────────
function applyHeight() {
  var h = window.innerHeight;
  try {
    if (window.parent && window.parent !== window && window.parent.innerHeight) {
      var parentFrame = window.frameElement;
      var frameTop = parentFrame ? parentFrame.getBoundingClientRect().top : 0;
      h = Math.min(h, Math.max(420, window.parent.innerHeight - frameTop));
    }
  } catch (error) {
    // Cross-frame sizing is best-effort; fall back to the iframe viewport.
  }
  var bannerEl = document.getElementById('loc-banner');
  var headerEl = document.getElementById('map-header');
  var bannerH = (bannerEl && bannerEl.offsetHeight > 0) ? bannerEl.offsetHeight : 0;
  var headerH = (headerEl && headerEl.offsetHeight > 0) ? headerEl.offsetHeight : 44;
  var mapH = h - headerH - bannerH;
  document.getElementById('app').style.height      = h + 'px';
  document.getElementById('ai-panel').style.height = h + 'px';
  document.getElementById('drag-handle').style.height = h + 'px';
  document.getElementById('map-panel').style.height   = h + 'px';
  document.getElementById('map-body').style.height    = mapH + 'px';
  document.getElementById('map-wrap').style.height    = mapH + 'px';
  document.getElementById('map').style.height         = mapH + 'px';
  document.getElementById('route-side').style.height  = mapH + 'px';
  if (typeof leafletMap !== 'undefined' && leafletMap) {
    leafletMap.invalidateSize();
  }
}
applyHeight();
window.addEventListener('resize', applyHeight);
window.addEventListener('resize', function() {
  if (isTourActive()) renderTourStep();
});

if (!SHOW_AI_PANEL) {
  document.getElementById('ai-panel').style.display = 'none';
  document.getElementById('drag-handle').style.display = 'none';
}

// ── drag handle ──────────────────────────────────────────────────────────────
var handle  = document.getElementById('drag-handle');
var aiPanel = document.getElementById('ai-panel');
var dragging = false;
handle.addEventListener('mousedown', function(e){ dragging=true; handle.classList.add('dragging'); e.preventDefault(); });
document.addEventListener('mousemove', function(e){
  if (!dragging) return;
  var rect = document.getElementById('app').getBoundingClientRect();
  var w = Math.max(260, Math.min(rect.width - 320, e.clientX - rect.left));
  aiPanel.style.width = w + 'px';
});
document.addEventListener('mouseup', function(){ dragging=false; handle.classList.remove('dragging'); });

// ── chat ─────────────────────────────────────────────────────────────────────
var selectedStop = mapPayload.selected_stop;
var destinationStop = mapPayload.destination_stop || selectedStop;
var dismissedAlertKey = '';
var hasUserSelectedStopManually = false;
var hasAutoSelectedNearestStop = false;
var stopSectionVisible = false; // hidden until user actively selects a stop
var chatHistory = Array.isArray(AI_CHAT_HISTORY) ? AI_CHAT_HISTORY.slice() : [];
var userSchedule = null; // parsed schedule text extracted from uploaded image
var userScheduleEntries = []; // structured entries extracted from uploaded image
var userProfile = {
  nickname: '',
  timing_style: 'balanced',
  crowd_style: 'balanced',
  max_wait_minutes: '10',
  preferred_route: ''
};

function escapeHtml(text) {
  return String(text).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

var tourIndex = -1;
var tourSteps = [
  {
    selector: '#route-side',
    title: 'Start with the right panel',
    body: function() {
      return userLatLng
        ? 'The first two prediction cards at the top are based on your current location, so they surface the best nearby boarding options first. Use them when you want the quickest next step without scanning the whole map.'
        : 'Once you allow location access, the first two prediction cards at the top of this panel are based on your current location. They become your quickest way to see the best nearby boarding options.'
    },
    placement: 'left'
  },
  {
    selector: '#map',
    title: 'Use the map to inspect stops and buses',
    body: 'Click any stop on the map to select it and see upcoming buses for that stop. Click a moving bus marker to open its live details, including current capacity. You can also use the route buttons in the right panel to focus on one route, then click any stop along that line.',
    placement: 'bottom'
  },
  {
    selector: '#locate-btn',
    title: 'Let the app find your nearest stop',
    body: 'Click the location button to center the map on you and automatically set Your stop to the nearest shuttle stop based on your current GPS location.',
    placement: 'bottom'
  },
  {
    selector: '#ai-panel',
    title: 'Ask the AI for personalized help',
    body: 'The AI panel on the left can answer personalized questions about timing, crowding, route choice, and what shuttle you should take right now. The suggestions update as your selected stop and location change.',
    placement: 'right'
  },
  {
    selector: '#profile-btn',
    title: 'Add your habits in Profile',
    body: 'Open Profile to add details like your name, timing style, crowding preference, and class schedule. The more context you add, the better the AI can tailor recommendations to your routine.',
    placement: 'bottom'
  }
];

function getTourStorageKey() {
  return 'bc_shuttle_guided_tour_v2';
}

function isTourActive() {
  return tourIndex >= 0;
}

function resolveTourStepBody(step) {
  return typeof step.body === 'function' ? step.body() : step.body;
}

function getTourTarget(step) {
  if (!step || !step.selector) return null;
  return document.querySelector(step.selector);
}

function positionTourCard(targetRect, placement) {
  var card = document.getElementById('tour-card');
  var margin = 18;
  var cardWidth = Math.min(360, window.innerWidth - 32);
  card.style.width = cardWidth + 'px';
  var cardHeight = card.offsetHeight || 220;
  var left = targetRect.left;
  var top = targetRect.bottom + margin;

  if (placement === 'left') {
    left = targetRect.left - cardWidth - margin;
    top = targetRect.top;
  } else if (placement === 'right') {
    left = targetRect.right + margin;
    top = targetRect.top;
  } else if (placement === 'top') {
    left = targetRect.left;
    top = targetRect.top - cardHeight - margin;
  }

  if (left + cardWidth > window.innerWidth - 16) left = window.innerWidth - cardWidth - 16;
  if (left < 16) left = 16;
  if (top + cardHeight > window.innerHeight - 16) top = window.innerHeight - cardHeight - 16;
  if (top < 16) top = 16;

  card.style.left = left + 'px';
  card.style.top = top + 'px';
}

function renderTourStep() {
  if (!isTourActive()) return;
  var step = tourSteps[tourIndex];
  var target = getTourTarget(step);
  if (!target) {
    stopTour();
    return;
  }

  var highlight = document.getElementById('tour-highlight');
  var overlay = document.getElementById('tour-overlay');
  var card = document.getElementById('tour-card');
  var rect = target.getBoundingClientRect();
  var padding = step.selector === '#profile-btn' ? 8 : 12;

  overlay.classList.add('active');
  highlight.classList.add('active');
  card.classList.add('active');

  highlight.style.left = Math.max(8, rect.left - padding) + 'px';
  highlight.style.top = Math.max(8, rect.top - padding) + 'px';
  highlight.style.width = Math.min(window.innerWidth - 16, rect.width + padding * 2) + 'px';
  highlight.style.height = Math.min(window.innerHeight - 16, rect.height + padding * 2) + 'px';

  document.getElementById('tour-step').textContent = 'Step ' + (tourIndex + 1) + ' of ' + tourSteps.length;
  document.getElementById('tour-title').textContent = step.title;
  document.getElementById('tour-body').textContent = resolveTourStepBody(step);
  document.getElementById('tour-back').style.visibility = tourIndex === 0 ? 'hidden' : 'visible';
  document.getElementById('tour-next').textContent = tourIndex === tourSteps.length - 1 ? 'Finish' : 'Next';

  positionTourCard(rect, step.placement || 'bottom');
}

function startTour(isManual) {
  closeProfileModal();
  if (!isManual) {
    try {
      if (localStorage.getItem(getTourStorageKey()) === 'done') return;
    } catch (error) {
      console.warn('Could not read guided-tour state', error);
    }
  }
  tourIndex = 0;
  renderTourStep();
}

function stopTour() {
  tourIndex = -1;
  document.getElementById('tour-overlay').classList.remove('active');
  document.getElementById('tour-highlight').classList.remove('active');
  document.getElementById('tour-card').classList.remove('active');
  try {
    localStorage.setItem(getTourStorageKey(), 'done');
  } catch (error) {
    console.warn('Could not persist guided-tour state', error);
  }
}

function nextTourStep() {
  if (!isTourActive()) return;
  if (tourIndex >= tourSteps.length - 1) {
    stopTour();
    return;
  }
  tourIndex += 1;
  renderTourStep();
}

function previousTourStep() {
  if (!isTourActive() || tourIndex === 0) return;
  tourIndex -= 1;
  renderTourStep();
}

function personalizedIntro() {
  return userProfile.nickname && userProfile.nickname.trim()
    ? userProfile.nickname.trim() + ', '
    : '';
}

function preferredRouteText() {
  return userProfile.preferred_route || 'the best route';
}

function parseDaysFromScheduleLine(line) {
  var dayTokens = [];
  var patterns = [
    {name: 'Sunday', aliases: ['sun', 'sunday', 'su']},
    {name: 'Monday', aliases: ['mon', 'monday', 'm']},
    {name: 'Tuesday', aliases: ['tue', 'tues', 'tuesday', 'tu']},
    {name: 'Wednesday', aliases: ['wed', 'wednesday', 'w']},
    {name: 'Thursday', aliases: ['thu', 'thur', 'thurs', 'thursday', 'th']},
    {name: 'Friday', aliases: ['fri', 'friday', 'f']},
    {name: 'Saturday', aliases: ['sat', 'saturday', 'sa']}
  ];
  var lower = line.toLowerCase();

  patterns.forEach(function(pattern) {
    if (pattern.aliases.some(function(alias) {
      return new RegExp('(^|[^a-z])' + alias + '([^a-z]|$)').test(lower);
    })) {
      dayTokens.push(pattern.name);
    }
  });

  if (!dayTokens.length) {
    var compactMatch = line.match(/\b(MWF|TR|TTH|MW|WF|MTWTHF)\b/i);
    if (compactMatch) {
      var compact = compactMatch[1].toUpperCase();
      if (compact === 'MWF') dayTokens = ['Monday', 'Wednesday', 'Friday'];
      else if (compact === 'MW') dayTokens = ['Monday', 'Wednesday'];
      else if (compact === 'WF') dayTokens = ['Wednesday', 'Friday'];
      else if (compact === 'TR' || compact === 'TTH') dayTokens = ['Tuesday', 'Thursday'];
      else if (compact === 'MTWTHF') dayTokens = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
    }
  }

  return dayTokens;
}

function easternDateTimeLabel() {
  return new Date().toLocaleString('en-US', {
    timeZone: 'America/New_York',
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short'
  });
}

function easternNow() {
  return new Date(new Date().toLocaleString('en-US', {timeZone: 'America/New_York'}));
}

function parseStartTimeMinutes(line) {
  var match = line.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*[–-]\s*\d{1,2}(?::\d{2})?\s*(am|pm)/i)
    || line.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)/i);
  if (!match) return null;

  var hour = parseInt(match[1], 10);
  var minute = parseInt(match[2] || '0', 10);
  var meridiem = match[3].toLowerCase();
  if (meridiem === 'pm' && hour !== 12) hour += 12;
  if (meridiem === 'am' && hour === 12) hour = 0;
  return hour * 60 + minute;
}

function parseClockTimeMinutes(value) {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (!value) return null;
  var match = String(value).match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
  if (!match) return null;
  var hour = parseInt(match[1], 10);
  var minute = parseInt(match[2] || '0', 10);
  var meridiem = match[3] ? match[3].toLowerCase() : '';
  if (meridiem === 'pm' && hour !== 12) hour += 12;
  if (meridiem === 'am' && hour === 12) hour = 0;
  if (!meridiem && hour < 7) hour += 12;
  return hour * 60 + minute;
}

function parseCourseName(line) {
  var parts = line.split(',').map(function(part) { return part.trim(); }).filter(Boolean);
  if (parts.length >= 3) return parts[2];
  if (parts.length >= 2) return parts[parts.length - 1];
  return line.trim();
}

function normalizeScheduleEntry(entry) {
  if (!entry || typeof entry !== 'object') return null;
  var rawDays = parseDaysFromScheduleLine(entry.raw || '');
  var days = rawDays.length
    ? rawDays
    : Array.isArray(entry.days)
      ? entry.days
      : [];
  var startMinutes = entry.start_minutes;
  if (startMinutes === undefined || startMinutes === null) {
    startMinutes = parseClockTimeMinutes(entry.start_time);
    if (startMinutes === null || startMinutes === undefined) {
      startMinutes = parseStartTimeMinutes(entry.raw || '');
    }
  }
  var course = entry.course || entry.course_name || entry.title || parseCourseName(entry.raw || '');
  var location = entry.location || entry.room || '';
  if (!days.length || startMinutes === null || startMinutes === undefined) return null;
  return {
    raw: entry.raw || [days.join('/'), entry.start_time || '', course, location].filter(Boolean).join(', '),
    days: days,
    startMinutes: startMinutes,
    course: course,
    location: location
  };
}

function parseScheduleEntries() {
  if (Array.isArray(userScheduleEntries) && userScheduleEntries.length) {
    return userScheduleEntries
      .map(normalizeScheduleEntry)
      .filter(Boolean);
  }
  if (!userSchedule) return [];
  return userSchedule
    .split('\n')
    .map(function(line) { return line.trim(); })
    .filter(Boolean)
    .map(function(line) {
      return {
        raw: line,
        days: parseDaysFromScheduleLine(line),
        startMinutes: parseStartTimeMinutes(line),
        course: parseCourseName(line),
        location: ''
      };
    })
    .filter(function(entry) {
      return entry.days.length && entry.startMinutes !== null;
    });
}

function nextScheduledClass() {
  var entries = parseScheduleEntries();
  if (!entries.length) return null;

  var dayIndex = {
    Sunday: 0,
    Monday: 1,
    Tuesday: 2,
    Wednesday: 3,
    Thursday: 4,
    Friday: 5,
    Saturday: 6
  };

  var now = easternNow();
  var best = null;

  entries.forEach(function(entry) {
    entry.days.forEach(function(dayName) {
      var candidate = new Date(now);
      var offset = (dayIndex[dayName] - now.getDay() + 7) % 7;
      candidate.setDate(now.getDate() + offset);
      candidate.setHours(Math.floor(entry.startMinutes / 60), entry.startMinutes % 60, 0, 0);
      if (candidate <= now) candidate.setDate(candidate.getDate() + 7);

      if (!best || candidate < best.when) {
        best = {
          when: candidate,
          dayName: dayName,
          course: entry.course,
          location: entry.location || '',
          raw: entry.raw
        };
      }
    });
  });

  return best;
}

function formatClassTimeLabel(date) {
  return date.toLocaleTimeString('en-US', {hour: 'numeric', minute: '2-digit'});
}

function relativeClassDayLabel(date) {
  var now = easternNow();
  var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  var target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  var diffDays = Math.round((target - today) / 86400000);
  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'tomorrow';
  return date.toLocaleDateString('en-US', {weekday: 'long'});
}

function getProfileStorageKey() {
  return 'bc_shuttle_user_profile_v1';
}

function getScheduleStorageKey() {
  return 'bc_shuttle_schedule_text_v1';
}

function getScheduleEntriesStorageKey() {
  return 'bc_shuttle_schedule_entries_v1';
}

function getUserIdStorageKey() {
  return 'bc_shuttle_user_id_v1';
}

function ensureUserId() {
  var existing = localStorage.getItem(getUserIdStorageKey());
  if (existing) return existing;
  var generated = (window.crypto && window.crypto.randomUUID)
    ? window.crypto.randomUUID()
    : 'user-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 10);
  localStorage.setItem(getUserIdStorageKey(), generated);
  return generated;
}

function supabaseEnabled() {
  return Boolean(SUPABASE_CONFIG && SUPABASE_CONFIG.enabled && SUPABASE_CONFIG.url && SUPABASE_CONFIG.anonKey);
}

function setProfileSyncStatus(message, state) {
  var el = document.getElementById('profile-sync-status');
  if (!el) return;
  el.textContent = message;
  el.className = 'profile-sync' + (state ? ' ' + state : '');
}

function summarizeSupabaseError(error) {
  var raw = error && error.message ? error.message : String(error || 'Unknown error');
  try {
    var parsed = JSON.parse(raw);
    if (parsed.message) return parsed.message;
    if (parsed.hint) return parsed.hint;
  } catch (parseError) {
    // Supabase sometimes returns plain text or an empty body.
  }
  return raw.length > 160 ? raw.slice(0, 157) + '...' : raw;
}

async function supabaseRequest(path, options) {
  if (!supabaseEnabled()) return null;
  var resp;
  try {
    var requestUrl = new URL(path, SUPABASE_CONFIG.url.replace(/\/+$/, '') + '/rest/v1/').toString();
    var headers = Object.assign({
      apikey: SUPABASE_CONFIG.anonKey,
      'Content-Type': 'application/json'
    }, (options && options.headers) || {});
    resp = await fetch(requestUrl, Object.assign({}, options || {}, {headers: headers}));
  } catch (error) {
    throw new Error('Supabase browser request failed for ' + path + ': ' + error.message);
  }
  if (!resp.ok) {
    var text = await resp.text();
    throw new Error(text || ('Supabase request failed with status ' + resp.status));
  }
  if (resp.status === 204) return null;
  var responseText = await resp.text();
  return responseText ? JSON.parse(responseText) : null;
}

function readLocalProfile() {
  try {
    var saved = localStorage.getItem(getProfileStorageKey());
    if (saved) {
      var parsed = JSON.parse(saved);
      userProfile = Object.assign({}, userProfile, parsed || {});
    }
  } catch (error) {
    console.warn('Could not restore user profile', error);
  }

  try {
    var savedSchedule = localStorage.getItem(getScheduleStorageKey());
    if (savedSchedule) userSchedule = savedSchedule;
    var savedScheduleEntries = localStorage.getItem(getScheduleEntriesStorageKey());
    if (savedScheduleEntries) userScheduleEntries = JSON.parse(savedScheduleEntries) || [];
  } catch (error) {
    console.warn('Could not restore schedule data', error);
  }
}

async function loadProfileFromSupabase(userId) {
  if (!supabaseEnabled()) return false;
  var profileRows = await supabaseRequest(
    'user_profiles?user_id=eq.' + encodeURIComponent(userId) + '&select=*',
    {method: 'GET'}
  );
  var scheduleRows = await supabaseRequest(
    'user_schedules?user_id=eq.' + encodeURIComponent(userId) + '&select=*',
    {method: 'GET'}
  );
  var remoteProfile = Array.isArray(profileRows) ? profileRows[0] : null;
  var remoteSchedule = Array.isArray(scheduleRows) ? scheduleRows[0] : null;

  if (remoteProfile) {
    userProfile = Object.assign({}, userProfile, {
      nickname: remoteProfile.nickname || '',
      timing_style: remoteProfile.timing_style || 'balanced',
      crowd_style: remoteProfile.crowd_style || 'balanced',
      max_wait_minutes: String(remoteProfile.max_wait_minutes || '10'),
      preferred_route: remoteProfile.preferred_route || ''
    });
  }
  if (remoteSchedule) {
    userSchedule = remoteSchedule.raw_text || null;
    userScheduleEntries = Array.isArray(remoteSchedule.parsed_entries) ? remoteSchedule.parsed_entries : [];
  }

  return Boolean(remoteProfile || remoteSchedule);
}

async function loadProfile() {
  readLocalProfile();
  var userId = ensureUserId();
  if (!supabaseEnabled()) {
    setProfileSyncStatus('Cloud sync is off. Check SUPABASE_URL and SUPABASE_ANON_KEY in Streamlit secrets.', 'warn');
    return;
  }
  try {
    var loadedRemote = await loadProfileFromSupabase(userId);
    if (loadedRemote) {
      writeLocalProfile();
      setProfileSyncStatus('Cloud sync connected. Loaded profile from Supabase.', 'ok');
    } else if (userProfile.nickname || userSchedule) {
      await saveProfileToSupabase(userId);
      setProfileSyncStatus('Cloud sync connected. Local profile copied to Supabase.', 'ok');
    } else {
      setProfileSyncStatus('Cloud sync connected. No saved profile yet.', 'ok');
    }
  } catch (error) {
    console.warn('Could not restore Supabase profile; using local profile', error);
    setProfileSyncStatus('Cloud sync failed: ' + summarizeSupabaseError(error), 'warn');
  }
}

function writeLocalProfile() {
  localStorage.setItem(getProfileStorageKey(), JSON.stringify(userProfile));
  if (userSchedule) {
    localStorage.setItem(getScheduleStorageKey(), userSchedule);
  } else {
    localStorage.removeItem(getScheduleStorageKey());
  }
  if (Array.isArray(userScheduleEntries) && userScheduleEntries.length) {
    localStorage.setItem(getScheduleEntriesStorageKey(), JSON.stringify(userScheduleEntries));
  } else {
    localStorage.removeItem(getScheduleEntriesStorageKey());
  }
}

async function saveProfileToSupabase(userId) {
  if (!supabaseEnabled()) return;
  var now = new Date().toISOString();
  await supabaseRequest('user_profiles?on_conflict=user_id', {
    method: 'POST',
    headers: {Prefer: 'resolution=merge-duplicates'},
    body: JSON.stringify({
      user_id: userId,
      nickname: userProfile.nickname || null,
      timing_style: userProfile.timing_style || 'balanced',
      crowd_style: userProfile.crowd_style || 'balanced',
      max_wait_minutes: parseInt(userProfile.max_wait_minutes || '10', 10),
      preferred_route: userProfile.preferred_route || null,
      updated_at: now
    })
  });

  if (userSchedule) {
    await supabaseRequest('user_schedules?on_conflict=user_id', {
      method: 'POST',
      headers: {Prefer: 'resolution=merge-duplicates'},
      body: JSON.stringify({
        user_id: userId,
        raw_text: userSchedule,
        parsed_entries: Array.isArray(userScheduleEntries) ? userScheduleEntries : [],
        updated_at: now
      })
    });
  } else {
    await supabaseRequest('user_schedules?user_id=eq.' + encodeURIComponent(userId), {method: 'DELETE'});
  }
}

async function deleteProfileAndScheduleFromSupabase(userId) {
  if (!supabaseEnabled()) return;
  await supabaseRequest('user_schedules?user_id=eq.' + encodeURIComponent(userId), {method: 'DELETE'});
  await supabaseRequest('user_profiles?user_id=eq.' + encodeURIComponent(userId), {method: 'DELETE'});
}

function saveProfileToStorage() {
  writeLocalProfile();
  if (!supabaseEnabled()) {
    setProfileSyncStatus('Saved locally. Cloud sync is off because Supabase secrets are missing.', 'warn');
    return Promise.resolve(false);
  }
  setProfileSyncStatus('Saving profile to Supabase...', '');
  return saveProfileToSupabase(ensureUserId())
    .then(function() {
      setProfileSyncStatus('Cloud sync saved just now.', 'ok');
      showToast('Profile saved to Supabase', 'success');
      return true;
    })
    .catch(function(error) {
      var reason = summarizeSupabaseError(error);
      console.warn('Could not sync profile to Supabase', error);
      setProfileSyncStatus('Cloud sync failed: ' + reason, 'warn');
      showToast('Profile saved locally; cloud sync failed', 'warn');
      return false;
    });
}

function currentNickname() {
  return userProfile.nickname && userProfile.nickname.trim() ? userProfile.nickname.trim() : 'Your profile';
}

function currentInitials() {
  var name = currentNickname();
  if (name === 'Your profile') return 'BC';
  return name.split(/\s+/).slice(0, 2).map(function(part) { return part.charAt(0).toUpperCase(); }).join('');
}

function syncProfileUi() {
  document.getElementById('profile-name').textContent = currentNickname();
  document.getElementById('profile-avatar').textContent = currentInitials();
  document.getElementById('profile-nickname').value = userProfile.nickname || '';
  document.getElementById('profile-max-wait').value = String(userProfile.max_wait_minutes || '10');
  document.getElementById('profile-route').value = userProfile.preferred_route || '';

  document.querySelectorAll('input[name="timing-style"]').forEach(function(input) {
    input.checked = input.value === (userProfile.timing_style || 'balanced');
  });
  document.querySelectorAll('input[name="crowd-style"]').forEach(function(input) {
    input.checked = input.value === (userProfile.crowd_style || 'balanced');
  });

  var scheduleStatus = document.getElementById('profile-schedule-status');
  if (userSchedule) {
    var parsedCount = parseScheduleEntries().length;
    scheduleStatus.textContent = parsedCount
      ? 'Schedule uploaded with ' + parsedCount + ' parsed classes for recommendations.'
      : 'Schedule uploaded; the assistant will use the extracted text.';
    document.getElementById('schedule-label').textContent = parsedCount
      ? 'Schedule loaded: ' + parsedCount + ' classes'
      : 'Schedule loaded';
    document.getElementById('schedule-badge').style.display = 'flex';
  } else {
    scheduleStatus.textContent = 'No schedule uploaded yet.';
    document.getElementById('schedule-badge').style.display = 'none';
  }

}

function openProfileModal() {
  syncProfileUi();
  document.getElementById('profile-modal-backdrop').classList.add('open');
}

function closeProfileModal() {
  document.getElementById('profile-modal-backdrop').classList.remove('open');
}

function handleProfileBackdrop(event) {
  if (event.target.id === 'profile-modal-backdrop') closeProfileModal();
}

// ── toast notifications ───────────────────────────────────────────────────────
var _toastTimer = null;
function showToast(msg, type) {
  var el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = 'show' + (type ? ' t-' + type : '');
  if (_toastTimer) clearTimeout(_toastTimer);
  _toastTimer = setTimeout(function() { el.className = ''; }, 3200);
}

function saveProfile() {
  var timingChoice = document.querySelector('input[name="timing-style"]:checked');
  var crowdChoice = document.querySelector('input[name="crowd-style"]:checked');
  var isNew = !userProfile.nickname;
  userProfile.nickname = document.getElementById('profile-nickname').value.trim();
  userProfile.timing_style = timingChoice ? timingChoice.value : 'balanced';
  userProfile.crowd_style = crowdChoice ? crowdChoice.value : 'balanced';
  userProfile.max_wait_minutes = document.getElementById('profile-max-wait').value;
  userProfile.preferred_route = document.getElementById('profile-route').value;
  saveProfileToStorage();
  syncProfileUi();
  renderSuggestedQuestions();
  renderProactiveAlert();
  closeProfileModal();
  showToast(isNew ? '✅ Rider profile created' : '✅ Rider profile updated', 'success');
}

function deleteProfile() {
  if (!confirm('Delete your rider profile and uploaded class schedule? This cannot be undone.')) return;
  userProfile = {timing_style:'balanced', crowd_style:'balanced', max_wait_minutes:10, preferred_route:'', nickname:''};
  userSchedule = null;
  userScheduleEntries = [];
  document.getElementById('schedule-file').value = '';
  writeLocalProfile();
  deleteProfileAndScheduleFromSupabase(ensureUserId()).catch(function(error) {
    console.warn('Could not delete Supabase profile and schedule', error);
    showToast('Profile and schedule cleared locally; cloud delete failed', 'warn');
  });
  syncProfileUi();
  renderSuggestedQuestions();
  renderProactiveAlert();
  closeProfileModal();
  showToast('🗑️ Rider profile and schedule deleted', 'warn');
}

function profileSummaryLines() {
  var lines = [];
  if (userProfile.nickname) lines.push('Nickname: ' + userProfile.nickname);
  if (userProfile.timing_style === 'early') lines.push('Timing preference: prefers leaving early and avoiding lateness.');
  else if (userProfile.timing_style === 'procrastinate') lines.push('Timing preference: tends to leave later and values procrastination time.');
  else lines.push('Timing preference: balanced.');

  if (userProfile.crowd_style === 'avoid_crowds') lines.push('Crowding preference: prefers less crowded buses.');
  else if (userProfile.crowd_style === 'fastest') lines.push('Crowding preference: prioritizes the fastest ride over comfort.');
  else lines.push('Crowding preference: balanced.');

  lines.push('Typical max wait: ' + userProfile.max_wait_minutes + ' minutes.');
  if (userProfile.preferred_route) lines.push('Preferred route: ' + userProfile.preferred_route + '.');
  return lines;
}

function nextClassLabel(nextClass) {
  if (!nextClass) return 'my next class';
  var parts = [
    formatClassTimeLabel(nextClass.when),
    relativeClassDayLabel(nextClass.when),
    nextClass.course || 'class'
  ];
  if (nextClass.location) parts.push('at ' + nextClass.location);
  return parts.join(' ');
}

function lastAssistantMessage() {
  for (var i = chatHistory.length - 1; i >= 0; i--) {
    if (chatHistory[i] && chatHistory[i].role === 'assistant') return chatHistory[i];
  }
  return null;
}

function followUpSuggestionsFromLastResponse(nextClass, needsDestination) {
  var last = lastAssistantMessage();
  if (!last) return [];
  var text = String(last.content || last.display || '').toLowerCase();
  var suggestions = [];

  if (text.indexOf('check the shuttle schedule') !== -1 || text.indexOf('closer to that time') !== -1 || text.indexOf('that time') !== -1) {
    suggestions.push("Check the shuttle schedule for that time.");
    suggestions.push("Which shuttle should I plan to catch then?");
    suggestions.push("What time should I leave if I want a safer buffer?");
  }

  if (text.indexOf('destination') !== -1 || needsDestination) {
    suggestions.push("Which destination should I set for my next class?");
  }

  if (nextClass && (text.indexOf('next class') !== -1 || text.indexOf('leave') !== -1)) {
    suggestions.push("How confident are you about that leave time?");
    suggestions.push("What if I want to arrive 10 minutes early?");
  }

  return suggestions;
}

function buildSuggestedQuestions() {
  var suggestions = [];
  var intro = personalizedIntro();
  var maxWait = String(userProfile.max_wait_minutes || '10');
  var preferredRoute = preferredRouteText();
  var nextClass = nextScheduledClass();
  var nextClassDay = nextClass ? relativeClassDayLabel(nextClass.when) : '';
  var nextClassTime = nextClass ? formatClassTimeLabel(nextClass.when) : '';
  var nextClassCourse = nextClass && nextClass.course ? nextClass.course : 'class';
  var nextClassText = nextClassLabel(nextClass);
  var needsDestination = selectedStop === destinationStop;
  followUpSuggestionsFromLastResponse(nextClass, needsDestination).forEach(function(question) {
    suggestions.push(question);
  });

  if (userSchedule) {
    if (nextClass) {
      suggestions.push("When should I leave for my next class?");
      suggestions.push("Which shuttle gets me there with the safest buffer?");
      if (needsDestination) {
        suggestions.push("Which destination should I set for my next class?");
      } else {
        suggestions.push("Which shuttle should I take for my next class?");
      }
      suggestions.push("Can you plan the safest shuttle option for my next class?");
    } else {
      suggestions.push("Can you use my uploaded schedule to plan my next class commute?");
      suggestions.push("Which class in my schedule should I plan around next?");
      suggestions.push("Can you summarize my shuttle plan from my uploaded schedule?");
    }
  }

  if (needsDestination) {
    suggestions.push("Which destination stop should I choose for my trip?");
    suggestions.push("What stops can I travel to from here?");
    suggestions.push("How do I update my destination?");
    return suggestions.filter(function(item, index, arr) {
      return item && arr.indexOf(item) === index;
    }).slice(0, 4);
  }

  // Surface location-based help after any schedule-aware prompts.
  if (userLatLng) {
    suggestions.push("Based on my current location, which shuttle should I take to " + destinationStop + " right now?");
  }

  if (!chatHistory.length) {
    if (nextClass && !userSchedule) {
      suggestions.push(
        "Do you want me to help plan when to leave for your " + nextClassTime + " " + nextClassDay + " " + nextClassCourse + "?"
      );
    }

    if (userProfile.timing_style === 'early') {
      suggestions.push(intro + "which shuttle should I take from " + selectedStop + " to " + destinationStop + " if I never want to be late?");
      suggestions.push("Which option gives me the safest arrival buffer for my next trip?");
    } else if (userProfile.timing_style === 'procrastinate') {
      suggestions.push(intro + "what is the latest shuttle I can take from " + selectedStop + " to " + destinationStop + " without cutting it too close?");
      suggestions.push("Can you help me leave as late as possible but still make it on time?");
    } else {
      suggestions.push("The next shuttle is running late");
      suggestions.push("What's the capacity of the next shuttle?");
    }

    if (userProfile.crowd_style === 'avoid_crowds') {
      suggestions.push("I would rather wait up to " + maxWait + " minutes for a less crowded bus. What should I take?");
    } else if (userProfile.crowd_style === 'fastest') {
      suggestions.push("I care more about speed than crowding. What is the fastest shuttle I can catch?");
    } else {
      suggestions.push("Can you compare the fastest option with the most comfortable one?");
    }

    if (userProfile.preferred_route) {
      suggestions.push("Is " + preferredRoute + " still the best choice for me right now?");
    } else {
      suggestions.push("Would waiting up to " + maxWait + " minutes improve my options?");
    }

    if (userSchedule) {
      if (nextClass) {
        suggestions.push("Can you check the best shuttle plan for my next class on " + nextClassDay + "?");
      } else {
        suggestions.push("Can you use my uploaded schedule to help me plan my next class commute?");
      }
    } else {
      suggestions.push("What if I leave 5 minutes later?");
    }
  } else {
    var lastUserMsg = '';
    for (var i = chatHistory.length - 1; i >= 0; i--) {
      if (chatHistory[i].role === 'user') { lastUserMsg = chatHistory[i].content || ''; break; }
    }
    if (lastUserMsg.toLowerCase().indexOf('running late') !== -1) {
      suggestions.push("The shuttle is running 5 mins late");
      suggestions.push("The shuttle is running 10 mins late");
      return suggestions.slice(0, 4);
    }

    if (nextClass && !userSchedule) {
      suggestions.push("Can you remind me when I should leave for my " + nextClassTime + " " + nextClassDay + " class?");
    }

    if (userProfile.timing_style === 'early') {
      suggestions.push("How confident are you that this keeps me from being late?");
      suggestions.push("Is there an even safer option if I want more time buffer?");
    } else if (userProfile.timing_style === 'procrastinate') {
      suggestions.push("How late can I leave before this gets risky?");
      suggestions.push("What is the latest realistic departure time for me?");
    } else {
      suggestions.push("How confident are you in that recommendation?");
      suggestions.push("Can you compare the best option with the next alternative?");
    }

    if (userProfile.crowd_style === 'avoid_crowds') {
      suggestions.push("Is there a less crowded option if I wait " + maxWait + " minutes?");
    } else if (userProfile.crowd_style === 'fastest') {
      suggestions.push("Is there any faster option even if it is more crowded?");
    } else {
      suggestions.push("What if I wait 10 more minutes?");
    }

    if (userProfile.preferred_route) {
      suggestions.push("Would you still recommend " + preferredRoute + " for me?");
    } else if (userSchedule) {
      if (nextClass) {
        suggestions.push("What is the safest plan for getting to my " + nextClassTime + " " + nextClassDay + " class?");
      } else {
        suggestions.push("Which shuttle should I take for my next class?");
      }
    } else {
      var liveArrivalsPost = arrivalsForStop(selectedStop);
      var nextBusPost = liveArrivalsPost.length ? liveArrivalsPost[0] : null;
      var nextDelayPost = nextBusPost ? (nextBusPost.shuttle.delay_minutes || 0) : 0;
      if (nextDelayPost >= 3) {
        suggestions.push("⚠\uFE0F The next shuttle is " + nextDelayPost + " min late — update ETA for all affected stops");
      } else if (nextDelayPost <= -3) {
        suggestions.push("🟢 The next shuttle is " + Math.abs(nextDelayPost) + " min early — update ETA for all affected stops");
      } else {
        suggestions.push("🟢 The next shuttle is on time — is it the best option for my trip?");
      }
    }
  }
  return suggestions.filter(function(item, index, arr) {
    return item && arr.indexOf(item) === index;
  }).slice(0, 4);
}

function renderSuggestedQuestions() {
  var root = document.getElementById('suggestions');
  if (!root) return;
  var suggestions = buildSuggestedQuestions();
  if (!suggestions.length) {
    root.innerHTML = '';
    return;
  }

  var label = chatHistory.length ? 'Next suggested questions' : 'Suggested for this trip';
  root.innerHTML =
    '<div class="suggest-label">' + escapeHtml(label) + '</div>' +
    '<div class="suggest-grid">' +
    suggestions.map(function(question, idx) {
      return '<button class="suggest-chip" data-index="' + idx + '">' + escapeHtml(question) + '</button>';
    }).join('') +
    '</div>';

  root.querySelectorAll('.suggest-chip').forEach(function(chip) {
    chip.addEventListener('click', function() {
      sendMessage(suggestions[parseInt(chip.getAttribute('data-index'), 10)]);
    });
  });
}

function buildProactiveAlert() {
  if (selectedStop === destinationStop) {
    return {
      key: 'destination|' + selectedStop,
      text: 'Your destination is still set to ' + escapeHtml(selectedStop) + '. Choose a different destination before asking for a shuttle recommendation.'
    };
  }

  var originArrivals = arrivalsForStop(selectedStop);
  var sharedRoutes = routeNamesForStop(selectedStop).filter(function(routeName) {
    return routeNamesForStop(destinationStop).indexOf(routeName) !== -1;
  });
  if (!sharedRoutes.length) {
    return {
      key: 'no-direct|' + selectedStop + '|' + destinationStop,
      text: 'No direct route currently serves both ' + escapeHtml(selectedStop) + ' and ' + escapeHtml(destinationStop) + '. Ask AI for the lowest-risk transfer or walking plan.'
    };
  }
  if (!originArrivals.length) {
    return null;
  }

  // Only fire when the next shuttle to the selected stop is arriving within 3 minutes.
  if (!selectedStop) return null;
  var arrivals = arrivalsForStop(selectedStop);
  if (!arrivals.length) return null;
  var best = arrivals[0];
  if (best.etaMinutes > 3) return null;

  var next = arrivals[1];
  var msg;
  if (best.etaMinutes <= 1) {
    msg = best.shuttle.label + ' is arriving now at ' + escapeHtml(selectedStop) + '! Head over now if you want to catch it.';
  } else {
    msg = best.shuttle.label + ' arrives in ' + best.etaMinutes + ' min at ' + escapeHtml(selectedStop) + '. Rush over to catch it';
    if (next) {
      msg += ', or wait ' + next.etaMinutes + ' min for ' + next.shuttle.label + '.';
    } else {
      msg += '!';
    }
  }
  return { key: selectedStop + '|' + best.shuttle.id, text: msg };
}

function renderProactiveAlert() {
  var alertEl = document.getElementById('map-alert');
  if (!alertEl) return;
  var alert = buildProactiveAlert();
  if (!alert || alert.key === dismissedAlertKey) {
    alertEl.className = '';
    alertEl.innerHTML = '';
    return;
  }
  if (alertEl.className === 'show') return; // already visible, don't re-render mid-countdown
  alertEl.className = 'show';
  alertEl.innerHTML =
    '<span class="alert-dot" aria-hidden="true"></span>' +
    '<div class="alert-body"><div class="alert-title">Heads Up</div>' + alert.text + '</div>' +
    '<button id="map-alert-close" type="button" title="Dismiss" onclick="dismissMapAlert()">×</button>';
}

function dismissMapAlert() {
  var alert = buildProactiveAlert();
  dismissedAlertKey = alert ? alert.key : '';
  var alertEl = document.getElementById('map-alert');
  if (alertEl) { alertEl.className = ''; alertEl.innerHTML = ''; }
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}

function meaningfulText(value) {
  if (value === null || value === undefined) return '';
  var text = String(value).trim();
  if (!text) return '';
  var normalized = text.toLowerCase().replace(/[.!?\s]+$/g, '');
  var emptyPhrases = [
    'none',
    'none at this time',
    'no alert',
    'no alerts',
    'no proactive alert',
    'not applicable',
    'n/a',
    'null'
  ];
  return emptyPhrases.indexOf(normalized) === -1 ? text : '';
}

function parseStructuredReply(raw) {
  var text = (raw || '').trim();
  if (text.indexOf('```') === 0) {
    text = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '');
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    var start = text.indexOf('{');
    var end = text.lastIndexOf('}');
    if (start >= 0 && end > start) {
      return JSON.parse(text.slice(start, end + 1));
    }
    throw error;
  }
}

function renderStructuredReply(payload) {
  if (!payload || typeof payload !== 'object') return '';
  var html = '<div class="ai-structured">';
  var summaryText = meaningfulText(payload.summary);
  if (summaryText) {
    html += '<div class="ai-section"><div class="ai-section-main">' + escapeHtml(summaryText) + '</div></div>';
  }

  var shuttleIdToLabel = {'comm-1':'Comm Ave 1','comm-2':'Comm Ave 2','newton-1':'Newton Express 1','newton-2':'Newton Express 2'};
  var rec = payload.recommended_option || {};
  if (rec.action || rec.route || rec.bus || rec.eta_minutes) {
    html += '<div class="ai-section"><div class="ai-section-title">Recommendation</div>';
    html += '<div class="ai-section-main">' + escapeHtml(String(rec.action || 'Check the live arrivals before leaving.')) + '</div>';
    var pills = [];
    if (rec.bus) pills.push(shuttleIdToLabel[rec.bus] || rec.bus);
    if (rec.route) pills.push(rec.route);
    if (Number(rec.eta_minutes) > 0) pills.push('~' + rec.eta_minutes + ' min');
    if (pills.length) {
      html += '<div class="ai-pill-row">' + pills.map(function(item) {
        return '<span class="ai-pill">' + escapeHtml(String(item)) + '</span>';
      }).join('') + '</div>';
    }
    var reasons = safeArray(rec.reasoning).slice(0, 3);
    if (reasons.length) {
      html += '<ul class="ai-list">' + reasons.map(function(item) { return '<li>' + escapeHtml(String(item)) + '</li>'; }).join('') + '</ul>';
    }
    html += '</div>';
  }

  var conf = payload.confidence || {};
  if (conf.score !== undefined || conf.explanation) {
    var label = conf.label ? String(conf.label).replace(/^\w/, function(c){ return c.toUpperCase(); }) + ' confidence' : 'Confidence';
    var confidenceScore = normalizedConfidenceScore(conf.score, conf.label);
    if (confidenceScore !== null) label += ' \u2014 ' + confidenceScore + '% certain';
    html += '<div class="ai-section"><div class="ai-section-title">Prediction Confidence</div><div class="ai-section-main">' + escapeHtml(label) + '</div>';
    if (conf.explanation) html += '<div class="ai-section-detail">' + escapeHtml(String(conf.explanation)) + '</div>';
    html += '</div>';
  }

  var alternatives = safeArray(payload.alternatives).slice(0, 2);
  if (alternatives.length) {
    html += '<div class="ai-section"><div class="ai-section-title">Backup Options</div><ul class="ai-list">';
    alternatives.forEach(function(item) {
      var line = item.action || '';
      if (item.tradeoff) line += ' (' + item.tradeoff + ')';
      if (line) html += '<li>' + escapeHtml(String(line)) + '</li>';
    });
    html += '</ul></div>';
  }

  var whatIf = safeArray(payload.what_if_options).slice(0, 2);
  if (whatIf.length) {
    html += '<div class="ai-section"><div class="ai-section-title">What If</div><ul class="ai-list">';
    whatIf.forEach(function(item) {
      var line = item.scenario && item.outcome ? item.scenario + ': ' + item.outcome : (item.outcome || item.scenario || '');
      if (line) html += '<li>' + escapeHtml(String(line)) + '</li>';
    });
    html += '</ul></div>';
  }

  var proactiveText = meaningfulText(payload.proactive_alert);
  if (proactiveText) {
    html += '<div class="ai-alert">' + escapeHtml(proactiveText) + '</div>';
  }
  var followUpText = meaningfulText(payload.follow_up_question);
  if (followUpText) {
    html += '<div class="ai-section"><div class="ai-section-title">Next Question</div><div class="ai-section-detail">' + escapeHtml(followUpText) + '</div></div>';
  }
  html += '</div>';
  return html;
}

function normalizedConfidenceScore(score, label) {
  var numericScore = Number(score);
  var hasNumericScore = Number.isFinite(numericScore);
  var normalizedLabel = String(label || '').trim().toLowerCase();
  if (hasNumericScore && numericScore === 0 && ['high', 'medium', 'low'].indexOf(normalizedLabel) !== -1) return null;
  if (!hasNumericScore) return null;
  return Math.max(0, Math.min(100, Math.round(numericScore)));
}

function extractJsonStringValue(text, key) {
  var pattern = new RegExp('"' + key + '"\\s*:\\s*"((?:\\\\.|[^"\\\\])*)"', 's');
  var match = String(text || '').match(pattern);
  if (!match) return '';
  try {
    return JSON.parse('"' + match[1] + '"');
  } catch (error) {
    return match[1].replace(/\\"/g, '"');
  }
}

function extractJsonNumberValue(text, key) {
  var pattern = new RegExp('"' + key + '"\\s*:\\s*(-?\\d+(?:\\.\\d+)?)');
  var match = String(text || '').match(pattern);
  return match ? Number(match[1]) : null;
}

function salvageStructuredReply(raw) {
  var text = String(raw || '');
  if (text.indexOf('"summary"') === -1 && text.indexOf('"recommended_option"') === -1) return null;
  var payload = {
    summary: extractJsonStringValue(text, 'summary'),
    recommended_option: {
      action: extractJsonStringValue(text, 'action'),
      route: extractJsonStringValue(text, 'route'),
      bus: extractJsonStringValue(text, 'bus'),
      eta_minutes: extractJsonNumberValue(text, 'eta_minutes'),
      reasoning: []
    },
    confidence: {
      score: extractJsonNumberValue(text, 'score'),
      label: extractJsonStringValue(text, 'label'),
      explanation: extractJsonStringValue(text, 'explanation')
    },
    alternatives: [],
    what_if_options: [],
    proactive_alert: null,
    follow_up_question: extractJsonStringValue(text, 'follow_up_question'),
    delay_update: null,
    capacity_update: null
  };
  var reason = extractJsonStringValue(text, 'reasoning');
  if (reason) payload.recommended_option.reasoning.push(reason);
  return payload;
}

function tryParseStructuredReply(raw) {
  var text = (raw || '').trim();
  if (text.indexOf('{') === -1 && text.indexOf('```') !== 0) return null;
  try {
    var parsed = parseStructuredReply(text);
    if (typeof parsed === 'string') {
      parsed = parseStructuredReply(parsed);
    }
    if (!parsed || typeof parsed !== 'object') return null;
    // Normalize bare {shuttle_id, delay_minutes} into proper delay_update wrapper
    if (parsed.shuttle_id && parsed.delay_minutes !== undefined && !parsed.delay_update) {
      return { delay_update: { shuttle_id: parsed.shuttle_id, delay_minutes: parsed.delay_minutes } };
    }
    // Normalize bare {shuttle_id, capacity_pct} into proper capacity_update wrapper
    if (parsed.shuttle_id && parsed.capacity_pct !== undefined && !parsed.capacity_update) {
      return { capacity_update: { shuttle_id: parsed.shuttle_id, capacity_pct: parsed.capacity_pct } };
    }
    var structuredKeys = [
      'recommended_option',
      'confidence',
      'alternatives',
      'what_if_options',
      'proactive_alert',
      'delay_update',
      'capacity_update'
    ];
    return structuredKeys.some(function(key) { return Object.prototype.hasOwnProperty.call(parsed, key); })
      ? parsed
      : null;
  } catch (error) {
    return salvageStructuredReply(text);
  }
}

function appendMsg(role, html, badgeText, badgeOk) {
  var box = document.getElementById('chat-box');
  var div = document.createElement('div');
  div.className = role === 'user' ? 'msg-user' : role === 'err' ? 'msg-err' : 'msg-ai';
  div.innerHTML = html;
  if (badgeText) {
    var b = document.createElement('div');
    b.className = badgeOk ? 'delay-ok' : 'delay-warn';
    b.textContent = badgeText;
    div.appendChild(b);
  }
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return div;
}

function clearChat() {
  chatHistory = [];
  var box = document.getElementById('chat-box');
  box.innerHTML = '';
  renderSuggestedQuestions();
  renderProactiveAlert();
}

function clearSchedule() {
  userSchedule = null;
  userScheduleEntries = [];
  document.getElementById('schedule-badge').style.display = 'none';
  document.getElementById('schedule-file').value = '';
  saveProfileToStorage();
  syncProfileUi();
  renderSuggestedQuestions();
  showToast('🗑️ Class schedule removed', 'warn');
}

function normalizeSchedulePayload(raw) {
  var payload = null;
  try {
    payload = parseStructuredReply(raw);
  } catch (error) {
    payload = null;
  }
  if (!payload || typeof payload !== 'object') {
    return {
      rawText: String(raw || '').trim(),
      entries: []
    };
  }
  var entries = Array.isArray(payload.classes) ? payload.classes : [];
  var normalizedEntries = entries
    .map(function(entry) {
      if (!entry || typeof entry !== 'object') return null;
      var days = Array.isArray(entry.days) ? entry.days : [];
      var rawLine = entry.raw || [
        days.join('/'),
        entry.start_time || '',
        entry.end_time ? '- ' + entry.end_time : '',
        entry.course || entry.course_name || entry.title || '',
        entry.location || ''
      ].filter(Boolean).join(' ');
      return {
        days: days,
        start_time: entry.start_time || '',
        end_time: entry.end_time || '',
        course: entry.course || entry.course_name || entry.title || '',
        location: entry.location || '',
        raw: rawLine
      };
    })
    .filter(function(entry) {
      return entry && entry.days.length && entry.start_time;
    });
  return {
    rawText: payload.raw_text || normalizedEntries.map(function(entry) { return entry.raw; }).join('\n') || String(raw || '').trim(),
    entries: normalizedEntries
  };
}

function scheduleExampleText() {
  var nextClass = nextScheduledClass();
  if (nextClass) {
    var label = nextClassLabel(nextClass);
    return '📅 I\'ve read your schedule and found your next class: ' + escapeHtml(label) + '. Ask me things like:<br>' +
      '"When should I leave for ' + escapeHtml(label) + '?"<br>' +
      '"Which shuttle gets me there with the safest buffer?"';
  }
  return '📅 I\'ve read your schedule. Ask me things like:<br>' +
    '"Which shuttle should I take for my next class?"<br>' +
    '"When should I leave based on my uploaded schedule?"';
}

document.getElementById('schedule-file').addEventListener('change', async function() {
  var file = this.files[0];
  if (!file) return;
  var apiKey = AI_API_KEY || (document.getElementById('api-key-inp').value || '').trim();
  if (!apiKey) { appendMsg('err', 'Enter your OpenAI API key to use schedule upload.'); return; }

  var uploadBtn = document.getElementById('upload-btn');
  uploadBtn.disabled = true;
  uploadBtn.textContent = '⏳';

  // Read file as base64
  var reader = new FileReader();
  reader.onload = async function(e) {
    var base64 = e.target.result.split(',')[1];
    var mimeType = file.type || 'image/jpeg';
    try {
      var resp = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {'Content-Type':'application/json','Authorization':'Bearer '+apiKey},
        body: JSON.stringify({
          model: 'gpt-4o-mini',
          max_tokens: 800,
          messages: [{
            role: 'user',
            content: [
              {type:'image_url', image_url:{url:'data:'+mimeType+';base64,'+base64}},
              {type:'text', text:
                'Extract the class schedule from this image. Return one valid JSON object only with this shape: ' +
                '{"raw_text":"plain text transcription","classes":[{"days":["Monday"],"start_time":"9:00 AM","end_time":"10:15 AM","course":"course name or number","location":"building and room if visible","raw":"original line"}]}. ' +
                'Read the weekday from the calendar column header above each class block; do not infer it from today or from neighboring columns. ' +
                'Include the weekday in each raw line, for example "Monday, 4:30 PM - 6:50 PM, BZAN2165, Fulton Hall 235". ' +
                'Use full weekday names in days. If a field is unclear, use an empty string except days should be an empty array. Do not add commentary.'}
            ]
          }],
          response_format: {type: 'json_object'}
        })
      });
      var data = await resp.json();
      if (data.error) throw new Error(data.error.message);
      var parsedSchedule = normalizeSchedulePayload(data.choices[0].message.content);
      userSchedule = parsedSchedule.rawText;
      userScheduleEntries = parsedSchedule.entries;
      await saveProfileToStorage();
      var label = file.name.length > 24 ? file.name.slice(0,22)+'…' : file.name;
      document.getElementById('schedule-label').textContent = 'Schedule loaded: ' + label;
      document.getElementById('schedule-badge').style.display = 'flex';
      appendMsg('ai', scheduleExampleText());
      chatHistory.push({role:'assistant', content:'I have read your schedule.'});
      syncProfileUi();
      renderSuggestedQuestions();
      showToast('📅 Class schedule added to your profile', 'success');
    } catch(err) {
      appendMsg('err', 'Could not read schedule: ' + err.message);
      showToast('❌ Could not read schedule image', 'warn');
    }
    uploadBtn.disabled = false;
    uploadBtn.textContent = '👤';
  };
  reader.readAsDataURL(file);
});

function updateSelectedStopMarkers() {
  Object.keys(stopMarkersByName).forEach(function(stopName) {
    stopMarkersByName[stopName].forEach(function(entry) {
      var isSelected = stopName === selectedStop;
      entry.marker.setStyle({
        radius: isSelected ? 9 : 6,
        fillColor: isSelected ? '#111827' : entry.color,
        color: 'white',
        weight: 2,
        fillOpacity: 1
      });
    });
  });
}

function busColorClass(routeName) {
  if (routeName === 'Newton Campus Express') return 'bus-color-newton';
  return 'bus-color-comm';
}

function capClass(pct) {
  return pct >= 85 ? 'ctx-cap-red' : pct >= 60 ? 'ctx-cap-yel' : 'ctx-cap-grn';
}

function updateStopContextBar() {
  var nameEl = document.getElementById('stop-ctx-name');
  var rowsEl = document.getElementById('stop-ctx-rows');
  if (!nameEl || !rowsEl) return;
  nameEl.textContent = selectedStop;
  var arrivals = arrivalsForStop(selectedStop);
  if (!arrivals.length) {
    rowsEl.innerHTML = '<div class="ctx-row">No buses currently approaching this stop.</div>';
    return;
  }
  var html = '';
  var next = arrivals[0];
  html += '<div class="ctx-row">'
    + 'Next: <span class="ctx-eta-val">' + next.etaMinutes + ' min</span>'
    + ' &nbsp;·&nbsp; ' + escapeHtml(next.shuttle.label)
    + '</div>';
  html += '<div class="ctx-row">'
    + 'Capacity: <span class="' + capClass(next.shuttle.capacity_pct) + '">'
    + next.shuttle.capacity_pct + '%</span>'
    + (next.shuttle.capacity_pct >= 85 ? ' · Very crowded'
      : next.shuttle.capacity_pct >= 60 ? ' · Moderate' : ' · Light')
    + '</div>';
  if (arrivals.length > 1) {
    var alt = arrivals[1];
    html += '<div class="ctx-row" style="margin-top:2px;opacity:.8;">'
      + 'Then: ' + alt.etaMinutes + ' min'
      + ' (<span class="' + capClass(alt.shuttle.capacity_pct) + '">' + alt.shuttle.capacity_pct + '%</span>)'
      + ' · ' + escapeHtml(alt.shuttle.label)
      + '</div>';
  }
  rowsEl.innerHTML = html;
}

function highlightRelevantShuttles(stopName) {
  // Mark each shuttle as relevant (serves this stop) or not
  var relevantRoutes = {};
  routeEntries.forEach(function(entry) {
    if (entry[1].stop_progress[stopName] !== undefined) {
      relevantRoutes[entry[0]] = true;
    }
  });
  (shuttles || []).forEach(function(s) {
    s._relevantForStop = !!relevantRoutes[s.route];
    updateMarkerVisual(s); // apply immediately
  });
}

function closeStopSection() {
  stopSectionVisible = false;
  renderStopCard();
  (shuttles || []).forEach(function(s) { s._relevantForStop = undefined; updateMarkerVisual(s); });
}

var selectedShuttleId = null;

function closeShuttleFloat() {
  selectedShuttleId = null;
  var el = document.getElementById('shuttle-float');
  if (el) el.style.display = 'none';
}

function renderShuttleFloat() {
  var el = document.getElementById('shuttle-float');
  if (!el) return;
  if (!selectedShuttleId) { el.style.display = 'none'; return; }
  var s = (shuttles || []).find(function(x) { return x.id === selectedShuttleId; });
  if (!s) { el.style.display = 'none'; return; }
  el.style.display = 'block';
  var route = mapPayload.routes[s.route];
  var capPct = s.capacity_pct;
  var capColor = capPct >= 85 ? '#ef4444' : capPct >= 60 ? '#f59e0b' : '#22c55e';
  document.getElementById('shuttle-float-title').innerHTML =
    escapeHtml(s.label) +
    '<span class="stop-route-pill" style="background:'+route.color+';font-size:9px;margin-left:8px;vertical-align:middle;">'+escapeHtml(s.route)+'</span>';
  var delayHtml = s.delay_minutes > 0
    ? '<div style="color:#ef4444;font-size:11px;font-weight:800;margin-top:6px;">⚠️ +'+s.delay_minutes+' min late</div>'
    : s.delay_minutes < 0
      ? '<div style="color:#22c55e;font-size:11px;font-weight:800;margin-top:6px;">⏰ '+Math.abs(s.delay_minutes)+' min early</div>'
      : '';
  var expressHtml = s.is_express ? '<div style="color:#7c3aed;font-size:11px;font-weight:800;margin-top:4px;">🚀 Express</div>' : '';
  var statusHtml = s.dwell_seconds_remaining > 0
    ? '<div style="color:#94a3b8;font-size:11px;margin-top:6px;">Boarding at <b style="color:#f1f5f9;">'+escapeHtml(s.current_stop)+'</b></div>'
    : '<div style="color:#94a3b8;font-size:11px;margin-top:6px;">Heading to <b style="color:#f1f5f9;">'+escapeHtml(s.next_stop)+'</b></div>';
  var capBarWidth = Math.min(100, capPct);
  var peopleHtml = capacityPeopleHtml(capPct).replace('color:#2563eb;', 'color:'+capColor+';');
  var capHtml = '<div style="margin-top:10px;">'
    + '<div style="font-size:10px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:#64748b;margin-bottom:2px;">Capacity</div>'
    + peopleHtml.replace('margin-top:10px;', 'margin-top:4px;')
    + '<div style="display:flex;align-items:center;gap:8px;margin-top:2px;">'
    + '<div style="flex:1;height:5px;border-radius:999px;background:rgba(148,163,184,.2);overflow:hidden;">'
    + '<div style="height:100%;width:'+capBarWidth+'%;background:'+capColor+';border-radius:999px;transition:width .4s ease;"></div>'
    + '</div>'
    + '<span style="font-size:12px;font-weight:900;color:'+capColor+';">'+capPct+'%</span>'
    + '</div>'
    + '<div style="color:#94a3b8;font-size:10px;margin-top:4px;">'+escapeHtml(s.capacity)+'</div>'
    + '</div>';
  document.getElementById('shuttle-float-body').innerHTML = statusHtml + delayHtml + expressHtml + capHtml;
}

function onStopChange(name, options) {
  options = options || {};
  if (!name) return;

  var isSameStop = (name === selectedStop);

  // Toggle: clicking the already-selected stop hides/shows the panel
  if (isSameStop && options.manual !== false && (hasUserSelectedStopManually || hasAutoSelectedNearestStop)) {
    stopSectionVisible = !stopSectionVisible;
    renderStopCard();
    return; // no re-fly or re-highlight needed
  }

  // New stop: always show the panel
  stopSectionVisible = true;
  dismissedAlertKey = '';
  if (options.manual !== false) {
    hasUserSelectedStopManually = true;
  }
  selectedStop = name;
  document.getElementById('stop-sel').value = name;
  updateSelectedStopMarkers();
  highlightRelevantShuttles(name);
  renderStopCard();
  updateStopContextBar();
  renderSuggestedQuestions();
  renderProactiveAlert();
  if (options.recenter !== false) {
    leafletMap.flyTo(stopCoords(name), 15, {duration: 0.7, easeLinearity: 0.4});
  }
}

function onDestinationChange(name) {
  if (!name) return;
  destinationStop = name;
  document.getElementById('dest-sel').value = name;
  renderSuggestedQuestions();
  renderProactiveAlert();
  showToast('Destination set to ' + name, 'success');
}

function buildContext() {
  var now = new Date();
  var time = now.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit',timeZone:'America/New_York',timeZoneName:'short'});
  var needsDestination = selectedStop === destinationStop;
  var nextClass = nextScheduledClass();
  var sharedRoutes = routeNamesForStop(selectedStop).filter(function(routeName) {
    return routeNamesForStop(destinationStop).indexOf(routeName) !== -1;
  });
  var lines = [
    'The user is currently at or starting from stop: ' + selectedStop + '.',
    'The user selected destination stop: ' + destinationStop + '.',
    'Current datetime: ' + easternDateTimeLabel() + '.',
    'Timezone: America/New_York.',
    'Destination status: ' + (needsDestination ? 'NOT SET - destination matches origin. Ask the user to update destination before recommending a shuttle.' : 'set') + '.',
    'Routes serving both selected stops: ' + (sharedRoutes.length ? sharedRoutes.join(', ') : 'none found in current route data') + '.',
    needsDestination
      ? 'Do not give a trip boarding recommendation yet; the rider has not chosen a real destination.'
      : 'When giving directions or arrival info, plan from ' + selectedStop + ' to ' + destinationStop + ' unless they say otherwise.',
    'Default boarding stop is the selected origin stop: ' + selectedStop + '. Only recommend a different boarding stop if you explicitly include the walk to that stop and the combined walk-plus-wait timing.',
    'Current time: ' + time + '.', '', '=== LIVE SHUTTLE STATUS ==='];
  (shuttles||[]).forEach(function(s) {
    var d  = s.delay_minutes||0;
    var ds = d>0?' (+'+d+' min delay)':d<0?' (running early)':' (on time)';
    var st = s.dwell_seconds_remaining>0
      ? 'boarding at '+s.current_stop
      : 'traveling from '+s.current_stop+' toward '+s.next_stop;
    lines.push('- '+s.id+' ('+s.label+'), route: '+s.route+', status: '+st+', capacity: '+s.capacity_pct+'%'+ds);
  });
  lines.push('','=== ROUTE SCHEDULES ===');
  Object.entries(mapPayload.routes).forEach(function(e){
    lines.push('- '+e[0]+': '+e[1].service_days+', '+e[1].service_window+', '+e[1].headway);
    lines.push('  Stops served: ' + e[1].ordered_stop_names.join(' → '));
  });
  lines.push('','=== UPCOMING ARRIVALS at origin '+selectedStop+' ===');
  var arr = arrivalsForStop(selectedStop);
  if (arr.length) {
    arr.slice(0,4).forEach(function(a){
      var tripDelta = routeProgressDelta(a.shuttle.route, selectedStop, destinationStop);
      var tripNote = tripDelta !== null && tripDelta < 0.001
        ? ' Same-stop destination: do not recommend boarding for this trip.'
        : '';
      lines.push('  - '+a.shuttle.label+' ('+a.shuttle.route+'): '+a.etaMinutes+' min away at selected origin '+selectedStop+', capacity '+a.shuttle.capacity_pct+'%.'+tripNote);
    });
  } else { lines.push('  No arrivals found.'); }
  lines.push('', '=== USER PROFILE ===');
  profileSummaryLines().forEach(function(line) {
    lines.push('- ' + line);
  });
  if (userSchedule) {
    lines.push('', '=== USER\'S CLASS SCHEDULE ===', userSchedule);
    var parsedEntries = parseScheduleEntries();
    if (parsedEntries.length) {
      if (nextClass) {
        lines.push(
          'Computed next class in America/New_York: ' +
          nextClassLabel(nextClass) +
          ' (parsed day: ' + nextClass.dayName + ', raw: ' + nextClass.raw + ')'
        );
      }
      lines.push('', '=== STRUCTURED CLASS SCHEDULE JSON ===');
      lines.push(JSON.stringify(parsedEntries.map(function(entry) {
        return {
          days: entry.days,
          start_minutes: entry.startMinutes,
          course: entry.course,
          location: entry.location,
          raw: entry.raw
        };
      })));
    }
  }
  if (userLatLng) {
    lines.push('', '=== USER\'S CURRENT LOCATION ===');
    lines.push('User has shared their GPS location. Nearby stops and next arrivals:');
    var nearStops = nearestStopsToUser(userLatLng[0], userLatLng[1], 3);
    nearStops.forEach(function(c) {
      var distStr = c.dist < 1000 ? Math.round(c.dist) + 'm' : (c.dist/1000).toFixed(1) + 'km';
      var walkMins = Math.max(1, Math.ceil(c.dist / 80));
      var tag = c.stop.name === nearStops[0].stop.name ? ' [NEAREST — shown first in Near You panel]' : '';
      var stopRole = c.stop.name === selectedStop ? 'selected origin' : 'alternate boarding stop';
      lines.push('Stop: ' + c.stop.name + tag + ' [' + stopRole + '] (' + distStr + ' away, ~' + walkMins + ' min walk, ' + c.route + ')');
      arrivalsForStop(c.stop.name).slice(0, 2).forEach(function(a) {
        var totalMins = walkMins + a.etaMinutes;
        var alternateNote = c.stop.name === selectedStop
          ? ''
          : ' If recommending this, say to walk to ' + c.stop.name + ' first; combined walk-plus-wait is about ' + totalMins + ' min.';
        lines.push('  → ' + a.shuttle.label + ' (' + a.shuttle.route + '): bus arrives there in ' + a.etaMinutes + ' min, capacity ' + a.shuttle.capacity_pct + '%.' + alternateNote);
      });
    });
    lines.push('Nearby stop rule: never describe an alternate-stop bus as catchable from the selected origin. For alternate stops, include the walk and combined timing; otherwise use arrivals at selected origin ' + selectedStop + '. Capacity shown is projected for when the shuttle arrives at that stop.');
  }
  return lines.join('\n');
}

function parseCapacityFromUserMsg(text) {
  var lower = text.toLowerCase();
  var hasCapacityKeyword = lower.indexOf('capacity') !== -1 || lower.indexOf('full') !== -1
    || lower.indexOf('crowd') !== -1 || lower.indexOf('empty') !== -1 || lower.indexOf('seat') !== -1;
  if (!hasCapacityKeyword) return null;
  // Match "55%", "55 percent", "about 55%", "55 per cent"
  var m = lower.match(/\b(\d{1,3})\s*(%|percent)/);
  if (!m) return null;
  var pct = parseInt(m[1], 10);
  if (pct < 0 || pct > 100) return null;
  return pct;
}

function isShuttleChoiceQuestion(text) {
  var lower = String(text || '').toLowerCase();
  var asksForChoice = /which\s+shuttle|what\s+shuttle|should\s+i\s+take|do\s+you\s+recommend|best\s+(option|shuttle|route)|fastest\s+(option|shuttle|route)|take\s+the\s+/.test(lower);
  var shuttleContext = /shuttle|bus|route|comm\s+ave|newton|to\s+/.test(lower);
  var explanatoryFollowUp = /why|how confident|confidence|how certain|how did|explain/.test(lower);
  return asksForChoice && shuttleContext && !explanatoryFollowUp;
}

function capacityLabelForPct(pct) {
  return pct >= 85 ? 'Very crowded' : pct >= 60 ? 'Moderate' : 'Light';
}

function buildShuttleChoiceStructuredReply(userMsg) {
  if (!isShuttleChoiceQuestion(userMsg)) return null;

  var needsDestination = selectedStop === destinationStop;
  if (needsDestination) {
    return {
      summary: 'Your destination is still set to ' + selectedStop + ', so I need a different destination before recommending a trip.',
      recommended_option: {
        action: 'Choose a destination stop first.',
        route: null,
        bus: null,
        eta_minutes: 0,
        reasoning: ['The origin and destination currently match.', 'A shuttle recommendation needs a real destination.']
      },
      confidence: {score: 95, label: 'high', explanation: 'The selected trip is incomplete because the destination matches the starting stop.'},
      alternatives: [],
      what_if_options: [],
      proactive_alert: null,
      follow_up_question: 'Where are you trying to go?',
      delay_update: null,
      capacity_update: null
    };
  }

  var useCurrentLocation = /current location|near me|nearby|right now/.test(String(userMsg || '').toLowerCase()) && userLatLng;
  var candidates = [];
  if (useCurrentLocation) {
    nearestStopsToUser(userLatLng[0], userLatLng[1], 5).forEach(function(c) {
      var walkMins = Math.max(1, Math.ceil(c.dist / 80));
      arrivalsForStop(c.stop.name).slice(0, 2).forEach(function(a) {
        candidates.push({
          stopName: c.stop.name,
          route: a.shuttle.route,
          bus: a.shuttle.label,
          eta: a.etaMinutes,
          capacityPct: a.shuttle.capacity_pct,
          walkMins: walkMins,
          distanceMeters: c.dist,
          totalMins: walkMins + a.etaMinutes,
          isAlternateStop: c.stop.name !== selectedStop
        });
      });
    });
  } else {
    arrivalsForStop(selectedStop).slice(0, 4).forEach(function(a) {
      candidates.push({
        stopName: selectedStop,
        route: a.shuttle.route,
        bus: a.shuttle.label,
        eta: a.etaMinutes,
        capacityPct: a.shuttle.capacity_pct,
        walkMins: 0,
        distanceMeters: 0,
        totalMins: a.etaMinutes,
        isAlternateStop: false
      });
    });
  }

  if (!candidates.length) return null;
  candidates.sort(function(a, b) {
    if (a.totalMins !== b.totalMins) return a.totalMins - b.totalMins;
    return a.capacityPct - b.capacityPct;
  });

  var best = candidates[0];
  var capLabel = capacityLabelForPct(best.capacityPct);
  var action = best.isAlternateStop
    ? 'Walk to ' + best.stopName + ' and take ' + best.bus + '.'
    : 'Take ' + best.bus + ' from ' + best.stopName + '.';
  var summary = best.isAlternateStop
    ? 'Best option: walk about ' + best.walkMins + ' min to ' + best.stopName + ', then board ' + best.bus + '. Combined walk-plus-wait is about ' + best.totalMins + ' min.'
    : 'Best option: board ' + best.bus + ' at ' + best.stopName + '. It is arriving in about ' + best.eta + ' min.';

  var reasons = [];
  reasons.push(best.isAlternateStop
    ? 'This has the lowest combined walk-plus-wait time among nearby stops.'
    : 'This is the soonest useful arrival from your selected stop.');
  reasons.push('Capacity is ' + best.capacityPct + '% (' + capLabel + ').');
  if (best.route) reasons.push('Route: ' + best.route + '.');

  var alternatives = candidates.slice(1, 3).map(function(c) {
    var altAction = c.isAlternateStop
      ? 'Walk to ' + c.stopName + ' for ' + c.bus
      : 'Wait for ' + c.bus + ' at ' + c.stopName;
    return {
      action: altAction,
      tradeoff: 'about ' + c.totalMins + ' min total, ' + c.capacityPct + '% capacity'
    };
  });

  var confidenceScore = best.eta <= 5 ? 88 : best.eta <= 15 ? 82 : 72;
  if (best.capacityPct >= 85) confidenceScore -= 4;
  var confidenceLabel = confidenceScore >= 80 ? 'high' : confidenceScore >= 60 ? 'medium' : 'low';

  return {
    summary: summary,
    recommended_option: {
      action: action,
      route: best.route,
      bus: best.bus,
      eta_minutes: best.totalMins,
      reasoning: reasons
    },
    confidence: {
      score: confidenceScore,
      label: confidenceLabel,
      explanation: 'Based on the current live ETA, nearby-stop walk time, and projected crowding.'
    },
    alternatives: alternatives,
    what_if_options: [],
    proactive_alert: best.capacityPct >= 85 ? best.bus + ' is projected to be very crowded.' : null,
    follow_up_question: null,
    delay_update: null,
    capacity_update: null
  };
}

function parseDelay(text) {
  // pattern: DELAY_UPDATE:{shuttle_id:X,delay_minutes:N}
  var m = text.match(/DELAY_UPDATE:\{shuttle_id:([^,]+),delay_minutes:(-?\d+)\}/);
  if (!m) return {clean: text, shuttleId: null, mins: 0};
  return {
    clean: text.slice(0, m.index).trimEnd(),
    shuttleId: m[1].trim(),
    mins: parseInt(m[2], 10)
  };
}

document.getElementById('send-btn').addEventListener('click', sendMessage);
document.getElementById('user-inp').addEventListener('keydown', function(e){
  if (e.key==='Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});
document.getElementById('tour-overlay').addEventListener('click', stopTour);
document.addEventListener('keydown', function(e) {
  if (!isTourActive()) return;
  if (e.key === 'Escape') {
    stopTour();
  } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
    nextTourStep();
  } else if (e.key === 'ArrowLeft') {
    previousTourStep();
  }
});

// ── theme toggle ──────────────────────────────────────────────────────────────
function tileUrlForTheme(isLight) {
  return isLight
    ? 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
    : 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
}

function syncMapTheme(isLight) {
  if (!leafletMap || !baseTileLayer) return;
  baseTileLayer.setUrl(tileUrlForTheme(isLight));
}

function toggleTheme() {
  var light = document.body.classList.toggle('light-mode');
  document.getElementById('theme-btn').textContent = light ? '🌙' : '☀️';
  localStorage.setItem('bc_shuttle_theme', light ? 'light' : 'dark');
  syncMapTheme(light);
}
(function() {
  if (localStorage.getItem('bc_shuttle_theme') === 'light') {
    document.body.classList.add('light-mode');
    document.getElementById('theme-btn').textContent = '🌙';
  }
})();

// Show server-key badge or user key input depending on configuration
(async function() {
  await loadProfile();
  syncProfileUi();
  var keyRow = document.getElementById('key-row');
  var keyInp = document.getElementById('api-key-inp');
  if (AI_SERVER_CONFIGURED) {
    keyRow.style.display = 'none';
  } else {
    // Restore user key from localStorage
    var saved = localStorage.getItem('bc_shuttle_openai_key');
    if (saved) keyInp.value = saved;
    keyInp.addEventListener('input', function() {
      localStorage.setItem('bc_shuttle_openai_key', this.value);
    });
  }
})();

async function sendMessage(prefilledMessage) {
  var inputEl = document.getElementById('user-inp');
  var sendBtn = document.getElementById('send-btn');
  var userMsg = typeof prefilledMessage === 'string' ? prefilledMessage.trim() : inputEl.value.trim();
  var apiKey = AI_API_KEY || (document.getElementById('api-key-inp').value || '').trim();
  if (!apiKey) {
    appendMsg('err', 'Enter your OpenAI API key above to enable AI chat.');
    return;
  }
  if (!userMsg) return;

  inputEl.value = '';
  sendBtn.disabled = true;
  chatHistory.push({role: 'user', content: userMsg});
  appendMsg('user', escapeHtml(userMsg).replace(/\n/g,'<br>'));

  // Apply capacity update immediately from user message
  var reportedCap = parseCapacityFromUserMsg(userMsg);
  if (reportedCap !== null) {
    var liveNow = arrivalsForStop(selectedStop);
    var targetShuttle = liveNow.length ? liveNow[0].shuttle : null;
    if (targetShuttle) {
      (shuttles||[]).forEach(function(s) {
        if (s.id === targetShuttle.id) {
          s.capacity_pct = reportedCap;
          s.capacity = reportedCap >= 85 ? 'Full' : reportedCap >= 60 ? 'Medium' : 'Empty';
          if (!s._reported_cap_at) s._reported_cap_at = {};
          s._reported_cap_at[selectedStop] = reportedCap;
        }
      });
      updateStopContextBar();
      renderStopCard();
    }
  }

  renderSuggestedQuestions();

  var box = document.getElementById('chat-box');
  var thinkEl = document.createElement('div');
  thinkEl.id = 'thinking';
  thinkEl.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  box.appendChild(thinkEl);
  box.scrollTop = box.scrollHeight;

  try {
    var msgs = [{role:'system', content: SYSTEM_PROMPT + '\n\n' + buildContext()}];
    chatHistory.slice(-10).forEach(function(m){ msgs.push({role:m.role, content:m.content}); });
    var requestBody = {model:'gpt-4o-mini', messages:msgs, temperature:0.3, max_tokens:1200};

    var resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {'Content-Type':'application/json', 'Authorization':'Bearer '+apiKey},
      body: JSON.stringify(requestBody)
    });
    var data = await resp.json();
    if (data.error) throw new Error(data.error.message);

    var raw = data.choices[0].message.content;
    var structured = tryParseStructuredReply(raw);
    var clean = escapeHtml(raw || '').replace(/\n/g,'<br>');
    if (structured) {
      clean = renderStructuredReply(structured) || clean;
    } else {
      var parsedFallback = parseDelay(raw);
      if (parsedFallback.shuttleId) {
        clean = escapeHtml(parsedFallback.clean || raw).replace(/\n/g,'<br>');
        structured = {delay_update: {shuttle_id: parsedFallback.shuttleId, delay_minutes: parsedFallback.mins}};
      } else {
        var recommendationFallback = buildShuttleChoiceStructuredReply(userMsg);
        if (recommendationFallback) {
          structured = recommendationFallback;
          clean = renderStructuredReply(structured) || clean;
        }
      }
    }
    var assistantMemory = structured ? JSON.stringify(structured) : (raw || '');
    chatHistory.push({role:'assistant', content:assistantMemory, display:clean});

    if (thinkEl.parentNode) thinkEl.parentNode.removeChild(thinkEl);

    var badgeText = null, badgeOk = false;
    var delayData = structured && structured.delay_update && structured.delay_update.shuttle_id ? structured.delay_update : null;
    if (delayData) {
      var delayMins = parseInt(delayData.delay_minutes || 0, 10);
      (shuttles||[]).forEach(function(s){
        if (s.id === delayData.shuttle_id) { s.delay_minutes = delayMins; s.on_time = delayMins === 0; }
      });
      badgeText = delayMins === 0 ? '✅ Delay cleared' : '⚠️ +'+ delayMins +' min delay applied';
      badgeOk = delayMins === 0;
    }
    // Only apply capacity_update if the user actually reported a value (not just asked about it)
    var userReportedCapacity = parseCapacityFromUserMsg(userMsg) !== null;
    var capData = userReportedCapacity && structured && structured.capacity_update && structured.capacity_update.shuttle_id ? structured.capacity_update : null;
    if (capData) {
      var newCap = Math.max(0, Math.min(100, parseInt(capData.capacity_pct || 0, 10)));
      (shuttles||[]).forEach(function(s){
        if (s.id === capData.shuttle_id) {
          s.capacity_pct = newCap;
          s.capacity = newCap >= 85 ? 'Full' : newCap >= 60 ? 'Medium' : 'Empty';
        }
      });
      updateStopContextBar();
      renderStopCard();
      var capLabel = newCap >= 85 ? 'Very crowded' : newCap >= 60 ? 'Moderate' : 'Light';
      badgeText = (badgeText ? badgeText + ' · ' : '') + '🚌 Capacity updated: ' + newCap + '% (' + capLabel + ')';
      badgeOk = true;
    }
    appendMsg('ai', clean, badgeText, badgeOk);
    renderSuggestedQuestions();
    renderProactiveAlert();
  } catch(err) {
    if (thinkEl.parentNode) thinkEl.parentNode.removeChild(thinkEl);
    chatHistory.pop();
    appendMsg('err', 'AI error: ' + err.message);
  }
  sendBtn.disabled = false;
}

// ── restore chat from sessionStorage ─────────────────────────────────────────
(function restoreChat(){
  if (!chatHistory.length && !EMBEDDED_AI_ERROR) return;
  var box = document.getElementById('chat-box');
  box.innerHTML = '';
  if (EMBEDDED_AI_ERROR) {
    appendMsg('err', 'Error: ' + EMBEDDED_AI_ERROR);
  }
  chatHistory.forEach(function(m){
    var div = document.createElement('div');
    div.className = m.role==='user' ? 'msg-user' : 'msg-ai';
    if (m.display) {
      div.innerHTML = m.display;
    } else {
      div.innerHTML = escapeHtml(m.content || '').replace(/\n/g,'<br>');
    }
    box.appendChild(div);
  });
  box.scrollTop = box.scrollHeight;
})();
renderSuggestedQuestions();

// ── map ───────────────────────────────────────────────────────────────────────
document.getElementById('map-ts').textContent = 'Initialized at ' + INIT_TIME + ' · buses update in real time';

var leafletMap;
var baseTileLayer;
var shuttles;
var activeRoute = mapPayload.selected_route_filter && mapPayload.selected_route_filter !== 'All routes'
  ? mapPayload.selected_route_filter
  : null;
var routeLayers = {};
var stopMarkersByName = {};

var routeEntries = Object.entries(mapPayload.routes);
leafletMap = L.map('map', {zoomControl:false, attributionControl:true})
  .setView([mapPayload.selected_coords.lat, mapPayload.selected_coords.lon], 14);

baseTileLayer = L.tileLayer(tileUrlForTheme(document.body.classList.contains('light-mode')), {
  maxZoom:19, attribution:'&copy; OpenStreetMap &copy; CARTO'
}).addTo(leafletMap);

routeEntries.forEach(function(entry) {
  var routeName = entry[0], route = entry[1];
  var polyline = L.polyline(route.path, {color:route.color, weight:6, opacity:0.9})
   .addTo(leafletMap).bindTooltip(routeName);
  var stopMarkers = [];
  route.stops.forEach(function(stop) {
    var isSel = stop.name === mapPayload.selected_stop;
    var marker = L.circleMarker([stop.lat, stop.lon], {
      radius:isSel?9:6, color:'white', weight:2,
      fillColor:isSel?'#111827':route.color, fillOpacity:1
    }).addTo(leafletMap).bindPopup('<b>'+stop.name+'</b><br>'+routeName);
    marker.on('click', function() {
      onStopChange(stop.name, {manual:true});
    });
    stopMarkers.push(marker);
    if (!stopMarkersByName[stop.name]) stopMarkersByName[stop.name] = [];
    stopMarkersByName[stop.name].push({marker: marker, color: route.color});
  });
  routeLayers[routeName] = {
    polyline: polyline,
    stopMarkers: stopMarkers,
    bounds: L.latLngBounds(route.path),
  };
});

var legend = L.control({position:'bottomleft'});
legend.onAdd = function() {
  var div = L.DomUtil.create('div','legend');
  div.innerHTML = '<b>Routes</b><br>' + routeEntries.map(function(e){
    return '<div style="margin-top:5px;"><span class="legend-dot" style="background:'+e[1].color+'"></span>'+e[0]+'</div>';
  }).join('');
  return div;
};
legend.addTo(leafletMap);

// ── You-are-here / geolocation ────────────────────────────────────────────────
var userLatLng = null;
var userMarker = null;
var userAccCircle = null;
var shouldSetNearestStopFromLocateClick = false;

function haversineDist(lat1, lon1, lat2, lon2) {
  var R = 6371000;
  var p1 = lat1*Math.PI/180, p2 = lat2*Math.PI/180;
  var dp = (lat2-lat1)*Math.PI/180, dl = (lon2-lon1)*Math.PI/180;
  var a = Math.sin(dp/2)*Math.sin(dp/2) + Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)*Math.sin(dl/2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
}

function nearestStopToUser(lat, lon) {
  var best = null, bestDist = Infinity;
  routeEntries.forEach(function(e) {
    e[1].stops.forEach(function(stop) {
      var d = haversineDist(lat, lon, stop.lat, stop.lon);
      if (d < bestDist) { bestDist = d; best = {stop:stop, route:e[0], color:e[1].color, dist:d}; }
    });
  });
  return best;
}

// Returns up to maxN closest unique stops (by name) with route info
function nearestStopsToUser(lat, lon, maxN) {
  var seen = {};
  routeEntries.forEach(function(e) {
    var routeName = e[0], route = e[1];
    route.stops.forEach(function(stop) {
      var d = haversineDist(lat, lon, stop.lat, stop.lon);
      if (!seen[stop.name] || seen[stop.name].dist > d) {
        seen[stop.name] = {stop: stop, route: routeName, color: route.color, dist: d};
      }
    });
  });
  return Object.values(seen)
    .sort(function(a, b) { return a.dist - b.dist; })
    .slice(0, maxN || 4);
}

function updateLocationRec() {
  if (!userLatLng) return;
  var lat = userLatLng[0], lon = userLatLng[1];
  var candidates = nearestStopsToUser(lat, lon, 5);

  var recs = candidates.map(function(c) {
    var arrivals = arrivalsForStop(c.stop.name);
    return {stop: c.stop, route: c.route, color: c.color, dist: c.dist, best: arrivals[0] || null};
  });
  if (!recs.length) return;

  // This panel is "Stops Near You", so keep it ordered by physical distance.
  // Faster-but-farther choices still appear as alternatives and in the AI card.
  recs.sort(function(a, b) {
    return a.dist - b.dist;
  });

  var html = '';
  recs.slice(0, 2).forEach(function(rec, i) {
    var distStr = rec.dist < 1000 ? Math.round(rec.dist) + ' m' : (rec.dist/1000).toFixed(1) + ' km';
    var walkMins = Math.max(1, Math.ceil(rec.dist / 80));
    var isBest = i === 0;
    html += '<div class="card' + (isBest ? ' loc-rec-best' : '') + '" style="border-left-color:' + rec.color + ';">';
    if (isBest) html += '<div class="loc-rec-badge">⭐ NEAREST</div>';
    html += '<div class="title">' + escapeHtml(rec.stop.name) + '</div>';
    html += '<div class="body">' + distStr + ' away · ~' + walkMins + ' min walk</div>';
    var askText = 'Based on my current location, should I wait at ' + rec.stop.name + '?';
    if (rec.best) {
      html += '<div style="display:flex;align-items:baseline;gap:8px;margin-top:7px;">'
        + '<span class="loc-rec-eta">' + rec.best.etaMinutes + ' min</span>'
        + '<span style="font-size:10px;color:' + rec.color + ';font-weight:800;">' + escapeHtml(rec.best.shuttle.route) + '</span>'
        + '</div>';
      var capColor = rec.best.shuttle.capacity_pct >= 85 ? '#ef4444' : rec.best.shuttle.capacity_pct >= 60 ? '#f59e0b' : '#22c55e';
      html += '<div class="body" style="margin-top:3px;">Capacity: <span style="color:' + capColor + ';font-weight:700;">'
        + rec.best.shuttle.capacity_pct + '%</span> · ' + escapeHtml(rec.best.shuttle.label) + '</div>';
      askText = 'Based on my current location, should I take the ' + rec.best.shuttle.route + ' from ' + rec.stop.name + '?';
    } else {
      html += '<div class="body" style="margin-top:7px;">No shuttle is currently approaching this stop.</div>';
    }
    html += '<button onclick="sendMessage(\'' + askText.replace(/\\/g,'\\\\').replace(/'/g,"\\'") + '\')" '
      + 'style="margin-top:8px;width:100%;background:transparent;border:1px solid #334155;color:#93c5fd;border-radius:8px;padding:5px 8px;font-size:11px;font-weight:700;cursor:pointer;" '
      + 'onmouseover="this.style.background=\'#1e3a5f\'" onmouseout="this.style.background=\'transparent\'">Ask AI about this option ›</button>';
    html += '</div>';
  });

  var recEl = document.getElementById('loc-rec');
  var titleEl = document.getElementById('loc-rec-title');
  recEl.innerHTML = html;
  recEl.style.display = 'block';
  titleEl.style.display = 'block';
}

function updateLocationBanner(lat, lon) {
  var nearest = nearestStopToUser(lat, lon);
  if (!nearest) return;
  var banner = document.getElementById('loc-banner');
  var d = nearest.dist;
  var distStr = d < 1000 ? Math.round(d) + ' m' : (d/1000).toFixed(1) + ' km';
  banner.innerHTML =
    '<span class="loc-dot" style="background:'+nearest.color+'"></span>' +
    '<span><b>You\'re near '+nearest.stop.name+'</b> &nbsp;·&nbsp; '+nearest.route+'</span>' +
    '<span class="loc-dist">'+distStr+' away</span>' +
    '<button class="loc-center-btn" onclick="centerOnUser()">Re-center</button>';
  banner.style.display = 'flex';
  applyHeight();
}

function centerOnUser() {
  if (userLatLng) { leafletMap.setView(userLatLng, 16); }
}

function setNearestStopFromLocation(lat, lon, options) {
  options = options || {};
  var nearest = nearestStopToUser(lat, lon);
  if (!nearest || !nearest.stop || !nearest.stop.name) return false;

  var shouldUpdate = options.force === true ||
    (!hasUserSelectedStopManually && !hasAutoSelectedNearestStop && nearest.stop.name !== selectedStop);
  if (!shouldUpdate) return false;

  onStopChange(nearest.stop.name, {manual:false, recenter:false});
  hasAutoSelectedNearestStop = true;
  if (options.force === true) {
    hasUserSelectedStopManually = false;
  }
  if (options.toast !== false) {
    showToast('Closest stop set to ' + nearest.stop.name, 'success');
  }
  return true;
}

function showMyLocation() {
  shouldSetNearestStopFromLocateClick = true;
  if (userLatLng) {
    centerOnUser();
    setNearestStopFromLocation(userLatLng[0], userLatLng[1], {force:true, toast:true});
    shouldSetNearestStopFromLocateClick = false;
    return;
  }
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(onLocationSuccess, onLocationError,
      {enableHighAccuracy:true, maximumAge:0, timeout:12000});
  } else {
    showToast('Location is not available in this browser.', 'warn');
  }
}

function onLocationSuccess(pos) {
  var lat = pos.coords.latitude, lon = pos.coords.longitude, acc = pos.coords.accuracy;
  var shouldForceNearestStop = shouldSetNearestStopFromLocateClick;
  shouldSetNearestStopFromLocateClick = false;
  userLatLng = [lat, lon];
  document.getElementById('locate-btn').classList.add('tracking');
  if (!userMarker) {
    userMarker = L.marker([lat, lon], {
      icon: L.divIcon({className:'', html:'<div class="user-dot"></div>', iconSize:[16,16], iconAnchor:[8,8]}),
      zIndexOffset: 1000
    }).addTo(leafletMap).bindTooltip('You are here', {direction:'top'});
    userAccCircle = L.circle([lat, lon], {
      radius: acc, color:'#3b82f6', fillColor:'#3b82f6', fillOpacity:0.08, weight:1
    }).addTo(leafletMap);
    // center map on user the first time
    leafletMap.setView([lat, lon], 15);
  } else {
    userMarker.setLatLng([lat, lon]);
    userAccCircle.setLatLng([lat, lon]).setRadius(acc);
  }
  updateLocationBanner(lat, lon);
  updateLocationRec();
  renderSuggestedQuestions();
  renderProactiveAlert();
  setNearestStopFromLocation(lat, lon, {force:shouldForceNearestStop, toast:shouldForceNearestStop});
  if (isTourActive()) renderTourStep();
}

function onLocationError(err) {
  console.warn('Geolocation unavailable:', err.message);
  if (shouldSetNearestStopFromLocateClick) {
    shouldSetNearestStopFromLocateClick = false;
    showToast('Could not get your current location.', 'warn');
  }
}

if (navigator.geolocation) {
  navigator.geolocation.watchPosition(onLocationSuccess, onLocationError,
    {enableHighAccuracy:true, maximumAge:5000, timeout:12000});
}

shuttles = mapPayload.shuttles.map(function(s) {
  var route = mapPayload.routes[s.route];
  var pos   = positionAtProgress(route, s.progress);
  var marker = L.marker(pos, {
    icon: L.divIcon({className:'bus-hit', html:'<div class="bus-marker '+busColorClass(s.route)+'">🚌</div>',
      iconSize:[52,52], iconAnchor:[26,26]})
  }).addTo(leafletMap);
  var badge = L.marker(pos, {
    icon: L.divIcon({className:'', html:'', iconSize:[90,22], iconAnchor:[45,32]})
  }).addTo(leafletMap);
  marker.bindTooltip(s.label + ' · ' + s.route);
  marker.on('click', function() {
    var sid = s.id;
    selectedShuttleId = (selectedShuttleId === sid) ? null : sid;
    renderShuttleFloat();
  });
  return Object.assign({}, s, {marker:marker, badge:badge, lastFrame:performance.now()});
});

function setLayerVisibility(layer, visible) {
  if (visible) {
    if (!leafletMap.hasLayer(layer)) layer.addTo(leafletMap);
  } else if (leafletMap.hasLayer(layer)) {
    leafletMap.removeLayer(layer);
  }
}

function applyRouteFilter() {
  routeEntries.forEach(function(entry) {
    var routeName = entry[0], route = entry[1];
    var isVisible = !activeRoute || activeRoute === routeName;
    var layers = routeLayers[routeName];
    setLayerVisibility(layers.polyline, isVisible);
    layers.polyline.setStyle({
      weight: activeRoute === routeName ? 8 : 6,
      opacity: isVisible ? 0.95 : 0.15,
    });
    layers.stopMarkers.forEach(function(marker) {
      setLayerVisibility(marker, isVisible);
    });
  });

  shuttles.forEach(function(s) {
    var isVisible = !activeRoute || activeRoute === s.route;
    setLayerVisibility(s.marker, isVisible);
    setLayerVisibility(s.badge, isVisible);
    if (isVisible && activeRoute === s.route) {
      s.badge.setOpacity(1);
    }
  });
}

function toggleRouteFilter(routeName) {
  activeRoute = activeRoute === routeName ? null : routeName;
  applyRouteFilter();
  renderRouteCards();
  if (activeRoute) {
    leafletMap.flyToBounds(routeLayers[activeRoute].bounds, {padding:[24,24], duration:0.7});
  } else {
    leafletMap.flyTo(stopCoords(selectedStop), 15, {duration: 0.7, easeLinearity: 0.4});
  }
}

function updateMarkerVisual(s) {
  var boarding = s.dwell_seconds_remaining > 0;
  var relevanceCls = s._relevantForStop === undefined ? '' : (s._relevantForStop ? ' relevant' : '');
  var newCls = 'bus-marker ' + busColorClass(s.route) + (boarding ? ' boarding' : '') + relevanceCls;

  // Patch the existing DOM node's className instead of calling setIcon every frame.
  // setIcon tears down and rebuilds the element, causing missed clicks during replacement.
  var iconEl = s.marker.getElement();
  if (iconEl) {
    var busEl = iconEl.querySelector('.bus-marker');
    if (busEl) {
      if (busEl.className !== newCls) busEl.className = newCls;
      var badgeEl = s.badge.getElement();
      if (badgeEl) {
        var pill = badgeEl.querySelector('.boarding-pill');
        var wantPill = boarding;
        if (wantPill && !pill) {
          badgeEl.innerHTML = '<div class="boarding-pill">Boarding</div>';
        } else if (!wantPill && pill) {
          badgeEl.innerHTML = '';
        }
      }
      return;
    }
  }
  // First frame: element not in DOM yet — create icon normally.
  s.marker.setIcon(L.divIcon({className:'bus-hit',
    html:'<div class="' + newCls + '">🚌</div>',
    iconSize:[52,52], iconAnchor:[26,26]}));
  s.badge.setIcon(L.divIcon({className:'',
    html: boarding ? '<div class="boarding-pill">Boarding</div>' : '',
    iconSize:[90,22], iconAnchor:[45,32]}));
}

function refreshPopup(s) {
  // Shuttle details are shown in the custom floating window on click; no Leaflet popup needed.
}

function updateShuttleState(s, dt) {
  var route = mapPayload.routes[s.route];
  if (s.dwell_seconds_remaining > 0) {
    s.dwell_seconds_remaining = Math.max(0, s.dwell_seconds_remaining - dt);
  } else {
    var distFrac = (s.speed_mph * dt / 3600) / route.total_length;
    var nextStop = nextStopName(route, s.progress, false);
    var nsp      = nearestStopProgress(route, nextStop);
    var proposed = (s.progress + distFrac) % 1;
    if (crossedStop(s.progress, proposed, nsp)) {
      s.progress = nsp; s.current_stop = nextStop;
      s.next_stop = nextStop + ' (boarding)';
      s.dwell_seconds_remaining = stopDwell(nextStop);
    } else {
      s.progress = proposed;
      s.next_stop = nextStopName(route, s.progress, false);
    }
  }
  var ordered  = route.ordered_stop_names;
  var nextName = nextStopName(route, s.progress, s.dwell_seconds_remaining > 0);
  var ni = ordered.indexOf(nextName);
  var pi = ni > 0 ? ni-1 : ordered.length-1;
  s.current_stop = ordered[pi];
  if (s.dwell_seconds_remaining > 0) {
    s.current_stop = nextName;
    s.next_stop    = nextName + ' (boarding)';
  } else {
    s.next_stop = nextName;
  }
}

var _locRecFrame = 0;
function animate(now) {
  shuttles.forEach(function(s) {
    var dt = Math.min(1.5, (now - s.lastFrame) / 1000);
    s.lastFrame = now;
    updateShuttleState(s, dt);
    var pos = positionAtProgress(mapPayload.routes[s.route], s.progress);
    s.marker.setLatLng(pos);
    s.badge.setLatLng(pos);
    updateMarkerVisual(s);
    refreshPopup(s);
  });
  renderStopCard();
  renderShuttleFloat();
  // Refresh stop context bar and location recs every ~3 s (≈180 frames at 60 fps)
  _locRecFrame++;
  if (_locRecFrame % 180 === 0) {
    updateStopContextBar();
    updateLocationRec();
    renderProactiveAlert();
  }
  requestAnimationFrame(animate);
}

function renderStopCard() {
  var show = stopSectionVisible && (hasUserSelectedStopManually || hasAutoSelectedNearestStop);
  var floatEl = document.getElementById('stop-float');
  if (!floatEl) return;
  floatEl.style.display = show ? 'block' : 'none';
  if (!show) return;

  document.getElementById('stop-float-title').textContent = selectedStop;

  var stopRoutes = routeNamesForStop(selectedStop);
  var routePills = stopRoutes.map(function(routeName) {
    var route = mapPayload.routes[routeName];
    return '<span class="stop-route-pill" style="background:'+route.color+';">'+routeName+'</span>';
  }).join('');
  document.getElementById('stop-float-routes').innerHTML =
    '<div class="stop-routes" style="margin-top:0;margin-bottom:10px;">' + routePills + '</div>';

  var arrivals = arrivalsForStop(selectedStop);
  var html = '';
  if (!arrivals.length) {
    html = '<div style="color:#94a3b8;font-size:11px;">No shuttle approaching this stop.</div>';
  } else {
    arrivals.slice(0, 4).forEach(function(arrival, idx) {
      var s = arrival.shuttle;
      var route = mapPayload.routes[s.route];
      var delayBadge = s.delay_minutes > 0
        ? '<span style="color:#ef4444;font-size:9px;font-weight:800;margin-left:4px;">+'+s.delay_minutes+'m late</span>'
        : s.delay_minutes < 0
          ? '<span style="color:#22c55e;font-size:9px;font-weight:800;margin-left:4px;">'+Math.abs(s.delay_minutes)+'m early</span>'
          : '';
      var expressBadge = s.is_express
        ? '<span style="color:#7c3aed;font-size:9px;font-weight:800;margin-left:4px;">🚀</span>' : '';
      html += '<div style="'+(idx>0?'margin-top:8px;padding-top:8px;border-top:1px solid rgba(148,163,184,.15);':'')+
        'display:flex;align-items:center;justify-content:space-between;gap:8px;">';
      html += '<div>';
      html += '<span style="font-size:'+(idx===0?'20':'15')+'px;font-weight:900;color:#f1f5f9;">'
        +arrival.etaMinutes+' min</span>';
      html += delayBadge + expressBadge;
      html += '<div style="color:#94a3b8;font-size:10px;margin-top:2px;">'+escapeHtml(s.label)+'</div>';
      html += '</div>';
      html += '<span class="stop-route-pill" style="background:'+route.color+';font-size:9px;flex-shrink:0;">'+escapeHtml(s.route)+'</span>';
      html += '</div>';
    });
  }
  document.getElementById('stop-float-arrivals').innerHTML = html;
}

function renderRouteCards() {
  document.getElementById('route-info').innerHTML = routeEntries.map(function(e){
    var n=e[0],r=e[1];
    var isActive = activeRoute === n;
    return "<button type='button' class='card route-filter"+(isActive?" active":"")+"' onclick='toggleRouteFilter("+JSON.stringify(n)+")' style='margin-bottom:9px;border-left-color:"+r.color+";'>"
      + "<div class='route-top'>"
      + "<div>"
      + "<div class='route-title'>Route</div>"
      + '<span class="route-chip" style="background:'+r.color+';">'+n+'</span>'
      + "</div>"
      + "</div>"
      + '<div class="route-stops">'+r.ordered_stop_names.length+' stops · '+r.service_days+' · '+r.headway+'</div>'
      + '<div class="route-action">'
      + (isActive ? 'Show all routes again' : 'Focus this route on the map')
      + '</div>'
      + '</button>';
  }).join('');
}

shuttles.forEach(function(s){ updateMarkerVisual(s); });
updateSelectedStopMarkers();
highlightRelevantShuttles(selectedStop);
applyRouteFilter();
renderStopCard();
updateStopContextBar();
renderProactiveAlert();
renderRouteCards();
applyHeight();
setTimeout(applyHeight, 200);
setTimeout(function() { startTour(false); }, 700);
requestAnimationFrame(animate);
</script>
</body>
</html>"""

    # Inject stop options into the template (heights are set by JS at runtime)
    html = html_template.replace("STOP_OPTIONS_PLACEHOLDER", stop_options)
    html = html.replace("DESTINATION_OPTIONS_PLACEHOLDER", destination_options)
    # Combine data script + template
    full_html = data_script + html
    # Use a large iframe height so the JS window.innerHeight is close to real viewport.
    # The JS applyHeight() will correct any mismatch immediately.
    components.html(full_html, height=TOTAL_H, scrolling=False)


def display_main_app() -> None:
    _sync_selected_stop_from_query()
    update_shuttle_positions(advance=False)
    apply_fullscreen_shell_styles()

    # Hide Streamlit chrome and pin the iframe to fill the full viewport
    st.markdown("""
    <style>
    header, header[data-testid="stHeader"] { display:none !important; height:0 !important; }
    #MainMenu, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
      display:none !important;
      height:0 !important;
    }
    [data-testid="stSidebar"]       { display:none !important; }
    [data-testid="collapsedControl"]{ display:none !important; }
    footer { display:none !important; }
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
      margin:0 !important;
      padding:0 !important;
      height:100dvh !important;
      overflow:hidden !important;
    }
    .stMain,
    .stMainBlockContainer,
    .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="block-container"] {
      margin:0 !important;
      padding:0 !important;
      max-width:100% !important;
    }
    [data-testid="stVerticalBlock"],
    [data-testid="stElementContainer"],
    div:has(> iframe[title="st.components.v1.html"]) {
      min-height:0 !important;
    }
    div:has(> iframe[title="st.components.v1.html"]) {
      height:0 !important;
      overflow:visible !important;
    }
    /* Pin the iframe to the viewport so it always fills the screen */
    iframe,
    [data-testid="stIFrame"] iframe,
    iframe[title="st.components.v1.html"] {
      position:fixed !important;
      top:0 !important; left:0 !important;
      width:100vw !important; height:100dvh !important;
      border:none !important; z-index:999 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    render_split_app(st.session_state.user_stop, show_ai_panel=True)


initialize_app_state()

if not st.session_state.has_seen_onboarding:
    show_onboarding()
else:
    display_main_app()
