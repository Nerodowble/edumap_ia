from datetime import datetime
from typing import Dict, List, Optional

_BLOOM_NAMES = {1: "Lembrar", 2: "Compreender", 3: "Aplicar", 4: "Analisar", 5: "Avaliar", 6: "Criar"}

try:
    from fpdf import FPDF
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def _fpdf_safe(text: str) -> str:
    """Remove chars that FPDF Latin-1 cannot handle."""
    return text.encode("latin-1", errors="replace").decode("latin-1")


def export_pdf(
    questions: List[Dict],
    recommendations: List[Dict],
    metadata: Dict,
) -> Optional[bytes]:
    if not _AVAILABLE:
        return None

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- Header ---
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "EduMap IA - Relatorio de Diagnostico", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(180, 180, 180)
    pdf.line(10, pdf.get_y() + 2, 200, pdf.get_y() + 2)
    pdf.ln(6)

    # --- Metadata ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Informacoes da Prova", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for k, v in metadata.items():
        pdf.cell(0, 6, _fpdf_safe(f"  {k}: {v}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # --- Questions table ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, _fpdf_safe(f"Questoes Analisadas ({len(questions)})"), new_x="LMARGIN", new_y="NEXT")

    # Table header
    pdf.set_fill_color(44, 62, 80)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(12, 7, "N", border=1, fill=True)
    pdf.cell(85, 7, "Enunciado (trecho)", border=1, fill=True)
    pdf.cell(45, 7, "Area", border=1, fill=True)
    pdf.cell(45, 7, "Nivel Bloom", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 9)
    for i, q in enumerate(questions):
        fill = i % 2 == 0
        if fill:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        raw_stem = q.get("stem") or q.get("text", "")
        stem = _fpdf_safe(raw_stem.replace("\n", " ")[:70])
        if len(raw_stem) > 70:
            stem += "..."

        bloom_name = _BLOOM_NAMES.get(q.get("bloom_level", 0), "?")
        area = _fpdf_safe(q.get("area_display", "-"))

        pdf.cell(12, 6, str(q.get("number", i + 1)), border=1, fill=fill)
        pdf.cell(85, 6, stem, border=1, fill=fill)
        pdf.cell(45, 6, area, border=1, fill=fill)
        pdf.cell(45, 6, bloom_name, border=1, fill=fill, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)

    # --- Recommendations ---
    if recommendations:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Recomendacoes Pedagogicas", new_x="LMARGIN", new_y="NEXT")

        icons = {"success": "[OK]", "warning": "[!]", "critical": "[!!]", "info": "[i]"}
        for rec in recommendations:
            icon = icons.get(rec.get("type", "info"), "[i]")
            pdf.set_font("Helvetica", "B", 10)
            title = _fpdf_safe(f"{icon} {rec.get('title', '')}")
            pdf.multi_cell(0, 6, title)
            pdf.set_font("Helvetica", "", 9)
            detail = _fpdf_safe(f"   {rec.get('detail', '')}")
            pdf.multi_cell(0, 5, detail)
            pdf.ln(2)

    return bytes(pdf.output())
