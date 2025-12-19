# storage.py
import os, json, datetime
from config import RESULTS_DIR
from helpers import datetime_converter
import streamlit as st
from github import Github

class Storage:
    """
    Handles saving and loading of participant session and trial data.
    """
    def __init__(self):
        self.participant_id = st.session_state.participant_id
        self.prolific_id = st.session_state.prolific_id
        self.session_file = os.path.join(RESULTS_DIR, f"participant_{self.participant_id}_session.json")
        
        if os.path.exists(self.session_file):
            with open(self.session_file, "r") as f:
                self.session_data = json.load(f)
        else:
            st.query_params = {}
            self.session_data = {}
            self.save_session_data()

    def load_all_trials(self):
        """
        Loads all saved trials for the participant.
        """
        trial_files = sorted(
            [f for f in os.listdir(RESULTS_DIR) if f.startswith(f"participant_{self.participant_id}_trial_")],
            key=lambda x: int(x.split("_")[-1].split(".")[0])
        )
        all_trials = {}
        for f in trial_files:
            with open(os.path.join(RESULTS_DIR, f), "r") as tf:
                data = json.load(tf)
                all_trials[data["trial_index"]] = data
        return all_trials
    
    def save_session_data(self):
        """
        Saves session data to a JSON file.
        """
        session_file = os.path.join(RESULTS_DIR, f"participant_{self.participant_id}_session.json")
        with open(session_file, "w") as f:
            json.dump(self.session_data, f, indent=2)
            
    def save_trial(self, trial_idx, extra_metadata=None):
        """
        Saves data for a single trial to a JSON file.
        """
        trial = st.session_state.all_trials[trial_idx]
        
        gt_label = st.session_state.gt_type
        gt_segments = st.session_state.gt_intervals  
        
        trial_data = {
            "participant_id": st.session_state.participant_id,
            "instruction_version": st.session_state.instruction_version,
            "valence_condition": st.session_state.valence_condition,
            "trust_cue": st.session_state.get("trust_cue", False),

            # Trial Metadata 
            "trial_index": trial_idx,
            "trial_number": trial_idx + 1,  
            "affect_image": os.path.basename(trial.get("affect_image") or ""),
            "audio": os.path.basename(trial.get("video") or ""),            
            "gt_label": gt_label,
            "gt_segments": gt_segments,  
            "gt_segments_raw": trial.get('spoof_segment_times', ''),  

            # User Annotations 
            "segments": st.session_state.segments_by_trial.get(trial_idx, []),
            "flags": st.session_state.flags_by_trial.get(trial_idx, []),
            "responses": st.session_state.responses_by_trial.get(trial_idx, {}),
            "action_log": st.session_state.action_log_by_trial.get(trial_idx, []),

            # Timing 
            "trial_start_time": str(st.session_state.get(f"trial_{trial_idx}_start_time")),
            "trial_end_time": str(st.session_state.get(f"trial_{trial_idx}_end_time")),
            "trial_duration": str(st.session_state.get(f"trial_{trial_idx}_duration")),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        if extra_metadata:
            trial_data.update(extra_metadata)

        trial_file = os.path.join(RESULTS_DIR, f"participant_{self.participant_id}_trial_{trial_idx}.json")
        with open(trial_file, "w") as f:
            json.dump(trial_data, f, indent=2)

        self.session_data["trial_index"] = trial_idx + 1        
        return trial_data

def save_to_github(trial_metadata, file_name):
    token = st.secrets["github"]["token"]
    repo_name = st.secrets["github"]["repo"]
    branch = st.secrets["github"].get("branch", "main")

    g = Github(token)
    repo = g.get_repo(repo_name)
    content = json.dumps(trial_metadata, indent=2, default=datetime_converter)

    try:
        file = repo.get_contents(file_name, ref=branch)
        repo.update_file(file.path, f"Update {file_name}", content, file.sha, branch=branch)
    except:
        repo.create_file(file_name, f"Add {file_name}", content, branch=branch)