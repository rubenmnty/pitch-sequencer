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

    rank_bonus = max(0, 6 - rank) * 8
    score = confidence + rank_bonus

    same_pitch_balls = consecutive_balls_for_pitch(pitch_name, history)
    if same_pitch_balls == 1:
        score -= 45
    elif same_pitch_balls == 2:
        score -= 90
    elif same_pitch_balls >= 3:
        score -= 140

    usage_count = recent_usage_count(pitch_name, history, window=4)
    score -= max(0, usage_count - 1) * 12

    last_event = last_pitch_event(history)
    if last_event:
        last_pitch = last_event["pitch"].strip().lower()
        last_outcome = last_event["outcome"].strip().lower()
        last_quality = get_last_ball_quality(history)

        if last_pitch == pitch_name.strip().lower() and last_outcome == "ball":
            if last_quality == "Uncompetitive":
                score -= 200
            elif last_quality == "Competitive":
                score -= 60
            else:
                score -= 120

    return score


def best_available(candidates, history, avoid_last_ball_pitch=False):
    available = [p for p in candidates if pitch_available(p)]
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

    if available:
        ordered = sorted(
            available,
            key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
        )
        return ordered[0]

    if st.session_state.pitcher_pitches:
        fallback = st.session_state.pitcher_pitches[:]

        if (
            avoid_last_ball_pitch
            and last_event
            and last_event["outcome"].strip().lower() == "ball"
        ):
            last_pitch = last_event["pitch"].strip().lower()
            if last_quality == "Uncompetitive":
                fallback_filtered = [
                    p for p in fallback if p.strip().lower() != last_pitch
                ]
                if fallback_filtered:
                    fallback = fallback_filtered

        if fallback:
            ordered = sorted(
                fallback,
                key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
            )
            return ordered[0]

    return None


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
        return ["up away", "middle away", "up in", "top of zone"]
    if pitch_name == "2-seam":
        return ["middle in", "low in", "middle away", "low away"]
    if pitch_name == "changeup":
        return ["low away", "bottom of zone", "low in"]
    if pitch_name == "curveball":
        return ["down away", "bottom of zone", "down in"]
    if pitch_name == "cutter":
        return ["middle in", "middle away", "low away", "up in"]
    if pitch_name == "splitter":
        return ["down out of zone", "bottom of zone", "low away"]
    if pitch_name == "slider":
        return ["down away off plate", "back foot", "front door"]
    if pitch_name == "sweeper":
        return ["away off plate", "edge away", "back door"]
    return [baseball_location_for_pitch(pitch_name, batter_hand)]


def baseball_competitive_adjusted_location(pitch_name: str, batter_hand: str):
    options = baseball_alternate_locations(pitch_name, batter_hand)
    return options[1] if len(options) > 1 else options[0]


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
        return ["up away", "top of zone", "up in"]
    if pitch_name == "drop":
        return ["down in zone", "bottom of zone", "low edge"]
    if pitch_name == "curve":
        return ["away", "edge away", "inside"]
    if pitch_name == "screw":
        return ["inside", "edge in", "away"]
    if pitch_name == "change":
        return ["down", "bottom of zone", "low edge"]
    if pitch_name == "drop curve":
        return ["down away", "low edge", "down in"]
    return [softball_location_for_pitch(pitch_name, batter_hand)]


def softball_competitive_adjusted_location(pitch_name: str, batter_hand: str):
    options = softball_alternate_locations(pitch_name, batter_hand)
    return options[1] if len(options) > 1 else options[0]


def confidence_note(pitch_name: str):
    return f" Confidence: {get_pitch_confidence_score(pitch_name)}."


def baseball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies

    first_pitch_of_ab = len(get_recent_pitch_events(history)) == 0

    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 1:
            pitch_name = best_available(["cutter", "2-seam", "4-seam"], history)
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Top of lineup default: get ahead with a safe strike."
                + confidence_note(pitch_name),
            )
        if use_default and slot_num == 4 and "Fastball hunter" in tendencies:
            pitch_name = best_available(
                ["slider", "sweeper", "curveball", "changeup"], history
            )
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Cleanup hitter: do not give a clean first fastball."
                + confidence_note(pitch_name),
            )
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(["slider", "sweeper", "curveball"], history)
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Aggressive fastball hunter: start with spin."
                + confidence_note(pitch_name),
            )
        pitch_name = best_available(["4-seam", "2-seam", "cutter"], history)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Default baseball first pitch." + confidence_note(pitch_name),
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
                ["sweeper", "slider"], history, avoid_last_ball_pitch=True
            )
            if pitch_name:
                return (
                    pitch_name,
                    baseball_location_for_pitch(pitch_name, handedness),
                    "Two strikes: hitter chases away." + confidence_note(pitch_name),
                )
        pitch_name = best_available(
            ["slider", "sweeper", "splitter", "curveball", "changeup"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Two-strike chase pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = best_available(
            ["cutter", "4-seam", "2-seam", "changeup"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Hitter count: safer competitive strike, with anti-repeat adjustment."
            + confidence_note(pitch_name),
        )

    last = ""
    actual_events = get_recent_pitch_events(history)
    if actual_events:
        last = actual_events[-1]["raw"].lower()

    if "4-seam" in last and "up" in last:
        pitch_name = best_available(
            ["splitter", "changeup", "curveball"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            "down out of zone"
            if pitch_name in ["splitter", "changeup"]
            else baseball_location_for_pitch(pitch_name, handedness),
            "Tunnel off elevated fastball." + confidence_note(pitch_name),
        )

    if "2-seam" in last or "cutter" in last:
        pitch_name = best_available(
            ["slider", "sweeper", "curveball", "splitter"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Move off previous hard pitch." + confidence_note(pitch_name),
        )

    if "slider" in last or "sweeper" in last:
        pitch_name = best_available(
            ["4-seam", "2-seam", "cutter"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Change lane after breaking ball." + confidence_note(pitch_name),
        )

    if "splitter" in last or "changeup" in last:
        pitch_name = best_available(
            ["4-seam", "cutter"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Climb after soft/down pitch." + confidence_note(pitch_name),
        )

    if "curveball" in last:
        pitch_name = best_available(
            ["4-seam", "cutter", "changeup"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Different speed/shape after curve." + confidence_note(pitch_name),
        )

    pitch_name = best_available(
        ["4-seam", "2-seam", "cutter"],
        history,
        avoid_last_ball_pitch=True,
    )
    if pitch_name is None:
        pitch_name = best_available(
            st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
        )
    return (
        pitch_name,
        baseball_location_for_pitch(pitch_name, handedness),
        "Default baseball sequence." + confidence_note(pitch_name),
    )


def softball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies

    first_pitch_of_ab = len(get_recent_pitch_events(history)) == 0

    if balls == 0 and strikes == 0 and first_pitch_of_ab:
        if use_default and slot_num == 1:
            pitch_name = best_available(["curve", "screw", "drop"], history)
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Top of lineup default: steal a strike with movement."
                + confidence_note(pitch_name),
            )
        if use_default and slot_num == 4:
            pitch_name = best_available(
                ["curve", "screw", "drop curve", "change"], history
            )
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Middle of lineup default: avoid giving a clean first look."
                + confidence_note(pitch_name),
            )
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(
                ["curve", "screw", "drop curve", "change"], history
            )
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Aggressive hitter: start with movement." + confidence_note(pitch_name),
            )
        pitch_name = best_available(["rise", "drop", "curve", "screw"], history)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Default softball first pitch." + confidence_note(pitch_name),
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
                    softball_location_for_pitch(pitch_name, handedness),
                    "Two strikes: move off barrel." + confidence_note(pitch_name),
                )
        pitch_name = best_available(
            ["drop curve", "drop", "curve", "screw", "change", "rise"],
            history,
            avoid_last_ball_pitch=True,
        )
        if pitch_name is None:
            pitch_name = best_available(
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
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
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
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
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
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
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
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
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
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
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
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
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
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
                st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
            )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "New lane after drop curve." + confidence_note(pitch_name),
        )

    pitch_name = best_available(
        ["rise", "drop", "curve", "screw", "change"],
        history,
        avoid_last_ball_pitch=True,
    )
    if pitch_name is None:
        pitch_name = best_available(
            st.session_state.pitcher_pitches, history, avoid_last_ball_pitch=True
        )
    return (
        pitch_name,
        softball_location_for_pitch(pitch_name, handedness),
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
                    new_location = baseball_location_for_pitch(new_pitch, batter["hand"])
                else:
                    new_location = softball_location_for_pitch(new_pitch, batter["hand"])

                new_reason = reason + " Changed pitch after uncompetitive ball."
                return new_pitch, new_location, new_reason

            if st.session_state.sport == "Baseball":
                options = baseball_alternate_locations(pitch_name, batter["hand"])
            else:
                options = softball_alternate_locations(pitch_name, batter["hand"])

            for loc in options:
                if loc.strip().lower() != last_location:
                    return (
                        pitch_name,
                        loc,
                        reason + " Same pitch kept because no better option, but moved location after uncompetitive ball.",
                    )

        return pitch_name, location, reason

    if last_quality == "Competitive":
        if current_pitch == last_pitch:
            if st.session_state.sport == "Baseball":
                options = baseball_alternate_locations(pitch_name, batter["hand"])
            else:
                options = softball_alternate_locations(pitch_name, batter["hand"])

            for loc in options:
                if loc.strip().lower() != last_location:
                    return (
                        pitch_name,
                        loc,
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
