$path = "frontend/app.py"
$s = Get-Content $path -Raw
$old = @"
            pdf_bytes = pdf.output(dest="S")
            if isinstance(pdf_bytes, str):
                pdf_bytes = pdf_bytes.encode("latin-1")
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name=f"hepatiq_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
            )
"@
$new = @"
            try:
                pdf_bytes = pdf.output()
            except Exception:
                try:
                    pdf_bytes = pdf.output(dest="S")
                except Exception:
                    pdf_bytes = pdf.output()
            if isinstance(pdf_bytes, str):
                pdf_bytes = pdf_bytes.encode("latin-1")
            elif hasattr(pdf_bytes, 'tobytes'):
                pdf_bytes = pdf_bytes.tobytes()
            st.download_button(
                label="Download PDF Report",
                data=bytes(pdf_bytes),
                file_name=f"hepatiq_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
            )
"@
if ($s.Contains($old)) {
  $s2 = $s.Replace($old, $new)
  Set-Content -Path $path -Value $s2 -NoNewline
  Write-Host "ok"
} else {
  Write-Host "no"
}
