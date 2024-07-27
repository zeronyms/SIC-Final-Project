import streamlit as st
import requests
from PIL import Image
from io import BytesIO

FLASK_SERVER_URL = 'http://127.0.0.1:5000'

def get_rtsp_url():
    response = requests.get(f'{FLASK_SERVER_URL}/get-rtsp')
    return response.json().get('url')

def update_rtsp_url(url):
    response = requests.post(f'{FLASK_SERVER_URL}/update-rtsp', json={'url': url})
    return response.json()

def process_rtsp_stream(url):
    response = requests.post(f'{FLASK_SERVER_URL}/process-rtsp', json={'rtsp_url': url}, stream=True)
    return response

def display_rtsp_url():
    rtsp_url = get_rtsp_url()
    if rtsp_url:
        url_placeholder.write(f"RTSP URL: {rtsp_url}")
    else:
        url_placeholder.write("Waiting for the RTSP URL...")

def is_valid_jpeg(buf):
    """Check if the buffer contains a valid JPEG image."""
    return buf.startswith(b'\xff\xd8') and buf.endswith(b'\xff\xd9')

# ==================================== Layout =========================================

st.title("Drowsiness Detection (Drow Ranger)")

# URL display section
url_placeholder = st.empty()
display_rtsp_url()

# Button
process_button = st.button('Process RTSP Stream')
refresh_button = st.button('Refresh')

# Placeholder for frame
frame_placeholder = st.empty()

if process_button:
    rtsp_url = get_rtsp_url()
    if rtsp_url:
        response = process_rtsp_stream(rtsp_url)
        if response.status_code == 200:
            st.write("Stream started")
            status_text = st.empty() 
            
            buffer = b""
            incomplete_counter = 0 

            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    buffer += chunk
                    start = buffer.find(b'\xff\xd8')
                    end = buffer.find(b'\xff\xd9')
                    
                    if start != -1 and end != -1 and start < end:
                        jpeg_data = buffer[start:end + 2]
                        buffer = buffer[end + 2:]
                        try:
                            img = Image.open(BytesIO(jpeg_data))
                            frame_placeholder.image(img, caption="Processed Frame with Bounding Boxes", use_column_width=True)
                            status_text.empty()
                            incomplete_counter = 0
                        except Exception as e:
                            st.write(f"Error loading image: {e}")
                    elif end != -1:
                        buffer = buffer[end + 2:]
                    else:
                        incomplete_counter += 1
                        if incomplete_counter % 10 == 0:
                            status_text.warning("Incomplete image data, accumulating more chunks...")
        else:
            st.error("Failed to process stream. Error: " + response.json().get("error", "Unknown error"))

if refresh_button:
    url_placeholder.empty()
    display_rtsp_url()
