import PyPDF2
import os
import sys

# Force UTF-8 output
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

output_dir = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\STARE LEKCIJE PDF'

for fname in files:
    fpath = os.path.join(pdf_dir, fname)
    out_path = os.path.join(output_dir, fname.replace('.pdf', '.txt'))

    try:
        reader = PyPDF2.PdfReader(fpath)
        all_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                all_text.append(f"=== Page {i+1} ===\n{text}")

        full_text = '\n\n'.join(all_text)

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(full_text)

        print(f"OK: {fname} -> {len(reader.pages)} pages, {len(full_text)} chars extracted")
    except Exception as e:
        print(f"ERROR: {fname} -> {e}")
