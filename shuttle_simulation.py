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
            (42.3369, -71.1676),
            (42.3354, -71.1682),
            (42.3336, -71.1701),
            (42.3330, -71.1731),
            (42.3340, -71.1762),
            (42.3358, -71.1788),
            (42.3381, -71.1811),
            (42.3399, -71.1826),
            (42.3417, -71.1808),
            (42.3421, -71.1772),
            (42.3413, -71.1734),
            (42.3391, -71.1712),
            (42.3374, -71.1695),
            (42.3369, -71.1676),
        ],
        "stops": [
            {"name": "A. Conte Forum", "lat": 42.3369, "lon": -71.1676},
            {"name": "B. McElroy - Beacon St.", "lat": 42.3354, "lon": -71.1682},
            {"name": "C. College Road", "lat": 42.3336, "lon": -71.1701},
            {"name": "D. Chestnut Hill - Main Gate", "lat": 42.3330, "lon": -71.1731},
            {"name": "E. Evergreen Cemetery", "lat": 42.3340, "lon": -71.1762},
            {"name": "F. 2000 Commonwealth Ave.", "lat": 42.3358, "lon": -71.1788},
            {"name": "G. Reservoir MBTA Stop", "lat": 42.3381, "lon": -71.1811},
            {"name": "H. B.O.A - Chestnut Hill Ave.", "lat": 42.3399, "lon": -71.1826},
            {"name": "I. Thai Bistro - Chiswick Rd.", "lat": 42.3417, "lon": -71.1808},
            {"name": "J. Corner of Comm. Ave/Chestnut Hill Ave.", "lat": 42.3421, "lon": -71.1772},
            {"name": "K. South Street", "lat": 42.3413, "lon": -71.1734},
            {"name": "L. Greycliff Hall", "lat": 42.3391, "lon": -71.1712},
            {"name": "M. Robsham Theater", "lat": 42.3374, "lon": -71.1695},
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

    if "show_feedback_modal" not in st.session_state:
        st.session_state.show_feedback_modal = False

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
