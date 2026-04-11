import json
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

from interaction_ui import apply_shared_styles
from shuttle_simulation import (
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


def initialize_app_state() -> None:
    initialize_simulation_state()


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
                "delay_minutes": shuttle.get("delay_minutes", 0),
                "is_express": shuttle.get("is_express", False),
            }
        )

    return {
        "selected_stop": selected_stop,
        "selected_coords": st.session_state.stops[selected_stop],
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
        f'<img src="{svg_src}" alt="{_capacity_label(capacity_pct)} crowd graphic" style="width:125px;height:40px;display:block;" />'
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
            delay_badge = f'<span style="background:#fef2f2;color:#dc2626;font-weight:700;padding:2px 10px;border-radius:999px;font-size:0.85rem;">⚠️ +{delay} min delay</span>'
        elif delay < 0:
            delay_badge = f'<span style="background:#f0fdf4;color:#16a34a;font-weight:700;padding:2px 10px;border-radius:999px;font-size:0.85rem;">⏰ Running {abs(delay)} min early</span>'
        else:
            delay_badge = '<span style="background:#f0fdf4;color:#16a34a;font-weight:700;padding:2px 10px;border-radius:999px;font-size:0.85rem;">✅ On time</span>'
        express_badge = '<span style="background:#f5f3ff;color:#7c3aed;font-weight:700;padding:2px 10px;border-radius:999px;font-size:0.85rem;">🚀 Express</span>' if best.get("is_express") else ""
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
            arrival_delay_badge = f'<span style="color:#dc2626;font-weight:700;font-size:0.8rem;">⚠️ +{delay} min delay</span>'
        elif delay < 0:
            arrival_delay_badge = f'<span style="color:#16a34a;font-weight:700;font-size:0.8rem;">⏰ {abs(delay)} min early</span>'
        else:
            arrival_delay_badge = ""
        arrival_express_badge = '<span style="color:#7c3aed;font-weight:700;font-size:0.8rem;">🚀 Express</span>' if arrival.get("is_express") else ""
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
    "Shuttle IDs: comm-1=Comm Ave 1, comm-2=Comm Ave 2, newton-1=Newton Express 1, newton-2=Newton Express 2. "
    "When a user reports or clears a delay, append at the very end of your reply EXACTLY: "
    "DELAY_UPDATE:{shuttle_id:SHUTTLE_ID,delay_minutes:NUMBER} "
    "Use delay_minutes 0 to clear. Only include this when the user explicitly reports or clears a delay. "
    "Be friendly, concise, and accurate."
)


def render_split_app(selected_stop: str) -> None:  # noqa: PLR0915 (long but intentional)
    TOTAL_H = 900   # iframe height — JS applyHeight() adjusts to actual window.innerHeight
    payload = build_map_payload(selected_stop)
    # Inject data as JSON into a separate <script> block so the HTML template
    # stays a plain (non-f-string) string and can never be corrupted by the data.
    payload_json      = json.dumps(payload)
    system_prompt_json = json.dumps(_AI_SYSTEM_PROMPT)
    init_time         = json.dumps(st.session_state.simulation_last_updated.strftime("%I:%M:%S %p"))
    stop_options = "".join(
        '<option value="{v}"{sel}>{v}</option>'.format(
            v=name,
            sel=" selected" if name == selected_stop else "",
        )
        for name in sorted(st.session_state.stops.keys())
    )

    # Data-only f-string — just numbers and pre-validated JSON blobs
    data_script = (
        f"<script>"
        f"var TOTAL_H={TOTAL_H};"
        f"var mapPayload={payload_json};"
        f"var SYSTEM_PROMPT={system_prompt_json};"
        f"var INIT_TIME={init_time};"
        f"</script>"
    )

    # HTML template — raw string so JS regex backslashes are safe.
    html_template = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  * {box-sizing:border-box;margin:0;padding:0;}
  html,body {height:100%;overflow:hidden;background:#0f172a;color:#f1f5f9;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}
  #app {display:flex;width:100%;overflow:hidden;}

  /* AI panel */
  #ai-panel {width:420px;min-width:260px;max-width:70%;
    display:flex;flex-direction:column;background:#1e293b;border-right:1px solid #334155;overflow:hidden;}
  #ai-header {padding:12px 14px 10px;border-bottom:1px solid #334155;flex-shrink:0;}
  #ai-title  {font-size:14px;font-weight:700;color:#f1f5f9;margin-bottom:8px;}
  #key-row   {display:flex;gap:6px;margin-bottom:7px;}
  #api-key   {flex:1;background:#0f172a;border:1px solid #334155;color:#f1f5f9;
    padding:6px 10px;border-radius:6px;font-size:12px;outline:none;}
  #api-key:focus {border-color:#3b82f6;}
  #clear-btn {background:#374151;color:#9ca3af;border:none;padding:6px 10px;
    border-radius:6px;cursor:pointer;font-size:13px;flex-shrink:0;}
  #clear-btn:hover {background:#4b5563;color:#f1f5f9;}
  #stop-row  {display:flex;align-items:center;gap:6px;}
  #stop-lbl  {font-size:11px;color:#64748b;white-space:nowrap;}
  #stop-sel  {flex:1;background:#0f172a;border:1px solid #334155;color:#f1f5f9;
    padding:4px 8px;border-radius:6px;font-size:12px;outline:none;}
  #chat-box  {flex:1;min-height:0;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px;}
  #chat-box::-webkit-scrollbar {width:4px;}
  #chat-box::-webkit-scrollbar-thumb {background:#334155;border-radius:2px;}
  .msg-user  {align-self:flex-end;background:#1d4ed8;color:#fff;padding:8px 12px;
    border-radius:14px 14px 3px 14px;max-width:88%;font-size:13px;line-height:1.5;word-wrap:break-word;}
  .msg-ai    {align-self:flex-start;background:#1e3a5f;color:#e2e8f0;padding:8px 12px;
    border-radius:14px 14px 14px 3px;max-width:88%;font-size:13px;line-height:1.5;word-wrap:break-word;}
  .msg-err   {align-self:center;background:#7f1d1d;color:#fca5a5;padding:6px 10px;
    border-radius:8px;font-size:12px;max-width:90%;}
  .placeholder {color:#475569;font-size:12px;text-align:center;padding:20px 10px;line-height:1.9;}
  .delay-ok  {display:inline-block;margin-top:5px;padding:2px 8px;border-radius:999px;
    font-size:11px;font-weight:700;background:#d1fae5;color:#065f46;}
  .delay-warn{display:inline-block;margin-top:5px;padding:2px 8px;border-radius:999px;
    font-size:11px;font-weight:700;background:#fef3c7;color:#92400e;}
  #thinking  {align-self:flex-start;background:#1e3a5f;padding:10px 14px;
    border-radius:14px 14px 14px 3px;}
  .dot       {display:inline-block;width:7px;height:7px;background:#94a3b8;border-radius:50%;
    animation:blink 1.2s infinite;margin:0 2px;}
  .dot:nth-child(2){animation-delay:.2s;} .dot:nth-child(3){animation-delay:.4s;}
  @keyframes blink {0%,80%,100%{transform:scale(1);opacity:.5;}40%{transform:scale(1.3);opacity:1;}}
  #input-row {padding:9px;border-top:1px solid #334155;display:flex;gap:6px;flex-shrink:0;}
  #user-inp  {flex:1;background:#0f172a;border:1px solid #334155;color:#f1f5f9;
    padding:8px 12px;border-radius:8px;font-size:13px;outline:none;}
  #user-inp:focus {border-color:#3b82f6;}
  #send-btn  {background:#3b82f6;color:#fff;border:none;padding:8px 14px;border-radius:8px;
    cursor:pointer;font-size:13px;font-weight:600;flex-shrink:0;}
  #send-btn:hover {background:#2563eb;}
  #send-btn:disabled {background:#374151;color:#6b7280;cursor:not-allowed;}

  /* Drag handle */
  #drag-handle {width:6px;flex-shrink:0;background:#1e293b;cursor:col-resize;
    display:flex;align-items:center;justify-content:center;
    border-left:1px solid #334155;border-right:1px solid #334155;user-select:none;}
  #drag-handle:hover,#drag-handle.dragging {background:#3b82f6;border-color:#3b82f6;}
  #drag-handle::after {content:'⋮';color:#475569;font-size:12px;}
  #drag-handle:hover::after,#drag-handle.dragging::after {color:#fff;}

  /* Map panel */
  #map-panel  {flex:1;display:flex;flex-direction:column;min-width:300px;overflow:hidden;}
  #map-header {padding:10px 16px;background:#1e293b;border-bottom:1px solid #334155;
    display:flex;align-items:center;gap:12px;flex-shrink:0;height:44px;}
  #map-header h2 {font-size:15px;font-weight:700;color:#f1f5f9;}
  #map-header span {font-size:11px;color:#64748b;}
  #map-body   {display:grid;grid-template-columns:1fr 240px;overflow:hidden;}
  #map        {width:100%;}
  #route-side {background:#fff;overflow-y:auto;padding:12px;
    font-family:sans-serif;font-size:12px;color:#111;}
  #route-side h3 {font-size:14px;margin:8px 0 6px;color:#1f2937;font-weight:800;letter-spacing:-.01em;}
  .card       {background:linear-gradient(180deg,#f7f9ff 0%,#eef2ff 100%);border-radius:18px;padding:14px 14px 13px;margin-bottom:12px;
    border-left:4px solid #cbd5e1;}
  .card .title{font-weight:700;font-size:12px;color:#111827;}
  .card .body {color:#4b5563;margin-top:3px;font-size:11px;line-height:1.4;}
  .stop-card {padding:14px 14px 12px;}
  .stop-card .title {font-size:12px;font-weight:900;line-height:1.18;letter-spacing:-.02em;word-break:break-word;}
  .stop-routes {display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;}
  .stop-route-pill {display:inline-flex;align-items:center;padding:5px 10px;border-radius:999px;
    color:#fff;font-size:9px;font-weight:800;letter-spacing:.01em;max-width:100%;line-height:1.2;}
  .stop-metric {margin-top:12px;padding-top:11px;border-top:1px solid rgba(148,163,184,.22);}
  .stop-metric-label {font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;}
  .stop-metric-value {margin-top:5px;font-size:18px;font-weight:900;color:#0f172a;line-height:1.02;letter-spacing:-.02em;}
  .stop-metric-detail {margin-top:5px;color:#475569;font-size:10px;line-height:1.4;}
  .stop-capacity-badge {display:inline-flex;align-items:center;padding:5px 10px;border-radius:999px;
    background:#dbeafe;color:#1d4ed8;font-size:10px;font-weight:800;}
  .capacity-people {display:flex;gap:5px;align-items:flex-end;margin-top:10px;margin-bottom:8px;flex-wrap:wrap;}
  .capacity-person {position:relative;width:8px;height:20px;opacity:.26;}
  .capacity-person.active {opacity:1;}
  .capacity-person::before {content:'';position:absolute;left:1px;top:0;width:6px;height:6px;border-radius:50%;background:currentColor;}
  .capacity-person::after {content:'';position:absolute;left:2px;top:7px;width:4px;height:11px;border-radius:3px;background:currentColor;box-shadow:-3px 2px 0 0 currentColor,3px 2px 0 0 currentColor,-2px 10px 0 0 currentColor,2px 10px 0 0 currentColor;}
  .stop-inline-route {font-weight:800;color:#1e40af;}
  .route-chip {display:inline-flex;align-items:center;gap:6px;color:#fff;border-radius:999px;padding:8px 14px;
    font-size:11px;font-weight:800;letter-spacing:.01em;margin-top:2px;box-shadow:inset 0 -1px 0 rgba(255,255,255,.18);}
  .route-top {min-width:0;}
  .route-chip {max-width:100%;white-space:nowrap;}
  .route-filter {width:100%;text-align:left;cursor:pointer;transition:transform .15s ease, box-shadow .15s ease, border-color .15s ease, background .15s ease;
    border-left-width:4px;border-left-style:solid;border-top:none;border-right:none;border-bottom:none;box-shadow:0 8px 20px rgba(148,163,184,.14);}
  .route-filter:hover {transform:translateY(-2px);box-shadow:0 14px 28px rgba(15,23,42,.14);}
  .route-filter:focus-visible {outline:none;box-shadow:0 0 0 3px rgba(37,99,235,.22),0 14px 28px rgba(15,23,42,.14);}
  .route-filter.active {background:linear-gradient(180deg,#eef4ff 0%,#dbeafe 100%);box-shadow:0 0 0 2px rgba(29,78,216,.16),0 14px 28px rgba(59,130,246,.18);}
  .route-filter .route-top {display:flex;align-items:flex-start;justify-content:space-between;gap:10px;}
  .route-filter .route-title {font-size:12px;font-weight:900;letter-spacing:.08em;text-transform:uppercase;color:#64748b;}
  .route-filter .route-stops {margin-top:10px;font-size:13px;font-weight:700;color:#334155;line-height:1.45;}
  .route-filter .route-action {margin-top:10px;font-size:11px;font-weight:700;color:#1d4ed8;display:flex;align-items:center;gap:6px;}
  .route-filter.active .route-action {color:#1e40af;}
  .legend     {background:#fff;padding:7px 9px;border-radius:7px;
    box-shadow:0 3px 10px rgba(0,0,0,.15);font-size:11px;line-height:1.5;}
  .legend-dot {display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;}
  .bus-marker {width:32px;height:32px;border-radius:50%;border:3px solid #fff;
    box-shadow:0 2px 6px rgba(0,0,0,.3);display:flex;align-items:center;
    justify-content:center;font-size:16px;}
  .bus-marker.boarding {box-shadow:0 0 0 5px rgba(255,255,255,.35),0 2px 6px rgba(0,0,0,.3);}
  .boarding-pill {background:rgba(17,24,39,.9);color:#fff;border-radius:999px;
    padding:3px 8px;font-size:11px;font-weight:700;white-space:nowrap;}
</style>
</head>
<body>
<div id="app">

  <div id="ai-panel">
    <div id="ai-header">
      <div id="ai-title">🤖 AI Shuttle Assistant</div>
      <div id="key-row">
        <input id="api-key" type="password" placeholder="OpenAI API key  sk-..." autocomplete="off"/>
        <button id="clear-btn" onclick="clearChat()" title="Clear chat">🗑️</button>
      </div>
      <div id="stop-row">
        <span id="stop-lbl">Your stop:</span>
        <select id="stop-sel" onchange="onStopChange(this.value)">STOP_OPTIONS_PLACEHOLDER</select>
      </div>
    </div>
    <div id="chat-box">
      <div class="placeholder">💡 Try asking:<br>
        "When's the next shuttle to Conte Forum?"<br>
        "Newton express is 10 minutes late."<br>
        "How crowded is the Comm Ave shuttle?"
      </div>
    </div>
    <div id="input-row">
      <input id="user-inp" type="text" placeholder="Ask about shuttles or report a delay…"/>
      <button id="send-btn">Send ➤</button>
    </div>
  </div>

  <div id="drag-handle"></div>

  <div id="map-panel">
    <div id="map-header">
      <h2>🗺️ Live Shuttle Map</h2>
      <span id="map-ts"></span>
    </div>
    <div id="map-body">
      <div id="map" style="width:100%;"></div>
      <div id="route-side">
        <h3>Your Stop</h3>
        <div class="card stop-card">
          <div class="title" id="stop-title"></div>
          <div class="body"  id="service-meta"></div>
        </div>
        <h3>Routes</h3>
        <div id="route-info"></div>
      </div>
    </div>
  </div>

</div>
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
function arrivalsForStop(stopName) {
  return (shuttles||[])
    .filter(function(s){ return mapPayload.routes[s.route].stop_progress[stopName] !== undefined; })
    .map(function(s) {
      var route = mapPayload.routes[s.route];
      var sp    = route.stop_progress[stopName];
      var delta = (sp - s.progress + 1) % 1;
      var miles = delta * route.total_length;
      var eta   = Math.max(1, Math.round(miles / Math.max(s.speed_mph,1) * 60));
      return {shuttle:s, etaMinutes: Math.max(1, eta + (s.delay_minutes||0))};
    })
    .sort(function(a,b){ return a.etaMinutes - b.etaMinutes; });
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
  var mapH = h - 44; // subtract map header
  document.getElementById('app').style.height      = h + 'px';
  document.getElementById('ai-panel').style.height = h + 'px';
  document.getElementById('drag-handle').style.height = h + 'px';
  document.getElementById('map-panel').style.height   = h + 'px';
  document.getElementById('map-body').style.height    = mapH + 'px';
  document.getElementById('map').style.height         = mapH + 'px';
  document.getElementById('route-side').style.height  = mapH + 'px';
  if (typeof leafletMap !== 'undefined' && leafletMap) {
    leafletMap.invalidateSize();
  }
}
applyHeight();
window.addEventListener('resize', applyHeight);

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
var chatHistory = [];
try { chatHistory = JSON.parse(sessionStorage.getItem('bc_chat') || '[]'); } catch(e){}

function saveChatHistory() {
  try { sessionStorage.setItem('bc_chat', JSON.stringify(chatHistory)); } catch(e){}
}

function appendMsg(role, html, badgeText, badgeOk) {
  var box = document.getElementById('chat-box');
  // remove placeholder
  var ph = box.querySelector('.placeholder');
  if (ph) ph.parentNode.removeChild(ph);
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
  saveChatHistory();
  var box = document.getElementById('chat-box');
  box.innerHTML = '<div class="placeholder">💡 Try asking:<br>"When\'s the next shuttle to Conte Forum?"<br>"Newton express is 10 minutes late."</div>';
}

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

function onStopChange(name) {
  selectedStop = name;
  document.getElementById('stop-sel').value = name;
  updateSelectedStopMarkers();
  renderStopCard();
  leafletMap.setView(stopCoords(name), 14);
}

function buildContext() {
  var time = new Date().toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'});
  var lines = ['Current time: '+time, '', '=== LIVE SHUTTLE STATUS ==='];
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
  });
  lines.push('','=== UPCOMING ARRIVALS at '+selectedStop+' ===');
  var arr = arrivalsForStop(selectedStop);
  if (arr.length) {
    arr.slice(0,4).forEach(function(a){
      lines.push('  - '+a.shuttle.label+' ('+a.shuttle.route+'): '+a.etaMinutes+' min away, capacity '+a.shuttle.capacity_pct+'%');
    });
  } else { lines.push('  No arrivals found.'); }
  return lines.join('\n');
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

async function sendMessage() {
  var apiKey  = document.getElementById('api-key').value.trim();
  var inputEl = document.getElementById('user-inp');
  var sendBtn = document.getElementById('send-btn');
  var userMsg = inputEl.value.trim();
  if (!apiKey) { appendMsg('err', 'Please enter your OpenAI API key at the top.'); return; }
  if (!userMsg) return;

  inputEl.value = '';
  sendBtn.disabled = true;

  appendMsg('user', userMsg.replace(/</g,'&lt;'));
  chatHistory.push({role:'user', content:userMsg});

  var box = document.getElementById('chat-box');
  var thinking = document.createElement('div');
  thinking.id = 'thinking';
  thinking.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  box.appendChild(thinking); box.scrollTop = box.scrollHeight;

  try {
    var sysMsg = SYSTEM_PROMPT + '\n\n' + buildContext();
    var messages = [{role:'system', content:sysMsg}];
    chatHistory.slice(-10).forEach(function(m){ messages.push({role:m.role, content:m.content}); });

    var resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {'Content-Type':'application/json','Authorization':'Bearer '+apiKey},
      body: JSON.stringify({model:'gpt-4o-mini', messages:messages, temperature:0.3, max_tokens:600})
    });
    if (!resp.ok) {
      var errData = {}; try { errData = await resp.json(); } catch(e){}
      throw new Error((errData.error && errData.error.message) || resp.statusText);
    }
    var data    = await resp.json();
    var raw     = data.choices[0].message.content;
    var parsed  = parseDelay(raw);
    var clean   = parsed.clean;
    var badgeText = null, badgeOk = false;

    if (parsed.shuttleId) {
      var found = (shuttles||[]).filter(function(s){ return s.id === parsed.shuttleId; });
      if (found.length) {
        found[0].delay_minutes = parsed.mins;
        badgeOk   = parsed.mins === 0;
        badgeText = badgeOk
          ? '✅ Delay cleared for ' + found[0].label
          : '⚠️ Applied: ' + found[0].label + ' ' + (parsed.mins>0?'+':'') + parsed.mins + ' min';
      }
    }

    if (thinking.parentNode) thinking.parentNode.removeChild(thinking);
    appendMsg('ai', clean.replace(/\n/g,'<br>').replace(/</g,'&lt;').replace(/&lt;br>/g,'<br>'), badgeText, badgeOk);
    chatHistory.push({role:'assistant', content:clean});
    saveChatHistory();
  } catch(e) {
    if (thinking.parentNode) thinking.parentNode.removeChild(thinking);
    appendMsg('err', 'Error: ' + e.message);
  }
  sendBtn.disabled = false;
}

// ── restore chat from sessionStorage ─────────────────────────────────────────
(function restoreChat(){
  if (!chatHistory.length) return;
  var box = document.getElementById('chat-box');
  box.innerHTML = '';
  chatHistory.forEach(function(m){
    var div = document.createElement('div');
    div.className = m.role==='user' ? 'msg-user' : 'msg-ai';
    div.innerHTML = m.content.replace(/\n/g,'<br>').replace(/</g,'&lt;').replace(/&lt;br>/g,'<br>');
    box.appendChild(div);
  });
  box.scrollTop = box.scrollHeight;
})();

// ── map ───────────────────────────────────────────────────────────────────────
document.getElementById('map-ts').textContent = 'Initialized at ' + INIT_TIME + ' · buses update in real time';

var selectedStop = mapPayload.selected_stop;
var leafletMap;
var shuttles;
var activeRoute = mapPayload.selected_route_filter && mapPayload.selected_route_filter !== 'All routes'
  ? mapPayload.selected_route_filter
  : null;
var routeLayers = {};
var stopMarkersByName = {};

var routeEntries = Object.entries(mapPayload.routes);
leafletMap = L.map('map', {zoomControl:false, attributionControl:true})
  .setView([mapPayload.selected_coords.lat, mapPayload.selected_coords.lon], 14);

L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
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
      onStopChange(stop.name);
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

shuttles = mapPayload.shuttles.map(function(s) {
  var route = mapPayload.routes[s.route];
  var pos   = positionAtProgress(route, s.progress);
  var marker = L.marker(pos, {
    icon: L.divIcon({className:'', html:'<div class="bus-marker" style="background:'+route.color+';">🚌</div>',
      iconSize:[32,32], iconAnchor:[16,16]})
  }).addTo(leafletMap);
  var badge = L.marker(pos, {
    icon: L.divIcon({className:'', html:'', iconSize:[90,22], iconAnchor:[45,32]})
  }).addTo(leafletMap);
  marker.bindTooltip(s.label + ' · ' + s.route);
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
    leafletMap.fitBounds(routeLayers[activeRoute].bounds, {padding:[24,24]});
  } else {
    leafletMap.setView([mapPayload.selected_coords.lat, mapPayload.selected_coords.lon], 14);
  }
}

function updateMarkerVisual(s) {
  var route   = mapPayload.routes[s.route];
  var boarding = s.dwell_seconds_remaining > 0;
  s.marker.setIcon(L.divIcon({className:'',
    html:'<div class="bus-marker'+(boarding?' boarding':'')+'" style="background:'+route.color+';">🚌</div>',
    iconSize:[32,32], iconAnchor:[16,16]}));
  s.badge.setIcon(L.divIcon({className:'',
    html: boarding ? '<div class="boarding-pill">Boarding</div>' : '',
    iconSize:[90,22], iconAnchor:[45,32]}));
}

function refreshPopup(s) {
  var delay = s.delay_minutes > 0
    ? '<br><span style="color:#dc2626;font-weight:700;">⚠️ +'+s.delay_minutes+' min late</span>'
    : s.delay_minutes < 0
      ? '<br><span style="color:#16a34a;font-weight:700;">⏰ '+Math.abs(s.delay_minutes)+' min early</span>' : '';
  var expr = s.is_express ? '<br><span style="color:#7c3aed;font-weight:700;">🚀 Express</span>' : '';
  s.marker.bindPopup('<b>'+s.label+'</b><br>Route: '+s.route+'<br>Stop: '+s.current_stop+
    '<br>Next: '+s.next_stop+'<br>Capacity: '+s.capacity+' ('+s.capacity_pct+'%)'+delay+expr);
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
  requestAnimationFrame(animate);
}

function renderStopCard() {
  var stopRoutes = routeNamesForStop(selectedStop);
  var arrivals = arrivalsForStop(selectedStop);
  var nextArrival = arrivals.length ? arrivals[0] : null;
  document.getElementById('stop-title').textContent = selectedStop;
  document.getElementById('service-meta').innerHTML =
    '<div class="stop-routes">' +
    stopRoutes.map(function(routeName) {
      var route = mapPayload.routes[routeName];
      return '<span class="stop-route-pill" style="background:'+route.color+';">'+routeName+'</span>';
    }).join('') +
    '</div>' +
    (nextArrival
      ? '<div class="stop-metric">' +
          '<div class="stop-metric-label">Next Bus</div>' +
          '<div class="stop-metric-value">'+nextArrival.etaMinutes+' min</div>' +
          '<div class="stop-metric-detail">'+nextArrival.shuttle.label+' on <span class="stop-inline-route">'+nextArrival.shuttle.route+'</span></div>' +
        '</div>' +
        '<div class="stop-metric">' +
          '<div class="stop-metric-label">Current Capacity</div>' +
          '<div class="stop-capacity-badge">'+nextArrival.shuttle.capacity+' · '+nextArrival.shuttle.capacity_pct+'%</div>' +
          capacityPeopleHtml(nextArrival.shuttle.capacity_pct) +
        '</div>'
      : '<div class="stop-metric">' +
          '<div class="stop-metric-label">Next Bus</div>' +
          '<div class="stop-metric-value">No live bus</div>' +
          '<div class="stop-metric-detail">No shuttle on the selected route is currently approaching this stop.</div>' +
        '</div>');
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

shuttles.forEach(function(s){ updateMarkerVisual(s); refreshPopup(s); });
updateSelectedStopMarkers();
applyRouteFilter();
renderStopCard();
renderRouteCards();
applyHeight();
setTimeout(applyHeight, 200);
requestAnimationFrame(animate);
</script>
</body>
</html>"""

    # Inject stop options into the template (heights are set by JS at runtime)
    html = html_template.replace("STOP_OPTIONS_PLACEHOLDER", stop_options)
    # Combine data script + template
    full_html = data_script + html
    # Use a large iframe height so the JS window.innerHeight is close to real viewport.
    # The JS applyHeight() will correct any mismatch immediately.
    components.html(full_html, height=TOTAL_H, scrolling=False)


def display_main_app() -> None:
    update_shuttle_positions(advance=False)

    # Hide Streamlit chrome so the split-pane fills the viewport
    st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility:hidden; height:0; }
    [data-testid="stSidebar"]       { display:none !important; }
    [data-testid="collapsedControl"]{ display:none !important; }
    .stMainBlockContainer { padding:0 !important; max-width:100% !important; }
    .stMain > div:first-child { padding:0 !important; }
    footer { display:none; }
    </style>
    """, unsafe_allow_html=True)

    render_split_app(st.session_state.user_stop)


initialize_app_state()

if not st.session_state.has_seen_onboarding:
    show_onboarding()
else:
    display_main_app()
