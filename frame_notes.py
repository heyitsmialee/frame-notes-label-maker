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
    "클래식 라벨 846 (24칸)": {
        "WIDTH": 50.0, "HEIGHT": 40.0, "MARGIN_LEFT": 5.0, "MARGIN_TOP": 21.0,
        "GAP_V": 2.94, "GAP_H": 0.0, "COLS": 4, "ROWS": 6, "MAX": 24
    },
    "슬림 저널 456 (30칸)": {
        "WIDTH": 35.0, "HEIGHT": 45.0, "MARGIN_LEFT": 13.5, "MARGIN_TOP": 11.5,
        "GAP_V": 0.0, "GAP_H": 2.95, "COLS": 5, "ROWS": 6, "MAX": 30
    }
}

st.set_page_config(page_title="프레임 노트", layout="wide")

if 'persistent_files' not in st.session_state:
    st.session_state.persistent_files = []
if 'settings' not in st.session_state:
    st.session_state.settings = {}


@st.cache_data
def load_and_fix_image(file_data):
    try:
        img = Image.open(file_data)
        return ImageOps.exif_transpose(img)
    except Exception:
        return None


def precision_crop(img, frame_w, frame_h, rotation, scale, off_x, off_y):
    if img is None: return None

    if rotation != 0:
        img = img.rotate(rotation, expand=True)

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

st.sidebar.header("인쇄 설정")
selected_model = st.sidebar.selectbox("어떤 라벨지를 사용하시나요", list(LABEL_SPECS.keys()))
spec = LABEL_SPECS[selected_model]
st.sidebar.divider()
st.sidebar.caption(f"한 장에 최대 {spec['MAX']}개의 사진을 담을 수 있어요.")

uploaded_files = st.file_uploader(
    f"이곳에 사진을 올려주세요 (최대 {spec['MAX']}장)",
    type=['png', 'jpg', 'jpeg', 'heic', 'heif'],
    accept_multiple_files=True
)

if uploaded_files:
    st.session_state.persistent_files = uploaded_files

if st.session_state.persistent_files:
    current_files = st.session_state.persistent_files[:spec['MAX']]

    tab_view, tab_refine = st.tabs(["전체 모아보기", "사진 하나씩 다듬기"])

    with tab_view:
        st.subheader("이런 모습으로 인쇄될 예정이에요")
        grid = st.columns(spec['COLS'])

        for idx, file in enumerate(current_files):
            cfg = st.session_state.settings.get(idx, {"rot": 0, "sc": 1.0, "x": 0.0, "y": 0.0})
            src = load_and_fix_image(file)
            thumb = precision_crop(src, spec['WIDTH'], spec['HEIGHT'],
                                   cfg["rot"], cfg["sc"], cfg["x"], cfg["y"])

            with grid[idx % spec['COLS']]:
                if thumb:
                    st.image(thumb, use_container_width=True)
                    st.caption(f"사진 {idx + 1}")
                st.markdown('<div style="margin-bottom:12px;"></div>', unsafe_allow_html=True)

    with tab_refine:
        asset_list = [f"{i + 1}번 사진 ({f.name})" for i, f in enumerate(current_files)]
        selected_asset = st.selectbox("어떤 사진을 수정해볼까요", asset_list)
        curr_idx = asset_list.index(selected_asset)

        if curr_idx not in st.session_state.settings:
            st.session_state.settings[curr_idx] = {"rot": 0, "sc": 1.0, "x": 0.0, "y": 0.0}

        st.divider()
        col_ctrl, _, col_preview = st.columns([1, 0.1, 0.8])

        s = st.session_state.settings[curr_idx]
        source_img = load_and_fix_image(current_files[curr_idx])

        with col_ctrl:
            st.subheader("원하는 느낌으로 조절해보세요")

            if st.button("90도 회전", key=f"r_btn_{curr_idx}"):
                s["rot"] = (s["rot"] + 90) % 360
                st.rerun()

            s["sc"] = st.slider("사진 확대", 1.0, 5.0, float(s["sc"]), 0.1, key=f"sc_f_{curr_idx}")
            s["x"] = st.slider("좌우로 위치 이동", -1.0, 1.0, float(s["x"]), 0.01, key=f"x_f_{curr_idx}")
            s["y"] = st.slider("위아래로 위치 이동", -1.0, 1.0, float(s["y"]), 0.01, key=f"y_f_{curr_idx}")

        with col_preview:
            st.subheader("미리보기")
            final_view = precision_crop(source_img, spec['WIDTH'], spec['HEIGHT'],
                                        s["rot"], s["sc"], s["x"], s["y"])
            if final_view:
                st.image(final_view, width=300)

    st.divider()
    if st.button("인쇄용 PDF 파일 만들기", use_container_width=True):
        with st.spinner("예쁘게 구워내는 중이에요..."):
            pdf_buffer = io.BytesIO()
            p = canvas.Canvas(pdf_buffer, pagesize=A4)
            h_a4 = A4[1]

            for idx, file in enumerate(current_files):
                cfg = st.session_state.settings.get(idx, {"rot": 0, "sc": 1.0, "x": 0.0, "y": 0.0})
                src = load_and_fix_image(file)
                final = precision_crop(src, spec['WIDTH'], spec['HEIGHT'],
                                       cfg["rot"], cfg["sc"], cfg["x"], cfg["y"])

                if final:
                    r, c = divmod(idx, spec['COLS'])
                    x_pos = (spec['MARGIN_LEFT'] + (c * (spec['WIDTH'] + spec['GAP_H']))) * mm
                    y_pos = h_a4 - ((spec['MARGIN_TOP'] + (r * (spec['HEIGHT'] + spec['GAP_V'])) + spec['HEIGHT']) * mm)

                    img_data = io.BytesIO()
                    final.save(img_io := io.BytesIO(), format='PNG', optimize=True)
                    img_io.seek(0)
                    from reportlab.lib.utils import ImageReader

                    p.drawImage(ImageReader(img_io), x_pos, y_pos, width=spec['WIDTH'] * mm, height=spec['HEIGHT'] * mm)

            p.showPage()
            p.save()

            st.success("완성되었어요. 이제 인쇄할 수 있어요.")
            st.download_button(
                label="완성된 PDF 다운로드",
                data=pdf_buffer.getvalue(),
                file_name=f"FrameNotes_{selected_model.split()[0]}.pdf",
                mime="application/pdf"
            )
else:
    st.info("시작하려면 사진을 먼저 올려주세요. 다이어리를 위한 예쁜 라벨을 만들어보아요.")