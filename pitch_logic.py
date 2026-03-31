import streamlit as st


def pitch_available(name: str) -> bool:
    return name in st.session_state.pitcher_pitches


def get_pitch_confidence_score(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("confidence_score", 50))


def get_pitch_rank(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("rank", 99))


def is_actual_pitch_event(item: str) -> bool:
    if item.startswith("Ball Quality |"):
        return False
    parts = [p.strip() for p in item.split("|")]
    return len(parts) >= 3


def get_recent_pitch_events(history):
    events = []
    for item in history:
        if not is_actual_pitch_event(item):
            continue
        parts = [p.strip() for p in item.split("|")]
        pitch = parts[0]
        location = parts[1]
        outcome = parts[2]
        events.append(
            {
                "pitch": pitch,
                "location": location,
                "outcome": outcome,
                "raw": item,
            }
        )
    return events


def last_pitch_event(history):
    events = get_recent_pitch_events(history)
    if not events:
        return None
    return events[-1]


def get_last_ball_quality(history):
    for item in reversed(history):
        if item == "Ball Quality | Competitive":
            return "Competitive"
        if item == "Ball Quality | Uncompetitive":
            return "Uncompetitive"
        if is_actual_pitch_event(item):
            break
    return None


def consecutive_balls_for_pitch(pitch_name: str, history) -> int:
    events = get_recent_pitch_events(history)
    count = 0

    for event in reversed(events):
        current_pitch = event["pitch"].strip().lower()
        outcome = event["outcome"].strip().lower()

        if current_pitch != pitch_name.strip().lower():
            break

        if outcome == "ball":
            count += 1
        else:
            break

    return count


def recent_usage_count(pitch_name: str, history, window: int = 4) -> int:
    events = get_recent_pitch_events(history)
    recent = events[-window:]
    return sum(
        1 for e in recent if e["pitch"].strip().lower() == pitch_name.strip().lower()
    )


def pitch_score(pitch_name: str, history) -> int:
    confidence = get_pitch_confidence_score(pitch_name)
    rank = get_pitch_rank(pitch_name)

    # make pitcher setup matter more
    rank_bonus = max(0, 6 - rank) * 14
    score = confidence + rank_bonus

    same_pitch_balls = consecutive_balls_for_pitch(pitch_name, history)
    if same_pitch_balls == 1:
        score -= 35
    elif same_pitch_balls == 2:
        score -= 80
    elif same_pitch_balls >= 3:
        score -= 140

    usage_count = recent_usage_count(pitch_name, history, window=4)
    score -= max(0, usage_count - 1) * 14

    last_event = last_pitch_event(history)
    if last_event:
        last_pitch = last_event["pitch"].strip().lower()
        last_outcome = last_event["outcome"].strip().lower()
        last_quality = get_last_ball_quality(history)

        if last_pitch == pitch_name.strip().lower():
            if last_outcome == "ball":
                if last_quality == "Uncompetitive":
                    score -= 220
                elif last_quality == "Competitive":
                    score -= 40
                else:
                    score -= 100
            elif last_outcome in ["called strike", "swing miss", "swing foul"]:
                score -= 12

    return score


def best_available(candidates, history, avoid_last_ball_pitch=False):
    available = [p for p in candidates if pitch_available(p)]
    last_event = last_pitch_event(history)
    last_quality = get_last_ball_quality(history)

    if (
        avoid_last_ball_pitch
        and last_event
        and last_event["outcome"].strip().lower() == "ball"
        and last_quality == "Uncompetitive"
    ):
        last_pitch = last_event["pitch"].strip().lower()
        filtered = [p for p in available if p.strip().lower() != last_pitch]
        if filtered:
            available = filtered

    if available:
        ordered = sorted(
            available,
            key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
        )
        return ordered[0]

    fallback = [p for p in st.session_state.pitcher_pitches if pitch_available(p)]
    if fallback:
        ordered = sorted(
            fallback,
            key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
        )
        return ordered[0]

    return None


def baseball_location_options(pitch_name: str, batter_hand: str):
    if pitch_name == "4-seam":
        return ["up away", "up in", "middle away", "top of zone"]
    if pitch_name == "2-seam":
        return ["middle in", "middle away", "low in", "low away"]
    if pitch_name == "changeup":
        return ["low away", "low in", "bottom of zone"]
    if pitch_name == "curveball":
        return ["down away", "down in", "bottom of zone"]
    if pitch_name == "cutter":
        return ["middle in", "middle away", "up in", "low away"]
    if pitch_name == "splitter":
        return ["down out of zone", "bottom of zone", "low away"]
    if pitch_name == "slider":
        return ["down away off plate", "down in off plate", "back foot", "front door"]
    if pitch_name == "sweeper":
        return ["away off plate", "edge away", "back door", "middle away"]
    return ["middle away"]


def softball_location_options(pitch_name: str, batter_hand: str):
    if pitch_name == "rise":
        return ["up away", "up in", "top of zone"]
    if pitch_name == "drop":
        return ["down in zone", "bottom of zone", "low edge"]
    if pitch_name == "curve":
        return ["away", "inside", "edge away"]
    if pitch_name == "screw":
        return ["inside", "away", "edge in"]
    if pitch_name == "change":
        return ["down", "bottom of zone", "low edge"]
    if pitch_name == "drop curve":
        return ["down away", "down in", "low edge"]
    return ["middle"]


def choose_location(pitch_name: str, batter_hand: str, history, sport: str):
    if sport == "Baseball":
        options = baseball_location_options(pitch_name, batter_hand)
    else:
        options = softball_location_options(pitch_name, batter_hand)

    if not history:
        return options[0]

    last_event = last_pitch_event(history)
    if not last_event:
        return options[0]

    last_pitch = last_event["pitch"].strip().lower()
    last_location = last_event["location"].strip().lower()
    current_pitch = pitch_name.strip().lower()

    # same pitch -> try a different location
    if current_pitch == last_pitch:
        for loc in options:
            if loc.strip().lower() != last_location:
                return loc

    # otherwise use top option
    return options[0]


def baseball_location_for_pitch(pitch_name: str, batter_hand: str, history=None):
    return choose_location(pitch_name, batter_hand, history or [], "Baseball")


def softball_location_for_pitch(pitch_name: str, batter_hand: str, history=None):
    return choose_location(pitch_name, batter_hand, history or [], "Softball")


def confidence_note(pitch_name: str):
    return f" Confidence: {get_pitch_confidence_score(pitch_name)}."


def baseball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies

    first_pitch_of_ab = len(get_recent_pitch_events(history)) == 0

    # first pitch: let rank/confidence drive it more
    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 4 and "Fastball hunter" in tendencies:
            pitch_name = best_available(
                ["curveball", "slider", "sweeper", "changeup", "cutter", "2-seam", "4-seam"],
                history,
            )
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness, history),
                "Cleanup hitter: avoid a clean first-pitch heater when possible."
                + confidence_note(pitch_name),
            )

        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(
                ["curveball", "slider", "sweeper", "changeup", "cutter", "2-seam", "4-seam"],
                history,
            )
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness, history),
                "Aggressive fastball hunter: mix in spin or offspeed first."
                + confidence_note(pitch_name),
            )

        pitch_name = best_available(st.session_state.pitcher_pitches, history)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness, history),
            "First pitch: best available by rank and confidence."
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
                ["sweeper", "slider", "curveball"],
                history,
                avoid_last_ball_pitch=True,
            )
            if pitch_name:
                return (
                    pitch_name,
                    baseball_location_for_pitch(pitch_name, handedness, history),
                    "Two strikes: hitter chases away." + confidence_note(pitch_name),
                )

        pitch_name = best_available(
            ["slider", "sweeper", "splitter", "curveball", "changeup"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness, history),
            "Two-strike chase pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = best_available(
            ["cutter", "2-seam", "changeup", "4-seam", "curveball"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness, history),
            "Hitter count: go to a safer competitive strike."
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
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            "down out of zone"
            if pitch_name in ["splitter", "changeup"]
            else baseball_location_for_pitch(pitch_name, handedness, history),
            "Tunnel off elevated fastball." + confidence_note(pitch_name),
        )

    if "2-seam" in last or "cutter" in last:
        pitch_name = best_available(
            ["curveball", "slider", "sweeper", "splitter", "changeup"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness, history),
            "Move off previous hard pitch." + confidence_note(pitch_name),
        )

    if "slider" in last or "sweeper" in last or "curveball" in last:
        pitch_name = best_available(
            ["changeup", "2-seam", "4-seam", "cutter"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness, history),
            "Change lane and speed after breaking ball." + confidence_note(pitch_name),
        )

    if "splitter" in last or "changeup" in last:
        pitch_name = best_available(
            ["curveball", "cutter", "4-seam", "2-seam"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness, history),
            "Climb or change shape after soft pitch." + confidence_note(pitch_name),
        )

    pitch_name = best_available(
        st.session_state.pitcher_pitches,
        history,
        avoid_last_ball_pitch=True,
    )
    return (
        pitch_name,
        baseball_location_for_pitch(pitch_name, handedness, history),
        "Default baseball sequence." + confidence_note(pitch_name),
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
                ["curve", "drop curve", "screw", "change", "rise", "drop"],
                history,
            )
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness, history),
                "Middle of lineup: avoid giving a clean first look."
                + confidence_note(pitch_name),
            )

        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(
                ["curve", "drop curve", "screw", "change", "rise", "drop"],
                history,
            )
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness, history),
                "Aggressive hitter: start with movement."
                + confidence_note(pitch_name),
            )

        pitch_name = best_available(st.session_state.pitcher_pitches, history)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness, history),
            "First pitch: best available by rank and confidence."
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

        pitch_name = best_available(
            ["drop curve", "drop", "curve", "screw", "change", "rise"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness, history),
            "Two-strike softball chase pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = best_available(
            ["drop", "curve", "screw", "change", "rise"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness, history),
            "Hitter count: safe movement strike."
            + confidence_note(pitch_name),
        )

    last = ""
    actual_events = get_recent_pitch_events(history)
    if actual_events:
        last = actual_events[-1]["raw"].lower()

    if "rise" in last:
        pitch_name = best_available(
            ["drop", "drop curve", "change", "curve"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness, history),
            "Pair rise with drop/change." + confidence_note(pitch_name),
        )

    if "drop" in last and "drop curve" not in last:
        pitch_name = best_available(
            ["rise", "screw", "curve", "change"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness, history),
            "Different look after drop." + confidence_note(pitch_name),
        )

    if "curve" in last and "drop curve" not in last:
        pitch_name = best_available(
            ["screw", "rise", "change", "drop"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness, history),
            "Opposite movement after curve." + confidence_note(pitch_name),
        )

    if "screw" in last:
        pitch_name = best_available(
            ["curve", "rise", "drop", "change"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness, history),
            "Opposite movement after screw." + confidence_note(pitch_name),
        )

    if "change" in last:
        pitch_name = best_available(
            ["rise", "drop", "curve", "screw"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(st.session_state.pitcher_pitches, history, True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness, history),
            "Speed change into movement." + confidence_note(pitch_name),
        )

    pitch_name = best_available(
        st.session_state.pitcher_pitches,
        history,
        avoid_last_ball_pitch=True,
    )
    return (
        pitch_name,
        softball_location_for_pitch(pitch_name, handedness, history),
        "Default softball sequence." + confidence_note(pitch_name),
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

                if st.session_state.sport == "Baseball":
                    new_location = baseball_location_for_pitch(new_pitch, batter["hand"], history)
                else:
                    new_location = softball_location_for_pitch(new_pitch, batter["hand"], history)

                new_reason = reason + " Changed pitch after uncompetitive ball."
                return new_pitch, new_location, new_reason

    if current_pitch == last_pitch:
        if st.session_state.sport == "Baseball":
            options = baseball_location_options(pitch_name, batter["hand"])
        else:
            options = softball_location_options(pitch_name, batter["hand"])

        for loc in options:
            if loc.strip().lower() != last_location:
                if last_quality == "Competitive":
                    return (
                        pitch_name,
                        loc,
                        reason + " Same pitch allowed after competitive ball, but moved location.",
                    )
                if last_quality == "Uncompetitive":
                    return (
                        pitch_name,
                        loc,
                        reason + " Same pitch kept only because no better option, moved location after uncompetitive ball.",
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
