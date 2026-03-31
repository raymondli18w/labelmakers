import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics import renderPDF
from reportlab.pdfbase.pdfmetrics import stringWidth
from io import BytesIO

st.set_page_config(page_title="CustomLabel Generator", layout="wide")
st.title("🖨️ Custom Label Generator")
st.write("Create warehouse labels. Use 'Maximize Text' to fill the entire label with large, centered text.")

# === State Management ===
if 'label_width' not in st.session_state:
    st.session_state.label_width = 4.0
if 'label_height' not in st.session_state:
    st.session_state.label_height = 3.0
if 'batch_count' not in st.session_state:
    st.session_state.batch_count = 1

# === Sidebar: Controls ===
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
        
        sample_nums = [seq_start + (i * seq_step) for i in range(min(5, batch))]
        st.info(f"Preview: {', '.join(map(str, sample_nums))}...")

    st.divider()
    
    # Maximize Text Option
    st.subheader("🔍 Layout Options")
    maximize_text = st.checkbox("✨ Maximize Text (Fill Label)", value=False, help="Calculates largest font size to fit text perfectly in the center. Hides barcode if enabled.")

    st.session_state.label_width = width_in
    st.session_state.label_height = height_in
    st.session_state.batch_count = batch

    # Preview box
    ratio = min(200 / max(width_in, height_in), 150)
    preview_w = int(width_in * ratio)
    preview_h = int(height_in * ratio)
    preview_label = "MAX FILL" if maximize_text else "Standard"
    st.markdown(f"### 🖼️ Preview ({width_in:.1f}″ × {height_in:.1f}″)")
    st.markdown(
        f'<div style="width:{preview_w}px; height:{preview_h}px; border:2px dashed #666; background:#f9f9f9; margin:10px 0; display:flex; align-items:center; justify-content:center; color:#aaa;">{preview_label}</div>',
        unsafe_allow_html=True
    )

# === Main Form ===
st.subheader("🔤 Label Content")
col1, col2 = st.columns([2, 3])

with col1:
    barcode_val = st.text_input("📦 Barcode (Optional)", help="Leave blank to skip barcode. Note: Hidden if 'Maximize Text' is on.")
with col2:
    line1 = st.text_input("Line 1", value="18 Wheels")
    line2 = st.text_input("Line 2", value="Re-sticker")
    line3 = st.text_input("Line 3", value="Completed")
    line4_base = st.text_input("Line 4 (Suffix)", value="")

if st.button("📄 Generate PDF"):
    # Validation
    has_text = any([line1, line2, line3, line4_base])
    if not barcode_val and not has_text:
        st.warning("⚠️ Please enter either a barcode or at least one text line.")
    else:
        buffer = BytesIO()
        w = st.session_state.label_width * inch
        h = st.session_state.label_height * inch
        c = canvas.Canvas(buffer, pagesize=(w, h))

        # Standard settings
        STD_FONT_SIZE = 29
        BARCODE_HUMAN_FONT_SIZE = 14
        
        # If maximizing, we force barcode off to prevent overlap issues
        draw_barcode = bool(barcode_val) and not maximize_text

        total_labels = st.session_state.batch_count

        for label_idx in range(total_labels):
            if label_idx > 0:
                c.showPage()

            # --- 1. Prepare Content ---
            current_suffix = ""
            if use_sequence:
                current_num = seq_start + (label_idx * seq_step)
                current_suffix = str(current_num)

            final_lines = []
            if line1.strip():
                final_lines.append(line1.strip())
            if line2.strip():
                final_lines.append(line2.strip())
            if line3.strip():
                final_lines.append(line3.strip())
            
            line4_content = line4_base.strip()
            if use_sequence:
                if line4_content:
                    line4_content = f"{line4_content} {current_suffix}"
                else:
                    line4_content = current_suffix
            
            if line4_content:
                final_lines.append(line4_content)

            # --- 2. Drawing Logic ---
            
            if maximize_text and final_lines:
                # === MAXIMIZE MODE ===
                # Margins (keep text slightly inside edges)
                margin_x = 0.15 * inch
                margin_y = 0.15 * inch
                available_w = w - (2 * margin_x)
                available_h = h - (2 * margin_y)
                
                # Find best font size
                font_size = 200.0 
                step_down = 10.0
                best_font_size = 12.0
                
                while font_size > 10:
                    # Check Width (based on the longest line)
                    max_line_width = 0
                    for line in final_lines:
                        lw = stringWidth(line, 'Helvetica-Bold', font_size)
                        if lw > max_line_width:
                            max_line_width = lw
                    
                    # Check Height (approximate based on lines * line_height_factor)
                    total_text_h = len(final_lines) * font_size * 1.15 
                    
                    if max_line_width <= available_w and total_text_h <= available_h:
                        best_font_size = font_size
                        font_size -= 1.0 # Fine tune
                    else:
                        font_size -= step_down
                        
                    if font_size < best_font_size - 20:
                         step_down = 1.0

                # Draw Centered
                c.setFont("Helvetica-Bold", best_font_size)
                
                # Calculate total block height for vertical centering
                line_height = best_font_size * 1.15
                total_block_h = len(final_lines) * line_height
                start_y = (h - total_block_h) / 2 + (line_height * 0.8)
                
                for line in final_lines:
                    text_w = stringWidth(line, 'Helvetica-Bold', best_font_size)
                    x_centered = (w - text_w) / 2
                    c.drawString(x_centered, start_y, line)
                    start_y -= line_height

            else:
                # === STANDARD MODE ===
                y_position = h - 1.3 * inch
                
                if final_lines:
                    for line in final_lines:
                        if y_position < 0.25 * inch:
                            break
                        text_width = stringWidth(line, 'Helvetica-Bold', STD_FONT_SIZE)
                        x_centered = (w - text_width) / 2
                        c.setFont("Helvetica-Bold", STD_FONT_SIZE)
                        c.drawString(x_centered, y_position, line)
                        y_position -= 0.68 * inch

                # Draw Barcode
                if draw_barcode:
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
                        y_bc = max(0.7 * inch, y_position - 0.3 * inch)

                        renderPDF.draw(barcode_obj, c, x_bc, y_bc)

                        human_text = barcode_val
                        text_w = stringWidth(human_text, 'Helvetica-Bold', BARCODE_HUMAN_FONT_SIZE)
                        c.setFont("Helvetica-Bold", BARCODE_HUMAN_FONT_SIZE)
                        c.drawString((w - text_w) / 2, y_bc - 0.2 * inch, human_text)

                    except Exception as e:
                        st.error(f"Barcode error: {e}")

        c.save()
        buffer.seek(0)

        mode_str = "_MAXFILL" if maximize_text else "_STD"
        st.success(f"✅ Generated {total_labels} label(s) [{mode_str}] at {width_in:.1f}″ × {height_in:.1f}″")
        
        st.download_button(
            "⬇️ Download PDF",
            buffer,
            f"warehouse_labels_{width_in}x{height_in}{mode_str}.pdf",
            "application/pdf"
        )
