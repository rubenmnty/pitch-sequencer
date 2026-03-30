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


def last_pitch_name(history):
    event = last_pitch_event(history)
    if not event:
        return None
    return event["pitch"]


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
    return sum(1 for e in recent if e["pitch"].strip().lower() == pitch_name.strip().lower())


def pitch_score(pitch_name: str, history) -> int:
    confidence = get_pitch_confidence_score(pitch_name)
    rank = get_pitch_rank(pitch_name)

    rank_bonus = max(0, 6 - rank) * 8
    score = confidence + rank_bonus

    same_pitch_balls = consecutive_balls_for_pitch(pitch_name, history)
    if same_pitch_balls >= 1:
        score -= 120

    usage_count = recent_usage_count(pitch_name, history, window=4)
    score -= max(0, usage_count - 1) * 12

    last_event = last_pitch_event(history)
    if last_event:
        last_pitch = last_event["pitch"].strip().lower()
        last_outcome = last_event["outcome"].strip().lower()

        if last_pitch == pitch_name.strip().lower() and last_outcome == "ball":
            score -= 150

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

    last_event = last_pitch_event(history)

    # 🔥 HARD BLOCK: if last pitch was a ball, NEVER repeat it
    if last_event and last_event["outcome"].strip().lower() == "ball":
        last_pitch = last_event["pitch"]
        filtered = [p for p in available if p != last_pitch]

        if filtered:
            available = filtered

    if not available:
        available = [p for p in candidates if pitch_available(p)]

    if available:
        ordered = sorted(
            available,
            key=lambda p: (-pitch_score(p, history), get_pitch_rank(p), p),
        )
        return ordered[0]

    if st.session_state.pitcher_pitches:
        ordered = sorted(
            st.session_state.pitcher_pitches,
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
                "Top of lineup default: get ahead with a safe strike." + confidence_note(pitch_name),
            )
        if use_default and slot_num == 4 and "Fastball hunter" in tendencies:
            pitch_name = best_available(["slider", "sweeper", "curveball", "changeup"], history)
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Cleanup hitter: do not give a clean first fastball." + confidence_note(pitch_name),
            )
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(["slider", "sweeper", "curveball"], history)
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Aggressive fastball hunter: start with spin." + confidence_note(pitch_name),
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
                return pitch_name, "up out of zone", "Two strikes: hitter chases up." + confidence_note(pitch_name)
        if "Chases splitter down" in tendencies:
            pitch_name = best_available(["splitter", "changeup", "curveball"], history, avoid_last_ball_pitch=True)
            if pitch_name:
                return pitch_name, "down out of zone", "Two strikes: hitter chases down." + confidence_note(pitch_name)
        if "Chases sweeper away" in tendencies:
            pitch_name = best_available(["sweeper", "slider"], history, avoid_last_ball_pitch=True)
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
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Hitter count: safer competitive strike, with anti-repeat adjustment." + confidence_note(pitch_name),
        )

    last = ""
    actual_events = get_recent_pitch_events(history)
    if actual_events:
        last = actual_events[-1]["raw"].lower()

    if "4-seam" in last and "up" in last:
        pitch_name = best_available(["splitter", "changeup", "curveball"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            "down out of zone" if pitch_name in ["splitter", "changeup"] else baseball_location_for_pitch(pitch_name, handedness),
            "Tunnel off elevated fastball." + confidence_note(pitch_name),
        )
    if "2-seam" in last or "cutter" in last:
        pitch_name = best_available(["slider", "sweeper", "curveball", "splitter"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Move off previous hard pitch." + confidence_note(pitch_name),
        )
    if "slider" in last or "sweeper" in last:
        pitch_name = best_available(["4-seam", "2-seam", "cutter"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Change lane after breaking ball." + confidence_note(pitch_name),
        )
    if "splitter" in last or "changeup" in last:
        pitch_name = best_available(["4-seam", "cutter"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Climb after soft/down pitch." + confidence_note(pitch_name),
        )
    if "curveball" in last:
        pitch_name = best_available(["4-seam", "cutter", "changeup"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Different speed/shape after curve." + confidence_note(pitch_name),
        )

    pitch_name = best_available(["4-seam", "2-seam", "cutter"], history, avoid_last_ball_pitch=True)
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
                "Top of lineup default: steal a strike with movement." + confidence_note(pitch_name),
            )
        if use_default and slot_num == 4:
            pitch_name = best_available(["curve", "screw", "drop curve", "change"], history)
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Middle of lineup default: avoid giving a clean first look." + confidence_note(pitch_name),
            )
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(["curve", "screw", "drop curve", "change"], history)
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
                return pitch_name, "up out of zone", "Two strikes: chase pitch up." + confidence_note(pitch_name)
        if "Chases splitter down" in tendencies:
            pitch_name = best_available(["drop", "drop curve", "change"], history, avoid_last_ball_pitch=True)
            if pitch_name:
                return pitch_name, "down out of zone", "Two strikes: chase pitch down." + confidence_note(pitch_name)
        if "Chases sweeper away" in tendencies or "Chases slider away" in tendencies:
            pitch_name = best_available(["curve", "drop curve", "screw"], history, avoid_last_ball_pitch=True)
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
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Hitter count: safe movement strike, with anti-repeat adjustment." + confidence_note(pitch_name),
        )

    last = ""
    actual_events = get_recent_pitch_events(history)
    if actual_events:
        last = actual_events[-1]["raw"].lower()

    if "rise" in last:
        pitch_name = best_available(["drop", "drop curve", "change"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Pair rise with drop/change." + confidence_note(pitch_name),
        )
    if "drop" in last and "drop curve" not in last:
        pitch_name = best_available(["rise", "screw", "curve"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Different look after drop." + confidence_note(pitch_name),
        )
    if "curve" in last and "drop curve" not in last:
        pitch_name = best_available(["screw", "rise", "change"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Opposite movement after curve." + confidence_note(pitch_name),
        )
    if "screw" in last:
        pitch_name = best_available(["curve", "rise", "drop"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Opposite movement after screw." + confidence_note(pitch_name),
        )
    if "change" in last:
        pitch_name = best_available(["rise", "drop", "curve"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Speed change into movement." + confidence_note(pitch_name),
        )
    if "drop curve" in last:
        pitch_name = best_available(["rise", "screw", "change"], history, avoid_last_ball_pitch=True)
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "New lane after drop curve." + confidence_note(pitch_name),
        )

    pitch_name = best_available(["rise", "drop", "curve", "screw", "change"], history, avoid_last_ball_pitch=True)
    return (
        pitch_name,
        softball_location_for_pitch(pitch_name, handedness),
        "Default softball sequence." + confidence_note(pitch_name),
    )


def recommend_pitch(batter, balls, strikes, history):
    if st.session_state.sport == "Baseball":
        return baseball_recommend_pitch(batter, balls, strikes, history)
    return softball_recommend_pitch(batter, balls, strikes, history)
