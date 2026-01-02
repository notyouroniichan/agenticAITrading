from fpdf import FPDF
from datetime import datetime

class RiskReportPDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'Agentic AI - Risk Briefing', border=False, align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_pdf_report(filename: str, metrics: dict, details: str):
    pdf = RiskReportPDF()
    pdf.add_page()
    
    # 1. Title Info
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(10)
    
    # 2. Executive Summary
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "1. Analyst Summary", ln=True)
    pdf.set_font("helvetica", size=11)
    pdf.multi_cell(0, 10, details)
    pdf.ln(10)
    
    # 3. Key Metrics
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "2. Key Risk Metrics", ln=True)
    pdf.set_font("helvetica", size=11)
    
    for key, val in metrics.items():
        pdf.cell(100, 10, f"{key}: {val}", ln=True)
        
    pdf.output(filename)
