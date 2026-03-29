import streamlit as st

st.set_page_config(page_title="Pitch Sequencer", layout="centered")

st.title("⚾ Pitch Sequencer")

if "balls" not in st.session_state:
    st.session_state.balls = 0
if "strikes" not in st.session_state:
    st.session_state.strikes = 0

balls = st.session_state.balls
strikes = st.session_state.strikes

st.subheader(f"Count: {balls}-{strikes}")

def recommend_pitch(balls, strikes):
    if strikes == 2:
        return "slider", "down away off plate", "2 strikes: chase pitch"
    if balls > strikes:
        return "cutter", "middle in", "hitter count: safe strike"
    return "4-seam", "up away", "default attack"

pitch, location, reason = recommend_pitch(balls, strikes)

st.markdown("### 🎯 Recommended Pitch")
st.write(f"**Pitch:** {pitch}")
st.write(f"**Location:** {location}")
st.write(f"**Why:** {reason}")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Ball"):
        st.session_state.balls += 1

with col2:
    if st.button("Strike"):
        if st.session_state.strikes < 2:
            st.session_state.strikes += 1

with col3:
    if st.button("Reset"):
        st.session_state.balls = 0
        st.session_state.strikes = 0
