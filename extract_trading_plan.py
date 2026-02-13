import fitz  # PyMuPDF
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

pdf_path = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\STARE LEKCIJE PDF\Trading Plan PDF .pdf'
output_dir = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\STARE LEKCIJE PDF\trading_plan_images'
os.makedirs(output_dir, exist_ok=True)

doc = fitz.open(pdf_path)
print(f'Pages: {len(doc)}')

for page_num in range(len(doc)):
    page = doc[page_num]

    # Try text extraction with PyMuPDF (better than PyPDF2)
    text = page.get_text()
    if text.strip():
        print(f'\n=== Page {page_num+1} TEXT ===')
        print(text)

    # Render page as image
    pix = page.get_pixmap(dpi=200)
    img_path = os.path.join(output_dir, f'page_{page_num+1}.png')
    pix.save(img_path)
    print(f'Saved: {img_path} ({pix.width}x{pix.height})')

doc.close()
