from __future__ import annotations

import logging
import math
import re
from datetime import datetime

import streamlit as st

_log = logging.getLogger(__name__)

SIMULATION_TIME_SCALE = 1.0
STOP_PROXIMITY_THRESHOLD = 0.012
SIMULATION_VERSION = "boarding-seed-v4"


BC_ROUTES = {
    "Comm Ave All Stops": {
        "color": "#1d4ed8",
        "service_days": "Weekdays",
        "service_window": "5:00pm - 2:00am",
        "headway": "Every 10 - 15 Minutes",
        "path": [
            (42.335945, -71.167993),
            (42.335872, -71.167625),
            (42.336207, -71.166462),
            (42.335755, -71.165252),
            (42.335355, -71.163777),
            (42.335198, -71.162977),
            (42.334279, -71.162442),
            (42.333823, -71.164708),
            (42.333564, -71.167158),
            (42.333196, -71.170327),
            (42.333026, -71.172860),
            (42.333475, -71.172676),
            (42.334195, -71.172056),
            (42.335061, -71.171631),
            (42.336063, -71.171576),
            (42.336959, -71.172011),
            (42.337347, -71.171808),
            (42.337974, -71.171072),
            (42.338554, -71.170470),
            (42.339228, -71.169101),
            (42.339780, -71.166995),
            (42.339897, -71.165890),
            (42.339963, -71.161273),
            (42.339788, -71.159100),
            (42.339002, -71.156344),
            (42.338335, -71.154913),
            (42.337719, -71.153045),
            (42.335881, -71.150990),
            (42.334678, -71.148946),
            (42.334757, -71.148675),
            (42.334994, -71.148820),
            (42.335080, -71.149535),
            (42.335742, -71.150465),
            (42.336484, -71.151267),
            (42.337435, -71.152448),
            (42.338008, -71.153078),
            (42.338252, -71.152680),
            (42.338893, -71.152250),
            (42.339614, -71.151805),
            (42.340502, -71.150791),
            (42.341135, -71.149601),
            (42.341381, -71.147945),
            (42.341476, -71.145878),
            (42.341733, -71.145831),
            (42.341885, -71.145930),
            (42.341847, -71.146371),
            (42.341832, -71.147150),
            (42.341849, -71.148323),
            (42.341746, -71.149222),
            (42.341057, -71.150667),
            (42.340560, -71.151289),
            (42.339885, -71.152035),
            (42.339034, -71.152607),
            (42.338397, -71.153096),
            (42.338230, -71.153602),
            (42.338368, -71.154297),
            (42.338621, -71.154919),
            (42.339628, -71.157347),
            (42.340031, -71.159095),
            (42.340211, -71.161142),
            (42.340276, -71.163957),
            (42.340155, -71.166000),
            (42.340034, -71.166133),
            (42.339785, -71.166104),
            (42.339275, -71.166098),
            (42.339103, -71.166514),
            (42.338698, -71.167653),
            (42.338206, -71.168818),
            (42.337718, -71.168946),
            (42.337335, -71.168595),
            (42.336727, -71.168361),
            (42.335945, -71.167993)
        ],
        "stops": [
        { "name": "Conte Forum", "lat": 42.336034, "lon": -71.167059 },
        { "name": "McElroy – Beacon St.", "lat": 42.333223, "lon": -71.170378 },
        { "name": "College Road", "lat": 42.336401, "lon": -71.171620 },
        { "name": "Chestnut Hill – Main Gate", "lat": 42.338157, "lon": -71.170724 },
        { "name": "Evergreen Cemetery", "lat": 42.339967, "lon": -71.163041 },
        { "name": "2000 Commonwealth Ave.", "lat": 42.339635, "lon": -71.158427 },
        { "name": "Reservoir MBTA Stop", "lat": 42.335034, "lon": -71.148967 },
        { "name": "B.O.A – Chestnut Hill Ave.", "lat": 42.337098113769784, "lon": -71.15194853316866 },
        { "name": "Chiswick Rd.", "lat": 42.340570, "lon": -71.151345 },
        { "name": "Corner of Comm. Ave / Chestnut Hill Ave.", "lat": 42.338299, "lon": -71.153711 },
        { "name": "South Street", "lat": 42.339710, "lon": -71.157444 },
        { "name": "Greycliff Hall", "lat": 42.340291973724014, "lon": -71.16119303561617 },
        { "name": "Robsham Theater", "lat": 42.338145, "lon": -71.168858 }
        ],
    },

    "Newton Campus Express": {
        "color": "#8B4513",         # route line stays dark red/brown
        "marker_color": "#8B4513",  # shuttle icon — same dark red as the route
        "service_days": "Weekdays",
        "service_window": "All Day",
        "headway": "Every 15 - 20 Minutes",
        "path": [
            # Start at Newton - Stuart Hall (Newton Campus)
            (42.34120257347508, -71.19375860329504),
            # To Newton - Main Gate
            (42.341500, -71.193400),
            (42.34176656451543, -71.19274984496883),
            # Exit Newton Campus onto Commonwealth Ave heading east
            (42.34186, -71.19206),
            # Follow Commonwealth Ave eastbound (Route 30)
            (42.34164, -71.19208),
            (42.34138, -71.19230),
            (42.34101, -71.19250),
            (42.34055, -71.19260),
            (42.33988, -71.19273),
            (42.33949, -71.19281),
            (42.33906, -71.19286),
            (42.33851, -71.19294),
            (42.33794, -71.19304),
            (42.33743, -71.19308),
            (42.33710, -71.19308),
            (42.33675, -71.19320),
            (42.33603, -71.19326),
            (42.33607, -71.19291),
            (42.33620, -71.19165),
            (42.33620, -71.19055),
            (42.33620, -71.18898),
            (42.33620, -71.18770),
            (42.33620, -71.18617),
            (42.33655, -71.18348),
            (42.33626, -71.18012),
            (42.33630, -71.17757),
            (42.33701, -71.17615),
            (42.33720, -71.17423),
            (42.33709, -71.17245),
            (42.33851, -71.17051),
            (42.33942, -71.16875),
            (42.33986, -71.16667),
            # Return journey - back along Commonwealth Ave westbound
            (42.33919, -71.16618), # ignacio's church 
            (42.33967, -71.16606),
            (42.34012, -71.16614),
            (42.33999, -71.16648),  
            (42.33983, -71.16799),
            (42.33956, -71.16906),
            (42.33921, -71.16996),
            (42.33869, -71.17080),
            (42.33775, -71.17179),
            (42.33729, -71.17296),
            (42.33741, -71.17389),
            (42.33744, -71.17510),
            (42.33659, -71.17744),
            (42.33635, -71.17934),
            (42.33655, -71.18184),
            (42.33683, -71.18426),
            (42.33657, -71.18671),
            (42.33637, -71.18911),
            (42.33632, -71.19086),
            (42.33615, -71.19314),
            (42.33705, -71.19312),
            (42.33890, -71.19281),
            (42.34039, -71.19259),
            (42.34175, -71.19186),
            (42.34207, -71.19237),
            (42.34128, -71.19283),
            (42.34125, -71.19354),
            (42.34141, -71.19466), # turning at law school
            (42.34109, -71.19472),
            (42.34103, -71.19429),
            (42.34117, -71.19422),
            (42.34125, -71.19377),
            (42.34130, -71.19282), # back to the start
        ],

        "stops": [
            { "name": "Newton – Stuart Hall", "lat": 42.34120257347508, "lon": -71.19375860329504 },
            { "name": "Newton – Main Gate", "lat": 42.34176656451543, "lon": -71.19274984496883 },
            { "name": "Chestnut Hill – Main Gate", "lat": 42.338157, "lon": -71.170724 }
        ],
    },
}


DEFAULT_SHUTTLES = {
    # ── Comm Ave All Stops ────────────────────────────────────────────────────
    # Three buses evenly spaced (~33 % apart) around the loop so riders never
    # wait more than ~10–13 min, matching the posted 10–15 min headway.
    "comm-1": {
        "label": "Comm Ave 1",
        "route": "Comm Ave All Stops",
        "progress": 0.04,          # near Conte Forum, just boarded
        "speed_mph": 11,            # typical urban crawl through campus
        "capacity_pct": 74,         # busy evening run
        "on_time": True,
        "dwell_seconds_remaining": 30,  # still boarding at Conte Forum
    },
    "comm-2": {
        "label": "Comm Ave 2",
        "route": "Comm Ave All Stops",
        "progress": 0.38,          # mid-route near Chestnut Hill / Reservoir area
        "speed_mph": 12,            # slightly faster stretch away from campus core
        "capacity_pct": 88,         # packed — heading back toward main campus
        "on_time": True,
        "dwell_seconds_remaining": 0,
    },
    "comm-3": {
        "label": "Comm Ave 3",
        "route": "Comm Ave All Stops",
        "progress": 0.70,          # two-thirds through, near Greycliff / South St.
        "speed_mph": 10,            # slower, heavier traffic near Comm Ave corridor
        "capacity_pct": 52,         # moderate — passengers have thinned out
        "on_time": True,
        "dwell_seconds_remaining": 0,
    },
    # ── Newton Campus Express ─────────────────────────────────────────────────
    # Two buses offset by ~half the loop so one is always outbound and one
    # inbound, giving ~15–18 min effective headway each direction.
    "newton-1": {
        "label": "Newton Express 1",
        "route": "Newton Campus Express",
        "progress": 0.06,          # just departed Newton Stuart Hall
        "speed_mph": 17,            # faster on the open Newton stretch of Comm Ave
        "capacity_pct": 62,         # good load for a mid-day express
        "on_time": True,
        "dwell_seconds_remaining": 20,  # finishing dwell at Newton – Main Gate
    },
    "newton-2": {
        "label": "Newton Express 2",
        "route": "Newton Campus Express",
        "progress": 0.52,          # inbound, approaching main campus
        "speed_mph": 14,            # slower in campus-side traffic
        "capacity_pct": 38,         # lighter — picked up at Newton, many already off
        "on_time": True,
        "dwell_seconds_remaining": 0,
    },
}


def _distance_miles(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    lat_miles = (b_lat - a_lat) * 69.0
    lon_miles = (b_lon - a_lon) * 51.0
    return math.hypot(lat_miles, lon_miles)


def _build_route_metrics(route: dict) -> dict:
    path = route["path"]
    segment_lengths = []
    cumulative = [0.0]
    for idx in range(len(path) - 1):
        start = path[idx]
        end = path[idx + 1]
        length = _distance_miles(start[0], start[1], end[0], end[1])
        segment_lengths.append(length)
        cumulative.append(cumulative[-1] + length)

    total_length = cumulative[-1] if cumulative[-1] > 0 else 1.0
    stop_progress = {}
    for stop in route["stops"]:
        stop_progress[stop["name"]] = _nearest_progress_on_path(stop["lat"], stop["lon"], path)

    return {
        "segment_lengths": segment_lengths,
        "cumulative": cumulative,
        "total_length": total_length,
        "stop_progress": stop_progress,
    }


@st.cache_data
def _cached_route_metrics(route_name: str, route_cache_key: tuple) -> dict:
    """Compute and cache route geometry until the route path or stop list changes."""
    del route_cache_key
    return _build_route_metrics(BC_ROUTES[route_name])


def _route_cache_key(route: dict) -> tuple:
    """Invalidate cached route metrics when a route path or stop list changes."""
    path_key = tuple(route["path"])
    stop_key = tuple((stop["name"], stop["lat"], stop["lon"]) for stop in route["stops"])
    return path_key, stop_key


def _nearest_progress_on_path(lat: float, lon: float, path: list[tuple[float, float]]) -> float:
    closest_progress = 0.0
    best_distance = float("inf")
    total = 0.0
    segment_totals = [0.0]
    for idx in range(len(path) - 1):
        total += _distance_miles(path[idx][0], path[idx][1], path[idx + 1][0], path[idx + 1][1])
        segment_totals.append(total)
    total = total or 1.0

    for idx in range(len(path) - 1):
        ax, ay = path[idx][0], path[idx][1]
        bx, by = path[idx + 1][0], path[idx + 1][1]
        abx = bx - ax
        aby = by - ay
        apx = lat - ax
        apy = lon - ay
        denom = abx * abx + aby * aby
        t = 0.0 if denom == 0 else max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
        proj_lat = ax + t * abx
        proj_lon = ay + t * aby
        distance = _distance_miles(lat, lon, proj_lat, proj_lon)
        if distance < best_distance:
            best_distance = distance
            segment_length = segment_totals[idx + 1] - segment_totals[idx]
            along_route = segment_totals[idx] + segment_length * t
            closest_progress = along_route / total

    return closest_progress


def _position_at_progress(route_name: str, progress: float) -> tuple[float, float]:
    route = st.session_state.route_definitions[route_name]
    metrics = route["metrics"]
    path = route["path"]
    target = (progress % 1.0) * metrics["total_length"]

    for idx, segment_length in enumerate(metrics["segment_lengths"]):
        start_distance = metrics["cumulative"][idx]
        end_distance = metrics["cumulative"][idx + 1]
        if target <= end_distance or idx == len(metrics["segment_lengths"]) - 1:
            ratio = 0.0 if segment_length == 0 else (target - start_distance) / segment_length
            start = path[idx]
            end = path[idx + 1]
            lat = start[0] + (end[0] - start[0]) * ratio
            lon = start[1] + (end[1] - start[1]) * ratio
            return lat, lon

    return path[-1]


def capacity_label(capacity_pct: int) -> str:
    if capacity_pct >= 85:
        return "Full"
    if capacity_pct >= 55:
        return "Medium"
    return "Empty"


def display_stop_name(stop_name: str) -> str:
    boarding_suffix = " (boarding)" if stop_name.endswith(" (boarding)") else ""
    base_name = stop_name.removesuffix(" (boarding)")
    cleaned_name = re.sub(r"^[A-Z]\.\s*", "", base_name)
    return f"{cleaned_name}{boarding_suffix}"


def _stop_dwell_seconds(stop_name: str, capacity_pct: int = 50) -> int:
    """Return realistic dwell time based on stop busyness and current capacity.

    Crowded buses take longer to board and alight, so dwell scales up with load.
    """
    base = stop_name.replace(" (boarding)", "").strip()
    # High-traffic hubs: full boarding cycle
    if base in {
        "Conte Forum",
        "McElroy – Beacon St.",
        "Newton – Stuart Hall",
        "Reservoir MBTA Stop",
    }:
        seconds = 35
    # Medium stops: moderate passenger exchange
    elif base in {
        "College Road",
        "Chestnut Hill – Main Gate",
        "Robsham Theater",
        "Newton – Main Gate",
        "2000 Commonwealth Ave.",
    }:
        seconds = 22
    # All other stops: quick pass-through
    else:
        seconds = 12

    # Crowded buses board and alight more slowly
    if capacity_pct >= 85:
        return int(seconds * 1.4)
    if capacity_pct >= 65:
        return int(seconds * 1.2)
    return seconds


# Net capacity change (percentage points) when a shuttle completes boarding at a stop.
# Positive = more passengers board than alight; negative = more alight than board.
#
# Loop structure for Comm Ave All Stops (evening service):
#   OUTBOUND leg: Conte Forum → McElroy → College Rd → … → 2000 Comm Ave → Reservoir
#     Students leave campus (board at Conte/McElroy), alight at residential stops.
#   INBOUND return leg: Reservoir → B.O.A / Cleveland Circle → … → South St → Greycliff → Robsham → Conte Forum
#     Students board at every stop heading back to campus, then all alight at Conte Forum.
#
# Deltas are balanced so the net sum per full loop ≈ 0 (stable steady-state capacity).
STOP_CAPACITY_DELTA: dict[str, int] = {
    # == Conte Forum — end of inbound trip / start of outbound ==
    # Heavy alighting (everyone arriving for class) outweighs new outbound boarding.
    "Conte Forum": -35,

    # == Outbound leg: students heading home ==
    "McElroy – Beacon St.": +8,       # campus-adjacent, many students hop on to go home
    "College Road": +5,               # moderate outbound boarding
    "Chestnut Hill – Main Gate": +2,  # light boarding
    "Evergreen Cemetery": -5,         # residential, alighting begins
    "2000 Commonwealth Ave.": -8,     # significant alighting (residential area)
    "Reservoir MBTA Stop": -7,        # major stop: many alight to connect to T; slight boarding from T riders

    # == Inbound return leg: students heading to campus ==
    # Cleveland Circle / Chestnut Hill Ave corridor — first major boarding cluster
    "B.O.A – Chestnut Hill Ave.": +4,
    "Chiswick Rd.": +4,
    "Corner of Comm. Ave / Chestnut Hill Ave.": +4,
    # Dorm / residential corridor — primary inbound boarding
    "South Street": +10,              # students living near campus boarding for class
    "Greycliff Hall": +13,            # heavy boarding: large dorm area
    "Robsham Theater": +5,            # boarding as shuttle approaches campus

    # Newton Campus Express
    "Newton – Stuart Hall": +22,      # Newton terminus, heavy boarding
    "Newton – Main Gate": +10,
}


def initialize_simulation_state() -> None:
    reset_seed_state = st.session_state.get("simulation_version") != SIMULATION_VERSION
    st.session_state.simulation_version = SIMULATION_VERSION

    route_definitions = {}
    for route_name, route in BC_ROUTES.items():
        route_definitions[route_name] = {
            **route,
            "metrics": _cached_route_metrics(route_name, _route_cache_key(route)),
        }
    st.session_state.route_definitions = route_definitions
    _log.info("Initialized route definitions for %d routes.", len(route_definitions))

    stops = {}
    for route_name, route in st.session_state.route_definitions.items():
        for stop in route["stops"]:
            existing = stops.get(stop["name"], {})
            routes = existing.get("routes", [])
            if route_name not in routes:
                routes.append(route_name)
            stops[stop["name"]] = {
                "lat": stop["lat"],
                "lon": stop["lon"],
                "routes": routes,
            }
    st.session_state.stops = stops

    existing_status = {}
    if "shuttle_data" in st.session_state and not reset_seed_state:
        for shuttle_id, shuttle in st.session_state.shuttle_data.items():
            existing_status[shuttle_id] = {
                "capacity_pct": shuttle.get("capacity_pct"),
                "on_time": shuttle.get("on_time"),
                "progress": shuttle.get("progress"),
                "dwell_seconds_remaining": shuttle.get("dwell_seconds_remaining", 0.0),
                "delay_minutes": shuttle.get("delay_minutes", 0),
                "is_express": shuttle.get("is_express", False),
                "speed_mph": shuttle.get("speed_mph"),
            }

    shuttle_data = {}
    for shuttle_id, shuttle in DEFAULT_SHUTTLES.items():
        prior = existing_status.get(shuttle_id, {})
        seed = {
            **shuttle,
            "capacity_pct": prior.get("capacity_pct", shuttle["capacity_pct"]),
            "on_time": prior.get("on_time", shuttle["on_time"]),
            "progress": prior.get("progress", shuttle["progress"]),
            "dwell_seconds_remaining": prior.get(
                "dwell_seconds_remaining",
                shuttle.get("dwell_seconds_remaining", 0.0),
            ),
            "delay_minutes": prior.get("delay_minutes", 0),
            "is_express": prior.get("is_express", False),
            "speed_mph": prior.get("speed_mph", shuttle["speed_mph"]),
        }
        lat, lon = _position_at_progress(seed["route"], seed["progress"])
        shuttle_data[shuttle_id] = {
            **seed,
            "lat": lat,
            "lon": lon,
            "capacity": capacity_label(seed["capacity_pct"]),
            "current_stop": "",
            "next_stop": "",
        }
    st.session_state.shuttle_data = shuttle_data

    # Apply driver overrides (stored separately so they survive shuttle_data rebuilds)
    if "driver_shuttle_overrides" not in st.session_state:
        st.session_state.driver_shuttle_overrides = {}
    for shuttle_id, overrides in st.session_state.driver_shuttle_overrides.items():
        if shuttle_id in st.session_state.shuttle_data:
            st.session_state.shuttle_data[shuttle_id].update(overrides)

    if "simulation_last_updated" not in st.session_state:
        st.session_state.simulation_last_updated = datetime.now()

    if "user_stop" not in st.session_state or st.session_state.user_stop not in st.session_state.stops:
        st.session_state.user_stop = "Conte Forum"

    if "destination_stop" not in st.session_state or st.session_state.destination_stop not in st.session_state.stops:
        st.session_state.destination_stop = "Conte Forum"

    if "selected_route_filter" not in st.session_state:
        st.session_state.selected_route_filter = "All routes"

    if "feedback_history" not in st.session_state:
        st.session_state.feedback_history = []

    if "rider_feedback_reports" not in st.session_state:
        st.session_state.rider_feedback_reports = []

    if "show_feedback_modal" not in st.session_state:
        st.session_state.show_feedback_modal = False

    if "show_boarding_feedback_form" not in st.session_state:
        st.session_state.show_boarding_feedback_form = False

    if "selected_feedback_bus_id" not in st.session_state:
        st.session_state.selected_feedback_bus_id = None

    if "recent_updates" not in st.session_state:
        st.session_state.recent_updates = []

    if "driver_updates" not in st.session_state:
        st.session_state.driver_updates = []

    if "dispatcher_overrides" not in st.session_state:
        st.session_state.dispatcher_overrides = []

    if "system_alerts" not in st.session_state:
        st.session_state.system_alerts = []

    if "has_seen_onboarding" not in st.session_state:
        st.session_state.has_seen_onboarding = False

    # Prevent unbounded memory growth for log lists accumulated during the session
    _LIST_MAX = 100
    for _key in (
        "recent_updates",
        "driver_updates",
        "dispatcher_overrides",
        "system_alerts",
        "feedback_history",
        "rider_feedback_reports",
    ):
        lst = st.session_state.get(_key)
        if isinstance(lst, list) and len(lst) > _LIST_MAX:
            st.session_state[_key] = lst[-_LIST_MAX:]

    update_shuttle_positions(advance=False)


def _progress_to_stop(route_name: str, shuttle_progress: float, stop_name: str) -> float | None:
    route = st.session_state.route_definitions[route_name]
    stop_progress = route["metrics"]["stop_progress"].get(stop_name)
    if stop_progress is None:
        return None
    return (stop_progress - shuttle_progress) % 1.0


def _nearest_stop_names(route_name: str, shuttle_progress: float) -> tuple[str, str]:
    route = st.session_state.route_definitions[route_name]
    ordered_stops = sorted(
        route["metrics"]["stop_progress"].items(),
        key=lambda item: item[1],
    )
    next_stop = ordered_stops[0][0]
    for stop_name, stop_progress in ordered_stops:
        if stop_progress >= shuttle_progress:
            next_stop = stop_name
            break

    previous_candidates = [item for item in ordered_stops if item[1] < route["metrics"]["stop_progress"][next_stop]]
    current_stop = previous_candidates[-1][0] if previous_candidates else ordered_stops[-1][0]
    return current_stop, next_stop


def update_shuttle_positions(advance: bool = True) -> None:
    now = datetime.now()
    elapsed_seconds = (now - st.session_state.simulation_last_updated).total_seconds()
    elapsed_seconds = max(0.0, min(elapsed_seconds, 45.0))
    simulated_seconds = elapsed_seconds * SIMULATION_TIME_SCALE

    for shuttle in st.session_state.shuttle_data.values():
        route = st.session_state.route_definitions[shuttle["route"]]
        route_length = route["metrics"]["total_length"]
        if advance and route_length > 0 and simulated_seconds > 0:
            if shuttle["dwell_seconds_remaining"] > 0:
                shuttle["dwell_seconds_remaining"] = max(
                    0.0,
                    shuttle["dwell_seconds_remaining"] - simulated_seconds,
                )
            else:
                distance_fraction = (shuttle["speed_mph"] * simulated_seconds / 3600.0) / route_length
                next_stop_name = _nearest_stop_names(shuttle["route"], shuttle["progress"])[1]
                remaining_to_stop = _progress_to_stop(shuttle["route"], shuttle["progress"], next_stop_name)

                if remaining_to_stop is not None and distance_fraction >= max(remaining_to_stop, STOP_PROXIMITY_THRESHOLD):
                    shuttle["progress"] = (
                        st.session_state.route_definitions[shuttle["route"]]["metrics"]["stop_progress"][next_stop_name]
                    )
                    shuttle["dwell_seconds_remaining"] = _stop_dwell_seconds(next_stop_name, shuttle["capacity_pct"])
                    _log.debug("Shuttle %s arrived at %s (capacity %d%%)", shuttle["label"], next_stop_name, shuttle["capacity_pct"])
                    # Apply boarding/alighting: capacity changes as passengers get on/off
                    delta = STOP_CAPACITY_DELTA.get(next_stop_name, 0)
                    shuttle["capacity_pct"] = max(5, min(95, shuttle["capacity_pct"] + delta))
                else:
                    shuttle["progress"] = (shuttle["progress"] + distance_fraction) % 1.0

        lat, lon = _position_at_progress(shuttle["route"], shuttle["progress"])
        shuttle["lat"] = lat
        shuttle["lon"] = lon
        shuttle["capacity"] = capacity_label(shuttle["capacity_pct"])
        current_stop, next_stop = _nearest_stop_names(shuttle["route"], shuttle["progress"])
        shuttle["current_stop"] = current_stop
        shuttle["next_stop"] = next_stop if shuttle["dwell_seconds_remaining"] <= 0 else f"{next_stop} (boarding)"

    st.session_state.simulation_last_updated = now
    st.session_state.simulated_seconds_per_refresh = simulated_seconds


def _dwell_minutes_enroute(route_name: str, shuttle_progress: float, stop_name: str, capacity_pct: int) -> float:
    """Sum dwell times (minutes) for all intermediate stops between shuttle and target.

    Only counts stops the shuttle will pass through before reaching stop_name, using
    progress fractions so the loop wrap-around is handled correctly.
    """
    route = st.session_state.route_definitions[route_name]
    stop_progress_map = route["metrics"]["stop_progress"]
    target_progress = stop_progress_map.get(stop_name)
    if target_progress is None:
        return 0.0
    to_target = (target_progress - shuttle_progress) % 1.0
    total_dwell = 0.0
    for sname, sprogress in stop_progress_map.items():
        if sname == stop_name:
            continue
        remaining = (sprogress - shuttle_progress) % 1.0
        if 0 < remaining < to_target:
            total_dwell += _stop_dwell_seconds(sname, capacity_pct)
    return total_dwell / 60.0


def get_stop_arrivals(stop_name: str) -> list[dict]:
    if stop_name not in st.session_state.stops:
        _log.warning("get_stop_arrivals: unknown stop %r — returning empty list.", stop_name)
        return []
    arrivals = []
    stop = st.session_state.stops[stop_name]
    for shuttle_id, shuttle in st.session_state.shuttle_data.items():
        if shuttle["route"] not in stop["routes"]:
            continue
        progress_delta = _progress_to_stop(shuttle["route"], shuttle["progress"], stop_name)
        if progress_delta is None:
            continue
        route_length = st.session_state.route_definitions[shuttle["route"]]["metrics"]["total_length"]
        remaining_miles = progress_delta * route_length
        travel_minutes = (remaining_miles / max(shuttle["speed_mph"], 1)) * 60
        # Include time still boarding at current stop plus dwell at all intermediate stops
        current_dwell_minutes = shuttle.get("dwell_seconds_remaining", 0) / 60.0
        enroute_dwell_minutes = _dwell_minutes_enroute(
            shuttle["route"], shuttle["progress"], stop_name, shuttle["capacity_pct"]
        )
        base_eta = round(travel_minutes + current_dwell_minutes + enroute_dwell_minutes)
        delay = max(-30, min(120, shuttle.get("delay_minutes", 0)))  # cap to ±30/120 min
        eta_minutes = max(1, base_eta + delay)

        # Count intermediate stops the shuttle will pass through before reaching the target
        stop_progress_map = st.session_state.route_definitions[shuttle["route"]]["metrics"]["stop_progress"]
        stops_remaining = sum(
            1 for sname, sp in stop_progress_map.items()
            if sname != stop_name
            and 0 < (sp - shuttle["progress"]) % 1.0 < progress_delta
        )
        # loop_wraps = True when the shuttle must cross the progress=0 boundary (i.e. complete
        # more than half the loop) to reach the stop — meaning it is currently heading away
        # from the target and the ETA includes the long way around.
        loop_wraps = progress_delta > 0.5

        arrivals.append(
            {
                "shuttle_id": shuttle_id,
                "label": shuttle["label"],
                "route": shuttle["route"],
                "route_color": st.session_state.route_definitions[shuttle["route"]]["color"],
                "eta_minutes": eta_minutes,
                "capacity_pct": shuttle["capacity_pct"],
                "capacity": shuttle["capacity"],
                "on_time": shuttle["on_time"],
                "current_stop": shuttle["current_stop"],
                "next_stop": shuttle["next_stop"],
                "lat": shuttle["lat"],
                "lon": shuttle["lon"],
                "speed_mph": shuttle["speed_mph"],
                "delay_minutes": delay,
                "is_express": shuttle.get("is_express", False),
                "stops_remaining": stops_remaining,
                "loop_wraps": loop_wraps,
            }
        )

    return sorted(arrivals, key=lambda item: item["eta_minutes"])


def build_eta_prediction(stop_name: str) -> dict:
    if stop_name not in st.session_state.get("stops", {}):
        _log.warning("build_eta_prediction: unknown stop %r.", stop_name)
        return {"min": 0, "max": 0, "confidence": 45, "best_match": None, "alternatives": []}
    arrivals = get_stop_arrivals(stop_name)
    if not arrivals:
        return {
            "min": 0,
            "max": 0,
            "confidence": 45,
            "best_match": None,
            "alternatives": [],
        }

    best = arrivals[0]
    min_eta = max(1, best["eta_minutes"] - 1)
    max_eta = best["eta_minutes"] + 2

    # Base confidence from on-time status
    confidence = 88 if best["on_time"] else 68

    # Rider feedback adjustments (capped window to last 5 events)
    recent_negative = sum(1 for item in st.session_state.feedback_history[-5:] if item["type"] == "wrong")
    recent_positive = sum(1 for item in st.session_state.feedback_history[-5:] if item["type"] == "accurate")
    confidence += recent_positive * 2 - recent_negative * 5

    # Position uncertainty compounds over longer distances — penalise far-away ETAs
    if best["eta_minutes"] > 20:
        confidence -= 12
    elif best["eta_minutes"] > 12:
        confidence -= 6

    # Large driver-reported delays mean we have less certainty about the exact arrival
    abs_delay = abs(best.get("delay_minutes", 0))
    if abs_delay >= 10:
        confidence -= 8
    elif abs_delay >= 5:
        confidence -= 4

    # Express buses skip stops so their ETA is more predictable
    if best.get("is_express"):
        confidence += 5

    confidence = max(45, min(97, confidence))

    return {
        "min": min_eta,
        "max": max_eta,
        "confidence": confidence,
        "best_match": best,
        "alternatives": arrivals[1:4],
    }
