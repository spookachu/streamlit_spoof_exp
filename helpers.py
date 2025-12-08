import streamlit as st
import re, os, datetime
try:
    from pylsl import StreamInfo, StreamOutlet, local_clock
except (RuntimeError, ImportError):
    print("Error. LSL not supported in cloud deployment.")

def datetime_converter(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def init_lsl():
    if "lsl_outlet" not in st.session_state:
        info = StreamInfo(
            name="StreamlitEvents",
            type="Markers",
            channel_count=1,
            nominal_srate=0,            
            channel_format="string",
            source_id="streamlit_ui_001"
        )
        st.session_state.lsl_outlet = StreamOutlet(info)

def htmlify(text):
    """
    Helper function for text displaying.
    """
    return text.strip().replace("\n", "<br>")

def parse_duration(raw):
    """
    Return correctly formatted duration from stimuli dataset.
    """
    if raw is None:
        return 0.0
    s = str(raw).strip().replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

def compute_answer_validity(trial_idx, required_wait):
    """
    Validates whether participant waited required time using:
    """
    start_ts_wall = st.session_state.get(f"trial_{trial_idx}_start_ts")

    action_log = st.session_state.action_log_by_trial.get(trial_idx, [])
    first_ts_wall = None

    for a in action_log:
        if a.get("action") in ["add_segment", "add_flag", "eval_response"]:
            if a.get("ts_wall") is not None:
                t = a["ts_wall"]
                if first_ts_wall is None or t < first_ts_wall:
                    first_ts_wall = t

    if start_ts_wall and first_ts_wall:
        waited = first_ts_wall - start_ts_wall
        return {
            "answer_validity": {
                "waited_seconds": waited,
                "required_wait": required_wait,
                "is_valid": waited >= required_wait,
                "source": "wall_clock"
            }
        }
    
    return {
        "answer_validity": {
            "waited_seconds": None,
            "required_wait": required_wait,
            "is_valid": False,
            "source": "none"
        }
    }

def parse_spoof_intervals(raw):
    """
    Parse spoofed segment timestamps.
    """
    if raw is None:
        return []
    s = str(raw).strip()
    if not s:
        return []
    pattern = r"([\d]+(?:\.[\d]+)?)\s*-\s*([\d]+(?:\.[\d]+)?)"
    matches = re.findall(pattern, s)
    intervals = []
    for a, b in matches:
        start = float(a)
        end = float(b)
        if end < start:
            start, end = end, start
        intervals.append((start, end))
    return intervals

def trial_is_correct(gt_type, gt_intervals, participant_segments, participant_flags):
    """
    Determines if a participant correctly marked a trial.
    """
    if participant_flags is None:
        participant_flags = []

    if gt_type.lower() == "bonafide":
        return len(participant_segments) == 0 and len(participant_flags) == 0

    if gt_type.lower() == "full_spoof":
        if not participant_segments and not participant_flags:
            return False
        for (gt_s, gt_e) in gt_intervals:
            segment_overlap = any(max(s, gt_s) < min(e, gt_e) for (s, e) in participant_segments)
            flag_inside = any(gt_s <= f['time'] <= gt_e for f in participant_flags)
            if not (segment_overlap or flag_inside):
                return False
        return True

    if gt_type.lower() == "partial_spoof":
        if not gt_intervals:
            return len(participant_segments) == 0 and len(participant_flags) == 0
        
        for (gt_s, gt_e) in gt_intervals:
            segment_overlap = any(max(s, gt_s) < min(e, gt_e) for (s, e) in participant_segments)
            flag_inside = any(gt_s <= f['time'] <= gt_e for f in participant_flags)
            if not (segment_overlap or flag_inside):
                return False
        return True

    return False

def evaluate_trial(trial):
    return {
        "duration": float(trial.get("trial_duration", 60.0)),
        "gt_type": trial.get("gt_label"),
        "gt_segments": trial.get("gt_segments", []),
        "participant_segments": [(s["start"], s["end"]) for s in trial.get("segments", [])],
        "participant_flags": trial.get("flags", []),
        "responses": trial.get("responses", {}),
    }