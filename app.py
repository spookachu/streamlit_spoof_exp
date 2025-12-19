#app.py
import streamlit as st
import os, json
from session_state import init_session_state
from trial_ui import show_trial
from debrief import show_debrief  
from config import apply_styling
from helpers import init_lsl

if "storage" in st.session_state:
    print("Storage.path:", getattr(st.session_state.storage, "session_file", "no path"))
    p = st.session_state.storage.session_file
    if os.path.exists(p):
        try:
            with open(p, "r") as f:
                data = json.load(f)
            print("Session file keys:", list(data.keys()))
            print("trial_index in file:", data.get("trial_index"))
        except Exception as e:
            print("Failed to read session file:", e)
else:
    print("No storage in session_state yet")

try:
    init_lsl()
except:
    print("LSL not supported in cloud deployment")

st.set_page_config(page_title="Moderator Task", layout="wide")
apply_styling()

test_subsample = 20
init_session_state(test_subsample)
if 'trial_index' not in st.session_state:
    st.session_state.trial_index = st.session_state.storage.session_data.get("trial_index", 0)

if st.session_state.trial_index >= len(st.session_state.trial_order):
    show_debrief()
else:
    show_trial()