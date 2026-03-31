import streamlit as st
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import io

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

LABEL_SPECS = {
    "명함 (4X5cm / 24칸)": {
        "WIDTH": 50.0, "HEIGHT": 40.0, "MARGIN_LEFT": 5.0, "MARGIN_TOP": 21.0,
        "GAP_V": 2.94, "GAP_H": 0.0, "COLS": 4, "ROWS": 6, "MAX": 24
    },
    "반명함 (3.5X4.5cm / 30칸)": {
        "WIDTH": 35.0, "HEIGHT": 45.0, "MARGIN_LEFT": 13.5, "MARGIN_TOP": 11.5,
        "GAP_V": 0.0, "GAP_H": 2.95, "COLS": 5, "ROWS": 6, "MAX": 30
    }
}

st.set_page_config(page_title="프레임 노트", layout="wide")

if 'persistent_files' not in st.session_state:
    st.session_state.persistent_files = []
if 'settings' not in st.session_state:
    st.session_state.settings = {}
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'overview'
if 'edit_target_idx' not in st.session_state:
    st.session_state.edit_target_idx = 0


@st.cache_data
def process_image_assets(file_bytes):
    try:
        img = Image.open(io.BytesIO(file_bytes))
        original = ImageOps.exif_transpose(img)
        
        ui_preview = original.copy()
        ui_preview.thumbnail((600, 600), Image.Resampling.LANCZOS)
        
        return original, ui_preview
    except Exception:
        return None, None


def get_auto_rotation(img_w, img_h, frame_w, frame_h):
    if frame_w < frame
