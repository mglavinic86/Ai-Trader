import fitz
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\STARE LEKCIJE PDF\1. lekcija Struktura Marketa.pdf'
output_dir = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\STARE LEKCIJE PDF\pdf1_images'
os.makedirs(output_dir, exist_ok=True)

doc = fitz.open(pdf_path)
# Only render page 1 (title) to check for content
for i in [0]:  # Just page 1
    pix = doc[i].get_pixmap(dpi=150)
    img_path = os.path.join(output_dir, f'page_{i+1}.png')
    pix.save(img_path)
    print(f'Saved: {img_path}')
doc.close()
