import json
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from shuttle_simulation import build_eta_prediction, initialize_simulation_state, update_shuttle_positions


st.set_page_config(
    page_title="BC Shuttle Tracker",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: 600;
    }
    .status-card {
        background: #f4f6fb;
        border-radius: 14px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .mini-route-chip {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        color: white;
        font-size: 0.8rem;
        font-weight: 700;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def initialize_app_state() -> None:
    initialize_simulation_state()
    st.session_state.eta_prediction = build_eta_prediction(st.session_state.user_stop)


def show_onboarding() -> None:
    st.title("🚌 Welcome to BC Shuttle Tracker")
    st.markdown("### Human-AI Collaboration for Reliable Transit")
    st.info("This demo now includes live route simulation so you can watch buses circulate around campus.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### What the live map shows")
        st.success(
            """
            - Colored route loops across BC and Newton
            - Moving shuttles that update every 2 seconds
            - Route-specific ETAs to your selected stop
            - Capacity and confidence cards tied to the nearest bus
            """
        )

    with col2:
        st.markdown("#### What would make it truly live")
        st.warning(
            """
            - Real GPS pings from shuttle devices
            - Official route polylines and stop order
            - Service alerts and detours from dispatch
            - Rider reports to validate actual delay/crowding
            """
        )

    st.markdown("---")
    if st.button("🚀 Open Live Map", type="primary"):
        st.session_state.has_seen_onboarding = True
        st.rerun()


def confidence_display(confidence: int) -> tuple[str, str]:
    if confidence >= 80:
        return "#02C39A", "High"
    if confidence >= 60:
        return "#028090", "Medium"
    return "#FF6B6B", "Low"


def render_feedback_section(selected_stop: str) -> None:
    eta = build_eta_prediction(selected_stop)
    best_match = eta["best_match"]
    conf_color, conf_label = confidence_display(eta["confidence"])

    st.markdown("## Human + AI Verification")
    st.caption("AI predicts the next shuttle. Riders confirm or correct it so confidence and future estimates improve.")

    left, right = st.columns([1.05, 1], gap="large")

    with left:
        st.markdown("### AI Estimate")
        if best_match:
            st.markdown(
                f"""
                <div class="status-card">
                    <div style="font-size:0.95rem;color:#6b7280;">Current best prediction for {selected_stop}</div>
                    <div style="font-size:1.9rem;font-weight:700;margin-top:0.35rem;">{eta['min']}-{eta['max']} min</div>
                    <div style="margin-top:0.35rem;">Vehicle: <strong>{best_match['label']}</strong></div>
                    <div>Route: <strong>{best_match['route']}</strong></div>
                    <div>Current segment: {best_match['current_stop']} → {best_match['next_stop']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("### Confidence")
        st.markdown(
            f"""
            <div class="status-card">
                <div style="font-size:2rem;font-weight:700;color:{conf_color};">{eta['confidence']}%</div>
                <div style="color:#6b7280;">{conf_label} confidence</div>
                <div style="margin-top:0.5rem;color:#4b5563;">
                    Based on route position, speed, dwell behavior, and recent rider feedback.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.progress(eta["confidence"] / 100)

    with right:
        st.markdown("### Verify Prediction")
        st.caption("Does this prediction look right from what you see on the ground?")

        quick1, quick2, quick3 = st.columns(3)
        with quick1:
            if st.button("✓ Accurate", use_container_width=True, type="primary"):
                st.session_state.feedback_history.append(
                    {
                        "type": "accurate",
                        "time": datetime.now(),
                        "stop": selected_stop,
                    }
                )
                st.session_state.recent_updates.append(
                    {
                        "time": datetime.now().strftime("%I:%M %p"),
                        "message": f"✅ Rider verified prediction at {selected_stop}",
                    }
                )
                st.success("Thanks. This confirmation strengthens the AI's confidence.")
                st.rerun()

        with quick2:
            if st.button("🕒 Late", use_container_width=True):
                st.session_state.show_feedback_modal = True
                st.session_state.feedback_issue_type = "Shuttle is late"
                st.rerun()

        with quick3:
            if st.button("📢 Report", use_container_width=True):
                st.session_state.show_feedback_modal = True
                st.session_state.feedback_issue_type = "Other"
                st.rerun()

        st.markdown("### Fast Crowd Signal")
        crowd1, crowd2, crowd3 = st.columns(3)
        with crowd1:
            if st.button("Seats open", use_container_width=True):
                if best_match:
                    st.session_state.feedback_history.append(
                        {
                            "type": "capacity_update",
                            "capacity_pct": 35,
                            "time": datetime.now(),
                            "stop": selected_stop,
                        }
                    )
                    st.session_state.shuttle_data[best_match["shuttle_id"]]["capacity_pct"] = 35
                st.rerun()
        with crowd2:
            if st.button("Standing room", use_container_width=True):
                if best_match:
                    st.session_state.feedback_history.append(
                        {
                            "type": "capacity_update",
                            "capacity_pct": 70,
                            "time": datetime.now(),
                            "stop": selected_stop,
                        }
                    )
                    st.session_state.shuttle_data[best_match["shuttle_id"]]["capacity_pct"] = 70
                st.rerun()
        with crowd3:
            if st.button("Full", use_container_width=True):
                if best_match:
                    st.session_state.feedback_history.append(
                        {
                            "type": "capacity_update",
                            "capacity_pct": 95,
                            "time": datetime.now(),
                            "stop": selected_stop,
                        }
                    )
                    st.session_state.shuttle_data[best_match["shuttle_id"]]["capacity_pct"] = 95
                st.rerun()

        if st.session_state.get("show_feedback_modal"):
            default_issue = st.session_state.get("feedback_issue_type", "Other")
            issue_options = [
                "Shuttle is late",
                "Shuttle is full",
                "Wrong stop shown",
                "Different route",
                "Skipped stop",
                "Other",
            ]
            default_index = issue_options.index(default_issue) if default_issue in issue_options else len(issue_options) - 1
            issue_type = st.selectbox("What happened?", issue_options, index=default_index)
            details = st.text_area(
                "Optional details",
                placeholder="Example: bus arrived 6 minutes later than predicted",
            )
            submit_col, cancel_col = st.columns(2)
            with submit_col:
                if st.button("Submit feedback", type="primary", use_container_width=True):
                    st.session_state.feedback_history.append(
                        {
                            "type": "wrong",
                            "issue": issue_type,
                            "details": details,
                            "time": datetime.now(),
                            "stop": selected_stop,
                        }
                    )
                    if best_match and "full" in issue_type.lower():
                        st.session_state.shuttle_data[best_match["shuttle_id"]]["capacity_pct"] = 95
                    st.session_state.recent_updates.append(
                        {
                            "time": datetime.now().strftime("%I:%M %p"),
                            "message": f"⚠️ Rider report at {selected_stop}: {issue_type}",
                        }
                    )
                    st.session_state.show_feedback_modal = False
                    st.success("Feedback recorded. This would feed the prediction model and rider alerts.")
                    st.rerun()
            with cancel_col:
                if st.button("Cancel feedback", use_container_width=True):
                    st.session_state.show_feedback_modal = False
                    st.rerun()

    st.markdown("### Recent Rider Feedback")
    recent_feedback = st.session_state.feedback_history[-5:]
    if recent_feedback:
        for item in reversed(recent_feedback):
            timestamp = item["time"].strftime("%I:%M %p")
            if item["type"] == "accurate":
                st.success(f"{timestamp} • Prediction confirmed at {item['stop']}")
            elif item["type"] == "capacity_update":
                st.info(f"{timestamp} • Capacity update at {item['stop']}: {item['capacity_pct']}% occupied")
            else:
                st.warning(f"{timestamp} • {item['stop']}: {item.get('issue', 'Issue reported')}")
    else:
        st.caption("No rider feedback yet. This is where the human-AI loop becomes visible.")


def build_map_payload(selected_stop: str) -> dict:
    routes = {}
    for route_name, route in st.session_state.route_definitions.items():
        ordered_stops = sorted(
            route["metrics"]["stop_progress"].items(),
            key=lambda item: item[1],
        )
        routes[route_name] = {
            "color": route["color"],
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
            }
        )

    return {
        "selected_stop": selected_stop,
        "selected_coords": st.session_state.stops[selected_stop],
        "routes": routes,
        "shuttles": shuttles,
    }


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
        .next-card {{
          background: #f4f6fb;
          border-radius: 14px;
          padding: 16px;
        }}
        .eta {{
          font-size: 46px;
          font-weight: 700;
          color: #111827;
          line-height: 1;
          margin: 8px 0 16px;
        }}
        .route-link {{
          color: #1d4ed8;
          font-weight: 700;
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
          <h2 id="stop-title"></h2>
          <div class="subtle" id="service-meta"></div>
          <h2>Fleet Status</h2>
          <div id="fleet-status"></div>
          <h2>Next Shuttle</h2>
          <div class="next-card" id="next-shuttle"></div>
        </div>
      </div>
      <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
      <script>
        const payload = {payload};
        const stopTitle = document.getElementById('stop-title');
        const serviceMeta = document.getElementById('service-meta');
        const fleetStatus = document.getElementById('fleet-status');
        const nextShuttle = document.getElementById('next-shuttle');
        const map = L.map('map', {{ zoomControl: false, attributionControl: true }}).setView(
          [payload.selected_coords.lat, payload.selected_coords.lon],
          14
        );

        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap &copy; CARTO'
        }}).addTo(map);

        const routeEntries = Object.entries(payload.routes);
        routeEntries.forEach(([routeName, route]) => {{
          L.polyline(route.path, {{
            color: route.color,
            weight: 6,
            opacity: 0.9
          }}).addTo(map).bindTooltip(routeName);

          route.stops.forEach((stop) => {{
            const isSelected = stop.name === payload.selected_stop;
            L.circleMarker([stop.lat, stop.lon], {{
              radius: isSelected ? 9 : 6,
              color: 'white',
              weight: 2,
              fillColor: isSelected ? '#111827' : route.color,
              fillOpacity: 1
            }}).addTo(map).bindPopup(`<b>${{stop.name}}</b><br>${{routeName}}`);
          }});
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
              html: `<div class="bus-marker" style="background:${{route.color}};">🚌</div>`,
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

        function updateMarkerVisual(shuttle) {{
          const route = payload.routes[shuttle.route];
          const boarding = shuttle.dwell_seconds_remaining > 0;
          shuttle.marker.setIcon(L.divIcon({{
            className: '',
            html: `<div class="bus-marker ${{boarding ? 'boarding' : ''}}" style="background:${{route.color}};">🚌</div>`,
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
          }} else {{
            shuttle.boardingBadge.setIcon(L.divIcon({{
              className: '',
              html: '',
              iconSize: [1, 1],
              iconAnchor: [0, 0]
            }}));
          }}
        }}

        function refreshPopup(shuttle) {{
          shuttle.marker.bindPopup(
            `<b>${{shuttle.label}}</b><br>` +
            `Route: ${{shuttle.route}}<br>` +
            `Current stop: ${{shuttle.current_stop}}<br>` +
            `Next stop: ${{shuttle.next_stop}}<br>` +
            `Status: ${{shuttle.dwell_seconds_remaining > 0 ? 'Boarding passengers' : 'In service'}}<br>` +
            `Capacity: ${{shuttle.capacity}} (${{shuttle.capacity_pct}}%)`
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
          renderSidePanel();
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
              return {{
                shuttle,
                etaMinutes
              }};
            }})
            .sort((a, b) => a.etaMinutes - b.etaMinutes);
        }}

        function renderSidePanel() {{
          const primaryRoute = payload.routes[Object.keys(payload.routes)[0]];
          stopTitle.textContent = payload.selected_stop;
          serviceMeta.textContent = `${{primaryRoute.service_days}} service: ${{primaryRoute.service_window}} (${{primaryRoute.headway}})`;

          fleetStatus.innerHTML = shuttles.map((shuttle) => {{
            const boarding = shuttle.dwell_seconds_remaining > 0;
            const accent = boarding ? '#b91c1c' : '#1d4ed8';
            const detail = boarding
              ? `Stopped at ${{shuttle.current_stop}}`
              : `${{shuttle.current_stop}} -> ${{shuttle.next_stop}}`;
            return `
              <div class="card" style="border-left-color:${{accent}};">
                <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;">
                  <div>
                    <div class="title">${{shuttle.label}}</div>
                    <div class="body">${{detail}}</div>
                  </div>
                  <div style="text-align:right;">
                    <div class="status" style="color:${{accent}};">${{boarding ? 'Boarding' : 'In service'}}</div>
                    <div class="body">${{Math.max(0, Math.round(shuttle.dwell_seconds_remaining))}}s dwell</div>
                  </div>
                </div>
              </div>
            `;
          }}).join('');

          const arrivals = arrivalsForSelectedStop();
          if (!arrivals.length) {{
            nextShuttle.innerHTML = `<div class="title">No service</div>`;
            return;
          }}

          const best = arrivals[0];
          const etaMin = Math.max(1, best.etaMinutes - 1);
          const etaMax = best.etaMinutes + 2;
          nextShuttle.innerHTML = `
            <div class="body">Predicted Arrival</div>
            <div class="eta">${{etaMin}}-${{etaMax}} min</div>
            <div class="title">Best option</div>
            <div class="body" style="margin-top:8px;">${{best.shuttle.label}}</div>
            <div class="body">Route: <span class="route-link">${{best.shuttle.route}}</span></div>
            <div class="body">${{best.shuttle.dwell_seconds_remaining > 0 ? 'Currently boarding at' : 'Heading to'}} ${{best.shuttle.next_stop}}</div>
            <div class="body">${{best.shuttle.capacity}} • ${{best.shuttle.capacity_pct}}% occupied</div>
          `;
        }}

        shuttles.forEach((shuttle) => {{
          updateMarkerVisual(shuttle);
          refreshPopup(shuttle);
        }});
        renderSidePanel();
        requestAnimationFrame(animate);
      </script>
    </body>
    </html>
    """
    components.html(html, height=640)


def display_sidebar() -> str:
    with st.sidebar:
        st.header("📍 Your Stop")
        selected_stop = st.selectbox(
            "Select your stop:",
            sorted(st.session_state.stops.keys()),
            index=sorted(st.session_state.stops.keys()).index(st.session_state.user_stop),
        )
        if selected_stop != st.session_state.user_stop:
            st.session_state.user_stop = selected_stop
            st.session_state.eta_prediction = build_eta_prediction(selected_stop)
            st.rerun()

        routes = st.session_state.stops[selected_stop]["routes"]
        route_html = "".join(
            f'<span class="mini-route-chip" style="background:{st.session_state.route_definitions[route]["color"]};">{route}</span>'
            for route in routes
        )
        st.markdown("**Routes serving this stop**", unsafe_allow_html=True)
        st.markdown(route_html, unsafe_allow_html=True)

        primary_route = st.session_state.route_definitions[routes[0]]
        st.caption(
            f"{primary_route['service_days']} • {primary_route['service_window']} • {primary_route['headway']}"
        )

        st.divider()
        st.markdown("### 🔄 Recent Updates")
        if st.session_state.recent_updates:
            for update in st.session_state.recent_updates[-4:]:
                st.info(f"🕐 {update['time']}\n{update['message']}")
        else:
            st.caption("No recent updates")

        if st.session_state.system_alerts:
            st.divider()
            st.markdown("### 🚨 Active Alerts")
            for alert in st.session_state.system_alerts[-3:]:
                st.warning(alert["message"])

        st.divider()
        st.info("This version uses simulated moving buses. Replace the simulator with real GPS feed data later for production.")
        if st.button("🔄 Reset Onboarding"):
            st.session_state.has_seen_onboarding = False
            st.rerun()

    return selected_stop


def display_main_app() -> None:
    update_shuttle_positions(advance=False)

    st.title("🚌 BC Shuttle Tracker")
    st.caption("Live shuttle simulation with moving buses, route overlays, and route-aware ETAs")

    selected_stop = display_sidebar()
    if selected_stop != st.session_state.user_stop:
        st.session_state.user_stop = selected_stop

    metric1, metric2, metric3 = st.columns(3)
    with metric1:
        st.metric("Active Routes", len(st.session_state.route_definitions))
    with metric2:
        st.metric("Buses in Service", len(st.session_state.shuttle_data))
    with metric3:
        st.metric("Map Motion", "Continuous")

    st.subheader("🗺️ Live Shuttle Map")
    last_updated = st.session_state.simulation_last_updated.strftime("%I:%M:%S %p")
    st.caption(f"Map initialized at {last_updated} • buses and status cards now animate from the same browser-side state")
    render_live_dashboard(st.session_state.user_stop)
    st.caption("Both buses should pause at every stop, and the fleet panel should update at the same moment because it now uses the same live animation state as the map.")
    st.divider()
    render_feedback_section(st.session_state.user_stop)

    with st.expander("🛠️ How This Live Map Works"):
        st.markdown(
            """
            1. Each shuttle is assigned to the Commonwealth route loop.
            2. The map and fleet panel now run from the same browser-side animation state.
            3. Every shuttle pauses at each stop for a dwell period to simulate boarding.
            4. The next-shuttle card is computed from the same live positions shown on the map.
            5. Riders can confirm or correct predictions, which is the human-in-the-loop layer for improving trust and estimate quality.
            """
        )


initialize_app_state()

if not st.session_state.has_seen_onboarding:
    show_onboarding()
else:
    display_main_app()
