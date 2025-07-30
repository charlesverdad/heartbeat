import streamlit as st
import os
import tempfile
from pathlib import Path
from video_downloader import VideoDownloader, VideoDownloadResult
from transcriber import Transcriber, TranscriptionResult
import time

# Configure Streamlit page
st.set_page_config(
    page_title="Youtube Transcript Processing Pipeline",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'download_result' not in st.session_state:
    st.session_state.download_result = None
if 'transcript_result' not in st.session_state:
    st.session_state.transcript_result = None
if 'audio_result' not in st.session_state:
    st.session_state.audio_result = None
if 'output_dir' not in st.session_state:
    st.session_state.output_dir = tempfile.mkdtemp(prefix="youtube_processing_")


def main():
    st.title("🎥 Heartbeat Church Sermon Processing Pipeline")
    st.markdown("Generate transcripts from sermon for easy translation and publishing")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Output directory
        output_dir = st.text_input(
            "Output Directory", 
            value=st.session_state.output_dir,
            help="Directory where files will be saved"
        )
        st.session_state.output_dir = output_dir
        
        # Model selection
        model_size = st.selectbox(
            "Whisper Model Size",
            options=["tiny", "base", "small", "medium", "large"],
            index=1,
            help="Larger models are more accurate but slower"
        )
        
        # Clear session button
        if st.button("🗑️ Clear Session"):
            for key in ['download_result', 'transcript_result', 'audio_result', 'selected_audio_file']:
                st.session_state[key] = None
            st.rerun()
    
    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["🔽 Download", "📝 Transcription", "🔄 Full Workflow"])
    
    with tab1:
        download_tab(output_dir)
    
    with tab2:
        transcription_tab(output_dir, model_size)
    
    with tab3:
        workflow_tab(output_dir, model_size)

def download_tab(output_dir):
    st.header("📥 YouTube Video Download")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste a YouTube video URL here"
        )
    
    with col2:
        extract_audio = st.checkbox("Extract Audio to MP3", value=True)
    
    # Time range options
    st.subheader("⏱️ Time Range (Optional)")
    col1, col2 = st.columns(2)
    
    with col1:
        start_time = st.text_input(
            "Start Time",
            placeholder="00:00:00",
            help="Format: HH:MM:SS or seconds"
        )
    
    with col2:
        end_time = st.text_input(
            "End Time", 
            placeholder="00:05:30",
            help="Format: HH:MM:SS or seconds"
        )
    
    if st.button("🚀 Download", type="primary"):
        if not url:
            st.error("Please enter a YouTube URL")
            return
        
        with st.spinner("Downloading video..."):
            downloader = VideoDownloader(output_dir=output_dir)
            result = downloader.download_video(
                url, 
                start_time=start_time if start_time else None,
                end_time=end_time if end_time else None,
                extract_audio=extract_audio
            )
            
            if result.success:
                st.session_state.download_result = result
                st.success(f"✅ Download successful!")
                
                # Display result info
                st.info(f"**File saved to:** `{result.output_path}`")
                if result.metadata:
                    st.json(result.metadata)
                
                # Audio player if MP3 was extracted
                if extract_audio and result.output_path.endswith('.mp3'):
                    if os.path.exists(result.output_path):
                        st.audio(result.output_path)
            else:
                st.error(f"❌ Download failed: {result.error_message}")


def transcription_tab(output_dir, model_size):
    st.header("📝 Audio Transcription")
    
    # Initialize selected audio file in session state
    if 'selected_audio_file' not in st.session_state:
        st.session_state.selected_audio_file = None
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.download_result and st.session_state.download_result.output_path.endswith('.mp3'):
            if st.button("📥 Use Downloaded Audio", key="transcribe_download"):
                st.session_state.selected_audio_file = st.session_state.download_result.output_path
                st.rerun()
    
    with col2:
        uploaded_audio = st.file_uploader(
            "Upload Audio File",
            type=['mp3', 'wav', 'm4a', 'ogg'],
            key="transcribe_upload"
        )
        
        if uploaded_audio:
            temp_path = os.path.join(output_dir, uploaded_audio.name)
            with open(temp_path, 'wb') as f:
                f.write(uploaded_audio.getbuffer())
            st.session_state.selected_audio_file = temp_path
    
    # Get the selected audio file
    audio_file = st.session_state.selected_audio_file
    
    if audio_file:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"📁 Selected for transcription: `{audio_file}`")
        with col2:
            if st.button("🗋 Clear Selection"):
                st.session_state.selected_audio_file = None
                st.rerun()
        
        st.audio(audio_file)
        
        if st.button("🎙️ Transcribe Audio", type="primary"):
            st.write(f"Selected file for transcription: `{audio_file}`")
            if not os.path.exists(audio_file):
                st.error("Audio file not found.")
                return
            
            with st.spinner(f"Transcribing with {model_size} model... This may take a while."):
                transcriber = Transcriber(model_size=model_size, output_dir=output_dir)
                result = transcriber.transcribe_audio(audio_file)
                
                if result.success:
                    st.session_state.transcript_result = result
                    st.success("✅ Transcription completed!")
                    
                    # Display transcript
                    st.subheader("📄 Transcript")
                    st.text_area("Transcript Text", result.transcript, height=300)
                    
                    # Add copy functionality using st.code which has built-in copy button
                    with st.expander("📋 Copy Transcript (click the copy icon in the code block)"):
                        st.code(result.transcript, language="text")
                    
                    # Download button
                    if result.output_path and os.path.exists(result.output_path):
                        with open(result.output_path, 'r') as f:
                            st.download_button(
                                "💾 Download Transcript",
                                f.read(),
                                file_name=os.path.basename(result.output_path),
                                mime="text/plain"
                            )
                    
                    # Show metadata
                    if result.metadata:
                        with st.expander("📊 Transcription Details"):
                            st.json(result.metadata)
                else:
                    st.error(f"❌ Transcription failed: {result.error_message}")

def workflow_tab(output_dir, model_size):
    st.header("🔄 Complete Workflow")
    st.markdown("Process a YouTube video from start to finish: Download → Transcribe")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        workflow_url = st.text_input(
            "YouTube URL",
            placeholder="https://www.youtube.com/watch?v=...",
            key="workflow_url"
        )
    
    with col2:
        st.write("") # Spacing
        st.write("") # Spacing
        auto_download = st.checkbox("Auto-download after transcription", value=True)
    
    # Time range
    st.subheader("⏱️ Time Range (Optional)")
    col1, col2 = st.columns(2)
    
    with col1:
        workflow_start = st.text_input("Start Time", placeholder="00:00:00", key="workflow_start")
    
    with col2:
        workflow_end = st.text_input("End Time", placeholder="00:05:00", key="workflow_end")
    
    if st.button("🚀 Run Complete Workflow", type="primary"):
        if not workflow_url:
            st.error("Please enter a YouTube URL")
            return
        
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Download
            status_text.text("🔽 Downloading video and extracting audio...")
            progress_bar.progress(25)
            
            downloader = VideoDownloader(output_dir=output_dir)
            download_result = downloader.download_video(
                workflow_url,
                start_time=workflow_start if workflow_start else None,
                end_time=workflow_end if workflow_end else None,
                extract_audio=True
            )
            
            if not download_result.success:
                st.error(f"❌ Download failed: {download_result.error_message}")
                return
            
            st.session_state.download_result = download_result
            progress_bar.progress(50)
            
            # Step 2: Transcribe
            status_text.text("🎙️ Transcribing audio... This may take a while.")
            progress_bar.progress(75)
            
            transcriber = Transcriber(model_size=model_size, output_dir=output_dir)
            transcript_result = transcriber.transcribe_audio(download_result.output_path)
            
            if not transcript_result.success:
                st.error(f"❌ Transcription failed: {transcript_result.error_message}")
                return
            
            st.session_state.transcript_result = transcript_result
            progress_bar.progress(100)
            status_text.text("✅ Workflow completed successfully!")
            
            # Display results
            st.success("🎉 Workflow completed successfully!")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🎵 Audio File")
                st.info(f"`{download_result.output_path}`")
                if os.path.exists(download_result.output_path):
                    st.audio(download_result.output_path)
            
            with col2:
                st.subheader("📄 Transcript")
                st.info(f"`{transcript_result.output_path}`")
                
                # Download buttons
                if auto_download and transcript_result.output_path:
                    with open(transcript_result.output_path, 'r') as f:
                        st.download_button(
                            "💾 Download Transcript",
                            f.read(),
                            file_name=os.path.basename(transcript_result.output_path),
                            mime="text/plain"
                        )
            
            # Show transcript content
            st.subheader("📝 Transcript Content")
            st.text_area("Full Transcript", transcript_result.transcript, height=200, key="workflow_transcript")
            
            # Add copy functionality using st.code which has built-in copy button
            with st.expander("📋 Copy Transcript (click the copy icon in the code block)"):
                st.code(transcript_result.transcript, language="text")
            
        except Exception as e:
            st.error(f"❌ Workflow failed: {str(e)}")
        finally:
            progress_bar.empty()
            status_text.empty()


# File browser section
def show_output_files(output_dir):
    st.subheader("📁 Output Files")
    
    if os.path.exists(output_dir):
        files = list(Path(output_dir).glob("*"))
        if files:
            for file_path in files:
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.text(file_path.name)
                
                with col2:
                    st.text(f"{file_path.stat().st_size / 1024:.1f} KB")
                
                with col3:
                    if file_path.suffix.lower() in ['.mp3', '.wav', '.m4a']:
                        if st.button("🎵", key=f"play_{file_path.name}"):
                            st.audio(str(file_path))
        else:
            st.info("No files generated yet")
    else:
        st.warning("Output directory doesn't exist")

# Add footer with file browser and console
with st.expander("📁 File Browser"):
    show_output_files(st.session_state.output_dir)


if __name__ == "__main__":
    main()
