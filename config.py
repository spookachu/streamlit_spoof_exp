# config.py
import os
import streamlit as st

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(PROJECT_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

AFFECT_EXCEL = os.path.join(PROJECT_DIR, "assets/affect_dataset.xlsx")
STIMULI_EXCEL = os.path.join(PROJECT_DIR, "assets/llama_subset.xlsx")

INSTRUCTIONS = {
    "new_tech": """
    WELCOME
You will explore a cutting-edge communication technology on this social media platform that uses artificial intelligence to enhance and transmit speech. This new system is designed to boost accessibility of content for all users.

Your task is to flag any moments that sound synthetic, artificially generated, or otherwise manipulated. 

For each audio clip:
- Listen carefully; you may pause and replay as needed.
- If you hear something suspicious, you can flag a specific timestamp, an audio segment, or the entire audio clip.
- Add multiple flags as needed, or remove flags if unsure.
- The sliders are always as the same duration as the audio.
- Complete a brief evaluation describing your overall impression of the clip.
- Click "Next" to proceed to the next clip.

There are 20 short recordings. Please do your best to detect synthetic or unusual audio. Your careful attention helps improve this platform.

If you feel uncomfortable at any time, use the "Emergency Exit" button to quit the experiment.
""",
    "monitor_attacks": """
    WARNING

A recent security briefing has revealed that a hostile external group has been attempting to infiltrate and sabotage this platform using audio content that has been altered or entirely fabricated using synthetic, AI-generated speech. These manipulations are designed to mislead users and undermine trust in legitimate communication.

Your task is to flag any moments that sound synthetic, artificially generated, or otherwise manipulated.

For each audio clip:
- Listen carefully; you may pause and replay as needed.
- If you hear something suspicious, you can flag a specific timestamp, an audio segment, or the entire audio clip.
- Add multiple flags as needed, or remove flags if unsure.
- The sliders are always as the same duration as the audio.
- Complete a brief evaluation describing your overall impression of the clip.
- Click "Next" to proceed to the next clip.

There are 20 short recordings. Please do your best to detect synthetic or unusual audio. Your careful attention helps keep users of this platform safe.

If you feel uncomfortable at any time, use the "Emergency Exit" button to quit the experiment.
"""
}

BASE_CSS = f"""
<style>
html, body, [class*="st-"] {{
    font-family: Arial, sans-serif;
    color: #111 !important;  
    font-size: 10px !important;
}}
.block-container {{
    padding-top: 0rem !important;
    padding-bottom: 0rem !important;
    padding-left: 1rem !important;  
    padding-right: 1rem !important;  
    margin-top: 3rem !important;
    max-width: 100% !important;
}}
div.row-widget.stRadio > div {{
    gap: 0.1rem !important;
}}
html, body, .stApp {{
    background-color: #ffffff !important;   
}}
body, .stText, .stMarkdown {{
    color: #111 !important;
}}
.sidebar .sidebar-content {{
    background: linear-gradient(180deg, #fdfdfd 0%, #f7f9fc 100%);
    padding: 0.5rem !important;
    margin: 0 !important;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
}}
</style>
"""

CARD_CSS = """
<style>
.feed-card {
    border-radius: 5px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.1);
    background: linear-gradient(180deg, #ffffff 0%, #f7f7f7 100%);
    padding: 4px;
    margin-bottom: 3px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.feed-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.15);
}
.meta-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}
.meta-text { 
    font-weight: 600; 
    font-size: 16px;
}
.small-muted { 
    color: #666; 
    font-size: 13px; 
}
.segment-chip {
    display: inline-block;
    border-radius: 12px;
    padding: 6px 12px;
    background: #eef2ff;
    margin-right: 8px;
    font-size: 13px;
}
</style>
"""
def apply_styling():
    st.set_page_config(page_title="Moderator Task", layout="wide")
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    st.markdown(CARD_CSS, unsafe_allow_html=True)