import fitz
import os

pdf_dir = r"C:\Users\mglav\Projects\AI Trader\novi skillovi\NOVE LEKCIJE PDF"
out_dir = r"C:\Users\mglav\Projects\AI Trader\temp_pdf_pages"
os.makedirs(out_dir, exist_ok=True)

files = [
    ("Privatni-Coaching-Program-Lekcija-17 (2).pdf", "L17"),
    ("Privatni-Coaching-Program-Lekcija-18.pdf", "L18"),
    ("Privatni-Coaching-Program-Lekcija-19.pdf", "L19"),
]

for fname, prefix in files:
    path = os.path.join(pdf_dir, fname)
    if not os.path.exists(path):
        print(f"NOT FOUND: {path}")
        continue

    doc = fitz.open(path)
    total = doc.page_count
    max_pages = min(20, total)
    print(f"{fname}: {total} pages, rendering {max_pages}")

    for i in range(max_pages):
        page = doc[i]
        # Render at 200 DPI for readability
        mat = fitz.Matrix(200/72, 200/72)
        pix = page.get_pixmap(matrix=mat)
        out_path = os.path.join(out_dir, f"{prefix}_page{i+1:02d}.png")
        pix.save(out_path)
        print(f"  Saved: {out_path}")

    doc.close()

print("\nDone! All pages rendered.")
