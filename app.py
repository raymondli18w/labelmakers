import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics import renderPDF
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO

st.set_page_config(page_title="CustomLabel Generator", layout="wide")
st.title("🖨️ Custom Label Generator")
st.write("Create warehouse labels with optional barcode + 4-line address. Choose size, preview, and batch count.")

# === State Management ===
if 'label_width' not in st.session_state:
    st.session_state.label_width = 4.0  # inches
if 'label_height' not in st.session_state:
    st.session_state.label_height = 3.0
if 'batch_count' not in st.session_state:
    st.session_state.batch_count = 1

# === Sidebar: Size & Batch Controls ===
with st.sidebar:
    st.header("📏 Label Dimensions")
    width_in = st.number_input("Width (inches)", min_value=1.0, max_value=10.0, value=st.session_state.label_width, step=0.5)
    height_in = st.number_input("Height (inches)", min_value=1.0, max_value=10.0, value=st.session_state.label_height, step=0.5)
    batch = st.number_input("Number of Labels", min_value=1, max_value=1000, value=1, step=1)

    st.session_state.label_width = width_in
    st.session_state.label_height = height_in
    st.session_state.batch_count = batch

    # Preview box (proportional)
    ratio = min(200 / max(width_in, height_in), 150)
    preview_w = int(width_in * ratio)
    preview_h = int(height_in * ratio)
    st.markdown(f"### 🖼️ Preview ({width_in:.1f}″ × {height_in:.1f}″)")
    st.markdown(
        f'<div style="width:{preview_w}px; height:{preview_h}px; border:2px dashed #666; background:#f9f9f9; margin:10px 0;"></div>',
        unsafe_allow_html=True
    )

# === Main Form ===
st.subheader("🔤 Label Content")
col1, col2 = st.columns([2, 3])

with col1:
    barcode_val = st.text_input("📦 Barcode (Optional)", help="Leave blank to skip barcode")
with col2:
    line1 = st.text_input("Line 1 (e.g., Address)")
    line2 = st.text_input("Line 2 (e.g., City)")
    line3 = st.text_input("Line 3 (e.g., Postal Code)")
    line4 = st.text_input("Line 4 (e.g., Country)")

# Combine non-empty lines
text_lines = [line.strip() for line in [line1, line2, line3, line4] if line.strip()]

if st.button("📄 Generate PDF"):
    if not barcode_val and not text_lines:
        st.warning("⚠️ Please enter either a barcode or at least one text line.")
    else:
        buffer = BytesIO()
        w = st.session_state.label_width * inch
        h = st.session_state.label_height * inch
        c = canvas.Canvas(buffer, pagesize=(w, h))

        TEXT_FONT_SIZE = 16  # Large and readable!
        BARCODE_HUMAN_FONT_SIZE = 12

        total_labels = st.session_state.batch_count

        for label_idx in range(total_labels):
            if label_idx > 0:
                c.showPage()

            y_position = h - 0.3 * inch  # Start near top

            # --- Draw centered, large, bold text lines ---
            if text_lines:
                for line in text_lines:
                    if y_position < 0.8 * inch:  # Stop if too low (barcode needs space)
                        break
                    text_width = stringWidth(line, 'Helvetica-Bold', TEXT_FONT_SIZE)
                    x_centered = (w - text_width) / 2
                    c.setFont("Helvetica-Bold", TEXT_FONT_SIZE)
                    c.drawString(x_centered, y_position, line)
                    y_position -= 0.32 * inch  # Spacing between lines

            # --- Draw Barcode (centered horizontally, below text) ---
            if barcode_val:
                try:
                    barcode_obj = createBarcodeDrawing(
                        'Code128',
                        value=barcode_val,
                        barWidth=0.022 * inch,
                        barHeight=0.6 * inch,
                        humanReadable=False,
                        quietZone=0.12 * inch
                    )

                    MAX_BARCODE_WIDTH = w - 0.6 * inch
                    if barcode_obj.width > MAX_BARCODE_WIDTH:
                        scale = MAX_BARCODE_WIDTH / barcode_obj.width
                        barcode_obj.scale(scale, 1)
                        barcode_obj.width = MAX_BARCODE_WIDTH

                    x_bc = (w - barcode_obj.width) / 2
                    y_bc = max(0.7 * inch, y_position - 0.4 * inch)  # Ensure it doesn't overlap text

                    renderPDF.draw(barcode_obj, c, x_bc, y_bc)

                    # Optional: human-readable barcode below bars
                    human_text = barcode_val
                    text_w = stringWidth(human_text, 'Helvetica-Bold', BARCODE_HUMAN_FONT_SIZE)
                    c.setFont("Helvetica-Bold", BARCODE_HUMAN_FONT_SIZE)
                    c.drawString((w - text_w) / 2, y_bc - 0.2 * inch, human_text)

                except Exception as e:
                    st.error(f"Barcode error: {e}")

        c.save()
        buffer.seek(0)

        st.success(f"✅ Generated {total_labels} label(s) at {width_in:.1f}″ × {height_in:.1f}″")
        st.download_button(
            "⬇️ Download PDF",
            buffer,
            f"warehouse_labels_{width_in}x{height_in}.pdf",
            "application/pdf"
        )
