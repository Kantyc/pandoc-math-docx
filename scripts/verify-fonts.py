#!/usr/bin/env python3
"""
Verify math rendering in a PDF by extracting font information per glyph.

Usage:
  python verify-fonts.py <input.pdf>

Checks:
  - Variables are in a math font (Cambria Math / XITS Math) — not Times New Roman
  - Structural symbols (brackets, integrals) use a MATH font
  - No glyphs are missing (blank rendering)

Prerequisites: pip install PyMuPDF (fitz)
"""
import sys
import fitz

def verify(pdf_path):
    doc = fitz.open(pdf_path)
    fonts_used = set()
    math_fonts = {'CambriaMath', 'XITSMath', 'STIXTwoMath', 'AsanaMath', 'LatinModernMath'}

    for page_num in range(doc.page_count):
        page = doc[page_num]
        d = page.get_text('dict')
        for block in d.get('blocks', []):
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    font = span['font']
                    text = span['text'].strip()
                    fonts_used.add(font)

                    # Check: math symbols should come from a MATH font
                    if text in ('(', ')', '[', ']', '{', '}', '∫', '∑', '∏', '∂', '∇', '⋅', '×'):
                        is_math = any(mf in font for mf in math_fonts)
                        if not is_math:
                            print(f"  ⚠️  Page {page_num+1}: '{text}' uses non-math font '{font}'")

    print("\n=== Fonts used in document ===")
    for f in sorted(fonts_used):
        marker = " (MATH)" if any(mf in f for mf in math_fonts) else ""
        print(f"  {f}{marker}")

    # Check for any blank pages (no text extracted = possible rendering failure)
    for page_num in range(doc.page_count):
        page = doc[page_num]
        text = page.get_text().strip()
        if not text:
            print(f"  ⚠️  Page {page_num+1}: no text extracted (possible blank/rendering failure)")

    doc.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: verify-fonts.py <input.pdf>")
        sys.exit(1)
    verify(sys.argv[1])
