import PyPDF2
import sys

sys.stdout.reconfigure(encoding='utf-8')

r = PyPDF2.PdfReader(r'C:\Users\mglav\Projects\AI Trader\novi skillovi\STARE LEKCIJE PDF\Trading Plan PDF .pdf')
print(f'Pages: {len(r.pages)}')
for i, p in enumerate(r.pages):
    t = p.extract_text()
    print(f'Page {i+1}: chars={len(t) if t else 0}')
    if t:
        print(repr(t[:500]))
    # Check for images
    if '/XObject' in p.get('/Resources', {}):
        xobj = p['/Resources']['/XObject'].get_object()
        print(f'  Images: {len(xobj)}')
