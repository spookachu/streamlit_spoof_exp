# trial_ui.py
import streamlit as st
from streamlit.components.v1 import html as components_html
from streamlit_extras.stylable_container import stylable_container
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
from helpers import htmlify, parse_spoof_intervals, compute_answer_validity
from config import RESULTS_DIR, INSTRUCTIONS
from debrief import show_debrief
from storage import save_to_github
import uuid, random, datetime, hashlib, time, os, json

try:
    from pylsl import StreamInfo, StreamOutlet, local_clock
    LSL_AVAILABLE = True
except (RuntimeError, ImportError):
    LSL_AVAILABLE = False

import time

def log_action(trial_idx, action_type, **kwargs):
    """
    Logs an action locally (wall clock) and optionally via LSL.
    Always records ts_wall.
    Records ts_lsl only if LSL is available.
    """
    ts_wall = time.time()

    ts_lsl = None
    if LSL_AVAILABLE and st.session_state.get("lsl_outlet") is not None:
        ts_lsl = local_clock() 
        msg = f"{action_type}|trial={trial_idx}|" + "|".join(f"{k}:{v}" for k, v in kwargs.items())
        st.session_state.lsl_outlet.push_sample([msg], ts_lsl)

    log_entry = {
        "action": action_type,
        "ts_wall": ts_wall,  
        **kwargs
    }

    if ts_lsl is not None:
        log_entry["ts_lsl"] = ts_lsl

    st.session_state.action_log_by_trial.setdefault(trial_idx, []).append(log_entry)

def show_trial():
    """
    Displays the current trial: affect image, video, segment marking, and evaluation questions.
    """    
    st.markdown('<a id="top-of-page"></a>', unsafe_allow_html=True)

    participant_id = st.session_state.get("participant_id")
    trial_idx = st.session_state.trial_index
    trial_start_key = f"trial_{trial_idx}_start_time"
    trial_start = datetime.datetime.now()
    if trial_start_key not in st.session_state:
        st.session_state[trial_start_key]  = trial_start
    trial = st.session_state.all_trials[trial_idx]

    # checks
    if trial_idx >= len(st.session_state.trial_order) :
        return 
    if st.session_state.get("emergency_quit", False): 
            show_debrief() 
            return

    storage = st.session_state.storage
    st.session_state.segments_by_trial.setdefault(trial_idx, [])
    st.session_state.flags_by_trial.setdefault(trial_idx, [])
    st.session_state.responses_by_trial.setdefault(trial_idx, {})
    st.session_state.action_log_by_trial.setdefault(trial_idx, [])
    st.session_state.saved_trials.setdefault(trial_idx, {})

    st.session_state.gt_type = trial.get("label")
    st.session_state.gt_intervals = parse_spoof_intervals(trial.get("spoof_segment_times", ""))
    duration = float(trial.get("duration", 60.0))
    if f"trial_{trial_idx}_start_ts" not in st.session_state:
        st.session_state[f"trial_{trial_idx}_start_ts"] = time.time()

    # trust source cue
    if "trust_cue" not in trial:
        trial_trust_cue = random.choice([True, False]) 
        st.session_state.all_trials[st.session_state.trial_index]["trust_cue"] = trial_trust_cue
    else:
        trial_trust_cue = trial["trust_cue"]
    st.session_state.trust_cue = trial_trust_cue

    instructions_html = htmlify(INSTRUCTIONS[st.session_state.instruction_version])
    with st.sidebar:
        st.markdown(
            f"""
        <div class="feed-card" style="padding: 12px 16px;">
            <div class="meta-row">
                <div>
                    <div class="meta-text">INSTRUCTIONS</div>
                    <div class="small-muted">System · just now</div>
                </div>
            </div>
            <div style="font-size:10px; line-height:1.4; margin-top: 6px;">
                {instructions_html}
            </div>
        </div>
            """,
            unsafe_allow_html=True
        )
        if "start_button_clicked" not in st.session_state:
            st.session_state.start_button_clicked = False

        if st.session_state.trial_index == 0 and not st.session_state.start_button_clicked:
            with stylable_container(
                "start",
                css_styles="""
                button { 
                    background-color: #73FFC2 !important; 
                    color: white !important; 
                    font-size: 100px !important; 
                    border-radius: 10px !important; 
                    border: 2px solid #361F27 !important; 
                    padding: 5px 10px; 
                    cursor: pointer; 
                    box-shadow: 2px 2px 6px rgba(0,0,0,0.2); 
                } 
                button:hover { 
                    background-color: #85A0A8 !important; 
                    box-shadow: 3px 3px 8px rgba(0,0,0,0.3); 
                } 
                """
            ):
                if st.button("I understand."):
                    st.session_state.start_button_clicked = True
                else:
                    st.stop()  


    aff_col, quit_col = st.columns([0.6, 0.4])
    with quit_col: 
        _,  emergency_esc = st.columns([0.7, 0.3]) 
        with emergency_esc: 
            with stylable_container( 
                "quit", 
                css_styles=""" 
                button { 
                background-color: #73FFC2 !important; 
                color: black !important; 
                font-size: 100px !important; 
                border-radius: 10px !important; 
                border: 2px solid #361F27 !important; 
                padding: 5px 10px; cursor: pointer; 
                box-shadow: 2px 2px 6px rgba(0,0,0,0.2); 
                } 
                button:hover { 
                    background-color: #85A0A8 !important; 
                    box-shadow: 3px 3px 8px rgba(0,0,0,0.3); 
                } """ ): 
                if st.button("EMERGENCY EXIT"): 
                    st.session_state["emergency_quit"] = True 
                    log_action(trial_idx, "emergency_quit")
                    st.rerun()       

    with aff_col:
        c1, c2, c3 = st.columns([0.2, 0.6, 0.1])

        aff = trial.get("affect_image")
        quadrant = trial.get("quadrant", "")
        with c1:
            st.markdown("<div style='font-size:24px; text-align:right;'>👤</div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:10px;">
                <div style="font-size:14px; font-weight:bold;"> Preview Audio Clip {trial_idx+1} / {len(st.session_state.trial_order)}</div>
            </div>
            """, unsafe_allow_html=True)
            if trial_trust_cue:
                st.markdown("<div style='font-size:14px; color:green; font-weight:bold; margin-bottom:6px;'>Audio originating from a trusted source</div>", unsafe_allow_html=True)

            if aff and os.path.exists(aff):
                st.image(aff, width=300)
            else:
                st.markdown("<div class='small-muted'>No affect preview image available</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    _, video_col, _ = st.columns([0.1, 0.8, 0.1])
    with video_col:
        st.markdown('<div class="video-wrapper">', unsafe_allow_html=True)
        if trial.get('video') and os.path.exists(trial['video']):
            st.video(trial['video'])
        else:
            st.warning("Video file not found or path invalid for this trial.")
        st.markdown("#### Listen to the entire audio before making any choices.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # FLAGGING
        st.markdown("### Mark suspicious segments")
        segment_slider = st.slider(
            "Select segment (start/end)",
            0.0, duration,
            value=(0.0, min(1.0, duration)),
            step=0.01,
            key=f"{trial_idx}_segment_slider",
            on_change=lambda: log_action(trial_idx, "update_slider", slider=f"{trial_idx}_segment_slider")
        )
        with stylable_container("add_segment", css_styles="""
            button {
                background-color: #f95738 !important;
                color: black !important;
                font-size: 14px !important;
                border-radius: 10px !important; 
                border: 2px solid #A53B3D !important;
                padding: 4px 10px;
                cursor: pointer;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
            }
            button:hover {
                background-color: #85A0A8 !important;
                box-shadow: 3px 3px 8px rgba(0,0,0,0.3);
            }
            """
            ):
            if st.button("Add segment", key=f"{trial_idx}_add_segment"):
                log_action(trial_idx, "add_segment", segment=f"{segment_slider[0]}-{segment_slider[1]}", id=str(uuid.uuid4()))
                st.session_state.segments_by_trial[trial_idx].append({ 
                    "id": str(uuid.uuid4()), 
                    "start": segment_slider[0], 
                    "end": segment_slider[1],  
                    "timestamp": datetime.datetime.now().isoformat() 
                })

        st.write("---")
        # --- FLAGS ---
        flag_slider = st.slider(
            "Mark flag (timestamp)",
            0.0, duration,
            value=0.0,
            step=0.01,
            key=f"{trial_idx}_flag_slider",
            on_change=lambda: log_action(trial_idx, "update_slider", slider=f"{trial_idx}_flag_slider")
        )
        with stylable_container("add_flag", css_styles="""
            button {
                background-color: #f95738 !important;
                color: black !important;
                font-size: 14px !important;
                border-radius: 10px !important; 
                border: 2px solid #A53B3D !important;
                padding: 4px 10px;
                cursor: pointer;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
            }
            button:hover {
                background-color: #85A0A8 !important;
                box-shadow: 3px 3px 8px rgba(0,0,0,0.3);
            }
            """
            ):
            if st.button("Add flag", key=f"{trial_idx}_add_flag"):
                log_action(trial_idx, "add_flag", flag=flag_slider, id=str(uuid.uuid4()))
                st.session_state.flags_by_trial[trial_idx].append({ 
                    "id": str(uuid.uuid4()), 
                    "time": flag_slider, 
                    "timestamp": datetime.datetime.now().isoformat() 
                    })

        st.markdown("<hr style='border:1px solid #F5F5F5'>", unsafe_allow_html=True)
        delete_col, plot_col = st.columns([0.5, 0.5])

        # Plot timeline
        with plot_col:
            fig_h, fig_w = 1.5, max(10, duration/5)
            fig, ax = plt.subplots(figsize=(fig_w, fig_h))
            ax.set_xlim(0, duration)
            ax.set_ylim(0, 1)
            ax.axis("off")

            ax.add_patch(Rectangle((0, 0.25), duration, 0.5, color="#eeeeee"))
            for seg in st.session_state.segments_by_trial[trial_idx]:
                ax.add_patch(Rectangle(
                    (seg["start"], 0.25),
                    max(1e-3, seg["end"] - seg["start"]),
                    0.5,
                    color=(0.0, 0.45, 0.8, 0.6)
                ))
                ax.text((seg["start"]+seg["end"])/2, 0.48, f"{seg['start']:.2f}-{seg['end']:.2f}s",
                        ha="center", va="center", fontsize=8, color="white")
            for flag in st.session_state.flags_by_trial[trial_idx]:
                t = flag["time"]
                ax.add_patch(Rectangle((t-0.01, 0.25), 0.02, 0.5, color=(1.0, 0.85, 0.2, 0.8)))
                ax.text(t, 0.78, f"{t:.2f}s", ha="center", va="bottom", fontsize=8, color="orange")

            st.pyplot(fig, bbox_inches="tight")

        # Delete list
        with delete_col:
            st.markdown("##### Current Segments")
            seg_to_delete = []
            for seg in st.session_state.segments_by_trial[trial_idx][:]:
                c1, c2, c3 = st.columns([0.3, 0.2, 0.4])
                with c1:
                    st.write(f"Segment: {seg['start']:.2f} - {seg['end']:.2f}s")
                with c2:
                    with stylable_container(f"delete_seg_{seg['id']}", css_styles="""
                        button {
                            background-color: #B0C6CE !important;
                            color: black !important;
                            font-size: 16px !important;
                            border-radius: 10px !important; 
                            border: 2px solid #82A4B0 !important;
                            padding: 5px 10px;
                            cursor: pointer;
                            box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
                        }
                        button:hover {
                            background-color: #85A0A8 !important;
                            box-shadow: 3px 3px 8px rgba(0,0,0,0.3);
                        }
                        """
                    ):
                        if st.button("Delete", key=f"{trial_idx}_del_seg_{seg['id']}"):
                            seg_to_delete.append(seg['id'])
                            log_action(trial_idx, "delete_segment", deleted_segment=seg['id'])
                            st.write("Confirm deletion?")
            if seg_to_delete:
                st.session_state.segments_by_trial[trial_idx] = [
                    s for s in st.session_state.segments_by_trial[trial_idx] if s['id'] not in seg_to_delete
                ]

            st.markdown("##### Current Flags")
            flags_to_delete = []
            for flag in st.session_state.flags_by_trial[trial_idx][:]: 
                c1, c2, c3 = st.columns([0.3, 0.2, 0.4])
                with c1:
                    st.write(f"Flag: {flag['time']:.2f}s")
                with c2:
                    with stylable_container(f"delete_flag_{flag['id']}",  css_styles="""
                            button {
                                background-color: #B0C6CE !important;
                                color: black !important;
                                font-size: 16px !important;
                                border-radius: 10px !important; 
                                border: 2px solid #82A4B0 !important;
                                padding: 5px 10px;
                                cursor: pointer;
                                box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
                            }
                            button:hover {
                                background-color: #85A0A8 !important;
                                box-shadow: 3px 3px 8px rgba(0,0,0,0.3);
                            }
                            """
                        ):
                        if st.button("Delete", key=f"{trial_idx}_del_flag_{flag['id']}"):
                            flags_to_delete.append(flag['id'])
                            log_action(trial_idx, "delete_flag", deleted_ids=flag['id'])
                            st.write("Confirm deletion?")
            if flags_to_delete:
                st.session_state.flags_by_trial[trial_idx] = [f for f in st.session_state.flags_by_trial[trial_idx] if f['id'] not in flags_to_delete]

        # EVALUATION
        # EVALUATION
        sanity_key = f"trial{trial_idx}_sanity"
        if sanity_key not in st.session_state:
            st.session_state[sanity_key] = random.choice([False, False, True])
        sanity_check = st.session_state[sanity_key]

        st.markdown("### Evaluate the audio")

        questions = [
            "The voice sounds mechanical.",
            "The voice sounds expressive.",
            "The voice is easy to understand.",
            "The audio sounds clean.",
            "The voice sounds calm.",
            "I am confident in my evaluation."
        ]

        if sanity_check:
            questions.append("What scenario were you given for this task?")

        options = ["Completely \n Disagree", "Disagree", "Unsure", "Agree", "Completely \n Agree"]
        sanity_options = ["Monitoring for audio attacks.", 
                            "Evaluating new technology.", 
                            "I did not pay attention.", 
                            "Creating new synthetic voices.",
                            "Moderating for offensive language."]

        if trial_idx not in st.session_state.responses_by_trial:
            st.session_state.responses_by_trial[trial_idx] = {}

        for q in questions:
            if "scenario" in q.lower() or "instructions" in q.lower():  
                st.session_state.responses_by_trial[trial_idx].setdefault(q, sanity_options[2])  # "I did not pay attention."
            else:
                st.session_state.responses_by_trial[trial_idx].setdefault(q, options[2])  # "Unsure"

        qorder_key = f"trial{trial_idx}_question_order"
        if qorder_key not in st.session_state:
            order = list(range(len(questions)))
            random.shuffle(order)
            st.session_state[qorder_key] = order
        question_order = st.session_state[qorder_key]

        i = 0
        while i < len(question_order):
            cols = st.columns(2)
            for j in range(2):
                if i + j >= len(question_order):
                    break

                q_index = question_order[i + j]
                q = questions[q_index]

                with cols[j]:
                    st.markdown(
                        f"<div style='font-size:12px; font-weight:bold; line-height:1.1; margin-bottom:6px;'>{q}</div>",
                        unsafe_allow_html=True
                    )

                    radio_key = f"trial{trial_idx}_question_{q_index}"

                    if "scenario" in q.lower() or "instructions" in q.lower():
                        selected = st.radio(
                            label=" ",
                            options=sanity_options,
                            key=radio_key,
                            index=sanity_options.index(
                                st.session_state.responses_by_trial[trial_idx][q]
                            ),
                            label_visibility="collapsed"
                        )
                    else:
                        selected = st.radio(
                            label=" ",
                            options=options,
                            key=radio_key,
                            index=options.index(
                                st.session_state.responses_by_trial[trial_idx][q]
                            ),
                            label_visibility="collapsed"
                        )

                    if selected != st.session_state.responses_by_trial[trial_idx][q]:
                        st.session_state.responses_by_trial[trial_idx][q] = selected
                        log_action(trial_idx, "eval_response", question=q, old_answer=None, new_answer=selected)
            i += 2

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    _, next_col = st.columns([0.8, 0.2])
    with next_col:
        with stylable_container( 
            "next", 
            css_styles=""" 
            button { 
            background-color: #B3BCB5 !important; 
            color: black !important; 
            border-radius: 5px !important; 
            padding: 5px 5px !important; 
            font-size: 14px !important; 
            font-weight: bold !important; 
            border: 2px solid #8A9A90 !important; 
            cursor: pointer; 
            box-shadow: 2px 2px 6px rgba(0,0,0,0.2); 
            } button:
            hover 
            { background-color: #95A49A !important; 
            box-shadow: 3px 3px 8px rgba(0,0,0,0.3); 
            } 
            """ ):
                if st.button("Save and Continue"):
                    trial_idx = st.session_state.trial_index
                    trial_end = datetime.datetime.now()
                    trial_end_key = f"trial_{trial_idx}_end_time"
                    if trial_end_key not in st.session_state:
                        st.session_state[trial_end_key] = datetime.datetime.now().isoformat()
                    trial_duration_key = f"trial_{trial_idx}_duration"
                    if trial_duration_key not in st.session_state:
                        st.session_state[trial_duration_key] = (trial_end - trial_start).total_seconds()

                    required_wait = float(trial.get("duration", 0))
                    validity_info = compute_answer_validity(trial_idx, required_wait)
                    trial_data = st.session_state.storage.save_trial(trial_idx, extra_metadata=validity_info)
                    st.session_state.trial_index += 1
                    st.session_state.storage.session_data["trial_index"] = st.session_state.trial_index
                    st.session_state.storage.save_session_data()
                    
                    file_name = f"{st.session_state.participant_id}_trial_{trial_idx}.json"
                    github_path = f"results/full_run/{file_name}"

                    try:
                        save_to_github(trial_data, github_path)
                        local_file = os.path.join(RESULTS_DIR, file_name)
                        if os.path.exists(local_file):
                            os.remove(local_file)
                            print(f"Deleted local file: {file_name}")
                    except Exception as e:
                        print(f"Upload failed: {e}")
                        print(f"Local file kept: {file_name}")
                        
                    log_action(trial_idx, "next_trial")
                
                    components_html( 
                    """ 
                    <script> 
                        window.location.hash = "top"; 
                        window.parent.location.reload(); 
                    </script> """, 
                    height=0, )
                    #st.rerun()
                    
    st.markdown("---")
    st.caption(f"Participant: {participant_id} · On trial {st.session_state.trial_index+1} of {len(st.session_state.trial_order)}")