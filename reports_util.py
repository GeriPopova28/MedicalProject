from fpdf import FPDF
import datetime

class ReportGenerator:
    @staticmethod
    def create_pdf(patient_name, data):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="MEDICAL REPORT", ln=True, align='C')
        # ... останалата част от export_pdf_report ...
        filename = f"Report_{patient_name}.pdf"
        pdf.output(filename)
        return filename