import streamlit as st

from pitch_history import (
    get_recent_pitch_events,
    last_pitch_event,
    get_last_ball_quality,
)
from pitch_scoring import pitch_score, get_pitch_rank
from pitch_locations import next_location_for_pitch


def get_pitch_confidence_score(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("confidence_score", 50))


def confidence_note(pitch_name: str):
    return f" Confidence: {get_pitch_confidence_score(pitch_name)}."


def pitch_family(pitch_name: str) -> str:
    name = pitch_name.strip().lower()

    if name in {"4-seam", "2-seam", "cutter", "rise"}:
        return "hard"

    if name in {
        "curveball",
        "slider",
        "sweeper",
        "curve",
        "screw",
        "drop curve",
        "drop",
    }:
        return "breaking"

    if name in {"changeup", "splitter", "change"}:
        return "offspeed"

    return "other"


def pitch_intent(pitch_name: str) -> str:
    name = pitch_name.strip().lower()

    if name in {"4-seam", "2-seam", "cutter", "rise", "drop"}:
        return "compete"

    if name in {"curveball", "curve", "changeup", "change", "2-seam", "cutter"}:
        return "steal"

    if name in {"slider", "sweeper", "splitter", "curveball", "drop curve"}:
        return "expand"

    return "neutral"


def recent_family_counts(history, window: int = 5):
    events = get_recent_pitch_events(history)[-window:]
    counts = {"hard": 0, "breaking": 0, "offspeed": 0, "other": 0}

    for event in events:
        family = pitch_family(event["pitch"])
        counts[family] = counts.get(family, 0) + 1

    return counts


def recent_intent_counts(history, window: int = 4):
    events = get_recent_pitch_events(history)[-window:]
    counts = {"steal": 0, "compete": 0, "expand": 0, "neutral": 0}

    for event in events:
        intent = pitch_intent(event["pitch"])
        counts[intent] = counts.get(intent, 0) + 1

    return counts


def get_count_mode(balls: int, strikes: int) -> str:
    if strikes == 2 and balls <= 1:
        return "putaway"
    if strikes == 2:
        return "protect_finish"
    if balls >= 3 and strikes <= 1:
        return "must_strike"
    if balls > strikes:
        return "behind"
    if strikes > balls:
        return "expand"
    if balls == 0 and strikes == 0:
        return "opener"
    if balls == 1 and strikes == 1:
        return "balance"
    if balls == 2 and strikes == 2:
        return "full_mix"
    return "neutral"


def get_at_bat_phase(history) -> str:
    pitch_count = len(get_recent_pitch_events(history))

    if pitch_count == 0:
        return "opening"
    if pitch_count == 1:
        return "second_pitch"
    if pitch_count in {2, 3}:
        return "middle"
    return "finish"


def available_pitches(candidates):
    return [p for p in candidates if p in st.session_state.pitcher_pitches]


def choose_by_mode(candidates, history, mode: str, phase: str):
    candidates = available_pitches(candidates)
    if not candidates:
        return None

    family_counts = recent_family_counts(history, window=5)
    intent_counts = recent_intent_counts(history, window=4)

    last_event = last_pitch_event(history)
    last_pitch = last_event["pitch"].strip().lower() if last_event else None
    last_family = pitch_family(last_pitch) if last_pitch else None
    last_intent = pitch_intent(last_pitch) if last_pitch else None

    adjusted = []

    for pitch in candidates:
        name = pitch.strip().lower()
        family = pitch_family(pitch)
        intent = pitch_intent(pitch)
        score = pitch_score(pitch, history)

        if family == "hard":
            score -= family_counts["hard"] * 8
        elif family == "breaking":
            score -= family_counts["breaking"] * 4
        elif family == "offspeed":
            score -= family_counts["offspeed"] * 4

        score -= intent_counts.get(intent, 0) * 5

        if last_family and family == last_family:
            score -= 12

        if last_intent and intent == last_intent:
            score -= 10

        if mode == "opener":
            if intent == "steal":
                score += 15
            if name in {"slider", "sweeper", "splitter"}:
                score -= 10
            if name in {"curveball", "curve", "changeup", "cutter", "2-seam"}:
                score += 8

        elif mode == "must_strike":
            if intent == "compete":
                score += 16
            if name in {"slider", "sweeper", "splitter"}:
                score -= 14

        elif mode == "behind":
            if intent == "compete":
                score += 12
            if name in {"changeup", "curveball", "curve", "cutter", "2-seam", "drop"}:
                score += 6
            if intent == "expand":
                score -= 8

        elif mode == "expand":
            if intent == "expand":
                score += 14
            if family == "hard":
                score -= 8

        elif mode == "putaway":
            if intent == "expand":
                score += 18
            if family == "hard":
                score -= 12

        elif mode == "protect_finish":
            if intent == "expand":
                score += 10
            if intent == "compete":
                score += 5

        elif mode == "balance":
            if intent == "compete":
                score += 6
            if intent == "steal":
                score += 5
            if intent == "expand":
                score += 2

        elif mode == "full_mix":
            if family in {"breaking", "offspeed"}:
                score += 10
            if intent == "compete":
                score += 4

        if phase == "opening":
            if intent == "steal":
                score += 12
            if intent == "expand":
                score -= 10

        elif phase == "second_pitch":
            if last_family == "hard" and family in {"breaking", "offspeed"}:
                score += 14
            if last_family in {"breaking", "offspeed"} and family == "hard":
                score += 10

        elif phase == "middle":
            if last_family == family:
                score -= 8

        elif phase == "finish":
            if intent == "expand":
                score += 10

        adjusted.append((pitch, score))

    adjusted.sort(key=lambda x: (-x[1], get_pitch_rank(x[0]), x[0]))
    return adjusted[0][0]


def baseball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies
    mode = get_count_mode(balls, strikes)
    phase = get_at_bat_phase(history)

    actual_events = get_recent_pitch_events(history)
    first_pitch_of_ab = len(actual_events) == 0

    last_event = last_pitch_event(history)
    last_pitch = last_event["pitch"].strip().lower() if last_event else None
    last_location = last_event["location"].strip().lower() if last_event else ""

    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 4 and "Fastball hunter" in tendencies:
            pitch_name = choose_by_mode(
                [
                    "curveball",
                    "changeup",
                    "cutter",
                    "2-seam",
                    "slider",
                    "splitter",
                    "sweeper",
                    "4-seam",
                ],
                history,
                "opener",
                "opening",
            )
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Cleanup hitter opener: avoid a clean first-pitch heater."
                + confidence_note(pitch_name),
            )

        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = choose_by_mode(
                [
                    "curveball",
                    "changeup",
                    "cutter",
                    "2-seam",
                    "slider",
                    "splitter",
                    "sweeper",
                    "4-seam",
                ],
                history,
                "opener",
                "opening",
            )
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Aggressive first-pitch hunter: start with an opener, not just best raw pitch."
                + confidence_note(pitch_name),
            )

        candidates = ["cutter", "2-seam", "curveball", "changeup", "4-seam"]
        if not available_pitches(candidates):
            candidates = st.session_state.pitcher_pitches

        pitch_name = choose_by_mode(candidates, history, "opener", "opening")
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "First pitch opener: best opening pitch for the at-bat, not just best overall pitch."
            + confidence_note(pitch_name),
        )

    if strikes == 2:
        if "Chases high fastball" in tendencies and "4-seam" in st.session_state.pitcher_pitches:
            return (
                "4-seam",
                "up out of zone",
                "Two strikes: hitter chases up." + confidence_note("4-seam"),
            )

        if "Chases splitter down" in tendencies:
            pitch_name = choose_by_mode(
                ["splitter", "changeup", "curveball"],
                history,
                "putaway",
                "finish",
            )
            if pitch_name:
                return (
                    pitch_name,
                    "down out of zone",
                    "Two strikes: hitter chases down." + confidence_note(pitch_name),
                )

        if "Chases sweeper away" in tendencies:
            pitch_name = choose_by_mode(
                ["sweeper", "slider"],
                history,
                "putaway",
                "finish",
            )
            if pitch_name:
                return (
                    pitch_name,
                    next_location_for_pitch(pitch_name, handedness, history),
                    "Two strikes: hitter chases away." + confidence_note(pitch_name),
                )

        pitch_name = choose_by_mode(
            ["slider", "sweeper", "splitter", "curveball", "changeup"],
            history,
            mode,
            phase,
        )
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                mode,
                phase,
            )

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Two-strike finish pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = choose_by_mode(
            ["cutter", "2-seam", "changeup", "curveball", "4-seam", "splitter"],
            history,
            mode,
            phase,
        )
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                mode,
                phase,
            )

        return (
            pitch_name,
            next_location_for_pitch(
                pitch_name, handedness, history, competitive_mode=True
            ),
            "Behind in count: choose a true compete pitch with command and mix in mind."
            + confidence_note(pitch_name),
        )

    if last_pitch == "4-seam" and "up" in last_location:
        pitch_name = choose_by_mode(
            ["splitter", "changeup", "curveball", "slider"],
            history,
            "expand",
            "middle",
        )
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "expand",
                "middle",
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Fastball up before: now change eye level and speed."
            + confidence_note(pitch_name),
        )

    if last_pitch in {"4-seam", "2-seam", "cutter"}:
        candidates = ["curveball", "splitter", "slider", "changeup", "sweeper"]
        if not available_pitches(candidates):
            candidates = [p for p in st.session_state.pitcher_pitches if p != last_pitch]

        pitch_name = choose_by_mode(candidates, history, "neutral", "middle")
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "neutral",
                "middle",
            )

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "After a hard pitch, prefer a real speed or shape change."
            + confidence_note(pitch_name),
        )

    if last_pitch in {"slider", "sweeper", "curveball"}:
        pitch_name = choose_by_mode(
            ["4-seam", "2-seam", "changeup", "splitter", "cutter"],
            history,
            "balance",
            "middle",
        )
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "balance",
                "middle",
            )

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "After breaking ball, change speed, lane, or eye level."
            + confidence_note(pitch_name),
        )

    if last_pitch in {"splitter", "changeup"}:
        pitch_name = choose_by_mode(
            ["4-seam", "cutter", "curveball", "2-seam"],
            history,
            "balance",
            "middle",
        )
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "balance",
                "middle",
            )

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "After soft pitch, change eye level or shape."
            + confidence_note(pitch_name),
        )

    pitch_name = choose_by_mode(
        st.session_state.pitcher_pitches,
        history,
        mode,
        phase,
    )
    return (
        pitch_name,
        next_location_for_pitch(pitch_name, handedness, history),
        "Default baseball sequence: best pitch that fits count, phase, and mix."
        + confidence_note(pitch_name),
    )


def softball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies
    mode = get_count_mode(balls, strikes)
    phase = get_at_bat_phase(history)

    actual_events = get_recent_pitch_events(history)
    first_pitch_of_ab = len(actual_events) == 0
    last_event = last_pitch_event(history)
    last_pitch = last_event["pitch"].strip().lower() if last_event else None

    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 4:
            pitch_name = choose_by_mode(
                ["curve", "screw", "drop curve", "change", "rise", "drop"],
                history,
                "opener",
                "opening",
            )
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Middle of lineup opener: avoid a clean first look."
                + confidence_note(pitch_name),
            )

        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = choose_by_mode(
                ["curve", "screw", "drop curve", "change", "rise", "drop"],
                history,
                "opener",
                "opening",
            )
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Aggressive hitter: start with opener logic, not just best pitch."
                + confidence_note(pitch_name),
            )

        candidates = ["drop", "curve", "change", "rise", "screw", "drop curve"]
        if not available_pitches(candidates):
            candidates = st.session_state.pitcher_pitches

        pitch_name = choose_by_mode(candidates, history, "opener", "opening")
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "First pitch opener: best opening pitch for the at-bat."
            + confidence_note(pitch_name),
        )

    if strikes == 2:
        pitch_name = choose_by_mode(
            ["drop curve", "drop", "curve", "screw", "change", "rise"],
            history,
            "putaway",
            "finish",
        )
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "putaway",
                "finish",
            )

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Two-strike softball finish pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = choose_by_mode(
            ["drop", "curve", "screw", "rise", "change"],
            history,
            "behind",
            "middle",
        )
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "behind",
                "middle",
            )

        return (
            pitch_name,
            next_location_for_pitch(
                pitch_name, handedness, history, competitive_mode=True
            ),
            "Behind in count: choose a true compete pitch with better mix control."
            + confidence_note(pitch_name),
        )

    if last_pitch == "rise":
        pitch_name = choose_by_mode(
            ["drop", "drop curve", "change"],
            history,
            "neutral",
            "middle",
        )
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "neutral",
                "middle",
            )

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Pair rise with something moving down." + confidence_note(pitch_name),
        )

    if last_pitch in {"drop", "drop curve", "curve", "screw", "change"}:
        candidates = [p for p in st.session_state.pitcher_pitches if p != last_pitch]
        pitch_name = choose_by_mode(candidates, history, "balance", "middle")
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "balance",
                "middle",
            )

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Change movement pattern after previous pitch."
            + confidence_note(pitch_name),
        )

    pitch_name = choose_by_mode(
        st.session_state.pitcher_pitches,
        history,
        mode,
        phase,
    )
    return (
        pitch_name,
        next_location_for_pitch(pitch_name, handedness, history),
        "Default softball sequence: best pitch that fits count, phase, and mix."
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
