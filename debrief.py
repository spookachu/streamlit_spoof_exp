# debrief_ui.py
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import json, os, datetime
from storage import Storage, save_to_github

def show_debrief():
    """
    Displays the debrief screen and aggregate results for the participant.
    """
    st.title("Debrief and results")
    
    debrief_text = """ 
    The message you received at the beginning of the experiment was part of a scenario designed 
    to make the task feel realistic. In reality, there is no ongoing external attack or real streaming platform.

    You were also shown affective images at the start of each trial. These images were selected from a standardized
    database and were used to subtly influence emotional state before you listened to the recordings. This helps us 
    understand how affect interacts with trust and detection performance. 
    
    The goal of this research is to better understand how trust, perception, and decision-making work when people encounter potential deepfakes in real time.
    This knowledge will help in developing better detection tools in the future. 
    
    Please type in your Prolific ID so your results can be linked to your account.
   
    """
    st.set_page_config(
        page_title="Debrief",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.markdown(debrief_text)
    storage = st.session_state.get("storage")
    if not storage:
        storage = st.session_state.storage = Storage(st.session_state.participant_id)

    all_trials = storage.load_all_trials()
    print(all_trials)
    all_summary = []

    for trial_idx, data in all_trials.items():
        trial = st.session_state.all_trials[trial_idx]
        participant_segments = data.get("segments", [])
        participant_flags = data.get("flags", [])
        participant_responses = data.get("responses", {})

        gt_type = data.get('gt_label', '').lower()  
        gt_intervals = data.get('gt_segments', [])  
        duration = float(trial.get("duration", 60.0))

        summary = {
            "trial_number": trial_idx+1,
            "duration": duration,
            "gt_type": gt_type,
            "gt_intervals": gt_intervals,
            "participant_segments": participant_segments,
            "participant_flags": participant_flags,
            "participant_responses": participant_responses
        }
        all_summary.append(summary)

    if st.session_state.storage.prolific_id == "unknown":
        st.markdown(
            '<div style="color:black;font-size:16px;style:bold">Please enter your Prolific ID:</div>',
            unsafe_allow_html=True
        )

        _, input_col, _ = st.columns([0.3, 0.3, 0.3])
        with input_col:
            prolific_input = st.text_input("Prolific ID", key="prolific_input")

            if prolific_input:
                st.session_state.prolific_id = prolific_input
                st.session_state.storage.prolific_id = prolific_input
                st.session_state.storage.session_data["prolific_id"] = prolific_input
                st.success("Prolific ID saved!")

                aggregate_out = storage.session_file.replace("_session.json", "_aggregate.json")

                aggregate_metadata = {
                    "participant_id": st.session_state.participant_id,
                    "prolific_id": prolific_input,
                    "instruction_version": st.session_state.instruction_version,
                    "summary": all_summary,
                    "timestamp": datetime.datetime.now().isoformat(),
                }

                with open(aggregate_out, "w") as f:
                    json.dump(aggregate_metadata, f, indent=2)

                github_path = f"results/{os.path.basename(aggregate_out)}"

                try:
                    save_to_github(aggregate_metadata, github_path)
                    print("Uploaded aggregate to GitHub:", github_path)
                    st.rerun()

                    try:
                        os.remove(aggregate_out)
                        print("Deleted local:", aggregate_out)
                    except:
                        print("Could not delete local file (Cloud)", aggregate_out)

                except Exception as e:
                    print("GitHub upload failed:", e)
                    print("Local file kept:", aggregate_out)

            else:
                st.stop()

    st.markdown("""
    Thank you for your contribution to this research.
    Below is a summary of your answers. 
    You can quit the application whenever you are ready.
    """)
    for trial_idx, data in all_trials.items():
        trial = st.session_state.all_trials[trial_idx]
        participant_segments = data.get("segments", [])
        participant_flags = data.get("flags", [])
        participant_responses = data.get("responses", {})

        gt_type = data.get('gt_label', '').lower()  
        gt_intervals = data.get('gt_segments', [])  
        duration = float(trial.get("duration", 60.0))
    
        st.markdown(f"## Trial {trial_idx+1}")
    
        # Correctness check
        participant_segments_list = [(seg["start"], seg["end"]) for seg in participant_segments]
        correct = False
        missed_gt = []
        extra_segments = []

        if gt_type == "bonafide":
            if not participant_segments_list:
                correct = True
            else:
                extra_segments = participant_segments_list
                
        elif gt_type == "full_spoof":
            if participant_segments_list:
                correct = True
            
        elif gt_type == "partial_spoof":
            correct = True
            if gt_intervals:
                for gt_start, gt_end in gt_intervals:
                    overlap_with_seg = any(max(s, gt_start) < min(e, gt_end) for s, e in participant_segments_list)
                    overlap_with_flag = any(gt_start <= f["time"] <= gt_end for f in participant_flags)
                    if not (overlap_with_seg or overlap_with_flag):
                        missed_gt.append((gt_start, gt_end))
                        correct = False

            for s, e in participant_segments_list:
                outside = all(e <= gt_start or s >= gt_end for gt_start, gt_end in gt_intervals)
                if outside:
                    extra_segments.append((s, e))

            if not participant_segments_list and not participant_flags:
                correct = False
                missed_gt = gt_intervals

        st.markdown(f"**Ground truth:** {gt_type.upper()}")
        st.markdown(f"**Your detection was:** {'CORRECT' if correct else 'INCORRECT'}")
        
        if missed_gt:
            st.markdown(f"**Missed spoofed segments:** {len(missed_gt)}")
        if extra_segments:
            st.markdown(f"**Incorrectly flagged segments:** {len(extra_segments)}")
            
        st.markdown("---")

        # Visualization
        fig, ax = plt.subplots(figsize=(10, 1.2))
        ax.set_xlim(0, duration)  
        ax.set_ylim(0, 1)
        ax.axis('off')
        ax.add_patch(Rectangle((0, 0.25), duration, 0.5, color="#eeeeee"))

        if gt_type == "partial_spoof" and gt_intervals:
            for gt_start, gt_end in gt_intervals:
                ax.add_patch(Rectangle((max(0, gt_start), 0.25), max(1e-3, gt_end - gt_start), 0.5, color=(1,0,0,0.35)))
                ax.text((gt_start + gt_end)/2, 0.78, "GT", ha='center', va='bottom', fontsize=8, color='red')
        elif gt_type == "full_spoof":
            ax.add_patch(Rectangle((0, 0.25), duration, 0.5, color=(1,0,0,0.35)))
            ax.text(duration/2, 0.78, "GT (Full Spoof)", ha='center', va='bottom', fontsize=8, color='red')

        for seg in participant_segments:
            s, e = max(0, seg["start"]), min(duration, seg["end"])
            ax.add_patch(Rectangle((s,0.25), max(duration, e-s),0.5, color=(0,0.45,0.8,0.6)))
            ax.text((s+e)/2,0.48,f"{s:.2f}-{e:.2f}s", ha='center', va='center', fontsize=8, color='white')

        for flag in participant_flags:
            t = flag["time"]
            ax.add_patch(Rectangle((t-0.01, 0.25), 0.02, 0.5, color=(1.0, 0.85, 0.2, 0.8)))
            ax.text(t, 0.78, f"{t:.2f}s", ha='center', va='bottom', fontsize=8, color='orange')

        st.pyplot(fig, bbox_inches='tight')

        st.write("**Evaluation responses:**")
        for q, a in participant_responses.items():
            clean_answer = a.replace("<br>", " ") if isinstance(a, str) else str(a)
            st.markdown(f"- **{q}**: {clean_answer}")

   
    st.stop()