---
name: pandoc-math-docx
description: "Generate Word documents containing mathematical formulas (equations, inline math, symbols) with correct typography. Use this skill whenever the user wants to create a .docx that includes equations, formulas, math notation, variables, integrals, fractions, or scientific/engineering content with math. Triggers: any request for a document with 'formulas', 'equations', 'math', '公式', '方程', '科学文档', '技术文档' in a Word/.docx file. Also use when the user asks to 'write a report/paper/document with formulas' or needs LaTeX math rendered into an editable Word document. Do NOT use for plain text documents without math, or for PDF-only output."
---

# Generate Word documents with mathematical formulas via Pandoc

This skill produces `.docx` files where formulas are **native, editable Word equations** (OMML format), not images. It uses **Pandoc** to convert Markdown+LaTeX math into Word's native equation format, then applies post-processing for correct typography.

**Mandatory formatting (格式要求):** 汉字 = 宋体 SimSun; 英文/数字 = Times New Roman (新罗马); 公式 = **TeX Gyre Termes Math** (Times-clone math font — 新罗马风格); 公式符号 = 斜体 (italic); 运算符 = 正体 (upright); 上下标 = 正体 (upright — wrap labels/units in `\mathrm{}`).

**⚠️ ALWAYS run the dependency check FIRST** — it installs pandoc and the Times-style math font if missing:

```bash
python scripts/ensure-deps.py --install
```

## Toolchain

| Tool | Purpose | Required? |
|---|---|---|
| **Pandoc** | Markdown+LaTeX → docx (OMML equations) | Yes — core engine |
| **TeX Gyre Termes Math** | Times-clone OpenType MATH font for equations | Yes — for 新罗马风格公式 |
| **Python 3** | Post-process the .docx XML (zip manipulation) | Yes — stdlib `zipfile` + `re` |
| **fontTools** | Read font metrics for the fontTable declaration | Yes — `pip install fonttools` |
| **Word COM** (optional) | Render .docx → PDF for visual verification | Recommended |
| **PyMuPDF** (optional) | Extract fonts/glyphs from PDF to verify rendering | Recommended |

## Step 0: Dependency check (ALWAYS run this first)

```bash
python scripts/ensure-deps.py            # report what's missing
python scripts/ensure-deps.py --install  # download + install it
```

This checks and installs:
1. **pandoc** — portable Windows build to `$TEMP/pandoc_extract/` if not on PATH
2. **TeX Gyre Termes Math** — downloaded from CTAN, verified to have a MATH table, installed to `C:\Windows\Fonts` + registered in HKLM
3. **fontTools / PyMuPDF** — via pip

Expected output when ready:
```
[OK]      pandoc          ...\pandoc.exe
[OK]      math font       TeX Gyre Termes Math
[OK]      python          fonttools (required)
[OK]      python          pymupdf (verification)
All dependencies present. Use mathFont="TeX Gyre Termes Math".
```

**Font install needs admin** (writes `C:\Windows\Fonts` + HKLM). If not elevated, the script says so and the workflow falls back to Cambria Math — equations still render correctly, just not in a Times style. A registry backup is written to `$TEMP/fonts-hklm-backup.reg` before the first change.

## 格式要求 / Formatting requirements

Every document this skill produces must follow these typography rules:

| 元素 Element | 字体 Font | 字形 Style | 如何实现 How |
|---|---|---|---|
| **汉字 Chinese body text** | 宋体 SimSun | regular | `--reference-doc` with `docDefaults` `eastAsia=SimSun` |
| **英文/数字 English & digits (body)** | Times New Roman (新罗马) | regular | `--reference-doc` with `ascii/eastAsia/hAnsi=Times New Roman` |
| **公式符号 Math symbols / variables** | **TeX Gyre Termes Math** (新罗马风格) | *italic* | `scripts/set-mathfont.py` — pandoc math mode auto-italicises variables |
| **运算符 Operators** (`+ − = · ∇ ∂ ∫`) | TeX Gyre Termes Math | upright (正体) | pandoc `sty="p"` auto; wrap named ops in `\mathrm{}` (e.g. `\mathrm{Re}`, `\mathrm{d}`) |
| **上下标 Sub/superscripts** | TeX Gyre Termes Math | upright (正体) | wrap subscript/superscript *text* in `\mathrm{}`; numeric indices (`a_1`) are already upright |

**Key rules for upright sub/superscripts (上下标正体):**

- A variable as an index stays italic by convention (`$a_i$` → *a*ᵢ). If the document requires *all* subscripts upright, wrap them: `$a_{\mathrm{i}}$`.
- Multi-letter / word labels MUST be `\mathrm{}`: `$T_{\mathrm{max}}$`, `$u_{\mathrm{in}}$`, `$\rho_{\mathrm{out}}$`.
- Units in superscript: `$\mathrm{kg\,m^{-3}}$` (note `\mathrm{}` wraps the whole unit group, `^{-3}` inside is upright).
- Digits are always upright — `$x^2$`, `$a_1$` need no wrapping.

### How the math font actually works (measured, not assumed)

**Times New Roman itself can never be the math font.** Two hard reasons, both verified with `fontTools`:

1. No OpenType `MATH` table → no data for stretchy brackets, fraction bars, integral sizing.
2. **No U+1D400 coverage.** Word transcodes math variables into the Unicode *Mathematical Alphanumeric Symbols* plane — the glyphs in your equations are `𝜌 𝑢 𝑥 𝐮`, not ASCII `ρ u x u`. Times New Roman has **zero** glyphs there.

```
                        MATH table   U+1D400 block
Times New Roman             no            none
TeX Gyre Termes Math        yes           full      <- use this
STIX Two Math               yes           full
XITS Math                   yes           full
Cambria Math                yes           full      <- Word default, fallback
```

**Use TeX Gyre Termes Math.** It is a *glyph-level clone* of Times (built on URW Nimbus Roman No9 L) with a complete MATH table. STIX Two Math and XITS Math are only *metric*-compatible with Times — their letterforms are redesigned and visibly not Times. Termes actually looks like 新罗马.

Word renders third-party math fonts correctly, and the equations stay native and editable. Verified: `min-termes.docx` opens in Word with no repair prompt, equations display in TeX Gyre Termes Math.

**⚠️ Do NOT try to force Times New Roman onto math runs via `w:rFonts`.** Measured result: only the *digits* change font, and they wrongly become italic; every variable stays in the math font because of the U+1D400 transcoding above. This approach is a dead end.

## Workflow (5 steps)

### Step 1: Write the Markdown source

Write a `.md` file with LaTeX math. Use standard Pandoc math syntax:

```markdown
# Section Title

Inline math: $E = mc^2$ and $\frac{\partial u}{\partial t}$.

Display equation (auto-numbered via table — see Step 3):

$$ \nabla \cdot \mathbf{u} = 0 $$

Use \mathbf{} for vectors, \mathrm{} for upright text (units, operators, sub/superscript labels like Re, max, in, out).
```

**LaTeX conventions for correct math typography:**

| What you want | LaTeX | Renders as |
|---|---|---|
| Variable (italic symbol) | `$u$`, `$\rho$` | *u*, *ρ* (auto-italic — 新罗马斜体) |
| Vector (bold) | `$\mathbf{u}$` | **u** (bold upright) |
| Upright text/unit/operator | `$\mathrm{Pa}$`, `$\mathrm{Re}$` | Pa, Re (upright — 正体) |
| Greek lowercase | `$\rho$`, `$\mu$`, `$\nu$` | ρ, μ, ν |
| Fraction | `$\frac{a}{b}$` or `$\dfrac{a}{b}$` | stacked fraction |
| Integral | `$\int_0^1 f\,\mathrm{d}x$` | ∫ with limits (∫ upright, d upright) |
| Partial derivative | `$\frac{\partial u}{\partial t}$` | ∂u/∂t (∂ operator, upright) |
| Numeric sub/superscript (upright) | `$x^2$`, `$a_1$` | x², a₁ (digits auto-upright) |
| **Word/label sub/superscript (upright)** | `$T_{\mathrm{max}}$`, `$u_{\mathrm{in}}$` | T_max, u_in (正体 — must wrap) |
| **Unit in superscript (upright)** | `$\rho = \rho_0\,\mathrm{kg\,m^{-3}}$` | ρ₀ kg m⁻³ (正体) |
| Display equation | `$$ ... $$` | centered, larger |

**⚠️ PITFALL: Always use `\mathrm{}` for multi-letter operators, units, AND sub/superscript labels.** Per the formatting requirements, operators and sub/superscripts must be upright (正体):
- Bare `$Re$` → *Re* (italic, looks like R×e). Use `$\mathrm{Re}$`.
- Bare `$T_max$` → *T**max* (italic, wrong). Use `$T_{\mathrm{max}}$`.
- Bare `$kg/m^3$` → *k**g*/*m*³ (italic, wrong). Use `$\mathrm{kg/m^3}$` or `$\mathrm{kg\,m^{-3}}$`.
- The differential `d` in integrals is an operator → `$\mathrm{d}x$`, not `$dx$`.

### Step 2: Convert with Pandoc

```bash
pandoc input.md -o output.docx --mathml
```

- `--mathml` is **mandatory** — it converts LaTeX to native OMML equations (editable in Word, not images).
- Do NOT use `--mathjax` or `--katex` — those produce images or HTML, not Word equations.
- Use `--reference-doc=reference.docx` if you need custom styles (see "Reference document" below).

### Step 3: Post-process the .docx for formula numbering + table layout

This is where the real work happens. The post-processing script handles:

1. **Equation numbering**: wrap each `$$...$$` in a 3-column borderless table (empty | centered equation | right-aligned `(N)`)
2. **Table styling**: fixed column widths, no borders, full page width
3. **Equation numbers**: Times New Roman font for `(1)`, `(2)`, etc.

Run the bundled script:

```bash
python scripts/post-process.py output.docx
```

The script prints a short summary (`Equations numbered: N`, `<m:nor/> stripped: N`) so you can confirm it ran correctly.

### Step 3b: Set the math font to TeX Gyre Termes Math

After post-processing, point the document at the Times-style math font:

```bash
python scripts/set-mathfont.py output.docx
# optional explicit font: python scripts/set-mathfont.py output.docx "Cambria Math"
```

This writes **both** required parts (missing either breaks rendering):
1. `word/settings.xml` → `<m:mathFont m:val="TeX Gyre Termes Math"/>`
2. `word/fontTable.xml` → declares the font with real metrics read via fontTools

Defaults to `TeX Gyre Termes Math`. If that font isn't installed (Step 0 wasn't run or wasn't elevated), it falls back to `Cambria Math` and warns — equations still render, just not in a Times style. Never adds `<m:nor/>` (see Pitfall 1).

**⚠️ PITFALL: Equation numbering via `\tag{}` does NOT survive Pandoc → docx conversion.** Pandoc drops `\tag{}` entirely. You MUST use the table-based approach (3-column borderless table: spacer | equation | number).

**⚠️ PITFALL: Do NOT use `\hfill` for equation numbering.** Pandoc cannot parse `\hfill` inside math and will emit a warning, producing broken output.

**⚠️ PITFALL: Do NOT use pipe tables (`|...|...|`) for equations containing `|` (absolute value, conditional probability).** The `|` character breaks Markdown table parsing. Use `\lvert` / `\rvert` or `\mid` instead.

### Step 4: Verify the output (render to PDF and check)

**⚠️ Verification caveat:** Word's *screen rendering* and its *PDF export* differ for non-Cambria math fonts. On screen, TeX Gyre Termes Math equations display correctly. But Word's `ExportAsFixedFormat` (PDF export) has been observed to **drop equations** when the math font is not Cambria Math — the equation count falls to 0 in the exported PDF while the on-screen document is fine.

So: **open the .docx in Word/WPS directly to verify the equations visually.** Treat a PDF export as unreliable for font verification when a third-party math font is in use. If a PDF preview is mandatory, fall back to `Cambria Math` for that document (equations survive PDF export) or render via LibreOffice instead of Word COM.

**Method A — open in Word/WPS (ground truth for math font):**

Open the `.docx` directly. Confirm:
- Variables are italic and look like Times (新罗马斜体)
- Operators, brackets, integrals are upright
- Equation numbers `(1)`, `(2)` are right-aligned, Times New Roman
- No table borders around equations

**Method B — render to PDF (for layout / page-flow checks only):**

```bash
# Word COM — use for layout, NOT for math-font verification (see caveat above)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/docx-to-pdf.ps1 output.docx output.pdf
```

**Method B — via LibreOffice (if Word unavailable):**
```bash
python ~/.claude/skills/docx/scripts/office/soffice.py --headless --convert-to pdf output.docx
```

Then visually inspect:
```bash
# Convert PDF pages to images and Read them
python -c "import fitz; d=fitz.open('output.pdf'); [d[i].get_pixmap(dpi=150).save(f'page{i+1}.png') for i in range(d.page_count)]"
# Then Read each page*.png to verify formulas render correctly
```

**What to check (against the formatting requirements):**
- Chinese body text is **宋体 SimSun**; English & digits are **Times New Roman**
- Variables/symbols are **italic** (新罗马斜体) — u, x, t, ρ
- Vectors are **bold** — **u**, **F**, **x**
- Operators are **upright (正体)** — +, =, ∂, ∇, ⋅, and the differential `d` in integrals
- Sub/superscript labels are **upright (正体)** — T_max, u_in, kg m⁻³ (not italic)
- Brackets/parentheses are **upright** and properly sized (stretch to match content height)
- Fractions are **stacked** (numerator over denominator), not inline slash
- Equation numbers `(1)`, `(2)` are right-aligned, Times New Roman
- No table borders visible around equations

### Step 5: Deliver

Copy the final `.docx` to the user's requested location. Optionally also deliver the `.pdf` preview.

---

## ⚠️ Critical pitfalls and how to avoid them

### Pitfall 1: DO NOT add `<m:nor/>` to math runs

**This is the #1 mistake.** If you try to change the math font by adding `<m:nor/>` (normal text mode) to equation runs, you will break everything:

- **Variables stop auto-italicizing** → you'll try to fix it by manually adding `<w:i/>`
- **Brackets and integral signs inherit the italic** → parentheses become italic (the exact bug the user reported)
- **`mathFont` setting stops working** → because normal-text mode bypasses the math engine entirely
- **Structural elements (brackets, integrals) lose auto-sizing** → they no longer stretch to match content

**Correct approach**: Leave pandoc's output **as-is** in math mode. Do NOT strip or modify `<m:sty>` tags. Do NOT inject `<m:nor/>` or `<w:rPr>` into math runs. Pandoc's default OMML is already correct:
- `sty="b"` → vectors (bold) ✓
- `sty="p"` → operators, units (upright) ✓
- No `sty` → variables (auto-italic) ✓
- `<m:d>` → brackets (auto-sized, upright) ✓
- `<m:nary>` → integrals (upright) ✓

### Pitfall 2: Times New Roman cannot be the math font — use TeX Gyre Termes Math

**Times New Roman itself can never be the math font** (no MATH table, no U+1D400 coverage — see "How the math font actually works" above). But a **Times-clone with a MATH table** works: set `mathFont` to **TeX Gyre Termes Math** via `scripts/set-mathfont.py`. Word renders it natively and equations stay editable.

What does **not** work, all measured:
- Forcing `w:rFonts="Times New Roman"` onto `<m:r>` runs → only digits change font, and they wrongly italicize; variables stay in the math font (U+1D400 transcoding).
- `<m:nor/>` (normal text mode) → breaks auto-italic, makes brackets italic, disables the math engine. See Pitfall 1.

Among Times-style math fonts, **prefer TeX Gyre Termes Math** (glyph clone of Times). STIX Two Math and XITS Math are only metric-compatible — their letterforms are visibly not Times, as the user confirmed by eye.

**Fallback:** if TeX Gyre Termes Math is not installed and cannot be (no admin), use `Cambria Math`. Equations render correctly, just not in a Times style.

### Pitfall 3: Pandoc's `\tag{}` is silently dropped

When converting LaTeX to docx, Pandoc **completely discards** `\tag{1}`, `\tag{2}`, etc. The equation appears without a number. There is no Pandoc flag to preserve tags.

**Solution**: Use the post-processing script's table-based numbering (Step 3). The script wraps each display equation in a 3-column borderless table where the right column holds `(N)`.

### Pitfall 4: Long display equations break table layout

If a display equation is too long for the center column, pandoc's pipe-table fallback (equal-width columns) causes it to wrap mid-equation.

**Solution**: The post-processing script forces **fixed column widths** (spacer=136dxa, equation=7100dxa, number=682dxa) and `tblLayout=fixed` + `tblW=100%`. This gives the equation column ~4.9 inches, enough for most equations. For extremely long equations, consider splitting or using `\resizebox` (not supported — restructure instead).

### Pitfall 5: Chinese + English body fonts (汉字宋体 / 英文新罗马)

Per the formatting requirements, body text must be **汉字 = 宋体 SimSun**, **英文/数字 = Times New Roman**. Pandoc's default reference doc does NOT set this — you must supply a `--reference-doc` whose `word/styles.xml` `docDefaults` sets:

```xml
<w:rPrDefault><w:rPr>
  <w:rFonts w:ascii="Times New Roman" w:eastAsia="SimSun" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>
</w:rPr></w:rPrDefault>
```

- `ascii`/`hAnsi` = Times New Roman → English & digits (新罗马)
- `eastAsia` = SimSun → Chinese (宋体)
- Build the reference.docx once: create a blank docx (or `pandoc -o ref.docx --print-default-data-file reference.docx` then edit `word/styles.xml`), or generate via `python-docx`.
- Always pass `--reference-doc=reference.docx` in Step 2.
- Math formulas use the math font set by `scripts/set-mathfont.py` (TeX Gyre Termes Math by default), independent of body font settings.

### Pitfall 6: File locking on cloud-synced directories

If the output directory is under WPS Cloud Drive, OneDrive, or similar sync services, the `.docx` may be **locked** by the sync process. You'll get "permission denied" when trying to write or overwrite.

**Solution**: Generate the file in a local temp directory (`$TEMP`), then copy to the destination. If copy fails, save with a different filename and inform the user.

### Pitfall 7: PowerShell script paths with non-ASCII characters

When passing file paths containing Chinese characters to PowerShell `-File` parameter, the path may get garbled (mojibake).

**Solution**: Copy scripts to `$TEMP` (pure ASCII path) before invoking, or pass paths as arguments rather than embedding in `-File`.

### Pitfall 8: `\mathrm{}` vs bare text in math mode

Inside `$...$`, everything is math mode by default — letters render italic. Multi-letter sequences like `kg`, `Pa`, `Re` will appear as *k**g*, *P**a*, *R**e* (each letter separately italicized).

**Rule**: Wrap any non-variable text in `\mathrm{}`:
- Units: `$\mathrm{kg/m^3}$`, `$\mathrm{Pa \cdot s}$`
- Named operators: `$\mathrm{Re}$` (Reynolds number), `$\mathrm{Pr}$` (Prandtl number)
- Text labels: `$\mathrm{out}$`, `$\mathrm{in}$`

### Pitfall 9: Word COM is slow on large documents

Documents with 50+ equations can take minutes to process via Word COM (opening, setting fonts, exporting to PDF).

**Solution**: Be patient, use `run_in_background` for long operations, and kill any zombie `WINWORD.EXE` processes before starting:
```bash
powershell.exe -NoProfile -Command "Get-Process WINWORD -ErrorAction SilentlyContinue | Stop-Process -Force"
```

---

## Post-processing script reference

The `scripts/post-process.py` script performs these transformations on the pandoc-generated `.docx`:

1. **Extract** the .docx (it's a ZIP of XML files)
2. **Strip any `<m:nor/>`** and injected `<w:rPr>` from math runs (safety net — restores pure math mode)
3. **Wrap display equations** in 3-column borderless tables for numbering
4. **Set table properties**: fixed layout, 100% width, specific column widths, all borders = nil
5. **Set equation numbers** to Times New Roman
6. **Re-zip** back into .docx

The `scripts/docx-to-pdf.ps1` script uses Word COM to export to PDF for verification.

---

## Quick reference: the complete one-liner workflow

```bash
# 0. Check & install deps (pandoc + TeX Gyre Termes Math + python pkgs) — run ONCE
python ~/.claude/skills/pandoc-math-docx/scripts/ensure-deps.py --install
# 1. Write source (you write input.md with LaTeX math)
# 2. Convert
pandoc input.md -o output.docx --mathml --reference-doc=reference.docx
# 3. Post-process (numbering + table layout + strip <m:nor/>)
python ~/.claude/skills/pandoc-math-docx/scripts/post-process.py output.docx
# 3b. Set math font to TeX Gyre Termes Math (新罗马风格公式)
python ~/.claude/skills/pandoc-math-docx/scripts/set-mathfont.py output.docx
# 4. Verify — open in Word/WPS directly (PDF export drops non-Cambria math fonts)
#    (optional layout check via PDF, but do NOT trust it for font verification)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ~/.claude/skills/pandoc-math-docx/scripts/docx-to-pdf.ps1 output.docx output.pdf
python -c "import fitz; d=fitz.open('output.pdf'); [d[i].get_pixmap(dpi=150).save(f'page{i+1}.png') for i in range(d.page_count)]"
# Read page*.png files to visually verify (note: equations may be absent in PDF if math font != Cambria Math)
# 5. Deliver output.docx to user
```

## When NOT to use this skill

- **Plain text documents** without any math → use the `docx` skill (docx-js) or pandoc without `--mathml`
- **PDF-only output** → use LaTeX (pdflatex/xelatex) directly for better control
- **Equations as images** → not what this skill does; use matplotlib or LaTeX → PNG
- **Spreadsheets with formulas** → use openpyxl or the docx skill's table features
