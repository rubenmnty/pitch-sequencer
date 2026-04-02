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


def get_last_pitch_name(history):
    last_event = last_pitch_event(history)
    if not last_event:
        return None
    return last_event["pitch"].strip().lower()


def get_default_baseball_opener_candidates(batter):
    tendencies = batter["tendencies"]

    candidates = ["cutter", "2-seam", "4-seam", "changeup", "curveball"]

    if "Fastball hunter" in tendencies or "Aggressive first pitch" in tendencies:
        candidates = ["cutter", "2-seam", "changeup", "curveball", "4-seam"]

    return candidates


def get_next_baseball_sequence_candidates(last_pitch):
    if last_pitch in {"4-seam", "2-seam", "cutter"}:
        return ["splitter", "changeup", "slider", "curveball", "sweeper"]

    if last_pitch in {"slider", "sweeper", "curveball"}:
        return ["4-seam", "2-seam", "cutter", "changeup", "splitter"]

    if last_pitch in {"splitter", "changeup"}:
        return ["4-seam", "2-seam", "cutter", "slider", "curveball"]

    return ["cutter", "2-seam", "4-seam", "changeup", "curveball"]


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
            if name in {"cutter", "2-seam", "4-seam"}:
                score += 16
            if name in {"changeup", "curveball", "curve"}:
                score += 4
            if name in {"slider", "sweeper", "splitter"}:
                score -= 14
            if intent == "steal":
                score += 6

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
        candidates = get_default_baseball_opener_candidates(batter)
        if not available_pitches(candidates):
            candidates = st.session_state.pitcher_pitches

        pitch_name = choose_by_mode(candidates, history, "opener", "opening")

        return (
            pitch_name,
            next_location_for_pitch(
                pitch_name,
                handedness,
                history,
                competitive_mode=True,
            ),
            "0-0 opener: establish a real starting pitch for the at-bat, usually a command hard pitch unless matchup says otherwise."
            + confidence_note(pitch_name),
        )

    if phase == "second_pitch":
        last_pitch_name = get_last_pitch_name(history)
        candidates = get_next_baseball_sequence_candidates(last_pitch_name)

        pitch_name = choose_by_mode(candidates, history, "balance", "second_pitch")
        if pitch_name is None:
            pitch_name = choose_by_mode(
                st.session_state.pitcher_pitches,
                history,
                "balance",
                "second_pitch",
            )

        return (
            pitch_name,
            next_location_for_pitch(pitch_name, handedness, history),
            "Second pitch: chosen to build off the opener and set up the rest of the at-bat."
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
This is pitch scoring 
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
    pitch_to_family = {
        "4-seam": "hard",
        "2-seam": "hard",
        "cutter": "hard",
        "rise": "hard",
        "curveball": "breaking",
        "slider": "breaking",
        "sweeper": "breaking",
        "curve": "breaking",
        "screw": "breaking",
        "drop curve": "breaking",
        "drop": "breaking",
        "changeup": "offspeed",
        "splitter": "offspeed",
        "change": "offspeed",
    }

    events = [
        item for item in st.session_state.ab_history
        if " | " in item and not item.startswith("Ball Quality |")
    ][-window:]

    count = 0
    for event in events:
        pitch = event.split("|")[0].strip().lower()
        if pitch_to_family.get(pitch, "other") == family:
            count += 1
    return count


def pitch_score(pitch_name: str, history) -> int:
    confidence = get_pitch_confidence_score(pitch_name)
    rank = get_pitch_rank(pitch_name)
    name = pitch_name.strip().lower()
    family = get_pitch_family(pitch_name)

    rank_bonus_map = {
        1: 55,
        2: 30,
        3: 12,
        4: 0,
        5: -10,
        6: -18,
    }
    rank_bonus = rank_bonus_map.get(rank, -24)

    score = confidence + rank_bonus

    same_pitch_balls = consecutive_balls_for_pitch(pitch_name, history)
    if same_pitch_balls == 1:
        score -= 55
    elif same_pitch_balls == 2:
        score -= 110
    elif same_pitch_balls >= 3:
        score -= 170

    consecutive_usage = consecutive_usage_for_pitch(pitch_name, history)
    if consecutive_usage == 1:
        score -= 8
    elif consecutive_usage == 2:
        score -= 26
    elif consecutive_usage >= 3:
        score -= 55

    usage_count = recent_usage_count(pitch_name, history, window=5)
    score -= usage_count * 15

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
                score -= 18

    if family == "hard":
        score -= recent_family_count("hard", history, window=5) * 10
    elif family == "breaking":
        score -= recent_family_count("breaking", history, window=5) * 5
    elif family == "offspeed":
        score -= recent_family_count("offspeed", history, window=5) * 4

    if name in {"4-seam", "2-seam", "cutter"}:
        hard_recent = recent_hard_pitch_count(history, window=5)
        score -= hard_recent * 10

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
And pitch locations 

import streamlit as st

from pitch_history import get_recent_pitch_events, last_location_for_pitch


def baseball_location_for_pitch(pitch_name: str, batter_hand: str):
    if pitch_name == "4-seam":
        return "up away" if batter_hand == "R" else "up in"
    if pitch_name == "2-seam":
        return "middle in" if batter_hand == "R" else "middle away"
    if pitch_name == "changeup":
        return "low away" if batter_hand == "R" else "low in"
    if pitch_name == "curveball":
        return "down away" if batter_hand == "R" else "down in"
    if pitch_name == "cutter":
        return "middle in" if batter_hand == "R" else "middle away"
    if pitch_name == "splitter":
        return "down out of zone"
    if pitch_name == "slider":
        return "down away off plate" if batter_hand == "R" else "down in off plate"
    if pitch_name == "sweeper":
        return "away off plate" if batter_hand == "R" else "in off plate"
    return "middle away"


def baseball_alternate_locations(pitch_name: str, batter_hand: str):
    if pitch_name == "4-seam":
        return (
            ["up away", "middle away", "top of zone", "up in", "middle in"]
            if batter_hand == "R"
            else ["up in", "middle in", "top of zone", "up away", "middle away"]
        )
    if pitch_name == "2-seam":
        return (
            ["middle in", "low in", "middle away", "low away", "top in"]
            if batter_hand == "R"
            else ["middle away", "low away", "middle in", "low in", "top away"]
        )
    if pitch_name == "changeup":
        return (
            ["low away", "bottom of zone", "low in", "middle away"]
            if batter_hand == "R"
            else ["low in", "bottom of zone", "low away", "middle in"]
        )
    if pitch_name == "curveball":
        return (
            ["down away", "bottom of zone", "down in", "front-door strike"]
            if batter_hand == "R"
            else ["down in", "bottom of zone", "down away", "back-door strike"]
        )
    if pitch_name == "cutter":
        return (
            ["middle in", "middle away", "low away", "up in", "front hip"]
            if batter_hand == "R"
            else ["middle away", "middle in", "low in", "up away", "front hip"]
        )
    if pitch_name == "splitter":
        return ["down out of zone", "bottom of zone", "low away", "low in", "below knees"]
    if pitch_name == "slider":
        return (
            ["down away off plate", "back foot", "front door", "edge away", "down middle"]
            if batter_hand == "R"
            else ["down in off plate", "back foot", "front door", "edge in", "down middle"]
        )
    if pitch_name == "sweeper":
        return (
            ["away off plate", "edge away", "back door", "middle away", "early strike away"]
            if batter_hand == "R"
            else ["in off plate", "edge in", "back door", "middle in", "early strike in"]
        )
    return [baseball_location_for_pitch(pitch_name, batter_hand)]


def softball_location_for_pitch(pitch_name: str, batter_hand: str):
    if pitch_name == "rise":
        return "up away" if batter_hand == "R" else "up in"
    if pitch_name == "drop":
        return "down in zone"
    if pitch_name == "curve":
        return "inside" if batter_hand == "L" else "away"
    if pitch_name == "screw":
        return "inside" if batter_hand == "R" else "away"
    if pitch_name == "change":
        return "down"
    if pitch_name == "drop curve":
        return "down away" if batter_hand == "R" else "down in"
    return "middle"


def softball_alternate_locations(pitch_name: str, batter_hand: str):
    if pitch_name == "rise":
        return ["up away", "top of zone", "up in", "middle up"]
    if pitch_name == "drop":
        return ["down in zone", "bottom of zone", "low edge", "low middle"]
    if pitch_name == "curve":
        return ["away", "edge away", "inside", "middle away"]
    if pitch_name == "screw":
        return ["inside", "edge in", "away", "middle in"]
    if pitch_name == "change":
        return ["down", "bottom of zone", "low edge", "middle down"]
    if pitch_name == "drop curve":
        return ["down away", "low edge", "down in", "bottom of zone"]
    return [softball_location_for_pitch(pitch_name, batter_hand)]


def location_band(location: str) -> str:
    loc = location.strip().lower()

    if any(word in loc for word in ["up", "top"]):
        return "up"
    if any(word in loc for word in ["down", "bottom", "low", "below"]):
        return "down"
    if any(word in loc for word in ["middle"]):
        return "middle"
    return "other"


def side_band(location: str) -> str:
    loc = location.strip().lower()

    if any(word in loc for word in ["away", "edge away", "back door"]):
        return "away"
    if any(word in loc for word in ["in", "inside", "edge in", "front hip", "back foot"]):
        return "in"
    return "middle"


def get_recent_locations(history, window: int = 4):
    events = get_recent_pitch_events(history)
    return [e["location"].strip().lower() for e in events[-window:]]


def count_matching_bands(locations, target_band, band_func):
    return sum(1 for loc in locations if band_func(loc) == target_band)


def next_location_for_pitch(
    pitch_name: str, batter_hand: str, history, competitive_mode=False
):
    if st.session_state.sport == "Baseball":
        options = baseball_alternate_locations(pitch_name, batter_hand)
    else:
        options = softball_alternate_locations(pitch_name, batter_hand)

    last_same_pitch_loc = last_location_for_pitch(pitch_name, history)
    recent_locations = get_recent_locations(history, window=4)

    scored_options = []

    for idx, loc in enumerate(options):
        score = 0
        loc_clean = loc.strip().lower()

        if loc_clean == (last_same_pitch_loc or ""):
            score -= 100

        same_exact_recent = recent_locations.count(loc_clean)
        score -= same_exact_recent * 30

        height = location_band(loc_clean)
        side = side_band(loc_clean)

        score -= count_matching_bands(recent_locations, height, location_band) * 8
        score -= count_matching_bands(recent_locations, side, side_band) * 6

        if competitive_mode:
            if idx == 0:
                score += 6
            elif idx == 1:
                score += 10
            elif idx == 2:
                score += 4
            else:
                score -= 2
        else:
            if idx == 0:
                score += 4
            elif idx == 1:
                score += 6
            else:
                score += 2

        scored_options.append((loc, score))

    scored_options.sort(key=lambda x: -x[1])
    return scored_options[0][0]
