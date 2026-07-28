# 数学公式示例文档

本文件演示如何在 Markdown 中正确书写数学公式，并通过 Pandoc 转换为 Word 原生公式。

## 行内公式

动量方程左端加速度项 $\frac{\partial \mathbf{u}}{\partial t}$ 表示局部变化率。
雷诺数 $\mathrm{Re} = \frac{\rho U L}{\mu}$ 为无量纲数（注意 $\mathrm{Re}$ 用 `\mathrm` 保持正体）。
单位记号如 $\mathrm{kg/m^{3}}$、$\mathrm{Pa \cdot s}$ 也需要用 `\mathrm` 包裹。

## 展示公式（自动编号）

连续性方程：

$$ \nabla \cdot \mathbf{u} = 0 $$

动量方程：

$$ \rho \left( \frac{\partial \mathbf{u}}{\partial t} + (\mathbf{u} \cdot \nabla) \mathbf{u} \right) = -\nabla p + \mu \nabla^{2} \mathbf{u} + \mathbf{f} $$

能量耗散率：

$$ \varepsilon = 2\nu \int_{V} \mathbf{S} : \mathbf{S} \, \mathrm{d}V $$

## 常见排版规则

| 类型 | LaTeX 写法 | 效果 |
|---|---|---|
| 标量变量 | `$u$` | *u*（斜体） |
| 向量 | `$\mathbf{u}$` | **u**（粗体） |
| 希腊字母 | `$\rho$, $\mu$, $\nu$` | ρ, μ, ν |
| 单位/算子 | `$\mathrm{Re}$, $\mathrm{Pa}$` | Re, Pa（正体） |
| 分式 | `$\frac{a}{b}$` | 上下结构 |
| 偏导 | `$\frac{\partial u}{\partial t}$` | ∂u/∂t |
| 积分 | `$\int_0^1 f(x)\,dx$` | ∫₀¹ |
| 上下标 | `$x^2$, $a_i$` | x², aᵢ |
