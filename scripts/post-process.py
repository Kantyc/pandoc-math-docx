#!/usr/bin/env python3
"""
Post-process a Pandoc-generated .docx for correct math typography and equation numbering.

Transformations:
1. Strips any <m:nor/> and injected <w:rPr> from math runs (restores pure math mode)
2. Replaces display equations (oMathPara) with 3-column borderless tables for (N) numbering
3. Sets table layout: fixed, 100% width, no borders
4. Sets equation numbers to Times New Roman
5. Re-zips back into .docx preserving original file order

Usage: python post-process.py <input.docx>
"""
import sys, os, zipfile, re, shutil, tempfile

def main():
    if len(sys.argv) < 2:
        print("Usage: post-process.py <input.docx>", file=sys.stderr)
        sys.exit(1)
    docx_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(docx_path):
        print(f"File not found: {docx_path}", file=sys.stderr)
        sys.exit(1)

    tmp = docx_path + ".pp_tmp"
    if os.path.exists(tmp): shutil.rmtree(tmp)
    with zipfile.ZipFile(docx_path) as z: z.extractall(tmp)

    # --- document.xml ---
    doc_xml = os.path.join(tmp, 'word', 'document.xml')
    with open(doc_xml, 'r', encoding='utf-8') as f: x = f.read()

    # 1. Strip <m:nor/> and injected <w:rPr> in math runs
    nor_count = x.count('<m:nor/>') + x.count('<m:nor />')
    x = x.replace('<m:nor/>', '').replace('<m:nor />', '')
    x = re.sub(r'(?s)(</m:rPr>)<w:rPr>.*?</w:rPr>(<m:t)', r'\1\2', x)

    # 2. Replace display equations: <w:p>...<m:oMathPara>...</m:oMathPara>...</w:p>
    #    with a <w:tbl> (table must be between paragraphs, NOT inside one)
    eq_counter = [0]

    def replace_equation(m):
        """Replace <w:p>...<m:oMathPara>...</m:oMathPara>...</w:p> with a table."""
        eq_counter[0] += 1
        num = f'({eq_counter[0]})'
        # Extract inner <m:oMath>...</m:oMath> (skip oMathParaPr)
        inner_match = re.search(r'(?s)<m:oMath>.+?</m:oMath>', m.group(1))
        inner = inner_match.group(0) if inner_match else ''

        tnr = '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman" />'
        nil_b = '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'

        tbl = '<w:tbl>'
        tbl += '<w:tblPr>' + nil_b + '<w:tblW w:type="pct" w:w="5000"/><w:tblLayout w:type="fixed"/>'
        tbl += '<w:tblLook w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="0" w:val="0000"/></w:tblPr>'
        tbl += '<w:tblGrid><w:gridCol w:w="136"/><w:gridCol w:w="7100"/><w:gridCol w:w="682"/></w:tblGrid>'
        tbl += '<w:tr>'
        # Spacer cell
        tbl += '<w:tc><w:tcPr><w:tcW w:w="136" w:type="dxa"/></w:tcPr><w:p><w:pPr><w:pStyle w:val="Compact"/></w:pPr></w:p></w:tc>'
        # Equation cell (centered)
        tbl += '<w:tc><w:tcPr><w:tcW w:w="7100" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>'
        tbl += '<w:p><w:pPr><w:pStyle w:val="Compact"/><w:jc w:val="center"/></w:pPr>' + inner + '</w:p></w:tc>'
        # Number cell (right-aligned)
        tbl += '<w:tc><w:tcPr><w:tcW w:w="682" w:type="dxa"/></w:tcPr>'
        tbl += '<w:p><w:pPr><w:pStyle w:val="Compact"/><w:jc w:val="right"/></w:pPr>'
        tbl += '<w:r><w:rPr>' + tnr + '</w:rPr><w:t xml:space="preserve">' + num + '</w:t></w:r></w:p></w:tc>'
        tbl += '</w:tr></w:tbl>'
        return tbl

    # Match: <w:p>...<m:oMathPara>...</m:oMathPara>...</w:p>
    # The entire paragraph containing an oMathPara gets replaced with a table
    x = re.sub(
        r'(?s)<w:p>(?:(?!<w:p[ >]).)*?<m:oMathPara>(?:<m:oMathParaPr>.+?</m:oMathParaPr>)?(<m:oMath>.+?</m:oMath>)</m:oMathPara>(?:(?!</w:p>).)*?</w:p>',
        replace_equation,
        x
    )
    print(f'Equations numbered: {eq_counter[0]}')
    print(f'<m:nor/> stripped: {nor_count}')

    with open(doc_xml, 'w', encoding='utf-8') as f: f.write(x)

    # --- styles.xml: remove table border defaults ---
    styles_xml = os.path.join(tmp, 'word', 'styles.xml')
    if os.path.exists(styles_xml):
        with open(styles_xml, 'r', encoding='utf-8') as f: s = f.read()
        s = re.sub(r'(?s)<w:tblBorders>.*?</w:tblBorders>', '', s)
        s = re.sub(r'(?s)<w:tcBorders>.*?</w:tcBorders>', '', s)
        with open(styles_xml, 'w', encoding='utf-8') as f: f.write(s)

    # --- Re-zip preserving original file order ---
    out = docx_path + '.pp_new'
    if os.path.exists(out): os.remove(out)
    src_zip = zipfile.ZipFile(docx_path)
    orig_names = src_zip.namelist()
    src_zip.close()

    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name in orig_names:
            full = os.path.join(tmp, name.replace('/', os.sep))
            if os.path.exists(full):
                zf.write(full, name)

    shutil.rmtree(tmp)
    os.remove(docx_path)
    shutil.move(out, docx_path)
    print(f'Post-processing complete: {docx_path}')


if __name__ == '__main__':
    main()
