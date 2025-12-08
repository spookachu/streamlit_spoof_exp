#app.py
import streamlit as st
from session_state import init_session_state
from trial_ui import show_trial
from debrief import show_debrief  
from config import apply_styling
from helpers import init_lsl

try:
    init_lsl()
except:
    print("Error. LSL not supported in cloud deployment.")
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