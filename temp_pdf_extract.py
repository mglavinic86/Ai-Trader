import fitz
import sys
import os

def extract_pdf(filepath, max_pages=20):
    try:
        doc = fitz.open(filepath)
        total = doc.page_count
        print(f"File: {os.path.basename(filepath)}")
        print(f"Total pages: {total}")
        print("=" * 80)

        for i in range(min(max_pages, total)):
            page = doc[i]
            text = page.get_text()
            if text.strip():
                print(f"\n--- PAGE {i+1} ---")
                # Replace problematic characters
                safe_text = text.encode('ascii', 'replace').decode('ascii')
                print(safe_text)

        doc.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False

pdf_dir = r"C:\Users\mglav\Projects\AI Trader\novi skillovi\NOVE LEKCIJE PDF"

files = [
    "Privatni-Coaching-Program-Lekcija-17 (2).pdf",
    "Privatni-Coaching-Program-Lekcija-18.pdf",
    "Privatni-Coaching-Program-Lekcija-19.pdf",
]

for f in files:
    path = os.path.join(pdf_dir, f)
    print("\n" + "#" * 80)
    print(f"# PROCESSING: {f}")
    print("#" * 80)
    if os.path.exists(path):
        extract_pdf(path, 20)
    else:
        print(f"FILE NOT FOUND: {path}")
    print("\n")
