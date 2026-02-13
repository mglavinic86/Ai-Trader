import fitz  # PyMuPDF
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

pdf_dir = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\STARE LEKCIJE PDF'
files = [
    '1. lekcija Struktura Marketa.pdf',
    '2. lekcija Supply  Demand  - Premium  Discount - BOS (Choch) (2).pdf',
    'FVG .pdf',
    'Liquidity Inducement .pdf',
    'Trading sesije, Vijesti & Slippage .pdf',
    'Entry Modeli.pdf',
    'Trading Plan PDF .pdf',
]

for fname in files:
    fpath = os.path.join(pdf_dir, fname)
    out_path = os.path.join(pdf_dir, fname.replace('.pdf', '_mupdf.txt'))

    try:
        doc = fitz.open(fpath)
        num_pages = len(doc)
        all_text = []
        for i in range(num_pages):
            text = doc[i].get_text()
            if text and text.strip():
                all_text.append(f'=== Page {i+1} ===\n{text}')
        doc.close()
        full = '\n\n'.join(all_text)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(full)
        print(f'OK: {fname} -> {num_pages} pages, {len(full)} chars')
    except Exception as e:
        print(f'ERR: {fname} -> {e}')
