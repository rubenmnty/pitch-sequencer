import streamlit as st


def initialize_session_state(defaults: dict):
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
        return [
            "Default to lineup spot",
            "Aggressive first pitch",
            "Fastball hunter",
            "Power hitter",
        ]
    if slot_num == 5:
        return ["Default to lineup spot", "Aggressive first pitch", "Power hitter"]
    if slot_num in [6, 7]:
        return ["Default to lineup spot"]
    return ["Default to lineup spot"]


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
