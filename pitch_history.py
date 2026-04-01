def is_actual_pitch_event(item: str) -> bool:
    if item.startswith("Ball Quality |"):
        return False
    parts = [p.strip() for p in item.split("|")]
    return len(parts) >= 3


def get_recent_pitch_events(history):
    events = []
    for item in history:
        if not is_actual_pitch_event(item):
            continue
        parts = [p.strip() for p in item.split("|")]
        pitch = parts[0]
        location = parts[1]
        outcome = parts[2]
        events.append(
            {
                "pitch": pitch,
                "location": location,
                "outcome": outcome,
                "raw": item,
            }
        )
    return events


def last_pitch_event(history):
    events = get_recent_pitch_events(history)
    if not events:
        return None
    return events[-1]


def get_last_ball_quality(history):
    for item in reversed(history):
        if item == "Ball Quality | Competitive":
            return "Competitive"
        if item == "Ball Quality | Uncompetitive":
            return "Uncompetitive"
        if is_actual_pitch_event(item):
            break
    return None


def consecutive_balls_for_pitch(pitch_name: str, history) -> int:
    events = get_recent_pitch_events(history)
    count = 0

    for event in reversed(events):
        current_pitch = event["pitch"].strip().lower()
        outcome = event["outcome"].strip().lower()

        if current_pitch != pitch_name.strip().lower():
            break

        if outcome == "ball":
            count += 1
        else:
            break

    return count


def consecutive_usage_for_pitch(pitch_name: str, history) -> int:
    events = get_recent_pitch_events(history)
    count = 0

    for event in reversed(events):
        current_pitch = event["pitch"].strip().lower()
        if current_pitch == pitch_name.strip().lower():
            count += 1
        else:
            break

    return count


def recent_usage_count(pitch_name: str, history, window: int = 5) -> int:
    events = get_recent_pitch_events(history)
    recent = events[-window:]
    return sum(
        1 for e in recent if e["pitch"].strip().lower() == pitch_name.strip().lower()
    )


def recent_hard_pitch_count(history, window: int = 5) -> int:
    hard_pitches = {"4-seam", "2-seam", "cutter"}
    events = get_recent_pitch_events(history)
    recent = events[-window:]
    return sum(1 for e in recent if e["pitch"].strip().lower() in hard_pitches)


def last_location_for_pitch(pitch_name: str, history):
    events = get_recent_pitch_events(history)
    for event in reversed(events):
        if event["pitch"].strip().lower() == pitch_name.strip().lower():
            return event["location"].strip().lower()
    return None
