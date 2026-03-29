import streamlit as st


def pitch_available(name: str) -> bool:
    return name in st.session_state.pitcher_pitches


def first_available(candidates):
    for pitch_name in candidates:
        if pitch_available(pitch_name):
            return pitch_name
    if st.session_state.pitcher_pitches:
        return st.session_state.pitcher_pitches[0]
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


def baseball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies

    if balls == 0 and strikes == 0 and len(history) == 0:
        if use_default and slot_num == 1:
            pitch_name = first_available(["cutter", "2-seam", "4-seam"])
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Top of lineup default: get ahead with a safe strike.",
            )
        if use_default and slot_num == 4:
            if "Fastball hunter" in tendencies:
                pitch_name = first_available(
                    ["slider", "sweeper", "curveball", "changeup"]
                )
                return (
                    pitch_name,
                    baseball_location_for_pitch(pitch_name, handedness),
                    "Cleanup hitter: do not give a clean first fastball.",
                )
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = first_available(["slider", "sweeper", "curveball"])
            return (
                pitch_name,
                baseball_location_for_pitch(pitch_name, handedness),
                "Aggressive fastball hunter: start with spin.",
            )
        pitch_name = first_available(["4-seam", "2-seam", "cutter"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Default baseball first pitch.",
        )

    if strikes == 2:
        if "Chases high fastball" in tendencies:
            pitch_name = first_available(["4-seam"])
            if pitch_name:
                return pitch_name, "up out of zone", "Two strikes: hitter chases up."
        if "Chases splitter down" in tendencies:
            pitch_name = first_available(["splitter", "changeup", "curveball"])
            if pitch_name:
                return pitch_name, "down out of zone", "Two strikes: hitter chases down."
        if "Chases sweeper away" in tendencies:
            pitch_name = first_available(["sweeper", "slider"])
            if pitch_name:
                return (
                    pitch_name,
                    baseball_location_for_pitch(pitch_name, handedness),
                    "Two strikes: hitter chases away.",
                )
        pitch_name = first_available(
            ["slider", "sweeper", "splitter", "curveball", "changeup"]
        )
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Two-strike chase pitch.",
        )

    if balls > strikes:
        pitch_name = first_available(["cutter", "2-seam", "4-seam"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Hitter count: safer competitive strike.",
        )

    last = history[-1].lower() if history else ""

    if "4-seam" in last and "up" in last:
        pitch_name = first_available(["splitter", "changeup", "curveball"])
        return (
            pitch_name,
            "down out of zone"
            if pitch_name in ["splitter", "changeup"]
            else baseball_location_for_pitch(pitch_name, handedness),
            "Tunnel off elevated fastball.",
        )
    if "2-seam" in last or "cutter" in last:
        pitch_name = first_available(["slider", "sweeper", "curveball", "splitter"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Move off previous hard pitch.",
        )
    if "slider" in last or "sweeper" in last:
        pitch_name = first_available(["4-seam", "2-seam", "cutter"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Change lane after breaking ball.",
        )
    if "splitter" in last or "changeup" in last:
        pitch_name = first_available(["4-seam", "cutter"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Climb after soft/down pitch.",
        )
    if "curveball" in last:
        pitch_name = first_available(["4-seam", "cutter", "changeup"])
        return (
            pitch_name,
            baseball_location_for_pitch(pitch_name, handedness),
            "Different speed/shape after curve.",
        )

    pitch_name = first_available(["4-seam", "2-seam", "cutter"])
    return (
        pitch_name,
        baseball_location_for_pitch(pitch_name, handedness),
        "Default baseball sequence.",
    )


def softball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies

    if balls == 0 and strikes == 0 and len(history) == 0:
        if use_default and slot_num == 1:
            pitch_name = first_available(["curve", "screw", "drop"])
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Top of lineup default: steal a strike with movement.",
            )
        if use_default and slot_num == 4:
            pitch_name = first_available(["curve", "screw", "drop curve", "change"])
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Middle of lineup default: avoid giving a clean first look.",
            )
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = first_available(["curve", "screw", "drop curve", "change"])
            return (
                pitch_name,
                softball_location_for_pitch(pitch_name, handedness),
                "Aggressive hitter: start with movement.",
            )
        pitch_name = first_available(["rise", "drop", "curve", "screw"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Default softball first pitch.",
        )

    if strikes == 2:
        if "Chases high fastball" in tendencies:
            pitch_name = first_available(["rise"])
            if pitch_name:
                return pitch_name, "up out of zone", "Two strikes: chase pitch up."
        if "Chases splitter down" in tendencies:
            pitch_name = first_available(["drop", "drop curve", "change"])
            if pitch_name:
                return pitch_name, "down out of zone", "Two strikes: chase pitch down."
        if "Chases sweeper away" in tendencies or "Chases slider away" in tendencies:
            pitch_name = first_available(["curve", "drop curve", "screw"])
            if pitch_name:
                return (
                    pitch_name,
                    softball_location_for_pitch(pitch_name, handedness),
                    "Two strikes: move off barrel.",
                )
        pitch_name = first_available(
            ["drop curve", "drop", "curve", "screw", "change", "rise"]
        )
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Two-strike softball chase pitch.",
        )

    if balls > strikes:
        pitch_name = first_available(["drop", "curve", "screw", "rise"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Hitter count: safe movement strike.",
        )

    last = history[-1].lower() if history else ""

    if "rise" in last:
        pitch_name = first_available(["drop", "drop curve", "change"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Pair rise with drop/change.",
        )
    if "drop" in last and "drop curve" not in last:
        pitch_name = first_available(["rise", "screw", "curve"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Different look after drop.",
        )
    if "curve" in last and "drop curve" not in last:
        pitch_name = first_available(["screw", "rise", "change"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Opposite movement after curve.",
        )
    if "screw" in last:
        pitch_name = first_available(["curve", "rise", "drop"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Opposite movement after screw.",
        )
    if "change" in last:
        pitch_name = first_available(["rise", "drop", "curve"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "Speed change into movement.",
        )
    if "drop curve" in last:
        pitch_name = first_available(["rise", "screw", "change"])
        return (
            pitch_name,
            softball_location_for_pitch(pitch_name, handedness),
            "New lane after drop curve.",
        )

    pitch_name = first_available(["rise", "drop", "curve", "screw", "change"])
    return (
        pitch_name,
        softball_location_for_pitch(pitch_name, handedness),
        "Default softball sequence.",
    )


def recommend_pitch(batter, balls, strikes, history):
    if st.session_state.sport == "Baseball":
        return baseball_recommend_pitch(batter, balls, strikes, history)
    return softball_recommend_pitch(batter, balls, strikes, history)
