from __future__ import annotations

import os

from docx import Document
from fpdf import FPDF


def export_to_txt(title: str, questions: list[dict], filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"{title}\n")
        f.write("=" * len(title) + "\n\n")
        
        for i, q in enumerate(questions, start=1):
            f.write(f"{i}. {q['question']}\n")
            for ans in q.get("answers", []):
                f.write(f"   {ans}\n")
            f.write(f"\nPoprawna odpowiedź: {q.get('correct', '?')}\n")
            if q.get("explanation"):
                f.write(f"Wyjaśnienie: {q['explanation']}\n")
            f.write("\n")


def export_to_pdf(title: str, questions: list[dict], filepath: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    
    font_path = "C:/Windows/Fonts/arial.ttf"
    has_font = os.path.exists(font_path)
    
    if has_font:
        pdf.add_font("Arial", "", font_path)
        pdf.add_font("Arial", "B", "C:/Windows/Fonts/arialbd.ttf")
        pdf.add_font("Arial", "I", "C:/Windows/Fonts/ariali.ttf")
        pdf.set_font("Arial", "B", 16)
    else:
        pdf.set_font("helvetica", "B", 16)
        
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    for i, q in enumerate(questions, start=1):
        if has_font:
            pdf.set_font("Arial", "B", 12)
        else:
            pdf.set_font("helvetica", "B", 12)
        pdf.multi_cell(0, 8, f"{i}. {q['question']}", new_x="LMARGIN", new_y="NEXT")
        
        if has_font:
            pdf.set_font("Arial", "", 11)
        else:
            pdf.set_font("helvetica", "", 11)
        for ans in q.get("answers", []):
            pdf.multi_cell(0, 6, f"   {ans}", new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(2)
        
        if has_font:
            pdf.set_font("Arial", "B", 11)
        else:
            pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 6, f"Poprawna odpowiedź: {q.get('correct', '?')}", new_x="LMARGIN", new_y="NEXT")
        
        if q.get("explanation"):
            if has_font:
                pdf.set_font("Arial", "I", 11)
            else:
                pdf.set_font("helvetica", "I", 11)
            pdf.multi_cell(0, 6, f"Wyjaśnienie: {q['explanation']}", new_x="LMARGIN", new_y="NEXT")
            
        pdf.ln(5)
        
    pdf.output(filepath)


def export_to_docx(title: str, questions: list[dict], filepath: str) -> None:
    doc = Document()
    doc.add_heading(title, 0)
    
    for i, q in enumerate(questions, start=1):
        p = doc.add_paragraph()
        p.add_run(f"{i}. {q['question']}").bold = True
        
        for ans in q.get("answers", []):
            doc.add_paragraph(f"   {ans}")
            
        p_correct = doc.add_paragraph()
        p_correct.add_run(f"Poprawna odpowiedź: {q.get('correct', '?')}").bold = True
        
        if q.get("explanation"):
            p_expl = doc.add_paragraph()
            p_expl.add_run(f"Wyjaśnienie: {q['explanation']}").italic = True
            
    doc.save(filepath)
