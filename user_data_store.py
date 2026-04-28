import os
from supabase import create_client
import streamlit as st


@st.cache_resource
def get_supabase():
    url = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
    key = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    if not url or not key:
        return None
    return create_client(url, key)


def save_profile(user_id: str, profile: dict):
    db = get_supabase()
    if not db:
        return

    payload = {
        "user_id": user_id,
        "nickname": profile.get("nickname", ""),
        "timing_style": profile.get("timing_style", "balanced"),
        "crowd_style": profile.get("crowd_style", "balanced"),
        "max_wait_minutes": int(profile.get("max_wait_minutes", 10)),
        "preferred_route": profile.get("preferred_route", ""),
    }

    db.table("user_profiles").upsert(payload).execute()


def load_profile(user_id: str) -> dict | None:
    db = get_supabase()
    if not db:
        return None

    result = (
        db.table("user_profiles")
        .select("*")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return result.data


def save_schedule(user_id: str, raw_text: str, parsed_entries: list[dict]):
    db = get_supabase()
    if not db:
        return

    db.table("user_schedules").upsert({
        "user_id": user_id,
        "raw_text": raw_text,
        "parsed_entries": parsed_entries,
    }).execute()


def load_schedule(user_id: str) -> dict | None:
    db = get_supabase()
    if not db:
        return None

    result = (
        db.table("user_schedules")
        .select("*")
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    )
    return result.data


def delete_schedule(user_id: str):
    db = get_supabase()
    if not db:
        return

    db.table("user_schedules").delete().eq("user_id", user_id).execute()


def delete_user_data(user_id: str):
    db = get_supabase()
    if not db:
        return

    delete_schedule(user_id)
    db.table("user_profiles").delete().eq("user_id", user_id).execute()
