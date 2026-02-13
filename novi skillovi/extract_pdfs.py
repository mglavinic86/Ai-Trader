import fitz, os

base = r'C:\Users\mglav\Projects\AI Trader\novi skillovi\NOVE LEKCIJE PDF'
out = os.path.join(base, 'img')
os.makedirs(out, exist_ok=True)

files = [
    ('Privatni-Mentorship-Lekcija-1 (1).pdf', 'L1'),
    ('Privatni-Mentorship-Lekcija-2-2 (1).pdf', 'L2'),
    ('Privatni-Coaching-Program-Lekcija-3 (1).pdf', 'L3'),
    ('Privatni-Coaching-Program-Lekcija-4-2 (1).pdf', 'L4'),
    ('Privatni-Coaching-Program-Lekcija-5 (1).pdf', 'L5'),
    ('Privatni-Coaching-Program-Lekcija-6-2 (1).pdf', 'L6'),
]

for fname, prefix in files:
    doc = fitz.open(os.path.join(base, fname))
    count = doc.page_count
    for p in range(count):
        pix = doc[p].get_pixmap(dpi=150)
        pix.save(os.path.join(out, f'{prefix}_p{p+1}.png'))
    doc.close()
    print(f'Done {prefix}: {count} pages')

print('All done!')
