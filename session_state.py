import streamlit as st
import hashlib, datetime, json, os, random, glob
from loader import Loader
from config import PROJECT_DIR, RESULTS_DIR, INSTRUCTIONS
from storage import Storage

def init_session_state(test_subsample=None):
    os.makedirs(RESULTS_DIR, exist_ok=True)

    query_params = st.query_params

    if "participant_id" in query_params:
        participant_id = query_params["participant_id"][0]
    elif "participant_id" in st.session_state:
        participant_id = st.session_state.participant_id
    else:
        participant_id = hashlib.sha256(
            datetime.datetime.now().isoformat().encode()
        ).hexdigest()[:10]

    st.session_state.participant_id = participant_id
    
    if "prolific_id" in query_params:
        prolific_id = query_params["prolific_id"][0]
    elif "prolific_id" in st.session_state:
        prolific_id = st.session_state.prolific_id
    else:
        prolific_id = "unknown"

    st.session_state.prolific_id = prolific_id
    st.query_params = {"participant_id": [participant_id]}
    
    if "storage" not in st.session_state:
        st.session_state.storage = Storage()
    storage = st.session_state.storage

    if storage.session_data.get("valence_condition"):
        st.session_state.valence_condition = storage.session_data["valence_condition"]
    else:
        st.session_state.valence_condition = random.choice(["HVHA", "LVHA"])
        storage.session_data["valence_condition"] = st.session_state.valence_condition
        storage.save_session_data()  

    if 'loader' not in st.session_state:
        st.session_state.loader = Loader(PROJECT_DIR, valence_condition=st.session_state.valence_condition)
        st.session_state.affect_imgs = st.session_state.loader.load_affect_images()

    st.session_state.emergency_quit = st.session_state.get("emergency_quit", False)
    st.session_state.refresh_occurred = st.session_state.get("refresh_occurred", False)

    if "all_trials" not in st.session_state:
        saved_trials = storage.session_data.get("all_trials")
        
        if saved_trials:
            print("Restoring trials from saved session")
            st.session_state.all_trials = saved_trials
        else:
            trials = st.session_state.loader.load_trials()
            if test_subsample:
                trials = trials[:test_subsample]
            st.session_state.all_trials = trials
            
            storage.session_data["all_trials"] = trials
            storage.save_session_data()

    st.session_state.trial_order = storage.session_data.get("trial_order")
    if not st.session_state.trial_order:
        st.session_state.trial_order = list(range(len(st.session_state.all_trials)))
        random.shuffle(st.session_state.trial_order) 
        storage.session_data["trial_order"] = st.session_state.trial_order
        storage.save_session_data()

    if "trial_affect_mapping" not in storage.session_data or not storage.session_data["trial_affect_mapping"]:
        affect_pool = st.session_state.affect_imgs.copy()
        random.shuffle(affect_pool)
        trial_affect_mapping = {}
        num_trials = len(st.session_state.all_trials)
        if len(affect_pool) < num_trials:
            # If not enough images, cycle through them
            affect_pool = affect_pool * ((num_trials // len(affect_pool)) + 1)
        for i in range(num_trials):
            trial_affect_mapping[i] = affect_pool[i]
            st.session_state.all_trials[i]["affect_image"] = affect_pool[i]["path"]
            st.session_state.all_trials[i]["quadrant"] = affect_pool[i]["quadrant"]
        storage.session_data["trial_affect_mapping"] = trial_affect_mapping
        storage.save_session_data()
    else:
        trial_affect_mapping = storage.session_data["trial_affect_mapping"]
        for trial_idx, affect_data in trial_affect_mapping.items():
            trial_idx = int(trial_idx)  # JSON keys are strings
            if trial_idx < len(st.session_state.all_trials):
                st.session_state.all_trials[trial_idx]["affect_image"] = affect_data["path"]
                st.session_state.all_trials[trial_idx]["quadrant"] = affect_data["quadrant"]
    st.session_state.trial_affect_mapping = trial_affect_mapping

    st.session_state.trial_index = storage.session_data.get("trial_index", 0)
    
    st.session_state.instruction_version = storage.session_data.get("instruction_version")
    if not st.session_state.instruction_version:
        st.session_state.instruction_version = random.choice(list(INSTRUCTIONS.keys()))
        storage.session_data["instruction_version"] = st.session_state.instruction_version

    for key in [
        "segments_by_trial",
        "flags_by_trial",
        "responses_by_trial",
        "action_log_by_trial",
        "saved_trials",
        "all_trials_restored"
    ]:
        if key not in st.session_state:
            st.session_state[key] = {}