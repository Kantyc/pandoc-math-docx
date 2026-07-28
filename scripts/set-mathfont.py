# -*- coding: utf-8 -*-
"""
Point a .docx at a Times-style OpenType MATH font, the complete way.

    python scripts/set-mathfont.py out.docx
    python scripts/set-mathfont.py out.docx "Cambria Math"

Two parts have to agree, and missing either one causes trouble:

  1. word/settings.xml   <m:mathFont m:val="...">   which font the math engine uses
  2. word/fontTable.xml  <w:font w:name="...">      declares it to the document

Defaults to "TeX Gyre Termes Math" - a glyph-level clone of Times with a
full OpenType MATH table, so equations look like Times New Roman while
Word's math engine keeps doing auto-italic, auto-bold and stretchy
brackets. Pass "Cambria Math" to fall back to Word's default.

Never adds <m:nor/>. See SKILL.md Pitfall 1.
"""
import sys, os, re, zipfile, tempfile, shutil, subprocess

DEFAULT_FONT = 'TeX Gyre Termes Math'
FONT_FILES = {
    'TeX Gyre Termes Math': r'C:\Windows\Fonts\texgyretermes-math.otf',
    'STIX Two Math':        r'C:\Windows\Fonts\STIX2Math.otf',
    'XITS Math':            r'C:\Windows\Fonts\XITSMath-Regular.otf',
    'Cambria Math':         r'C:\Windows\Fonts\cambria.ttc',
}


def font_available(family):
    try:
        r = subprocess.run(
            ['powershell.exe', '-NoProfile', '-Command',
             'Add-Type -AssemblyName System.Drawing; '
             '(New-Object System.Drawing.Text.InstalledFontCollection)'
             '.Families | ForEach-Object { $_.Name }'],
            capture_output=True, text=True, timeout=90, errors='replace')
        return any(l.strip() == family for l in r.stdout.splitlines())
    except Exception:
        return True   # don't block on a probe failure


def font_decl(name, otf):
    """Build a <w:font> declaration, reading real metrics when we can."""
    panose = '02020603050405020304'          # Times New Roman's panose
    usb = ('00000003', '00000000', '00000000', '00000000')
    csb = ('00000001', '00000000')
    if otf and os.path.exists(otf):
        try:
            from fontTools.ttLib import TTFont
            kw = {'fontNumber': 0} if otf.lower().endswith('.ttc') else {}
            o = TTFont(otf, lazy=True, **kw)['OS/2']
            p = o.panose
            panose = ''.join(f'{v:02X}' for v in [
                p.bFamilyType, p.bSerifStyle, p.bWeight, p.bProportion,
                p.bContrast, p.bStrokeVariation, p.bArmStyle, p.bLetterForm,
                p.bMidline, p.bXHeight])
            usb = (f'{o.ulUnicodeRange1:08X}', f'{o.ulUnicodeRange2:08X}',
                   f'{o.ulUnicodeRange3:08X}', f'{o.ulUnicodeRange4:08X}')
            csb = (f'{o.ulCodePageRange1:08X}', f'{o.ulCodePageRange2:08X}')
        except Exception as e:
            print(f'  (metrics probe failed, using Times defaults: {e})')
    return (f'<w:font w:name="{name}">'
            f'<w:panose1 w:val="{panose}"/><w:charset w:val="00"/>'
            f'<w:family w:val="roman"/><w:pitch w:val="variable"/>'
            f'<w:sig w:usb0="{usb[0]}" w:usb1="{usb[1]}" w:usb2="{usb[2]}" '
            f'w:usb3="{usb[3]}" w:csb0="{csb[0]}" w:csb1="{csb[1]}"/></w:font>')


def main(docx, font=DEFAULT_FONT):
    if font != 'Cambria Math' and not font_available(font):
        print(f'WARNING: "{font}" is not installed.')
        print('         Run: python scripts/ensure-deps.py --install')
        print('         Falling back to Cambria Math.')
        font = 'Cambria Math'

    tmp = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(docx) as z:
            names = z.namelist()
            z.extractall(tmp)

        # --- settings.xml -------------------------------------------------
        sp = os.path.join(tmp, 'word', 'settings.xml')
        s = open(sp, encoding='utf-8').read()
        if re.search(r'<m:mathFont\b[^>]*/>', s):
            s = re.sub(r'<m:mathFont\b[^>]*/>',
                       f'<m:mathFont m:val="{font}"/>', s, count=1)
        elif '<m:mathPr>' in s:
            s = s.replace('<m:mathPr>',
                          f'<m:mathPr><m:mathFont m:val="{font}"/>', 1)
        else:
            if 'xmlns:m=' not in s[:s.find('>') + 400]:
                s = s.replace(
                    '<w:settings ',
                    '<w:settings xmlns:m="http://schemas.openxmlformats.org/'
                    'officeDocument/2006/math" ', 1)
            s = s.replace('</w:settings>',
                          f'<m:mathPr><m:mathFont m:val="{font}"/>'
                          f'<m:brkBin m:val="before"/><m:smallFrac m:val="0"/>'
                          f'<m:dispDef/><m:intLim m:val="subSup"/>'
                          f'<m:naryLim m:val="undOvr"/></m:mathPr>'
                          '</w:settings>')
        open(sp, 'w', encoding='utf-8').write(s)
        print(f'settings.xml  : mathFont = {font}')

        # --- fontTable.xml -----------------------------------------------
        fp = os.path.join(tmp, 'word', 'fontTable.xml')
        if os.path.exists(fp):
            ft = open(fp, encoding='utf-8').read()
            if f'w:name="{font}"' in ft:
                print('fontTable.xml : already declared')
            else:
                ft = ft.replace('</w:fonts>',
                                font_decl(font, FONT_FILES.get(font))
                                + '</w:fonts>')
                open(fp, 'w', encoding='utf-8').write(ft)
                print(f'fontTable.xml : declared "{font}"')
        else:
            print('fontTable.xml : absent (skipped)')

        out = docx + '.tmp'
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for n in names:                     # preserve original order
                z.write(os.path.join(tmp, n), n)
        os.replace(out, docx)
        print(f'done          : {docx}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else DEFAULT_FONT)
