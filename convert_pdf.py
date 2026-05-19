import pikepdf, os
pdf_in = r'R:/Dissertation/Tex/Титульный_лист.pdf'
pdf_out = r'R:/Dissertation/Tex/Титульный_лист_flat.pdf'
with pikepdf.open(pdf_in) as pdf:
    print('Pages:', len(pdf.pages))
    print('PDF version:', pdf.pdf_version)
    pdf.save(pdf_out, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
print('Saved, size:', os.path.getsize(pdf_out), 'bytes')