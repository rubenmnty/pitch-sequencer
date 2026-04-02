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
