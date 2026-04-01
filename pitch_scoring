import streamlit as st

from pitch_history import (
    last_pitch_event,
    get_last_ball_quality,
    consecutive_balls_for_pitch,
    consecutive_usage_for_pitch,
    recent_usage_count,
    recent_hard_pitch_count,
)


def pitch_available(name: str) -> bool:
    return name in st.session_state.pitcher_pitches


def get_pitch_confidence_score(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("confidence_score", 50))


def get_pitch_rank(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("rank", 99))


def pitch_score(pitch_name: str, history) -> int:
    confidence = get_pitch_confidence_score(pitch_name)
    rank = get_pitch_rank(pitch_name)

    rank_bonus_map = {
        1: 50,
        2: 28,
        3: 10,
        4: 0,
        5: -10,
        6: -18,
    }
    rank_bonus = rank_bonus_map.get(rank, -24)

    score = confidence + rank_bonus
    name = pitch_name.strip().lower()

    same_pitch_balls = consecutive_balls_for_pitch(pitch_name, history)
    if same_pitch_balls == 1:
        score -= 50
    elif same_pitch_balls == 2:
        score -= 100
    elif same_pitch_balls >= 3:
        score -= 160

    consecutive_usage = consecutive_usage_for_pitch(pitch_name, history)
    if consecutive_usage == 1:
        score -= 10
    elif consecutive_usage == 2:
        score -= 30
    elif consecutive_usage >= 3:
        score -= 60

    usage_count = recent_usage_count(pitch_name, history, window=5)
    score -= usage_count * 18

    last_event = last_pitch_event(history)
    if last_event:
        last_pitch = last_event["pitch"].strip().lower()
        last_outcome = last_event["outcome"].strip().lower()
        last_quality = get_last_ball_quality(history)

        if last_pitch == name:
            if last_outcome == "ball":
                if last_quality == "Uncompetitive":
                    score -= 240
                elif last_quality == "Competitive":
                    score -= 90
                else:
                    score -= 140
            else:
                score -= 20

    if name in {"4-seam", "2-seam", "cutter"}:
        hard_recent = recent_hard_pitch_count(history, window=5)
        score -= hard_recent * 8

    return score


def sort_candidates(candidates, history):
    available = [p for p in candidates if pitch_available(p)]
    if not available:
        return []
    return sorted(
        available,
        key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
    )


def best_available(candidates, history, avoid_last_ball_pitch=False):
    available = [p for p in candidates if pitch_available(p)]
    if not available:
        return None

    last_event = last_pitch_event(history)
    last_quality = get_last_ball_quality(history)

    if (
        avoid_last_ball_pitch
        and last_event
        and last_event["outcome"].strip().lower() == "ball"
    ):
        last_pitch = last_event["pitch"].strip().lower()

        if last_quality == "Uncompetitive":
            filtered = [p for p in available if p.strip().lower() != last_pitch]
            if filtered:
                available = filtered

    ordered = sorted(
        available,
        key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
    )
    return ordered[0]
