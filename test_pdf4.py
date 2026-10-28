from fpdf import FPDF
pdf=FPDF()
pdf.add_page()
pdf.set_font('Helvetica','B',16)
pdf.cell(0,10,'test',ln=True,align='C')
b=pdf.output(dest='S')
if isinstance(b,str): b=b.encode('latin-1')
print(type(b))
