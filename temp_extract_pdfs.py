import fitz
import os

pdf_dir = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\NOVE LEKCIJE PDF'
files = [
    'Privatni-Coaching-Program-Lekcija-13-3.pdf',
    'Privatni-Coaching-Program-Lekcija-14 (1).pdf',
    'Privatni-Coaching-Program-Lekcija-16.pdf'
]

for f in files:
    path = os.path.join(pdf_dir, f)
    print(f'\n{"="*80}')
    print(f'FILE: {f}')
    print(f'{"="*80}')
    if not os.path.exists(path):
        print(f'  FILE NOT FOUND')
        continue
    try:
        doc = fitz.open(path)
        total_pages = len(doc)
        print(f'Total pages: {total_pages}')
        max_page = min(20, total_pages)
        for i in range(max_page):
            text = doc[i].get_text()
            if text.strip():
                print(f'\n--- Page {i+1} ---')
                print(text)
        doc.close()
    except Exception as e:
        print(f'ERROR: {e}')
