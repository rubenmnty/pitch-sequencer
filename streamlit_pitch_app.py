import streamlit as st
import app_data as data

TENDENCY_OPTIONS = data.TENDENCY_OPTIONS
POSITIONS_IN_PLAY = data.POSITIONS_IN_PLAY
CONTACT_TYPES = data.CONTACT_TYPES
PLAY_RESULTS = data.PLAY_RESULTS
BASEBALL_PITCHES = data.BASEBALL_PITCHES
SOFTBALL_PITCHES = data.SOFTBALL_PITCHES
DEFAULT_SESSION_STATE = data.DEFAULT_SESSION_STATE

CONTACT_QUALITY_OPTIONS = getattr(
    data, "CONTACT_QUALITY_OPTIONS", ["Weak", "Medium", "Hard-hit"]
)
BALL_QUALITY_OPTIONS = getattr(
    data, "BALL_QUALITY_OPTIONS", ["Competitive", "Uncompetitive"]
)

from app_helpers import (
    initialize_session_state,
    reset_at_bat,
    next_batter,
    current_batter,
    get_default_profile,
    record_pitch_line,
    end_at_bat,
)
from pitch_logic import recommend_pitch

st.set_page_config(page_title="Pitch Sequencer", layout="centered")

initialize_session_state(DEFAULT_SESSION_STATE)


def confidence_to_score(label):
    mapping = {1: 20, 2: 40, 3: 60, 4: 80, 5: 95}
    return mapping.get(label, 60)


def update_pitch_confidence(pitch_name, delta):
    if pitch_name not in st.session_state.pitch_profiles:
        return
    current = st.session_state.pitch_profiles[pitch_name]["confidence_score"]
    new_score = max(0, min(100, current + delta))
    st.session_state.pitch_profiles[pitch_name]["confidence_score"] = new_score


def add_out_local():
    st.session_state.outs += 1
    if st.session_state.outs >= 3:
        st.session_state.outs = 0
        st.session_state.inning += 1


def auto_check_count_end_local():
    if st.session_state.balls >= 4:
        end_at_bat("Walk")
        return True
    if st.session_state.strikes >= 3:
        add_out_local()
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

    available_pitches = (
        BASEBALL_PITCHES if st.session_state.sport == "Baseball" else SOFTBALL_PITCHES
    )

    pitcher_pitches = st.multiselect(
        "Select the pitches this pitcher throws",
        available_pitches,
        default=st.session_state.pitcher_pitches,
    )

    st.write("Pick the pitches, then rank them and set confidence.")

    pitch_profiles = {}
    if pitcher_pitches:
        st.markdown("### Pitch Order and Confidence")
        st.write("Rank 1 = primary pitch. Confidence 1–5 = how good it feels today.")

        used_ranks = []
        for pitch in pitcher_pitches:
            col1, col2 = st.columns(2)
            with col1:
                rank = st.selectbox(
                    f"{pitch} rank",
                    options=list(range(1, len(pitcher_pitches) + 1)),
                    key=f"rank_{pitch}",
                )
            with col2:
                confidence_label = st.selectbox(
                    f"{pitch} confidence",
                    options=[1, 2, 3, 4, 5],
                    index=2,
                    key=f"conf_{pitch}",
                )
            used_ranks.append(rank)
            pitch_profiles[pitch] = {
                "rank": rank,
                "confidence_label": confidence_label,
                "confidence_score": confidence_to_score(confidence_label),
            }

        if len(set(used_ranks)) != len(used_ranks):
            st.warning("Each pitch should have a different rank.")

    if st.button("Continue to Lineup", use_container_width=True):
        if not pitcher_pitches:
            st.error("Select at least one pitch.")
        elif len(set([pitch_profiles[p]["rank"] for p in pitcher_pitches])) != len(pitcher_pitches):
            st.error("Each selected pitch needs its own unique rank.")
        else:
            st.session_state.pitcher_name = pitcher_name.strip() or "Pitcher"
            st.session_state.pitcher_hand = pitcher_hand
            st.session_state.pitcher_pitches = pitcher_pitches
            st.session_state.pitch_profiles = pitch_profiles
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
                default=st.session_state.get(
                    f"tendencies_{slot_num}",
                    get_default_profile(slot_num),
                ),
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
        st.session_state.outs = 0
        st.session_state.inning = 1
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
        lineup_size = len(st.session_state.lineup)
        batter_number = st.session_state.current_batter_index + 1

        st.title("At-Bat")
        st.write(
            f"{st.session_state.sport} | Pitcher: {st.session_state.pitcher_name} "
            f"({st.session_state.pitcher_hand})"
        )
        st.write(f"Pitch Mix: {', '.join(st.session_state.pitcher_pitches)}")

        with st.expander("Pitch Confidence"):
            for pitch_name in sorted(
                st.session_state.pitch_profiles.keys(),
                key=lambda p: st.session_state.pitch_profiles[p]["rank"]
            ):
                profile = st.session_state.pitch_profiles[pitch_name]
                st.write(
                    f"{profile['rank']}. {pitch_name} | "
                    f"Pregame {profile['confidence_label']}/5 | "
                    f"Live {profile['confidence_score']}"
                )

        info1, info2, info3 = st.columns(3)
        with info1:
            st.metric("Inning", st.session_state.inning)
        with info2:
            st.metric("Outs", st.session_state.outs)
        with info3:
            st.metric("Batter", f"{batter_number} of {lineup_size}")

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
                st.session_state.pending_result = "Ball"
                st.session_state.stage = "ball_quality"
                st.rerun()

            if c2.button("Called Strike", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                st.session_state.strikes += 1
                record_pitch_line(pitch, location, "Called Strike")
                update_pitch_confidence(pitch, 4)
                auto_check_count_end_local()
                st.rerun()

            c3, c4 = st.columns(2)
            if c3.button("Swing Miss", use_container_width=True):
                pitch = st.session_state.pending_pitch["pitch"]
                location = st.session_state.pending_pitch["location"]
                st.session_state.strikes += 1
                record_pitch_line(pitch, location, "Swing Miss")
                update_pitch_confidence(pitch, 8)
                if auto_check_count_end_local():
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
                update_pitch_confidence(pitch, 1)
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
                update_pitch_confidence(pitch, -6)
                end_at_bat("Hit By Pitch")
                st.rerun()

        elif st.session_state.stage == "ball_quality":
            st.markdown("## Ball Quality")
            pitch = st.session_state.pending_pitch["pitch"]

            ball_quality = st.radio(
                "Was it competitive?",
                BALL_QUALITY_OPTIONS,
                horizontal=True,
            )

            if st.button("Submit Ball Quality", use_container_width=True):
                if ball_quality == "Competitive":
                    update_pitch_confidence(pitch, -2)
                    st.session_state.ab_history.append("Ball | Competitive")
                else:
                    update_pitch_confidence(pitch, -8)
                    st.session_state.ab_history.append("Ball | Uncompetitive")
                st.session_state.pending_result = None
                st.session_state.stage = "result"
                auto_check_count_end_local()
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
            contact_quality = st.selectbox("Contact Quality", CONTACT_QUALITY_OPTIONS)

            if st.button("Submit Play", use_container_width=True):
                play_text = f"{contact_type} to {direction} | {play_result} | {contact_quality}"
                st.session_state.ab_history.append(play_text)

                pitch = st.session_state.pending_pitch["pitch"]
                if contact_quality == "Weak":
                    update_pitch_confidence(pitch, 5)
                elif contact_quality == "Medium":
                    update_pitch_confidence(pitch, 0)
                else:
                    update_pitch_confidence(pitch, -10)

                if play_result == "Out":
                    add_out_local()
                end_at_bat(play_text)
                st.rerun()

        elif st.session_state.stage == "at_bat_end":
            st.success(f"At-Bat Over: {st.session_state.last_outcome_text}")
            st.write(f"Inning: {st.session_state.inning}")
            st.write(f"Outs: {st.session_state.outs}")
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
