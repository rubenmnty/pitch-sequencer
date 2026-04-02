import streamlit as st

from pitch_history import (
    last_pitch_event,
    get_last_ball_quality,
    consecutive_balls_for_pitch,
    consecutive_usage_for_pitch,
    recent_usage_count,
    recent_hard_pitch_count,
    get_recent_pitch_events,
)


def pitch_available(name: str) -> bool:
    return name in st.session_state.pitcher_pitches


def get_pitch_confidence_score(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("confidence_score", 50))


def get_pitch_rank(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("rank", 99))


def get_pitch_family(name: str) -> str:
    pitch = name.strip().lower()

    if pitch in {"4-seam", "2-seam", "cutter", "rise"}:
        return "hard"
    if pitch in {
        "curveball",
        "slider",
        "sweeper",
        "curve",
        "screw",
        "drop curve",
        "drop",
    }:
        return "breaking"
    if pitch in {"changeup", "splitter", "change"}:
        return "offspeed"
    return "other"


def recent_family_count(family: str, history, window: int = 5) -> int:
    events = get_recent_pitch_events(history)[-window:]
    count = 0

    for event in events:
        if get_pitch_family(event["pitch"]) == family:
            count += 1

    return count


def pitch_score(pitch_name: str, history) -> int:
    confidence = get_pitch_confidence_score(pitch_name)
    rank = get_pitch_rank(pitch_name)
    name = pitch_name.strip().lower()
    family = get_pitch_family(pitch_name)

    rank_bonus_map = {
        1: 58,
        2: 32,
        3: 12,
        4: 0,
        5: -10,
        6: -18,
    }
    rank_bonus = rank_bonus_map.get(rank, -24)

    score = confidence + rank_bonus

    # Same pitch balls in a row = big problem
    same_pitch_balls = consecutive_balls_for_pitch(pitch_name, history)
    if same_pitch_balls == 1:
        score -= 55
    elif same_pitch_balls == 2:
        score -= 115
    elif same_pitch_balls >= 3:
        score -= 180

    # Same pitch repeated in sequence
    consecutive_usage = consecutive_usage_for_pitch(pitch_name, history)
    if consecutive_usage == 1:
        score -= 10
    elif consecutive_usage == 2:
        score -= 32
    elif consecutive_usage >= 3:
        score -= 65

    # General recent usage
    usage_count = recent_usage_count(pitch_name, history, window=5)
    if usage_count == 1:
        score -= 12
    elif usage_count == 2:
        score -= 28
    elif usage_count >= 3:
        score -= 45

    last_event = last_pitch_event(history)
    if last_event:
        last_pitch = last_event["pitch"].strip().lower()
        last_outcome = last_event["outcome"].strip().lower()
        last_quality = get_last_ball_quality(history)

        if last_pitch == name:
            if last_outcome == "ball":
                if last_quality == "Uncompetitive":
                    score -= 260
                elif last_quality == "Competitive":
                    score -= 95
                else:
                    score -= 150
            else:
                score -= 24

    # Family overuse penalties
    hard_count = recent_family_count("hard", history, window=5)
    breaking_count = recent_family_count("breaking", history, window=5)
    offspeed_count = recent_family_count("offspeed", history, window=5)

    if family == "hard":
        score -= hard_count * 12
    elif family == "breaking":
        score -= breaking_count * 6
    elif family == "offspeed":
        score -= offspeed_count * 5

    # Extra anti-hard spam
    if name in {"4-seam", "2-seam", "cutter"}:
        hard_recent = recent_hard_pitch_count(history, window=5)
        score -= hard_recent * 12

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
