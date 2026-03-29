import streamlit as st

st.set_page_config(page_title="Pitch Sequencer", layout="centered")

# -------------------------
# DATA
# -------------------------
TENDENCY_OPTIONS = [
    "Default to lineup spot",
    "Takes first pitch",
    "Aggressive first pitch",
    "Fastball hunter",
    "Offspeed hunter",
    "Chases high fastball",
    "Chases sweeper away",
    "Chases slider away",
    "Chases splitter down",
    "Struggles inside",
    "Struggles away",
    "Handles inside",
    "Handles away",
    "Late on velocity",
    "Out front on offspeed",
    "Tough two strikes",
    "Expands with two strikes",
    "Contact hitter",
    "Power hitter",
    "Pull hitter",
    "Opposite field hitter",
    "Ground ball hitter",
    "Fly ball hitter",
]

POSITIONS_IN_PLAY = ["P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"]
CONTACT_TYPES = ["Ground ball", "Line drive", "Fly ball", "Pop up"]
PLAY_RESULTS = [
    "Out",
    "Single",
    "Double",
    "Triple",
    "Home run",
    "Reached on error",
    "Fielder's choice",
]

BASEBALL_PITCHES = [
    "4-seam",
    "2-seam",
    "changeup",
    "curveball",
    "cutter",
    "splitter",
    "sweeper",
    "slider",
]

SOFTBALL_PITCHES = [
    "rise",
    "drop",
    "curve",
    "screw",
    "change",
    "drop curve",
]

# -------------------------
# SESSION STATE
# -------------------------
defaults = {
    "page": "welcome",
    "sport": None,
    "pitcher_name": "",
    "pitcher_hand": "R",
    "pitcher_pitches": [],
    "lineup_count": 9,
    "lineup": [],
    "current_batter_index": 0,
    "balls": 0,
    "strikes": 0,
    "ab_history": [],
    "game_log": [],
    "stage": "result",          # result, swing_details, in_play, at_bat_end
    "pending_result": None,
    "pending_pitch": None,
    "last_outcome_text": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# -------------------------
# HELPERS
# -------------------------
def reset_at_bat():
    st.session_state.balls = 0
    st.session_state.strikes = 0
    st.session_state.ab_history = []
    st.session_state.stage = "result"
    st.session_state.pending_result = None
    st.session_state.pending_pitch = None
    st.session_state.last_outcome_text = ""


def next_batter():
    if st.session_state.lineup:
        st.session_state.current_batter_index = (
            st.session_state.current_batter_index + 1
        ) % len(st.session_state.lineup)
    reset_at_bat()


def current_batter():
    if not st.session_state.lineup:
        return None
    return st.session_state.lineup[st.session_state.current_batter_index]


def get_default_profile(slot_num: int):
    if slot_num == 1:
        return ["Default to lineup spot", "Takes first pitch"]
    if slot_num == 2:
        return ["Default to lineup spot"]
    if slot_num == 3:
        return ["Default to lineup spot"]
    if slot_num == 4:
        return ["Default to lineup spot", "Aggressive first pitch", "Fastball hunter", "Power hitter"]
    if slot_num == 5:
        return ["Default to lineup spot", "Aggressive first pitch", "Power hitter"]
    if slot_num in [6, 7]:
        return ["Default to lineup spot"]
    return ["Default to lineup spot"]


def pitch_available(name: str) -> bool:
    return name in st.session_state.pitcher_pitches


def first_available(candidates):
    for p in candidates:
        if pitch_available(p):
            return p
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

    # 0-0 first pitch
    if balls == 0 and strikes == 0 and len(history) == 0:
        if use_default and slot_num == 1:
            pitch_name = first_available(["cutter", "2-seam", "4-seam"])
            return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Top of lineup default: get ahead with a safe strike."
        if use_default and slot_num == 4:
            if "Fastball hunter" in tendencies:
                pitch_name = first_available(["slider", "sweeper", "curveball", "changeup"])
                return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Cleanup hitter: do not give a clean first fastball."
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = first_available(["slider", "sweeper", "curveball"])
            return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Aggressive fastball hunter: start with spin."
        pitch_name = first_available(["4-seam", "2-seam", "cutter"])
        return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Default baseball first pitch."

    # 2 strikes
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
                return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Two strikes: hitter chases away."
        pitch_name = first_available(["slider", "sweeper", "splitter", "curveball", "changeup"])
        return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Two-strike chase pitch."

    # hitter count
    if balls > strikes:
        pitch_name = first_available(["cutter", "2-seam", "4-seam"])
        return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Hitter count: safer competitive strike."

    # sequence off last pitch
    last = history[-1].lower() if history else ""

    if "4-seam" in last and "up" in last:
        pitch_name = first_available(["splitter", "changeup", "curveball"])
        return pitch_name, "down out of zone" if pitch_name in ["splitter", "changeup"] else baseball_location_for_pitch(pitch_name, handedness), "Tunnel off elevated fastball."
    if "2-seam" in last or "cutter" in last:
        pitch_name = first_available(["slider", "sweeper", "curveball", "splitter"])
        return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Move off previous hard pitch."
    if "slider" in last or "sweeper" in last:
        pitch_name = first_available(["4-seam", "2-seam", "cutter"])
        return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Change lane after breaking ball."
    if "splitter" in last or "changeup" in last:
        pitch_name = first_available(["4-seam", "cutter"])
        return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Climb after soft/down pitch."
    if "curveball" in last:
        pitch_name = first_available(["4-seam", "cutter", "changeup"])
        return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Different speed/shape after curve."

    pitch_name = first_available(["4-seam", "2-seam", "cutter"])
    return pitch_name, baseball_location_for_pitch(pitch_name, handedness), "Default baseball sequence."


def softball_recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]
    use_default = "Default to lineup spot" in tendencies

    # 0-0 first pitch
    if balls == 0 and strikes == 0 and len(history) == 0:
        if use_default and slot_num == 1:
            pitch_name = first_available(["curve", "screw", "drop"])
            return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Top of lineup default: steal a strike with movement."
        if use_default and slot_num == 4:
            pitch_name = first_available(["curve", "screw", "drop curve", "change"])
            return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Middle of lineup default: avoid giving a clean first look."
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            pitch_name = first_available(["curve", "screw", "drop curve", "change"])
            return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Aggressive hitter: start with movement."
        pitch_name = first_available(["rise", "drop", "curve", "screw"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Default softball first pitch."

    # 2 strikes
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
                return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Two strikes: move off barrel."
        pitch_name = first_available(["drop curve", "drop", "curve", "screw", "change", "rise"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Two-strike softball chase pitch."

    # hitter count
    if balls > strikes:
        pitch_name = first_available(["drop", "curve", "screw", "rise"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Hitter count: safe movement strike."

    # sequence off last pitch
    last = history[-1].lower() if history else ""

    if "rise" in last:
        pitch_name = first_available(["drop", "drop curve", "change"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Pair rise with drop/change."
    if "drop" in last and "drop curve" not in last:
        pitch_name = first_available(["rise", "screw", "curve"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Different look after drop."
    if "curve" in last and "drop curve" not in last:
        pitch_name = first_available(["screw", "rise", "change"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Opposite movement after curve."
    if "screw" in last:
        pitch_name = first_available(["curve", "rise", "drop"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Opposite movement after screw."
    if "change" in last:
        pitch_name = first_available(["rise", "drop", "curve"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Speed change into movement."
    if "drop curve" in last:
        pitch_name = first_available(["rise", "screw", "change"])
        return pitch_name, softball_location_for_pitch(pitch_name, handedness), "New lane after drop curve."

    pitch_name = first_available(["rise", "drop", "curve", "screw", "change"])
    return pitch_name, softball_location_for_pitch(pitch_name, handedness), "Default softball sequence."


def recommend_pitch(batter, balls, strikes, history):
    if st.session_state.sport == "Baseball":
        return baseball_recommend_pitch(batter, balls, strikes, history)
    return softball_recommend_pitch(batter, balls, strikes, history)


def record_pitch_line(pitch, location, outcome):
    st.session_state.ab_history.append(f"{pitch} | {location} | {outcome}")


def end_at_bat(reason_text):
    batter = current_batter()
    if batter:
        st.session_state.game_log.append(
            f"{batter['name']} ({batter['hand']}) - {reason_text}"
        )
    st.session_state.last_outcome_text = reason_text
    st.session_state.stage = "at_bat_end"


def auto_check_count_end():
    if st.session_state.balls >= 4:
        end_at_bat("Walk")
        return True
    if st.session_state.strikes >= 3:
        end_at_bat("Strikeout")
        return True
    return False


# -------------------------
# WELCOME
# -------------------------
if st.session_state.page == "welcome":
    st.title("Pitch Sequencer")
    st.write("Choose a sport to start.")

    c1, c2 = st.columns(2)
    if c1.button("Softball", use_container_width=True):
        st.session_state.sport = "Softball"
        st.session_state.page = "pitcher_setup"
        st.rerun()

    if c2.button("Baseball", use_container_width=True):
        st.session_state.sport = "Baseball"
        st.session_state.page = "pitcher_setup"
        st.rerun()


# -------------------------
# PITCHER SETUP
# -------------------------
elif st.session_state.page == "pitcher_setup":
    st.title(f"{st.session_state.sport} Pitcher Setup")

    pitcher_name = st.text_input("Pitcher Name", value=st.session_state.pitcher_name)
    pitcher_hand = st.selectbox(
        "Pitcher Handedness",
        ["R", "L"],
        index=0 if st.session_state.pitcher_hand == "R" else 1,
    )

    available_pitches = BASEBALL_PITCHES if st.session_state.sport == "Baseball" else SOFTBALL_PITCHES

    pitcher_pitches = st.multiselect(
        "Select the pitches this pitcher throws",
        available_pitches,
        default=st.session_state.pitcher_pitches,
    )

    st.write("Pick at least 2 if possible so the sequencing has more to work with.")

    if st.button("Continue to Lineup", use_container_width=True):
        if not pitcher_pitches:
            st.error("Select at least one pitch.")
        else:
            st.session_state.pitcher_name = pitcher_name.strip() or "Pitcher"
            st.session_state.pitcher_hand = pitcher_hand
            st.session_state.pitcher_pitches = pitcher_pitches
            st.session_state.page = "lineup"
            st.rerun()


# -------------------------
# LINEUP BUILDER
# -------------------------
elif st.session_state.page == "lineup":
    st.title("Enter Lineup")
    st.write(f"Sport: {st.session_state.sport}")
    st.write(
        f"Pitcher: {st.session_state.pitcher_name} ({st.session_state.pitcher_hand}) | "
        f"Pitches: {', '.join(st.session_state.pitcher_pitches)}"
    )

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.write(f"Players: {st.session_state.lineup_count}")
    with col_b:
        if st.session_state.lineup_count < 10:
            if st.button("Add Slot 10", use_container_width=True):
                st.session_state.lineup_count = 10
                st.rerun()
    with col_c:
        if st.session_state.lineup_count < 11:
            if st.button("Add Slot 11", use_container_width=True):
                st.session_state.lineup_count = 11
                st.rerun()

    lineup = []
    for i in range(st.session_state.lineup_count):
        slot_num = i + 1
        with st.expander(f"Player {slot_num}", expanded=(slot_num <= 3)):
            name = st.text_input(
                f"Name {slot_num}",
                value=st.session_state.get(f"name_{slot_num}", f"Batter {slot_num}"),
                key=f"name_{slot_num}",
            )
            hand = st.selectbox(
                f"Handedness {slot_num}",
                ["R", "L"],
                index=0,
                key=f"hand_{slot_num}",
            )
            tendencies = st.multiselect(
                f"Tendencies {slot_num}",
                TENDENCY_OPTIONS,
                default=st.session_state.get(f"tendencies_{slot_num}", get_default_profile(slot_num)),
                key=f"tendencies_{slot_num}",
            )
            lineup.append(
                {
                    "slot_num": slot_num,
                    "name": name,
                    "hand": hand,
                    "tendencies": tendencies,
                }
            )

    if st.button("Start Pitch Sequencer", use_container_width=True):
        st.session_state.lineup = lineup
        st.session_state.current_batter_index = 0
        reset_at_bat()
        st.session_state.page = "game"
        st.rerun()


# -------------------------
# GAME
# -------------------------
elif st.session_state.page == "game":
    batter = current_batter()
    if batter is None:
        st.write("No lineup loaded.")
        if st.button("Back to Welcome"):
            st.session_state.page = "welcome"
            st.rerun()
    else:
        st.title("At-Bat")
        st.write(
            f"{st.session_state.sport} | Pitcher: {st.session_state.pitcher_name} "
            f"({st.session_state.pitcher_hand})"
        )
        st.write(f"Pitch Mix: {', '.join(st.session_state.pitcher_pitches)}")

        st.subheader(f"{batter['name']}")
        st.write(f"Handedness: {batter['hand']}")
        st.write(f"Count: {st.session_state.balls}-{st.session_state.strikes}")

        if st.session_state.stage != "at_bat_end":
            pitch, location, reason = recommend_pitch(
                batter,
                st.session_state.balls,
                st.session_state.strikes,
                st.session_state.ab_history,
            )
            st.session_state.pending_pitch = {
                "pitch": pitch,
                "location": location,
                "reason": reason,
            }

            st.markdown("### Pitch Call")
            st.write(f"**Pitch:** {pitch}")
            st.write(f"**Location:** {location}")
            st.write(f"**Why:** {reason}")

        if st.session_state.stage == "result":
            st.markdown("### Result")

            c1, c2 = st.columns(2)
            if c1.button("Ball", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                st.session_state.balls += 1
                record_pitch_line(pitch, location, "Ball")
                auto_check_count_end()
                st.rerun()

            if c2.button("Called Strike", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                st.session_state.strikes += 1
                record_pitch_line(pitch, location, "Called Strike")
                auto_check_count_end()
                st.rerun()

            c3, c4 = st.columns(2)
            if c3.button("Swing Miss", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                st.session_state.strikes += 1
                record_pitch_line(pitch, location, "Swing Miss")
                if auto_check_count_end():
                    st.rerun()
                st.session_state.pending_result = "Swing Miss"
                st.session_state.stage = "swing_details"
                st.rerun()

            if c4.button("Swing Foul", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                if st.session_state.strikes < 2:
                    st.session_state.strikes += 1
                record_pitch_line(pitch, location, "Swing Foul")
                st.session_state.pending_result = "Swing Foul"
                st.session_state.stage = "swing_details"
                st.rerun()

            c5, c6 = st.columns(2)
            if c5.button("Swing In Play", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                record_pitch_line(pitch, location, "In Play")
                st.session_state.pending_result = "In Play"
                st.session_state.stage = "in_play"
                st.rerun()

            if c6.button("HBP", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                record_pitch_line(pitch, location, "HBP")
                end_at_bat("Hit By Pitch")
                st.rerun()

        elif st.session_state.stage == "swing_details":
            st.markdown("## Swing Feedback")
            st.warning("Enter swing feedback before moving on.")

            timing = st.radio(
                "Timing",
                ["Early", "Late", "On Time"],
                horizontal=True,
                key="timing_radio",
            )
            plane = st.radio(
                "Plane",
                ["Above", "Below", "On Plane"],
                horizontal=True,
                key="plane_radio",
            )

            if st.button("Submit Swing Feedback", use_container_width=True):
                st.session_state.ab_history.append(
                    f"{st.session_state.pending_result} | {timing} | {plane}"
                )
                st.session_state.pending_result = None
                st.session_state.stage = "result"
                st.rerun()

        elif st.session_state.stage == "in_play":
            st.markdown("## Ball In Play")
            st.warning("Finish the play result to end the at-bat.")

            contact_type = st.selectbox("Contact Type", CONTACT_TYPES)
            direction = st.selectbox("Direction", POSITIONS_IN_PLAY)
            play_result = st.selectbox("Result", PLAY_RESULTS)

            if st.button("Submit Play", use_container_width=True):
                play_text = f"{contact_type} to {direction} | {play_result}"
                st.session_state.ab_history.append(play_text)
                end_at_bat(play_text)
                st.rerun()

        elif st.session_state.stage == "at_bat_end":
            st.success(f"At-Bat Over: {st.session_state.last_outcome_text}")
            if st.button("Next Batter", use_container_width=True):
                next_batter()
                st.rerun()

        st.markdown("### At-Bat Summary")
        if st.session_state.ab_history:
            for item in st.session_state.ab_history:
                st.write(f"- {item}")
        else:
            st.write("No pitches yet.")

        with st.expander("Game Log"):
            if st.session_state.game_log:
                for item in st.session_state.game_log:
                    st.write(f"- {item}")
            else:
                st.write("No completed at-bats yet.")
