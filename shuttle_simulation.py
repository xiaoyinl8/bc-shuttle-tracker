from __future__ import annotations

import math
from datetime import datetime

import streamlit as st

SIMULATION_TIME_SCALE = 1.0
STOP_PROXIMITY_THRESHOLD = 0.012
SIMULATION_VERSION = "boarding-seed-v2"


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
        { "name": "A. Conte Forum", "lat": 42.336034, "lon": -71.167059 },
        { "name": "B. McElroy – Beacon St.", "lat": 42.333223, "lon": -71.170378 },
        { "name": "C. College Road", "lat": 42.336401, "lon": -71.171620 },
        { "name": "D. Chestnut Hill – Main Gate", "lat": 42.338157, "lon": -71.170724 },
        { "name": "E. Evergreen Cemetery", "lat": 42.339967, "lon": -71.163041 },
        { "name": "F. 2000 Commonwealth Ave.", "lat": 42.339635, "lon": -71.158427 },
        { "name": "G. Reservoir MBTA Stop", "lat": 42.335034, "lon": -71.148967 },
        { "name": "H. B.O.A – Chestnut Hill Ave.", "lat": 42.337098113769784, "lon": -71.15194853316866 },
        { "name": "I. Chiswick Rd.", "lat": 42.340570, "lon": -71.151345 },
        { "name": "J. Corner of Comm. Ave / Chestnut Hill Ave.", "lat": 42.338299, "lon": -71.153711 },
        { "name": "K. South Street", "lat": 42.339710, "lon": -71.157444 },
        { "name": "L. Greycliff Hall", "lat": 42.340291973724014, "lon": -71.16119303561617 },
        { "name": "M. Robsham Theater", "lat": 42.338145, "lon": -71.168858 }
        ],
    },
}


DEFAULT_SHUTTLES = {
    "comm-1": {
        "label": "Comm Ave 1",
        "route": "Comm Ave All Stops",
        "progress": 0.0,
        "speed_mph": 11,
        "capacity_pct": 58,
        "on_time": True,
        "dwell_seconds_remaining": 45,
    },
    "comm-2": {
        "label": "Comm Ave 2",
        "route": "Comm Ave All Stops",
        "progress": 0.56,
        "speed_mph": 10,
        "capacity_pct": 81,
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


def _stop_dwell_seconds(stop_name: str) -> int:
    if stop_name.startswith(("A.", "G.", "M.")):
        return 35
    if stop_name.startswith(("D.", "J.")):
        return 25
    return 18


def initialize_simulation_state() -> None:
    reset_seed_state = st.session_state.get("simulation_version") != SIMULATION_VERSION
    st.session_state.simulation_version = SIMULATION_VERSION

    route_definitions = {}
    for route_name, route in BC_ROUTES.items():
        route_definitions[route_name] = {
            **route,
            "metrics": _build_route_metrics(route),
        }
    st.session_state.route_definitions = route_definitions

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

    if "simulation_last_updated" not in st.session_state:
        st.session_state.simulation_last_updated = datetime.now()

    if "user_stop" not in st.session_state or st.session_state.user_stop not in st.session_state.stops:
        st.session_state.user_stop = "A. Conte Forum"

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
                    shuttle["dwell_seconds_remaining"] = _stop_dwell_seconds(next_stop_name)
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


def get_stop_arrivals(stop_name: str) -> list[dict]:
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
        eta_minutes = max(1, round((remaining_miles / max(shuttle["speed_mph"], 1)) * 60))
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
            }
        )

    return sorted(arrivals, key=lambda item: item["eta_minutes"])


def build_eta_prediction(stop_name: str) -> dict:
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

    confidence = 88 if best["on_time"] else 68
    recent_negative = sum(1 for item in st.session_state.feedback_history[-5:] if item["type"] == "wrong")
    recent_positive = sum(1 for item in st.session_state.feedback_history[-5:] if item["type"] == "accurate")
    confidence = max(45, min(97, confidence - recent_negative * 5 + recent_positive * 2))

    return {
        "min": min_eta,
        "max": max_eta,
        "confidence": confidence,
        "best_match": best,
        "alternatives": arrivals[1:4],
    }
