import streamlit as st
import os
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range
import yt_dlp
import tempfile
import io

st.set_page_config(page_title="Audio Editor", page_icon="🎵", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🎵 Audio Editor</h1>', unsafe_allow_html=True)

# Initialize session state
if 'audio' not in st.session_state:
    st.session_state.audio = None
if 'original_audio' not in st.session_state:
    st.session_state.original_audio = None
if 'filename' not in st.session_state:
    st.session_state.filename = "edited_audio.mp3"

def download_youtube_audio(url):
    """Download audio from YouTube"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            audio_file = os.path.join(temp_dir, 'audio.mp3')
            audio = AudioSegment.from_mp3(audio_file)
            return audio
    except Exception as e:
        st.error(f"Error downloading YouTube audio: {str(e)}")
        return None

def load_audio(file):
    """Load audio file"""
    try:
        audio = AudioSegment.from_file(file)
        return audio
    except Exception as e:
        st.error(f"Error loading audio: {str(e)}")
        return None

def export_audio(audio, format="mp3"):
    """Export audio to bytes"""
    buffer = io.BytesIO()
    audio.export(buffer, format=format)
    buffer.seek(0)
    return buffer

# Sidebar for input
with st.sidebar:
    st.header("📥 Input Source")
    
    input_method = st.radio("Choose input method:", ["Upload File", "YouTube Link"])
    
    if input_method == "Upload File":
        uploaded_file = st.file_uploader("Upload audio file", type=['mp3', 'wav', 'ogg', 'flac', 'm4a'])
        
        if uploaded_file and st.button("Load Audio"):
            with st.spinner("Loading audio..."):
                audio = load_audio(uploaded_file)
                if audio:
                    st.session_state.audio = audio
                    st.session_state.original_audio = audio
                    st.session_state.filename = uploaded_file.name.rsplit('.', 1)[0] + "_edited.mp3"
                    st.success("Audio loaded successfully!")
    
    else:
        youtube_url = st.text_input("Enter YouTube URL:")
        
        if youtube_url and st.button("Download Audio"):
            with st.spinner("Downloading from YouTube..."):
                audio = download_youtube_audio(youtube_url)
                if audio:
                    st.session_state.audio = audio
                    st.session_state.original_audio = audio
                    st.session_state.filename = "youtube_audio_edited.mp3"
                    st.success("Audio downloaded successfully!")
    
    st.divider()
    
    if st.session_state.audio:
        st.info(f"Duration: {len(st.session_state.audio) / 1000:.2f}s")
        st.info(f"Channels: {st.session_state.audio.channels}")
        st.info(f"Sample Rate: {st.session_state.audio.frame_rate}Hz")

# Main content area
if st.session_state.audio:
    tabs = st.tabs(["✂️ Trim", "🔗 Merge", "🎚️ Effects", "📊 Export"])
    
    # Trim Tab
    with tabs[0]:
        st.subheader("Trim Audio")
        
        col1, col2 = st.columns(2)
        
        max_duration = len(st.session_state.audio) / 1000
        
        with col1:
            start_time = st.number_input("Start time (seconds)", min_value=0.0, max_value=max_duration, value=0.0, step=0.1)
        
        with col2:
            end_time = st.number_input("End time (seconds)", min_value=0.0, max_value=max_duration, value=max_duration, step=0.1)
        
        if st.button("Apply Trim"):
            if start_time < end_time:
                st.session_state.audio = st.session_state.original_audio[start_time * 1000:end_time * 1000]
                st.success(f"Audio trimmed to {start_time}s - {end_time}s")
            else:
                st.error("Start time must be less than end time")
    
    # Merge Tab
    with tabs[1]:
        st.subheader("Merge with Another Audio")
        
        merge_file = st.file_uploader("Upload audio to merge", type=['mp3', 'wav', 'ogg', 'flac'], key="merge")
        
        merge_position = st.selectbox("Merge position:", ["Append (End)", "Prepend (Start)", "Overlay"])
        
        if merge_file and st.button("Merge Audio"):
            with st.spinner("Merging audio..."):
                merge_audio = load_audio(merge_file)
                if merge_audio:
                    if merge_position == "Append (End)":
                        st.session_state.audio = st.session_state.audio + merge_audio
                    elif merge_position == "Prepend (Start)":
                        st.session_state.audio = merge_audio + st.session_state.audio
                    else:  # Overlay
                        st.session_state.audio = st.session_state.audio.overlay(merge_audio)
                    st.success("Audio merged successfully!")
    
    # Effects Tab
    with tabs[2]:
        st.subheader("Audio Effects")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Volume**")
            volume_change = st.slider("Volume (dB)", min_value=-30, max_value=30, value=0, step=1)
            
            st.markdown("**Speed**")
            speed = st.slider("Speed", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
        
        with col2:
            st.markdown("**Fade**")
            fade_in = st.number_input("Fade in (ms)", min_value=0, max_value=5000, value=0, step=100)
            fade_out = st.number_input("Fade out (ms)", min_value=0, max_value=5000, value=0, step=100)
        
        effects_col1, effects_col2 = st.columns(2)
        
        with effects_col1:
            normalize_audio = st.checkbox("Normalize Audio")
        
        with effects_col2:
            reverse_audio = st.checkbox("Reverse Audio")
        
        if st.button("Apply Effects"):
            with st.spinner("Applying effects..."):
                audio = st.session_state.audio
                
                # Volume
                if volume_change != 0:
                    audio = audio + volume_change
                
                # Speed
                if speed != 1.0:
                    audio = audio._spawn(audio.raw_data, overrides={
                        "frame_rate": int(audio.frame_rate * speed)
                    }).set_frame_rate(audio.frame_rate)
                
                # Fade
                if fade_in > 0:
                    audio = audio.fade_in(fade_in)
                if fade_out > 0:
                    audio = audio.fade_out(fade_out)
                
                # Normalize
                if normalize_audio:
                    audio = normalize(audio)
                
                # Reverse
                if reverse_audio:
                    audio = audio.reverse()
                
                st.session_state.audio = audio
                st.success("Effects applied successfully!")
    
    # Export Tab
    with tabs[3]:
        st.subheader("Export Audio")
        
        col1, col2 = st.columns(2)
        
        with col1:
            export_format = st.selectbox("Export format:", ["mp3", "wav", "ogg"])
        
        with col2:
            filename = st.text_input("Filename:", value=st.session_state.filename)
        
        if st.button("Generate Download"):
            with st.spinner("Preparing download..."):
                audio_bytes = export_audio(st.session_state.audio, format=export_format)
                
                st.download_button(
                    label=f"⬇️ Download {export_format.upper()}",
                    data=audio_bytes,
                    file_name=f"{filename.rsplit('.', 1)[0]}.{export_format}",
                    mime=f"audio/{export_format}"
                )
                st.success("Ready to download!")
        
        st.divider()
        
        if st.button("🔄 Reset to Original"):
            st.session_state.audio = st.session_state.original_audio
            st.success("Audio reset to original!")

else:
    st.info("👈 Please upload an audio file or provide a YouTube link to get started!")
    
    st.markdown("""
    ### Features:
    - ✂️ **Trim**: Cut audio to specific time range
    - 🔗 **Merge**: Combine multiple audio files
    - 🎚️ **Effects**: Adjust volume, speed, add fades, normalize, reverse
    - 📊 **Export**: Download in MP3, WAV, or OGG format
    - 🎥 **YouTube**: Download and edit audio from YouTube videos
    """)

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Built with Streamlit | Audio processing powered by PyDub</p>
    </div>
""", unsafe_allow_html=True)
