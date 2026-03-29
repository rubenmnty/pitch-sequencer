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

DEFAULT_SESSION_STATE = {
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
