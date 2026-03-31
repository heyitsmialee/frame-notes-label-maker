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

st.markdown("""
<style>
    .stButton>button {
        border-radius: 4px;
        border: 1px solid #D1C7B7;
        background-color: transparent;
        color: #3E3A39;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        border-color: #8B7355;
        color: #8B7355;
    }
    img {
        border-radius: 2px;
        box-shadow: 2px 4px 12px rgba(0, 0, 0, 0.08);
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

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
        
        original.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        
        ui_preview = original.copy()
        # 해상도를 250에서 375로 50% 상향 조정
        ui_preview.thumbnail((375, 375), Image.Resampling.LANCZOS)
        
        return original, ui_preview
    except Exception:
        return None, None

def get_auto_rotation(img_w, img_h, frame_w, frame_h):
    if frame_w < frame_h and img_w > img_h:
        return 90
    elif frame_w > frame_h and img_w < img_h:
        return 90
    return 0

def precision_crop(img, frame_w, frame_h, rotation, scale, off_x, off_y):
    if img is None:
        return None
    if rotation != 0:
        img = img.rotate(-rotation, expand=True)
        
    img_w, img_h = img.size
    target_ratio = frame_w / frame_h
    img_ratio = img_w / img_h
    
    if img_ratio > target_ratio:
        base_w, base_h = int(img_h * target_ratio), img_h
    else:
        base_w, base_h = img_w, int(img_w / target_ratio)
        
    crop_w, crop_h = int(base_w / scale), int(base_h / scale)
    max_dx = max(0, (img_w - crop_w) / 2)
    max_dy = max(0, (img_h - crop_h) / 2)
    
    left = (img_w / 2) - (crop_w / 2) + (off_x * max_dx)
    top = (img_h / 2) - (crop_h / 2) + (off_y * max_dy)
    
    return img.crop((int(left), int(top), int(left + crop_w), int(top + crop_h)))

st.title("프레임 노트")
st.markdown("기록의 온도를 높여주는 나만의 사진 편집기")

selected_model = st.selectbox("어떤 라벨지를 사용하시나요?", list(LABEL_SPECS.keys()))
spec = LABEL_SPECS[selected_model]
st.caption(f"이 라벨지는 한 장에 최대 {spec['MAX']}개의 사진을 담을 수 있어요.")

uploaded_files = st.file_uploader(
    "이곳에 사진을 올려주세요",
    type=['png', 'jpg', 'jpeg', 'heic', 'heif'],
    accept_multiple_files=True
)

if uploaded_files:
    st.session_state.persistent_files = uploaded_files

if st.session_state.persistent_files:
    current_files = st.session_state.persistent_files[:spec['MAX']]

    for idx, file in enumerate(current_files):
        if idx not in st.session_state.settings:
            _, ui_img = process_image_assets(file.getvalue())
            auto_rot = 0
            if ui_img:
                auto_rot = get_auto_rotation(ui_img.width, ui_img.height, spec['WIDTH'], spec['HEIGHT'])
            st.session_state.settings[idx] = {"rot": auto_rot, "sc": 1.0, "x": 0.0, "y": 0.0}

    if st.session_state.current_view == 'overview':
        st.subheader("이런 모습으로 인쇄될 예정이에요")
        for i in range(0, len(current_files), spec['COLS']):
            cols = st.columns(spec['COLS'])
            for j in range(spec['COLS']):
                idx = i + j
                if idx < len(current_files):
                    file = current_files[idx]
                    cfg = st.session_state.settings[idx]
                    _, ui_img = process_image_assets(file.getvalue())
                    thumb = precision_crop(ui_img, spec['WIDTH'], spec['HEIGHT'],
                                           cfg["rot"], cfg["sc"], cfg["x"], cfg["y"])
                    with cols[j]:
                        if thumb:
                            st.image(thumb, use_container_width=True)
                            if st.button("수정", key=f"edit_btn_{idx}"):
                                st.session_state.edit_target_idx = idx
                                st.session_state.current_view = 'edit'
                                st.rerun()
                    st.markdown('<div style="margin-bottom:12px;"></div>', unsafe_allow_html=True)

        st.divider()
        if st.button("인쇄용 피디에프 파일 생성", use_container_width=True):
            with st.spinner("예쁘게 구워내는 중이에요..."):
                pdf_buffer = io.BytesIO()
                p = canvas.Canvas(pdf_buffer, pagesize=A4)
                h_a4 = A4[1]
                for idx, file in enumerate(current_files):
                    cfg = st.session_state.settings[idx]
                    original_img, _ = process_image_assets(file.getvalue())
                    final = precision_crop(original_img, spec['WIDTH'], spec['HEIGHT'],
                                           cfg["rot"], cfg["sc"], cfg["x"], cfg["y"])
                    if final:
                        r, c = divmod(idx, spec['COLS'])
                        x_pos = (spec['MARGIN_LEFT'] + (c * (spec['WIDTH'] + spec['GAP_H']))) * mm
                        y_pos = h_a4 - ((spec['MARGIN_TOP'] + (r * (spec['HEIGHT'] + spec['GAP_V'])) + spec['HEIGHT']) * mm)
                        
                        final.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        if final.mode in ("RGBA", "P"):
                            final = final.convert("RGB")
                        
                        img_io = io.BytesIO()
                        final.save(img_io, format='JPEG', quality=90)
                        img_io.seek(0)
                        
                        from reportlab.lib.utils import ImageReader
                        p.drawImage(ImageReader(img_io), x_pos, y_pos, width=spec['WIDTH'] * mm, height=spec['HEIGHT'] * mm)
                p.showPage()
                p.save()
                st.success("완성되었어요. 이제 다운로드할 수 있어요.")
                st.download_button(
                    label="완성된 파일 다운로드",
                    data=pdf_buffer.getvalue(),
                    file_name="FrameNotes_Result.pdf",
                    mime="application/pdf"
                )

    elif st.session_state.current_view == 'edit':
        curr_idx = st.session_state.edit_target_idx
        st.subheader(f"사진 {curr_idx + 1} 다듬기")
        
        s = st.session_state.settings[curr_idx]
        _, ui_img = process_image_assets(current_files[curr_idx].getvalue())

        preview_placeholder = st.empty()
            
        if st.button("↻ 90도 회전", use_container_width=True):
            s["rot"] = (s["rot"] + 90) % 360
            s["sc"] = 1.0
            s["x"] = 0.0
            s["y"] = 0.0
            st.rerun()

        st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)

        s["sc"] = st.slider("확대", 1.0, 5.0, float(s["sc"]), 0.1)
        s["x"] = st.slider("좌우 이동", -1.0, 1.0, float(s["x"]), 0.01)
        s["y"] = st.slider("상하 이동", -1.0, 1.0, float(s["y"]), 0.01)
        
        final_view = precision_crop(ui_img, spec['WIDTH'], spec['HEIGHT'],
                                    s["rot"], s["sc"], s["x"], s["y"])
        if final_view:
            preview_placeholder.image(final_view, use_container_width=True)
                
        if st.button("완료하고 돌아가기", use_container_width=True):
            st.session_state.current_view = 'overview'
            st.rerun()

else:
    st.info("시작하려면 사진을 먼저 올려주세요. 다이어리를 위한 포토 스티커를 만들어보아요.")
