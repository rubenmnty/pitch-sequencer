import streamlit as st

from pitch_history import (
    get_recent_pitch_events,
    last_pitch_event,
    get_last_ball_quality,
)
from pitch_scoring import best_available, pitch_score
from pitch_locations import next_location_for_pitch


def get_pitch_confidence_score(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("confidence_score", 50))


def get_pitch_rank(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("rank", 99))


def confidence_note(pitch_name: str):
    return f" Confidence: {get_pitch_confidence_score(pitch_name)}."


def pitch_family(pitch_name: str) -> str:
    name = pitch_name.strip().lower()

    if name in {"4-seam", "2-seam", "cutter", "rise"}:
        return "hard"

    if name in {"curveball", "slider", "sweeper", "curve", "screw", "drop curve", "drop"}:
        return "breaking"

    if name in {"changeup", "splitter", "change"}:
        return "offspeed"

    return "other"


def recent_family_counts(history, window: int = 5):
    events = get_recent_pitch_events(history)[-window:]
    counts = {"hard": 0, "breaking": 0, "offspeed": 0, "other": 0}

    for event in events:
        family = pitch_family(event["pitch"])
        counts[family] = counts.get(family, 0) + 1

    return counts


def get_count_mode(balls: int, strikes: int) -> str:
    if strikes == 2:
        return "putaway"
    if balls >= 3 and strikes <= 1:
        return "must_strike"
    if balls > strikes:
        return "behind"
    if strikes > balls:
        return "expand"
    if balls == 0 and strikes == 0:
        return "steal_strike"
    return "neutral"


def choose_by_mode(candidates, history, mode: str):
    if not candidates:
        return None

    family_counts = recent_family_counts(history, window=5)

    adjusted = []
    for pitch in candidates:
        score = pitch_score(pitch, history)
        family = pitch_family(pitch)

        if family == "hard":
            score -= family_counts["hard"] * 8
        elif family == "breaking":
            score -= family_counts["breaking"] * 4
        elif family == "offspeed":
            score -= family_counts["offspeed"] * 4

        if mode == "steal_strike":
            if family == "hard":
                score += 8
            if pitch.strip().lower() in {"curveball", "curve", "drop", "drop curve"}:
                score += 6

        elif mode == "must_strike":
            if family == "hard":
                score += 6
            if pitch.strip().lower() in {"splitter", "slider", "sweeper"}:
                score -= 10

        elif mode == "behind":
            if pitch.strip().lower() in {"cutter", "2-seam", "changeup", "drop", "curve"}:
                score += 6
            if pitch.strip().lower() in {"sweeper", "slider", "curveball", "splitter"}:
                score -= 4

        elif mode == "expand":
            if family in {"breaking", "offspeed"}:
                score += 10
            if family == "hard":
                score -= 8

        elif mode == "putaway":
            if family in {"breaking", "offspeed"}:
                score += 14
            if family == "hard":
                score -= 10

        adjusted.append((pitch, score))

    adjusted.sort(key=lambda x: (-x[1], get_pitch_rank(x[0]), x[0]))
    return adjusted[0][0]


def baseball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies
    mode = get_count_mode(balls, strikes)

    actual_events = get_recent_pitch_events(history)
    first_pitch_of_ab = len(actual_events) == 0

    last_event = last_pitch_event(history)
    last_pitch = last_event["pitch"].strip().lower() if last_event else None
    last_location = last_event["location"].strip().lower() if last_event else ""

    # 0-0 first pitch
    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 4 and "Fastball hunter" in tendencies:
            candidates = [
                p for p in [
                    "curveball",
                    "splitter",
                    "slider",
                    "changeup",
                    "sweeper",
                    "cutter",
                    "2-seam",
                    "4-seam",
                ]
                if p in st.session_state.pitcher_pitches
            ]
            pitch_name = choose_by_mode(candidates, history, "steal_strike")
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Cleanup hitter: avoid a clean first-pitch fastball when possible."
                + confidence_note(pitch_name),
            )

        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            candidates = [
                p for p in [
                    "curveball",
                    "splitter",
                    "slider",
                    "changeup",
                    "sweeper",
                    "cutter",
                    "2-seam",
                    "4-seam",
                ]
                if p in st.session_state.pitcher_pitches
            ]
            pitch_name = choose_by_mode(candidates, history, "steal_strike")
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Aggressive fastball hunter: start with spin or offspeed."
                + confidence_note(pitch_name),
            )

        candidates = [p for p in st.session_state.pitcher_pitches]
        pitch_name = choose_by_mode(candidates, history, "steal_strike")
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "First pitch: best available based on rank, confidence, and mix."
            + confidence_note(pitch_name),
        )

    # 2-strike logic
    if strikes == 2:
        if "Chases high fastball" in tendencies and "4-seam" in st.session_state.pitcher_pitches:
            return (
                "4-seam",
                "up out of zone",
                "Two strikes: hitter chases up." + confidence_note("4-seam"),
            )

        if "Chases splitter down" in tendencies:
            candidates = [
                p for p in ["splitter", "changeup", "curveball"]
                if p in st.session_state.pitcher_pitches
            ]
            pitch_name = choose_by_mode(candidates, history, "putaway")
            if pitch_name:
                return (
                    pitch_name,
                    "down out of zone",
                    "Two strikes: hitter chases down." + confidence_note(pitch_name),
                )

        if "Chases sweeper away" in tendencies:
            candidates = [
                p for p in ["sweeper", "slider"] if p in st.session_state.pitcher_pitches
            ]
            pitch_name = choose_by_mode(candidates, history, "putaway")
            if pitch_name:
                return (
                    pitch_name,
                    next_location_for_pitch(pitch_name, handedness, history),
                    "Two strikes: hitter chases away." + confidence_note(pitch_name),
                )

        candidates = [
            p for p in ["slider", "sweeper", "splitter", "curveball", "changeup"]
            if p in st.session_state.pitcher_pitches
        ]
        pitch_name = choose_by_mode(candidates, history, "putaway")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "putaway")

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Two-strike chase pitch." + confidence_note(pitch_name),
        )

    # hitter counts
    if balls > strikes:
        candidates = [
            p for p in ["cutter", "2-seam", "changeup", "curveball", "4-seam", "splitter"]
            if p in st.session_state.pitcher_pitches
        ]
        pitch_name = choose_by_mode(candidates, history, "behind")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "behind")

        return (
            pitch_name,
            next_location_for_pitch(
                pitch_name, handedness, history, competitive_mode=True
            ),
            "Hitter count: best competitive option with command and mix in mind."
            + confidence_note(pitch_name),
        )

    # sequence logic off previous pitch
    if last_pitch == "4-seam" and "up" in last_location:
        candidates = [
            p for p in ["splitter", "changeup", "curveball", "slider"]
            if p in st.session_state.pitcher_pitches
        ]
        pitch_name = choose_by_mode(candidates, history, "expand")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "expand")
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Fastball up before: now change eye level and/or speed."
            + confidence_note(pitch_name),
        )

    if last_pitch in {"4-seam", "2-seam", "cutter"}:
        candidates = [
            p for p in ["curveball", "splitter", "slider", "changeup", "sweeper"]
            if p in st.session_state.pitcher_pitches
        ]
        if not candidates:
            candidates = [p for p in st.session_state.pitcher_pitches if p != last_pitch]

        pitch_name = choose_by_mode(candidates, history, "neutral")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "neutral")

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "After a hard pitch, prefer shape or speed change."
            + confidence_note(pitch_name),
        )

    if last_pitch in {"slider", "sweeper", "curveball"}:
        candidates = [
            p for p in ["4-seam", "2-seam", "changeup", "splitter", "cutter"]
            if p in st.session_state.pitcher_pitches
        ]
        pitch_name = choose_by_mode(candidates, history, "neutral")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "neutral")

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "After breaking ball, change speed or lane."
            + confidence_note(pitch_name),
        )

    if last_pitch in {"splitter", "changeup"}:
        candidates = [
            p for p in ["4-seam", "cutter", "curveball", "2-seam"]
            if p in st.session_state.pitcher_pitches
        ]
        pitch_name = choose_by_mode(candidates, history, "neutral")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "neutral")

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "After soft pitch, change eye level or shape."
            + confidence_note(pitch_name),
        )

    pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, mode)
    return (
        pitch_name,
        next_location_for_pitch(pitch_name, handedness, history),
        "Default baseball sequence: best score that still fits the count and mix."
        + confidence_note(pitch_name),
    )


def softball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies
    mode = get_count_mode(balls, strikes)

    actual_events = get_recent_pitch_events(history)
    first_pitch_of_ab = len(actual_events) == 0
    last_event = last_pitch_event(history)
    last_pitch = last_event["pitch"].strip().lower() if last_event else None

    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 4:
            candidates = [
                p for p in ["curve", "screw", "drop curve", "change", "rise", "drop"]
                if p in st.session_state.pitcher_pitches
            ]
            pitch_name = choose_by_mode(candidates, history, "steal_strike")
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Middle of lineup default: avoid giving a clean first look."
                + confidence_note(pitch_name),
            )

        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            candidates = [
                p for p in ["curve", "screw", "drop curve", "change", "rise", "drop"]
                if p in st.session_state.pitcher_pitches
            ]
            pitch_name = choose_by_mode(candidates, history, "steal_strike")
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Aggressive hitter: start with movement." + confidence_note(pitch_name),
            )

        pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "steal_strike")
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "First pitch: best available based on rank, confidence, and mix."
            + confidence_note(pitch_name),
        )

    if strikes == 2:
        candidates = [
            p for p in ["drop curve", "drop", "curve", "screw", "change", "rise"]
            if p in st.session_state.pitcher_pitches
        ]
        pitch_name = choose_by_mode(candidates, history, "putaway")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "putaway")

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Two-strike softball chase pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        candidates = [
            p for p in ["drop", "curve", "screw", "rise", "change"]
            if p in st.session_state.pitcher_pitches
        ]
        pitch_name = choose_by_mode(candidates, history, "behind")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "behind")

        return (
            pitch_name,
            next_location_for_pitch(
                pitch_name, handedness, history, competitive_mode=True
            ),
            "Hitter count: safe movement strike with better mix control."
            + confidence_note(pitch_name),
        )

    if last_pitch in {"rise"}:
        candidates = [
            p for p in ["drop", "drop curve", "change"]
            if p in st.session_state.pitcher_pitches
        ]
        pitch_name = choose_by_mode(candidates, history, "neutral")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "neutral")

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Pair rise with something moving down." + confidence_note(pitch_name),
        )

    if last_pitch in {"drop", "drop curve", "curve", "screw", "change"}:
        candidates = [p for p in st.session_state.pitcher_pitches if p != last_pitch]
        pitch_name = choose_by_mode(candidates, history, "neutral")
        if pitch_name is None:
            pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, "neutral")

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Change movement pattern after previous pitch."
            + confidence_note(pitch_name),
        )

    pitch_name = choose_by_mode(st.session_state.pitcher_pitches, history, mode)
    return (
        pitch_name,
        next_location_for_pitch(pitch_name, handedness, history),
        "Default softball sequence: best score that still fits count and mix."
        + confidence_note(pitch_name),
    )


def adjust_after_ball(pitch_name, location, reason, batter, history):
    last_event = last_pitch_event(history)
    if not last_event:
        return pitch_name, location, reason

    if last_event["outcome"].strip().lower() != "ball":
        return pitch_name, location, reason

    last_pitch = last_event["pitch"].strip().lower()
    last_location = last_event["location"].strip().lower()
    last_quality = get_last_ball_quality(history)
    current_pitch = pitch_name.strip().lower()

    if last_quality == "Uncompetitive":
        if current_pitch == last_pitch:
            alternatives = [
                p
                for p in st.session_state.pitcher_pitches
                if p.strip().lower() != last_pitch
            ]

            if alternatives:
                ordered = sorted(
                    alternatives,
                    key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
                )
                new_pitch = ordered[0]
                new_location = next_location_for_pitch(
                    new_pitch, batter["hand"], history
                )
                new_reason = reason + " Changed pitch after uncompetitive ball."
                return new_pitch, new_location, new_reason

            new_location = next_location_for_pitch(pitch_name, batter["hand"], history)
            if new_location.strip().lower() != last_location:
                return (
                    pitch_name,
                    new_location,
                    reason
                    + " Same pitch kept because no better option, but moved location after uncompetitive ball.",
                )

        return pitch_name, location, reason

    if last_quality == "Competitive":
        if current_pitch == last_pitch:
            new_location = next_location_for_pitch(
                pitch_name,
                batter["hand"],
                history,
                competitive_mode=True,
            )
            if new_location.strip().lower() != last_location:
                return (
                    pitch_name,
                    new_location,
                    reason
                    + " Same pitch allowed after competitive ball, but moved location.",
                )

    return pitch_name, location, reason


def recommend_pitch(batter, balls, strikes, history):
    if st.session_state.sport == "Baseball":
        pitch_name, location, reason = baseball_recommend_pitch(
            batter, balls, strikes, history
        )
    else:
        pitch_name, location, reason = softball_recommend_pitch(
            batter, balls, strikes, history
        )

    pitch_name, location, reason = adjust_after_ball(
        pitch_name, location, reason, batter, history
    )

    return pitch_name, location, reason
