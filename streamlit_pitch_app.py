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

# -------------------------
# SESSION STATE
# -------------------------
defaults = {
    "page": "welcome",
    "lineup_count": 9,
    "lineup": [],
    "current_batter_index": 0,
    "balls": 0,
    "strikes": 0,
    "ab_history": [],
    "game_log": [],
    "stage": "result",          # result, swing_details, in_play, at_bat_end
    "pending_result": None,     # swing_miss, swing_foul, in_play
    "pending_pitch": None,      # dict with pitch/location/reason
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


def recommend_pitch(batter, balls, strikes, history):
    handedness = batter["hand"]
    tendencies = batter["tendencies"]
    slot_num = batter["slot_num"]

    # default profile effect
    use_default = "Default to lineup spot" in tendencies

    # very simple first-pitch logic
    if balls == 0 and strikes == 0 and len(history) == 0:
        if use_default and slot_num == 1:
            return "cutter", "middle in", "Top of lineup default: steal strike one with a firmer safe pitch."
        if use_default and slot_num == 4:
            if handedness == "R":
                return "slider", "down away", "Cleanup default: avoid giving a righty fastball hunter a clean first heater."
            return "sweeper", "down away", "Cleanup default: avoid giving a lefty fastball hunter a clean first heater."
        if "Aggressive first pitch" in tendencies and "Fastball hunter" in tendencies:
            if handedness == "R":
                return "slider", "down away", "Aggressive fastball hunter: start with spin away."
            return "sweeper", "down away", "Aggressive fastball hunter: start with sweep away."
        return "4-seam", "up away" if handedness == "R" else "up in", "Default attack."

    # two-strike logic
    if strikes == 2:
        if "Chases high fastball" in tendencies:
            return "4-seam", "up out of zone", "Two strikes: hitter tends to chase high fastball."
        if "Chases splitter down" in tendencies:
            return "splitter", "down out of zone", "Two strikes: hitter tends to chase down."
        if "Chases sweeper away" in tendencies:
            return "sweeper", "away off plate", "Two strikes: hitter tends to chase sweep away."
        return "slider", "down away off plate", "Two strikes: default chase pitch."

    # hitter count
    if balls > strikes:
        return "cutter", "middle in" if handedness == "R" else "middle away", "Hitter count: safe competitive strike."

    # neutral / pitcher count
    last = history[-1] if history else ""
    if "4-seam" in last and "up" in last:
        return "splitter", "down out of zone", "Tunnel off previous elevated fastball."
    if "slider" in last or "sweeper" in last:
        return "running fastball", "up in" if handedness == "R" else "up away", "Change lane after breaking ball."
    return "4-seam", "up away" if handedness == "R" else "up in", "Default attack."


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
    st.title("⚾ Pitch Sequencer")
    st.write("Build your lineup, set tendencies, and sequence pitches one batter at a time.")
    if st.button("Enter Lineup", use_container_width=True):
        st.session_state.page = "lineup"
        st.rerun()


# -------------------------
# LINEUP BUILDER
# -------------------------
elif st.session_state.page == "lineup":
    st.title("Enter Lineup")

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
        st.subheader(f"{batter['name']}")
        st.write(f"Handedness: {batter['hand']}")
        st.write(f"Count: {st.session_state.balls}-{st.session_state.strikes}")

        # show call unless at-bat just ended
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

        # -------- Result stage --------
        if st.session_state.stage == "result":
            st.markdown("### Result")

            c1, c2 = st.columns(2)
            if c1.button("Ball", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                st.session_state.balls += 1
                record_pitch_line(pitch, location, "Ball")
                if not auto_check_count_end():
                    st.rerun()
                st.rerun()

            if c2.button("Called Strike", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                st.session_state.strikes += 1
                record_pitch_line(pitch, location, "Called Strike")
                if not auto_check_count_end():
                    st.rerun()
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

        # -------- Swing details stage --------
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

        # -------- In play stage --------
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

        # -------- At-bat end stage --------
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
