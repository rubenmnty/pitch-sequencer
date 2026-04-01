import streamlit as st

from pitch_history import last_location_for_pitch


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
            ["up away", "middle away", "top of zone", "up in"]
            if batter_hand == "R"
            else ["up in", "middle in", "top of zone", "up away"]
        )
    if pitch_name == "2-seam":
        return (
            ["middle in", "low in", "middle away", "low away"]
            if batter_hand == "R"
            else ["middle away", "low away", "middle in", "low in"]
        )
    if pitch_name == "changeup":
        return (
            ["low away", "bottom of zone", "low in"]
            if batter_hand == "R"
            else ["low in", "bottom of zone", "low away"]
        )
    if pitch_name == "curveball":
        return (
            ["down away", "bottom of zone", "down in"]
            if batter_hand == "R"
            else ["down in", "bottom of zone", "down away"]
        )
    if pitch_name == "cutter":
        return (
            ["middle in", "middle away", "low away", "up in"]
            if batter_hand == "R"
            else ["middle away", "middle in", "low in", "up away"]
        )
    if pitch_name == "splitter":
        return ["down out of zone", "bottom of zone", "low away", "low in"]
    if pitch_name == "slider":
        return (
            ["down away off plate", "back foot", "front door", "edge away"]
            if batter_hand == "R"
            else ["down in off plate", "back foot", "front door", "edge in"]
        )
    if pitch_name == "sweeper":
        return (
            ["away off plate", "edge away", "back door", "middle away"]
            if batter_hand == "R"
            else ["in off plate", "edge in", "back door", "middle in"]
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


def next_location_for_pitch(
    pitch_name: str, batter_hand: str, history, competitive_mode=False
):
    if st.session_state.sport == "Baseball":
        options = baseball_alternate_locations(pitch_name, batter_hand)
    else:
        options = softball_alternate_locations(pitch_name, batter_hand)

    last_loc = last_location_for_pitch(pitch_name, history)

    if competitive_mode and len(options) > 1:
        for loc in options[1:]:
            if loc.strip().lower() != (last_loc or ""):
                return loc

    for loc in options:
        if loc.strip().lower() != (last_loc or ""):
            return loc

    return options[0]
