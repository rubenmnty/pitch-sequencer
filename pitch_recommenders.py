import streamlit as st

from pitch_history import get_recent_pitch_events, last_pitch_event, get_last_ball_quality
from pitch_scoring import (
    best_available,
    pitch_score,
    get_pitch_confidence_score,
    get_pitch_rank,
)
from pitch_locations import next_location_for_pitch


def confidence_note(pitch_name: str):
    return f" Confidence: {get_pitch_confidence_score(pitch_name)}."


def baseball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies

    first_pitch_of_ab = len(get_recent_pitch_events(history)) == 0

    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 4 and "Fastball hunter" in tendencies:
            pitch_name = best_available(
                ["curveball", "splitter", "slider", "changeup", "sweeper", "cutter", "2-seam", "4-seam"],
                history,
            )
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Cleanup hitter: avoid a clean first-pitch fastball when possible."
                + confidence_note(pitch_name),
            )

        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(
                ["curveball", "splitter", "slider", "changeup", "sweeper", "cutter", "2-seam", "4-seam"],
                history,
            )
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Aggressive fastball hunter: start with spin or offspeed."
                + confidence_note(pitch_name),
            )

        pitch_name = best_available(st.session_state.pitcher_pitches, history)
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "First pitch: best available based mostly on your ranking and confidence."
            + confidence_note(pitch_name),
        )

    if strikes == 2:
        if "Chases high fastball" in tendencies:
            pitch_name = best_available(["4-seam"], history, avoid_last_ball_pitch=True)
            if pitch_name:
                return (
                    pitch_name,
                    "up out of zone",
                    "Two strikes: hitter chases up." + confidence_note(pitch_name),
                )
        if "Chases splitter down" in tendencies:
            pitch_name = best_available(
                ["splitter", "changeup", "curveball"],
                history,
                avoid_last_ball_pitch=True,
            )
            if pitch_name:
                return (
                    pitch_name,
                    "down out of zone",
                    "Two strikes: hitter chases down." + confidence_note(pitch_name),
                )
        if "Chases sweeper away" in tendencies:
            pitch_name = best_available(
                ["sweeper", "slider"],
                history,
                avoid_last_ball_pitch=True,
            )
            if pitch_name:
                return (
                    pitch_name,
                    next_location_for_pitch(pitch_name, handedness, history),
                    "Two strikes: hitter chases away." + confidence_note(pitch_name),
                )

        pitch_name = best_available(
            ["slider", "sweeper", "splitter", "curveball", "changeup"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Two-strike chase pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = best_available(
            ["splitter", "curveball", "changeup", "cutter", "2-seam", "4-seam"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(
                pitch_name, handedness, history, competitive_mode=True
            ),
            "Hitter count: best competitive pitch, not automatically a fastball."
            + confidence_note(pitch_name),
        )

    last = ""
    actual_events = get_recent_pitch_events(history)
    if actual_events:
        last = actual_events[-1]["raw"].lower()

    if "4-seam" in last and "up" in last:
        pitch_name = best_available(
            ["splitter", "changeup", "curveball", "slider"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Tunnel off elevated fastball." + confidence_note(pitch_name),
        )

    if "2-seam" in last or "cutter" in last or "4-seam" in last:
        pitch_name = best_available(
            ["curveball", "splitter", "slider", "changeup", "sweeper", "cutter", "2-seam", "4-seam"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "After a hard pitch, prefer changing speed or shape."
            + confidence_note(pitch_name),
        )

    if "slider" in last or "sweeper" in last:
        pitch_name = best_available(
            ["curveball", "splitter", "changeup", "4-seam", "2-seam", "cutter"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Change lane after breaking ball." + confidence_note(pitch_name),
        )

    if "splitter" in last or "changeup" in last:
        pitch_name = best_available(
            ["curveball", "4-seam", "2-seam", "cutter"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Climb or change shape after soft/down pitch." + confidence_note(pitch_name),
        )

    if "curveball" in last:
        pitch_name = best_available(
            ["splitter", "changeup", "4-seam", "2-seam", "cutter"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Different speed/shape after curve." + confidence_note(pitch_name),
        )

    pitch_name = best_available(
        st.session_state.pitcher_pitches,
        history,
        avoid_last_ball_pitch=True,
    )
    return (
        pitch_name,
        next_location_for_pitch(pitch_name, handedness, history),
        "Default baseball sequence: best available by rank, confidence, and recent usage."
        + confidence_note(pitch_name),
    )


def softball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies

    first_pitch_of_ab = len(get_recent_pitch_events(history)) == 0

    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 4:
            pitch_name = best_available(
                ["curve", "screw", "drop curve", "change", "rise", "drop"],
                history,
            )
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Middle of lineup default: avoid giving a clean first look."
                + confidence_note(pitch_name),
            )

        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(
                ["curve", "screw", "drop curve", "change", "rise", "drop"],
                history,
            )
            return (
                pitch_name,
                next_location_for_pitch(pitch_name, handedness, history),
                "Aggressive hitter: start with movement." + confidence_note(pitch_name),
            )

        pitch_name = best_available(st.session_state.pitcher_pitches, history)
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "First pitch: best available based mostly on your ranking and confidence."
            + confidence_note(pitch_name),
        )

    if strikes == 2:
        if "Chases high fastball" in tendencies:
            pitch_name = best_available(["rise"], history, avoid_last_ball_pitch=True)
            if pitch_name:
                return (
                    pitch_name,
                    "up out of zone",
                    "Two strikes: chase pitch up." + confidence_note(pitch_name),
                )
        if "Chases splitter down" in tendencies:
            pitch_name = best_available(
                ["drop", "drop curve", "change"],
                history,
                avoid_last_ball_pitch=True,
            )
            if pitch_name:
                return (
                    pitch_name,
                    "down out of zone",
                    "Two strikes: chase pitch down." + confidence_note(pitch_name),
                )
        if "Chases sweeper away" in tendencies or "Chases slider away" in tendencies:
            pitch_name = best_available(
                ["curve", "drop curve", "screw"],
                history,
                avoid_last_ball_pitch=True,
            )
            if pitch_name:
                return (
                    pitch_name,
                    next_location_for_pitch(pitch_name, handedness, history),
                    "Two strikes: move off barrel." + confidence_note(pitch_name),
                )

        pitch_name = best_available(
            ["drop curve", "drop", "curve", "screw", "change", "rise"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Two-strike softball chase pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = best_available(
            ["drop", "curve", "screw", "rise", "change"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(
                pitch_name, handedness, history, competitive_mode=True
            ),
            "Hitter count: safe movement strike, with anti-repeat adjustment."
            + confidence_note(pitch_name),
        )

    last = ""
    actual_events = get_recent_pitch_events(history)
    if actual_events:
        last = actual_events[-1]["raw"].lower()

    if "rise" in last:
        pitch_name = best_available(
            ["drop", "drop curve", "change"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Pair rise with drop/change." + confidence_note(pitch_name),
        )

    if "drop" in last and "drop curve" not in last:
        pitch_name = best_available(
            ["rise", "screw", "curve"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Different look after drop." + confidence_note(pitch_name),
        )

    if "curve" in last and "drop curve" not in last:
        pitch_name = best_available(
            ["screw", "rise", "change"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Opposite movement after curve." + confidence_note(pitch_name),
        )

    if "screw" in last:
        pitch_name = best_available(
            ["curve", "rise", "drop"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Opposite movement after screw." + confidence_note(pitch_name),
        )

    if "change" in last:
        pitch_name = best_available(
            ["rise", "drop", "curve"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Speed change into movement." + confidence_note(pitch_name),
        )

    if "drop curve" in last:
        pitch_name = best_available(
            ["rise", "screw", "change"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches,
                history,
                avoid_last_ball_pitch=True,
            )
        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "New lane after drop curve." + confidence_note(pitch_name),
        )

    pitch_name = best_available(
        st.session_state.pitcher_pitches,
        history,
        avoid_last_ball_pitch=True,
    )
    return (
        pitch_name,
        next_location_for_pitch(pitch_name, handedness, history),
        "Default softball sequence: best available by rank, confidence, and recent usage."
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
                p for p in st.session_state.pitcher_pitches
                if p.strip().lower() != last_pitch
            ]

            if alternatives:
                ordered = sorted(
                    alternatives,
                    key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
                )
                new_pitch = ordered[0]
                new_location = next_location_for_pitch(new_pitch, batter["hand"], history)
                new_reason = reason + " Changed pitch after uncompetitive ball."
                return new_pitch, new_location, new_reason

            new_location = next_location_for_pitch(pitch_name, batter["hand"], history)
            if new_location.strip().lower() != last_location:
                return (
                    pitch_name,
                    new_location,
                    reason + " Same pitch kept because no better option, but moved location after uncompetitive ball.",
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
                    reason + " Same pitch allowed after competitive ball, but moved location.",
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
