# requirements.txt
"""
streamlit==1.29.0
pydub==0.25.1
yt-dlp==2023.12.30
pytube==15.0.0
numpy==1.24.3
scipy==1.10.1
matplotlib==3.7.2
plotly==5.17.0
streamlit-player==0.1.6
st_audiorec==0.0.7
streamlit-extras==0.4.0
"""

# app.py
import streamlit as st
import os
import tempfile
from pathlib import Path
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
import base64
import time

# Audio processing imports
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range, high_pass_filter, low_pass_filter
import yt_dlp as youtube_dl
from pytube import YouTube
import warnings
warnings.filterwarnings('ignore')

# Set page config
st.set_page_config(
    page_title="Audio Editor Pro",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4CAF50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #2196F3;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .stButton button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .stDownloadButton button {
        background-color: #2196F3;
        color: white;
    }
    .audio-player {
        margin: 20px 0;
        padding: 20px;
        background-color: #f5f5f5;
        border-radius: 10px;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'audio' not in st.session_state:
    st.session_state.audio = None
if 'audio_file' not in st.session_state:
    st.session_state.audio_file = None
if 'edited_audio' not in st.session_state:
    st.session_state.edited_audio = None
if 'sample_rate' not in st.session_state:
    st.session_state.sample_rate = None

def get_audio_duration(audio):
    """Get audio duration in seconds"""
    return len(audio) / 1000.0

def plot_waveform(audio):
    """Create waveform visualization"""
    samples = np.array(audio.get_array_of_samples())
    
    if audio.channels == 2:
        samples = samples.reshape((-1, 2))
        samples = samples.mean(axis=1)
    
    # Downsample for performance
    if len(samples) > 50000:
        step = len(samples) // 50000
        samples = samples[::step]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        y=samples,
        mode='lines',
        line=dict(color='#4CAF50', width=1),
        name='Waveform'
    ))
    
    fig.update_layout(
        height=200,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=True, gridcolor='lightgray', zeroline=True),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    return fig

def download_from_youtube(url):
    """Download audio from YouTube URL"""
    try:
        with st.spinner("Downloading audio from YouTube..."):
            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            
            # Download using yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_path = ydl.prepare_filename(info)
                audio_path = audio_path.rsplit('.', 1)[0] + '.mp3'
            
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            
            # Clean up
            try:
                os.remove(audio_path)
            except:
                pass
            
            return audio, info.get('title', 'youtube_audio')
    
    except Exception as e:
        st.error(f"Error downloading from YouTube: {str(e)}")
        return None, None

def process_audio_file(uploaded_file):
    """Process uploaded audio file"""
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # Load audio
        audio = AudioSegment.from_file(tmp_path)
        
        # Clean up
        os.unlink(tmp_path)
        
        return audio, uploaded_file.name
    
    except Exception as e:
        st.error(f"Error processing audio file: {str(e)}")
        return None, None

def apply_fade(audio, fade_in_duration, fade_out_duration):
    """Apply fade in and fade out effects"""
    if fade_in_duration > 0:
        audio = audio.fade_in(int(fade_in_duration * 1000))
    if fade_out_duration > 0:
        audio = audio.fade_out(int(fade_out_duration * 1000))
    return audio

def apply_normalization(audio, target_dBFS):
    """Normalize audio to target dBFS"""
    return normalize(audio, headroom=target_dBFS)

def get_download_link(audio, filename, format='mp3'):
    """Generate download link for audio file"""
    # Export audio to bytes
    buffer = BytesIO()
    
    if format == 'mp3':
        audio.export(buffer, format='mp3', bitrate='192k')
        mime_type = 'audio/mpeg'
        file_ext = 'mp3'
    elif format == 'wav':
        audio.export(buffer, format='wav')
        mime_type = 'audio/wav'
        file_ext = 'wav'
    
    buffer.seek(0)
    
    # Create download link
    b64 = base64.b64encode(buffer.read()).decode()
    href = f'<a href="data:{mime_type};base64,{b64}" download="{filename}.{file_ext}">Download {file_ext.upper()}</a>'
    return href

def main():
    st.markdown('<h1 class="main-header">🎵 Audio Editor Pro</h1>', unsafe_allow_html=True)
    
    # Sidebar for input
    with st.sidebar:
        st.markdown('<h3 class="sub-header">📥 Input Source</h3>', unsafe_allow_html=True)
        
        input_method = st.radio(
            "Choose input method:",
            ["Upload Audio File", "YouTube URL"]
        )
        
        audio_loaded = False
        
        if input_method == "Upload Audio File":
            uploaded_file = st.file_uploader(
                "Upload audio file",
                type=['mp3', 'wav', 'm4a', 'ogg', 'flac']
            )
            
            if uploaded_file is not None:
                with st.spinner("Loading audio file..."):
                    audio, filename = process_audio_file(uploaded_file)
                    if audio is not None:
                        st.session_state.audio = audio
                        st.session_state.audio_file = filename
                        audio_loaded = True
        
        else:  # YouTube URL
            youtube_url = st.text_input("Enter YouTube URL:")
            if youtube_url:
                if st.button("Download from YouTube"):
                    audio, title = download_from_youtube(youtube_url)
                    if audio is not None:
                        st.session_state.audio = audio
                        st.session_state.audio_file = title or "youtube_audio"
                        audio_loaded = True
        
        # Audio info display
        if audio_loaded:
            st.markdown("---")
            st.markdown('<h4 class="sub-header">📊 Audio Info</h4>', unsafe_allow_html=True)
            
            duration = get_audio_duration(st.session_state.audio)
            channels = st.session_state.audio.channels
            sample_width = st.session_state.audio.sample_width
            frame_rate = st.session_state.audio.frame_rate
            
            st.write(f"**Duration:** {duration:.2f} seconds")
            st.write(f"**Channels:** {channels}")
            st.write(f"**Sample Width:** {sample_width * 8} bits")
            st.write(f"**Frame Rate:** {frame_rate} Hz")
            
            # Quick preview
            st.audio(st.session_state.audio.export(format='mp3').read())
    
    # Main editing interface
    if st.session_state.audio is not None:
        audio = st.session_state.audio
        duration = get_audio_duration(audio)
        
        st.markdown('<h3 class="sub-header">✂️ Audio Editing Tools</h3>', unsafe_allow_html=True)
        
        # Create tabs for different editing functions
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "✂️ Trim/Cut", "🎚️ Effects", "📊 Normalize", "🔊 Fade", "📈 Visualize"
        ])
        
        with tab1:
            st.markdown("**Trim Audio**")
            col1, col2 = st.columns(2)
            
            with col1:
                start_time = st.slider(
                    "Start time (seconds)",
                    0.0, duration, 0.0, 0.1,
                    key="trim_start"
                )
            
            with col2:
                end_time = st.slider(
                    "End time (seconds)",
                    0.0, duration, duration, 0.1,
                    key="trim_end"
                )
            
            if st.button("Apply Trim", key="trim_button"):
                if start_time < end_time:
                    st.session_state.edited_audio = audio[start_time * 1000:end_time * 1000]
                    st.success(f"Audio trimmed to {start_time:.1f}s - {end_time:.1f}s")
                else:
                    st.error("Start time must be less than end time")
        
        with tab2:
            st.markdown("**Audio Effects**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Volume adjustment
                volume_change = st.slider(
                    "Volume Change (dB)",
                    -20.0, 20.0, 0.0, 0.1
                )
                
                # Speed adjustment
                speed_factor = st.slider(
                    "Playback Speed",
                    0.5, 2.0, 1.0, 0.1
                )
            
            with col2:
                # High pass filter
                hp_freq = st.slider(
                    "High Pass Filter (Hz)",
                    20, 5000, 20, 10
                )
                
                # Low pass filter
                lp_freq = st.slider(
                    "Low Pass Filter (Hz)",
                    100, 20000, 20000, 100
                )
            
            if st.button("Apply Effects", key="effects_button"):
                edited = audio
                
                # Apply volume change
                if volume_change != 0:
                    edited = edited + volume_change
                
                # Apply speed change
                if speed_factor != 1.0:
                    edited = edited._spawn(
                        edited.raw_data,
                        overrides={
                            "frame_rate": int(edited.frame_rate * speed_factor)
                        }
                    )
                    edited = edited.set_frame_rate(audio.frame_rate)
                
                # Apply filters
                if hp_freq > 20:
                    edited = high_pass_filter(edited, hp_freq)
                if lp_freq < 20000:
                    edited = low_pass_filter(edited, lp_freq)
                
                st.session_state.edited_audio = edited
                st.success("Effects applied successfully!")
        
        with tab3:
            st.markdown("**Normalization & Compression**")
            
            target_level = st.slider(
                "Target Loudness (dBFS)",
                -30.0, -5.0, -20.0, 0.1
            )
            
            compression = st.checkbox("Apply Compression")
            
            if compression:
                threshold = st.slider(
                    "Compression Threshold (dBFS)",
                    -40.0, -10.0, -20.0, 1.0
                )
                ratio = st.slider(
                    "Compression Ratio",
                    1.0, 10.0, 4.0, 0.1
                )
            
            if st.button("Apply Normalization", key="norm_button"):
                edited = apply_normalization(audio, target_level)
                
                if compression:
                    # Simple compression using pydub
                    edited = compress_dynamic_range(edited, threshold=threshold, ratio=ratio)
                
                st.session_state.edited_audio = edited
                st.success("Normalization applied successfully!")
        
        with tab4:
            st.markdown("**Fade In/Out Effects**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                fade_in = st.slider(
                    "Fade In Duration (seconds)",
                    0.0, 10.0, 0.0, 0.1
                )
            
            with col2:
                fade_out = st.slider(
                    "Fade Out Duration (seconds)",
                    0.0, 10.0, 0.0, 0.1
                )
            
            if st.button("Apply Fade", key="fade_button"):
                edited = apply_fade(audio, fade_in, fade_out)
                st.session_state.edited_audio = edited
                st.success(f"Fade In: {fade_in}s, Fade Out: {fade_out}s applied!")
        
        with tab5:
            st.markdown("**Audio Visualization**")
            
            # Display waveform
            current_audio = st.session_state.edited_audio if st.session_state.edited_audio else audio
            fig = plot_waveform(current_audio)
            st.plotly_chart(fig, use_container_width=True)
            
            # Audio spectrum analysis option
            if st.button("Generate Spectrum Analysis", key="spectrum_button"):
                with st.spinner("Generating spectrum..."):
                    # Simple spectrum visualization
                    samples = np.array(current_audio.get_array_of_samples())
                    if len(samples) > 0:
                        # Take FFT
                        fft_result = np.fft.fft(samples[:min(len(samples), 44100)])
                        freq = np.fft.fftfreq(len(fft_result), 1/44100)
                        
                        fig2 = go.Figure()
                        fig2.add_trace(go.Scatter(
                            x=freq[:len(freq)//2],
                            y=np.abs(fft_result[:len(freq)//2]),
                            mode='lines',
                            line=dict(color='#FF5722', width=1)
                        ))
                        
                        fig2.update_layout(
                            title="Frequency Spectrum",
                            xaxis_title="Frequency (Hz)",
                            yaxis_title="Magnitude",
                            height=300
                        )
                        
                        st.plotly_chart(fig2, use_container_width=True)
        
        # Audio player section
        st.markdown("---")
        st.markdown('<h3 class="sub-header">🎧 Preview & Download</h3>', unsafe_allow_html=True)
        
        # Determine which audio to display
        display_audio = st.session_state.edited_audio if st.session_state.edited_audio else audio
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Original Audio**")
            st.audio(audio.export(format='mp3').read())
        
        with col2:
            st.markdown("**Edited Audio**")
            st.audio(display_audio.export(format='mp3').read())
        
        # Download section
        st.markdown("---")
        st.markdown('<h4 class="sub-header">💾 Download Options</h4>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            filename = st.text_input(
                "Download filename",
                value=Path(st.session_state.audio_file).stem + "_edited"
            )
        
        with col2:
            format_choice = st.selectbox(
                "Format",
                ["mp3", "wav"]
            )
        
        # Generate download links
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Download Original**")
            original_link = get_download_link(audio, filename + "_original", format_choice)
            st.markdown(original_link, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Download Edited**")
            edited_link = get_download_link(display_audio, filename, format_choice)
            st.markdown(edited_link, unsafe_allow_html=True)
        
        # Reset button
        if st.button("Reset All Edits", type="secondary"):
            st.session_state.edited_audio = None
            st.rerun()
    
    else:
        # Welcome screen when no audio loaded
        st.markdown("""
        <div style='text-align: center; padding: 50px;'>
            <h2>Welcome to Audio Editor Pro! 🎵</h2>
            <p style='font-size: 1.2rem;'>
                Upload an audio file or paste a YouTube link to start editing.
            </p>
            <div style='margin-top: 30px;'>
                <p><strong>Supported Features:</strong></p>
                <ul style='text-align: left; display: inline-block;'>
                    <li>Trim and cut audio segments</li>
                    <li>Apply audio effects (volume, speed, filters)</li>
                    <li>Normalize and compress audio</li>
                    <li>Add fade in/out effects</li>
                    <li>Visualize audio waveform</li>
                    <li>Export in MP3 or WAV format</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick demo option
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col2:
            if st.button("🎵 Try Sample Audio", type="primary"):
                # Create a simple demo audio
                from pydub.generators import Sine
                st.info("Loading sample audio...")
                
                # Generate a simple tone
                tone = Sine(440).to_audio_segment(duration=3000)  # 3 second tone
                st.session_state.audio = tone
                st.session_state.audio_file = "sample_tone"
                st.rerun()

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
            <p>Audio Editor Pro | Made with Streamlit</p>
            <p>Note: For YouTube downloads, please ensure you have the rights to use the content.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
