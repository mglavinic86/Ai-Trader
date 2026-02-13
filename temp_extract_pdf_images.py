import fitz
import os

pdf_dir = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\NOVE LEKCIJE PDF'
out_dir = r'C:\Users\mglav\Projects\AI Trader\temp_pdf_pages'
os.makedirs(out_dir, exist_ok=True)

files = [
    ('Privatni-Coaching-Program-Lekcija-13-3.pdf', 'L13'),
    ('Privatni-Coaching-Program-Lekcija-14 (1).pdf', 'L14'),
    ('Privatni-Coaching-Program-Lekcija-16.pdf', 'L16'),
]

for fname, prefix in files:
    path = os.path.join(pdf_dir, fname)
    if not os.path.exists(path):
        print(f'NOT FOUND: {fname}')
        continue
    doc = fitz.open(path)
    total = len(doc)
    max_page = min(20, total)
    print(f'{fname}: {total} pages, rendering {max_page}')
    for i in range(max_page):
        pix = doc[i].get_pixmap(dpi=150)
        out_path = os.path.join(out_dir, f'{prefix}_p{i+1:02d}.png')
        pix.save(out_path)
        print(f'  Saved: {out_path}')
    doc.close()

print(f'\nDone! All pages saved to {out_dir}')
