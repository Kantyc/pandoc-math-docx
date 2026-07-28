# pandoc-math-docx 技能

用 **Pandoc** 生成包含数学公式的 Word 文档（`.docx`）。公式是**原生可编辑的 Word 方程**（OMML 格式），不是图片。

## 功能

- Markdown + LaTeX 数学公式 → Word 原生方程
- 公式自动编号（通过 3 列无边框表格实现，`\tag{}` 会被 pandoc 丢弃）
- 新罗马风格的数学字体（TeX Gyre Termes Math，Times 的字形克隆）
- 正文：汉字宋体 / 英文数字 Times New Roman
- 公式：变量斜体、运算符正体、上下标标签正体（`\mathrm{}`）
- 依赖自动检测与安装

## 目录结构

```
pandoc-math-docx/
├── SKILL.md              # 完整文档（5 步工作流 + 9 个坑）
├── README.md             # 本文件
├── scripts/
│   ├── ensure-deps.py    # 依赖检测与安装（第 0 步）
│   ├── post-process.py   # 公式编号 + 表格布局（第 3 步）
│   ├── set-mathfont.py   # 设置数学字体为 TeX Gyre Termes Math（第 3b 步）
│   ├── docx-to-pdf.ps1   # Word COM 导出 PDF（用于版式验证）
│   └── verify-fonts.py   # PDF 字体/字形提取验证
└── examples/
    ├── weno5-intro.md            # 示例源文件
    ├── WENO5数值格式介绍.docx    # 示例输出（WENO5 格式介绍）
    └── WENO5数值格式介绍.pdf     # 示例 PDF 预览
```

## 快速开始

```bash
# 0. 检测并安装依赖（首次运行）
python scripts/ensure-deps.py --install

# 1. 写 Markdown 源文件（含 LaTeX 公式），如 weno5-intro.md

# 2. Pandoc 转换
pandoc input.md -o output.docx --mathml --reference-doc=reference.docx

# 3. 后处理（公式编号 + 表格布局）
python scripts/post-process.py output.docx

# 3b. 设置数学字体
python scripts/set-mathfont.py output.docx

# 4. 用 Word/WPS 打开 output.docx 验证公式
```

## 格式要求

| 元素 | 字体 | 字形 |
|---|---|---|
| 汉字 | 宋体 SimSun | regular |
| 英文/数字 | Times New Roman | regular |
| 公式符号 | TeX Gyre Termes Math | 斜体 |
| 运算符 | TeX Gyre Termes Math | 正体 |
| 上下标标签 | TeX Gyre Termes Math | 正体 |

### LaTeX 写法要点

```markdown
变量：$u$、$\rho$、$\mathbf{u}$       → 斜体变量、粗体向量
运算符：$\mathrm{Re}$、$\mathrm{d}x$    → 正体运算符（必须 \mathrm{}）
上下标标签：$T_{\mathrm{max}}$          → 正体标签（必须 \mathrm{}）
数字上下标：$x^2$、$a_1$                → 自动正体（无需 \mathrm{}）
分式：$\frac{\partial u}{\partial t}$
积分：$\int_0^1 f\,\mathrm{d}x$
```

## 关键技术点

### 为什么用 TeX Gyre Termes Math？

- Times New Roman **没有** OpenType MATH 表，不能作数学字体
- Word 把公式变量转码到 U+1D400 数学字母平面，Times New Roman 在该区段无字形
- TeX Gyre Termes Math 是 Times 的**字形克隆**（基于 URW Nimbus Roman），带完整 MATH 表
- STIX Two Math / XITS Math 只是度量兼容，字形不是 Times（肉眼可辨）

### 重要坑（详见 SKILL.md）

1. **绝不能注入 `<m:nor/>`**——会破坏自动斜体、让括号变斜体、禁用数学引擎
2. **不能强制 Times New Roman**——U+1D400 转码导致只有数字会被改字体
3. **Word PDF 导出会丢失非 Cambria 数学字体的公式**——用 WPS 导出 PDF，或在 Word/WPS 里直接打开 .docx 验证
4. **`\tag{}` 被 pandoc 丢弃**——用表格方案编号
5. **表必须在段落之间**——放在 `<w:p>` 里是非法 OMML

## 示例

`examples/WENO5数值格式介绍.docx` 是用本技能完整流程生成的示例文档：
- 22 个编号公式
- 67 个原生 OMML 方程
- 数学字体：TeX Gyre Termes Math
- 正文：宋体 + Times New Roman
- 内容：WENO5 数值格式及其在欧拉方程求解中的应用

对应源文件：`examples/weno5-intro.md`
