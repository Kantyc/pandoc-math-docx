# -*- coding: utf-8 -*-
"""
Check (and optionally install) everything this skill needs, then report.

Run this FIRST, before generating any document:

    python scripts/ensure-deps.py            # check only, report what's missing
    python scripts/ensure-deps.py --install  # download + install what's missing

Checks:
  1. pandoc                     -> PATH, or common portable locations
  2. TeX Gyre Termes Math font  -> the Times-clone OpenType MATH font
  3. python packages            -> fontTools (required), pymupdf (verification)

Installing the font writes to C:\\Windows\\Fonts and HKLM (needs admin).
A registry backup is written before the first change.

Exit code 0 = everything present. 1 = something missing (see report).
"""
import sys, os, re, glob, shutil, subprocess, argparse

TERMES_NAME = 'TeX Gyre Termes Math'
TERMES_FILE = 'texgyretermes-math.otf'
TERMES_URLS = [
    'https://mirrors.ctan.org/fonts/tex-gyre-math/opentype/texgyretermes-math.otf',
    'https://ctan.org/tex-archive/fonts/tex-gyre-math/opentype/texgyretermes-math.otf',
]
PANDOC_VER = '3.1.11'
PANDOC_URL = (f'https://github.com/jgm/pandoc/releases/download/{PANDOC_VER}/'
              f'pandoc-{PANDOC_VER}-windows-x86_64.zip')

TEMP = os.environ.get('TEMP', r'C:\Windows\Temp')


def ps(script, timeout=180):
    """Run PowerShell, return (rc, stdout)."""
    r = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy',
                        'Bypass', '-Command', script],
                       capture_output=True, text=True, timeout=timeout,
                       errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


# ---------------------------------------------------------------- pandoc

def find_pandoc():
    p = shutil.which('pandoc')
    if p:
        return p
    pats = [
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Pandoc', 'pandoc.exe'),
        os.path.join(TEMP, 'pandoc_extract', '*', 'pandoc.exe'),
        r'C:\Program Files\Pandoc\pandoc.exe',
    ]
    for pat in pats:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def install_pandoc():
    zp = os.path.join(TEMP, 'pandoc.zip')
    ex = os.path.join(TEMP, 'pandoc_extract')
    print(f'  downloading pandoc {PANDOC_VER} ...')
    rc, out = ps(
        f"Invoke-WebRequest -Uri '{PANDOC_URL}' -OutFile '{zp}' "
        f"-UseBasicParsing -TimeoutSec 300; "
        f"Expand-Archive '{zp}' -DestinationPath '{ex}' -Force", timeout=600)
    if rc != 0:
        print('  FAILED:', out.strip()[:300])
        return None
    return find_pandoc()


# ------------------------------------------------------------------ font

def font_installed(family):
    rc, out = ps(
        "Add-Type -AssemblyName System.Drawing; "
        "(New-Object System.Drawing.Text.InstalledFontCollection)"
        ".Families | ForEach-Object { $_.Name }")
    return any(l.strip() == family for l in out.splitlines())


def is_admin():
    rc, out = ps(
        "$p=New-Object Security.Principal.WindowsPrincipal("
        "[Security.Principal.WindowsIdentity]::GetCurrent()); "
        "$p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)")
    return 'True' in out


def install_termes():
    """Download TeX Gyre Termes Math and register it system-wide (HKLM)."""
    if not is_admin():
        print('  NOT ADMIN - cannot install a system font.')
        print('  Re-run this session elevated, or install the font manually:')
        print(f'    {TERMES_URLS[0]}')
        return False

    dst_dl = os.path.join(TEMP, TERMES_FILE)
    ok = False
    for url in TERMES_URLS:
        print(f'  downloading {TERMES_NAME} ...')
        rc, out = ps(f"try {{ Invoke-WebRequest -Uri '{url}' -OutFile "
                     f"'{dst_dl}' -UseBasicParsing -TimeoutSec 180; "
                     f"'OK' }} catch {{ 'ERR ' + $_.Exception.Message }}",
                     timeout=300)
        if 'OK' in out and os.path.exists(dst_dl) \
                and os.path.getsize(dst_dl) > 100_000:
            ok = True
            break
        print('   ', out.strip()[:160])
    if not ok:
        print('  download FAILED from all mirrors')
        return False

    # Sanity-check the font actually has a MATH table before installing it.
    try:
        from fontTools.ttLib import TTFont
        f = TTFont(dst_dl, lazy=True)
        if 'MATH' not in f:
            print('  REJECTED: downloaded font has no MATH table')
            return False
        fam = next(r.toUnicode() for r in f['name'].names
                   if r.nameID == 1 and r.platformID == 3)
        print(f'  verified: family="{fam}", MATH table present')
    except ImportError:
        print('  (fontTools missing - skipping MATH-table verification)')
        fam = TERMES_NAME

    backup = os.path.join(TEMP, 'fonts-hklm-backup.reg')
    dest = os.path.join(os.environ.get('WINDIR', r'C:\Windows'),
                        'Fonts', TERMES_FILE)
    # NOTE: register under HKLM with the correct "(OpenType)" suffix and do
    # NOT add an HKCU entry. A per-user .otf mislabelled "(TrueType)" that
    # duplicates the HKLM entry is a known source of font-resolution trouble.
    script = f'''
$ErrorActionPreference='Stop'
$k='HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts'
if (-not (Test-Path '{backup}')) {{
  reg export 'HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts' '{backup}' /y | Out-Null
  Write-Output 'registry backup written'
}}
Copy-Item '{dst_dl}' '{dest}' -Force
New-ItemProperty -Path $k -Name '{TERMES_NAME} (OpenType)' -Value '{TERMES_FILE}' -PropertyType String -Force | Out-Null
Add-Type -Namespace W -Name N -MemberDefinition '[DllImport("gdi32.dll")] public static extern int AddFontResource(string f);'
[W.N]::AddFontResource('{dest}') | Out-Null
Write-Output 'installed'
'''
    rc, out = ps(script, timeout=180)
    print('  ' + ' / '.join(l.strip() for l in out.splitlines() if l.strip())[:200])
    return font_installed(TERMES_NAME)


# --------------------------------------------------------------- packages

def pkg(name, import_as=None):
    try:
        __import__(import_as or name)
        return True
    except ImportError:
        return False


def install_pkg(name):
    r = subprocess.run([sys.executable, '-m', 'pip', 'install', name],
                       capture_output=True, text=True, timeout=600)
    return r.returncode == 0


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--install', action='store_true',
                    help='download and install anything missing')
    args = ap.parse_args()

    print('=' * 60)
    print('pandoc-math-docx: dependency check')
    print('=' * 60)
    missing = []

    # 1. pandoc
    p = find_pandoc()
    if p:
        print(f'[OK]      pandoc          {p}')
    elif args.install:
        print('[INSTALL] pandoc          not found')
        p = install_pandoc()
        print(f'{"[OK]     " if p else "[MISSING]"} pandoc          {p or "install failed"}')
        if not p:
            missing.append('pandoc')
    else:
        print('[MISSING] pandoc          run with --install')
        missing.append('pandoc')

    # 2. math font
    if font_installed(TERMES_NAME):
        print(f'[OK]      math font       {TERMES_NAME}')
    elif args.install:
        print(f'[INSTALL] math font       {TERMES_NAME} not found')
        if install_termes():
            print(f'[OK]      math font       {TERMES_NAME}')
        else:
            print(f'[MISSING] math font       falling back to Cambria Math')
            missing.append(TERMES_NAME)
    else:
        print(f'[MISSING] math font       {TERMES_NAME} - run with --install')
        missing.append(TERMES_NAME)

    # 3. python packages
    for name, imp, why in [('fonttools', 'fontTools', 'required'),
                           ('pymupdf', 'fitz', 'verification')]:
        if pkg(name, imp):
            print(f'[OK]      python          {name} ({why})')
        elif args.install:
            print(f'[INSTALL] python          {name}')
            ok = install_pkg(name)
            print(f'{"[OK]     " if ok else "[MISSING]"} python          {name}')
            if not ok:
                missing.append(name)
        else:
            print(f'[MISSING] python          {name} ({why}) - run with --install')
            missing.append(name)

    print('-' * 60)
    if missing:
        print('MISSING:', ', '.join(missing))
        if TERMES_NAME in missing:
            print(f'\nNOTE: without {TERMES_NAME}, use mathFont="Cambria Math".')
            print('Equations still render correctly, just not in a Times style.')
        return 1
    print(f'All dependencies present. Use mathFont="{TERMES_NAME}".')
    return 0


if __name__ == '__main__':
    sys.exit(main())
