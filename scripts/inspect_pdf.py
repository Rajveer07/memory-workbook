"""Extract and render a private PDF for manual authoring; never generates questions."""
import argparse
import hashlib
import json
from pathlib import Path
import pymupdf

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('pdf',type=Path)
    parser.add_argument('--expected-pages',type=int)
    parser.add_argument('--output',type=Path,default=Path('private/inspection'))
    args=parser.parse_args()
    document=pymupdf.open(args.pdf)
    if document.is_encrypted:raise SystemExit('Encrypted PDF; unlock your local copy first.')
    if args.expected_pages and len(document)!=args.expected_pages:
        raise SystemExit(f'Expected {args.expected_pages} pages; found {len(document)}.')
    args.output.mkdir(parents=True,exist_ok=True)
    for index,page in enumerate(document,1):
        (args.output/f'page-{index:03}.txt').write_text(page.get_text(),encoding='utf-8')
        page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(args.output/f'page-{index:03}.png')
    (args.output/'manifest.json').write_text(json.dumps(dict(filename=args.pdf.name,pages=len(document),sha256=hashlib.sha256(args.pdf.read_bytes()).hexdigest()),indent=2)+'\n')
    print(f'Opened, extracted and rendered {len(document)} pages. Inspect every image before authoring.')
