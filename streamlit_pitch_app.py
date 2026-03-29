import streamlit as st

st.set_page_config(page_title="Pitch Sequencer", layout="centered")

# -------------------------
# SESSION STATE SETUP
# -------------------------
if "page" not in st.session_state:
    st.session_state.page = "welcome"

if "lineup" not in st.session_state:
    st.session_state.lineup = []

if "current_batter" not in st.session_state:
    st.session_state.current_batter = 0

if "balls" not in st.session_state:
    st.session_state.balls = 0

if "strikes" not in st.session_state:
    st.session_state.strikes = 0

if "history" not in st.session_state:
    st.session_state.history = []

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# -------------------------
# BASIC PITCH LOGIC (we'll expand later)
# -------------------------
def recommend_pitch(balls, strikes):
    if strikes == 2:
        return "slider", "down away off plate", "Put-away pitch"
    if balls > strikes:
        return "cutter", "middle in", "Hitter count safe strike"
    return "4-seam", "up away", "Default attack"


# -------------------------
# WELCOME PAGE
# -------------------------
if st.session_state.page == "welcome":
    st.title("⚾ Pitch Sequencer")

    if st.button("Enter Lineup"):
        st.session_state.page = "lineup"


# -------------------------
# LINEUP PAGE
# -------------------------
elif st.session_state.page == "lineup":
    st.title("Lineup Builder")

    num_players = st.number_input("Number of players (9–11)", 9, 11, 9)

    lineup = []

    for i in range(num_players):
        st.subheader(f"Batter {i+1}")
        name = st.text_input(f"Name {i+1}", key=f"name{i}")
        hand = st.selectbox(f"Handedness {i+1}", ["R", "L"], key=f"hand{i}")

        lineup.append({
            "name": name if name else f"Batter {i+1}",
            "hand": hand
        })

    if st.button("Start Pitch Sequencer"):
        st.session_state.lineup = lineup
        st.session_state.page = "game"


# -------------------------
# GAME PAGE
# -------------------------
elif st.session_state.page == "game":

    lineup = st.session_state.lineup
    batter = lineup[st.session_state.current_batter]

    st.title("Pitch Sequencer")

    st.subheader(f"Batter: {batter['name']} ({batter['hand']})")
    st.write(f"Count: {st.session_state.balls}-{st.session_state.strikes}")

    pitch, loc, reason = recommend_pitch(st.session_state.balls, st.session_state.strikes)

    st.markdown("### 🎯 Pitch Call")
    st.write(f"**Pitch:** {pitch}")
    st.write(f"**Location:** {loc}")
    st.write(f"**Why:** {reason}")

    st.markdown("### Result")

    col1, col2 = st.columns(2)

    if col1.button("Ball"):
        st.session_state.balls += 1
        st.session_state.history.append(f"{pitch} - ball")

    if col2.button("Called Strike"):
        if st.session_state.strikes < 2:
            st.session_state.strikes += 1
        st.session_state.history.append(f"{pitch} - called strike")

    col3, col4, col5 = st.columns(3)

    if col3.button("Swing Miss"):
        if st.session_state.strikes < 2:
            st.session_state.strikes += 1
        st.session_state.last_result = "swing"

    if col4.button("Swing Foul"):
        if st.session_state.strikes < 2:
            st.session_state.strikes += 1
        st.session_state.last_result = "swing"

    if col5.button("Swing In Play"):
        st.session_state.last_result = "inplay"

    st.markdown("### Other")

    if st.button("Walk"):
        st.session_state.current_batter += 1
        st.session_state.balls = 0
        st.session_state.strikes = 0
        st.session_state.history = []

    if st.button("Strikeout"):
        st.session_state.current_batter += 1
        st.session_state.balls = 0
        st.session_state.strikes = 0
        st.session_state.history = []

    if st.button("HBP"):
        st.session_state.current_batter += 1
        st.session_state.balls = 0
        st.session_state.strikes = 0
        st.session_state.history = []

    # -------------------------
    # SWING FEEDBACK
    # -------------------------
    if st.session_state.last_result == "swing":
        st.markdown("### Timing")
        timing = st.radio("Timing", ["Early", "Late", "On Time"])

        st.markdown("### Plane")
        plane = st.radio("Plane", ["Above", "Below", "On Plane"])

        if st.button("Submit Swing Feedback"):
            st.session_state.history.append(f"{pitch} - {timing} / {plane}")
            st.session_state.last_result = None

    # -------------------------
    # IN PLAY
    # -------------------------
    if st.session_state.last_result == "inplay":
        st.markdown("### Contact")

        contact = st.selectbox("Type", ["Ground ball", "Line drive", "Fly ball", "Pop up"])
        direction = st.selectbox("Direction", ["P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"])
        result = st.selectbox("Result", ["Out", "Single", "Double", "Triple", "Home run"])

        if st.button("Submit Play"):
            st.session_state.history.append(f"{contact} to {direction} - {result}")
            st.session_state.current_batter += 1
            st.session_state.balls = 0
            st.session_state.strikes = 0
            st.session_state.history = []
            st.session_state.last_result = None

    # -------------------------
    # SUMMARY
    # -------------------------
    st.markdown("### At-Bat Summary")
    for item in st.session_state.history:
        st.write(item)
