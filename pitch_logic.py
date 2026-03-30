import streamlit as st


def pitch_available(name: str) -> bool:
    return name in st.session_state.pitcher_pitches


def get_pitch_confidence_score(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("confidence_score", 50))


def get_pitch_rank(name: str) -> int:
    profile = st.session_state.pitch_profiles.get(name, {})
    return int(profile.get("rank", 99))


def sort_candidates(candidates):
    available = [p for p in candidates if pitch_available(p)]
    if not available:
        return []
    return sorted(
        available,
        key=lambda p: (-get_pitch_confidence_score(p), get_pitch_rank(p), p)
    )


def best_available(candidates):
    ordered = sort_candidates(candidates)
    if ordered:
        return ordered[0]
    if st.session_state.pitcher_pitches:
        return sorted(
            st.session_state.pitcher_pitches,
            key=lambda p: (-get_pitch_confidence_score(p), get_pitch_rank(p), p)
        )[0]
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

    if balls == 0 and strikes == 0 and len(history) == 0:
        if use_default and slot_num == 1:
            pitch_name = best_available(["cutter", "2-seam", "4-seam"])
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Top of lineup default: get ahead with a safe strike." + confidence_note(pitch_name),
            )
        if use_default and slot_num == 4 and "Fastball hunter" in tendencies:
            pitch_name = best_available(["slider", "sweeper", "curveball", "changeup"])
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Cleanup hitter: do not give a clean first fastball." + confidence_note(pitch_name),
            )
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(["slider", "sweeper", "curveball"])
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Aggressive fastball hunter: start with spin." + confidence_note(pitch_name),
            )
        pitch_name = best_available(["4-seam", "2-seam", "cutter"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Default baseball first pitch." + confidence_note(pitch_name),
        )

    if strikes == 2:
        if "Chases high fastball" in tendencies:
            pitch_name = best_available(["4-seam"])
            if pitch_name:
                return pitch_name, "up out of zone", "Two strikes: hitter chases up." + confidence_note(pitch_name)
        if "Chases splitter down" in tendencies:
            pitch_name = best_available(["splitter", "changeup", "curveball"])
            if pitch_name:
                return pitch_name, "down out of zone", "Two strikes: hitter chases down." + confidence_note(pitch_name)
        if "Chases sweeper away" in tendencies:
            pitch_name = best_available(["sweeper", "slider"])
            if pitch_name:
                return (
                    pitch_name,
                    baseball_location_for_pitch(pitch_name, handedness),
                    "Two strikes: hitter chases away." + confidence_note(pitch_name),
                )
        pitch_name = best_available(["slider", "sweeper", "splitter", "curveball", "changeup"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Two-strike chase pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = best_available(["cutter", "2-seam", "4-seam"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Hitter count: safer competitive strike." + confidence_note(pitch_name),
        )

    last = history[-1].lower() if history else ""

    if "4-seam" in last and "up" in last:
        pitch_name = best_available(["splitter", "changeup", "curveball"])
        return (
            pitch_name,
            "down out of zone" if pitch_name in ["splitter", "changeup"] else baseball_location_for_pitch(pitch_name, handedness),
            "Tunnel off elevated fastball." + confidence_note(pitch_name),
        )
    if "2-seam" in last or "cutter" in last:
        pitch_name = best_available(["slider", "sweeper", "curveball", "splitter"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Move off previous hard pitch." + confidence_note(pitch_name),
        )
    if "slider" in last or "sweeper" in last:
        pitch_name = best_available(["4-seam", "2-seam", "cutter"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Change lane after breaking ball." + confidence_note(pitch_name),
        )
    if "splitter" in last or "changeup" in last:
        pitch_name = best_available(["4-seam", "cutter"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Climb after soft/down pitch." + confidence_note(pitch_name),
        )
    if "curveball" in last:
        pitch_name = best_available(["4-seam", "cutter", "changeup"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Different speed/shape after curve." + confidence_note(pitch_name),
        )

    pitch_name = best_available(["4-seam", "2-seam", "cutter"])
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

    if balls == 0 and strikes == 0 and len(history) == 0:
        if use_default and slot_num == 1:
            pitch_name = best_available(["curve", "screw", "drop"])
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Top of lineup default: steal a strike with movement." + confidence_note(pitch_name),
            )
        if use_default and slot_num == 4:
            pitch_name = best_available(["curve", "screw", "drop curve", "change"])
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Middle of lineup default: avoid giving a clean first look." + confidence_note(pitch_name),
            )
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = best_available(["curve", "screw", "drop curve", "change"])
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Aggressive hitter: start with movement." + confidence_note(pitch_name),
            )
        pitch_name = best_available(["rise", "drop", "curve", "screw"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Default softball first pitch." + confidence_note(pitch_name),
        )

    if strikes == 2:
        if "Chases high fastball" in tendencies:
            pitch_name = best_available(["rise"])
            if pitch_name:
                return pitch_name, "up out of zone", "Two strikes: chase pitch up." + confidence_note(pitch_name)
        if "Chases splitter down" in tendencies:
            pitch_name = best_available(["drop", "drop curve", "change"])
            if pitch_name:
                return pitch_name, "down out of zone", "Two strikes: chase pitch down." + confidence_note(pitch_name)
        if "Chases sweeper away" in tendencies or "Chases slider away" in tendencies:
            pitch_name = best_available(["curve", "drop curve", "screw"])
            if pitch_name:
                return (
                    pitch_name,
                    softball_location_for_pitch(pitch_name, handedness),
                    "Two strikes: move off barrel." + confidence_note(pitch_name),
                )
        pitch_name = best_available(["drop curve", "drop", "curve", "screw", "change", "rise"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Two-strike softball chase pitch." + confidence_note(pitch_name),
        )

    if balls > strikes:
        pitch_name = best_available(["drop", "curve", "screw", "rise"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Hitter count: safe movement strike." + confidence_note(pitch_name),
        )

    last = history[-1].lower() if history else ""

    if "rise" in last:
        pitch_name = best_available(["drop", "drop curve", "change"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Pair rise with drop/change." + confidence_note(pitch_name),
        )
    if "drop" in last and "drop curve" not in last:
        pitch_name = best_available(["rise", "screw", "curve"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Different look after drop." + confidence_note(pitch_name),
        )
    if "curve" in last and "drop curve" not in last:
        pitch_name = best_available(["screw", "rise", "change"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Opposite movement after curve." + confidence_note(pitch_name),
        )
    if "screw" in last:
        pitch_name = best_available(["curve", "rise", "drop"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Opposite movement after screw." + confidence_note(pitch_name),
        )
    if "change" in last:
        pitch_name = best_available(["rise", "drop", "curve"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Speed change into movement." + confidence_note(pitch_name),
        )
    if "drop curve" in last:
        pitch_name = best_available(["rise", "screw", "change"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "New lane after drop curve." + confidence_note(pitch_name),
        )

    pitch_name = best_available(["rise", "drop", "curve", "screw", "change"])
    return (
        pitch_name,
        softball_location_for_pitch(pitch_name, handedness),
        "Default softball sequence." + confidence_note(pitch_name),
    )


def recommend_pitch(batter, balls, strikes, history):
    if st.session_state.sport == "Baseball":
        return baseball_recommend_pitch(batter, balls, strikes, history)
    return softball_recommend_pitch(batter, balls, strikes, history)
