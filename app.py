import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics import renderPDF
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO

st.set_page_config(page_title="CustomLabel Generator", layout="wide")
st.title("🖨️ Custom Label Generator")
st.write("Create warehouse labels with optional barcode + 4-line address. Choose size, preview, batch count, and numbering sequence.")

# === State Management ===
if 'label_width' not in st.session_state:
    st.session_state.label_width = 4.0  # inches
if 'label_height' not in st.session_state:
    st.session_state.label_height = 3.0
if 'batch_count' not in st.session_state:
    st.session_state.batch_count = 1

# === Sidebar: Size, Batch & Sequence Controls ===
with st.sidebar:
    st.header("📏 Label Dimensions")
    width_in = st.number_input("Width (inches)", min_value=1.0, max_value=10.0, value=st.session_state.label_width, step=0.5)
    height_in = st.number_input("Height (inches)", min_value=1.0, max_value=10.0, value=st.session_state.label_height, step=0.5)
    
    st.header("🔢 Batch & Sequence")
    batch = st.number_input("Number of Labels", min_value=1, max_value=1000, value=1, step=1)
    
    st.divider()
    
    # Sequence Controls
    st.subheader("🔢 Numbering Sequence")
    use_sequence = st.checkbox("Enable Number Sequence", value=False)
    
    seq_start = 1
    seq_step = 1
    
    if use_sequence:
        col_seq1, col_seq2 = st.columns(2)
        with col_seq1:
            seq_start = st.number_input("Start At", min_value=0, value=1, step=1)
        with col_seq2:
            seq_step = st.number_input("Step (Skip)", min_value=1, value=1, step=1)
        
        # Preview the sequence
        sample_nums = [seq_start + (i * seq_step) for i in range(min(5, batch))]
        st.info(f"Preview: {', '.join(map(str, sample_nums))}...")

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
    line1 = st.text_input("Line 1 (e.g., Address)", value="18 Wheels")
    line2 = st.text_input("Line 2 (e.g., City)", value="Re-sticker")
    line3 = st.text_input("Line 3 (e.g., Postal Code)", value="Completed")
    line4_base = st.text_input("Line 4 (e.g., Country / Suffix)", value="")

if st.button("📄 Generate PDF"):
    if not barcode_val and not any([line1, line2, line3, line4_base]):
        st.warning("⚠️ Please enter either a barcode or at least one text line.")
    else:
        buffer = BytesIO()
        w = st.session_state.label_width * inch
        h = st.session_state.label_height * inch
        c = canvas.Canvas(buffer, pagesize=(w, h))

        TEXT_FONT_SIZE = 29  # Large and readable for warehouse!
        BARCODE_HUMAN_FONT_SIZE = 14

        total_labels = st.session_state.batch_count

        for label_idx in range(total_labels):
            if label_idx > 0:
                c.showPage()

            # Calculate Sequence Number if enabled
            current_suffix = ""
            if use_sequence:
                current_num = seq_start + (label_idx * seq_step)
                current_suffix = str(current_num)

            # Construct final lines list
            # We take the base inputs, and if sequence is on, we append/add the number to Line 4
            final_lines = []
            
            # Add static lines if they exist
            if line1.strip(): final_lines.append(line1.strip())
            if line2.strip(): final_lines.append(line2.strip())
            if line3.strip(): final_lines.append(line3.strip())
            
            # Handle Line 4 logic
            line4_content = line4_base.strip()
            if use_sequence:
                if line4_content:
                    # Combine existing Line 4 text with the number (e.g., "Canada 5")
                    line4_content = f"{line4_content} {current_suffix}"
                else:
                    # If Line 4 was empty, just use the number
                    line4_content = current_suffix
            
            if line4_content:
                final_lines.append(line4_content)

            # Start drawing text from near the top
            y_position = h - 1.3 * inch

            # --- Draw centered, large, bold text lines ---
            if final_lines:
                for line in final_lines:
                    # Allow text very close to bottom (only stop if overlapping barcode zone)
                    if y_position < 0.25 * inch:
                        break
                    text_width = stringWidth(line, 'Helvetica-Bold', TEXT_FONT_SIZE)
                    x_centered = (w - text_width) / 2
                    c.setFont("Helvetica-Bold", TEXT_FONT_SIZE)
                    c.drawString(x_centered, y_position, line)
                    y_position -= 0.68 * inch  # Adjusted spacing for 29pt

            # --- Draw Barcode (centered below text, if provided) ---
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
                    # Ensure barcode doesn't overlap text if text runs low
                    y_bc = max(0.7 * inch, y_position - 0.3 * inch)

                    renderPDF.draw(barcode_obj, c, x_bc, y_bc)

                    # Human-readable barcode
                    human_text = barcode_val
                    text_w = stringWidth(human_text, 'Helvetica-Bold', BARCODE_HUMAN_FONT_SIZE)
                    c.setFont("Helvetica-Bold", BARCODE_HUMAN_FONT_SIZE)
                    c.drawString((w - text_w) / 2, y_bc - 0.2 * inch, human_text)

                except Exception as e:
                    st.error(f"Barcode error: {e}")

        c.save()
        buffer.seek(0)

        st.success(f"✅ Generated {total_labels} label(s) at {width_in:.1f}″ × {height_in:.1f}″")
        
        filename_suffix = "_sequenced" if use_sequence else ""
        st.download_button(
            "⬇️ Download PDF",
            buffer,
            f"warehouse_labels_{width_in}x{height_in}{filename_suffix}.pdf",
            "application/pdf"
        )
