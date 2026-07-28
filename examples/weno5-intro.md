# WENO5 数值格式及其在欧拉方程求解中的应用

## 1. 引言

在计算流体力学（CFD）中，含激波的可压缩流动模拟对数值格式的**激波捕捉能力**与**高阶精度**提出了双重挑战。传统的高阶格式（如二阶 TVD 格式）在光滑区域会损失精度，而在激波附近又会产生非物理振荡。五阶加权本质无振荡格式（**WENO5**）由 Jiang 与 Shu 于 1996 年系统提出，在光滑区保持高阶精度，同时以非线性权实现激波附近的essentially non-oscillatory（ENO）性质。

本文介绍 WENO5 格式的构造原理，并阐述其在求解一维 Euler 方程中的实现方法。

## 2. 守恒型 Euler 方程

一维无粘可压缩流动由如下守恒型方程组描述：

$$\frac{\partial \mathbf{U}}{\partial t} + \frac{\partial \mathbf{F}(\mathbf{U})}{\partial x} = 0$$

其中守恒变量与通量分别为

$$\mathbf{U} = \begin{pmatrix} \rho \\ \rho u \\ E \end{pmatrix}, \qquad \mathbf{F}(\mathbf{U}) = \begin{pmatrix} \rho u \\ \rho u^2 + p \\ (E + p)u \end{pmatrix}$$

式中 $\rho$ 为密度，$u$ 为速度，$p$ 为压力，$E$ 为单位体积总能。理想气体状态方程给出压力与总能的关系：

$$p = (\gamma - 1)\left(E - \tfrac{1}{2}\rho u^2\right)$$

其中 $\gamma$ 为比热比，对空气通常取 $\gamma = 1.4$。

采用有限体积法，将计算域离散为单元 $[x_{i-1/2},\, x_{i+1/2}]$，对式 (1) 积分得到半离散格式：

$$\frac{\mathrm{d} \mathbf{U}_i}{\mathrm{d} t} = -\frac{1}{\Delta x}\left(\hat{\mathbf{F}}_{i+1/2} - \hat{\mathbf{F}}_{i-1/2}\right)$$

式中 $\hat{\mathbf{F}}_{i+1/2}$ 为单元界面数值通量。对流通量的计算是 WENO 格式的核心。

## 3. WENO5 重构

### 3.1 基本思想

在单元界面 $x_{i+1/2}$ 处，需构造通量 $\hat{\mathbf{F}}_{i+1/2}$。以右通量 $f^+$ 为例，利用三个候选模板（stencil）各得到一个三阶逼近，再以**非线性权**加权平均，得到五阶精度的界面值。

定义界面 $x_{i+1/2}$ 左侧单元均值 $v_k = \bar{f}_{i+k}$（$k=-2,\dots,2$），三个三阶候选为：

$$v^{(1)} = \frac{1}{6}\left(2v_{-2} - 7v_{-1} + 11v_{0}\right)$$
$$v^{(2)} = \frac{1}{6}\left(-v_{-1} + 5v_{0} + 2v_{1}\right)$$
$$v^{(3)} = \frac{1}{6}\left(2v_{0} + 5v_{1} - v_{2}\right)$$

### 3.2 理想权与非线性权

当解在模板范围内光滑时，理想权为 $\gamma_1 = \gamma_3 = \tfrac{1}{10}$，$\gamma_2 = \tfrac{3}{5}$，此时加权即得五阶格式：

$$v^{\mathrm{ideal}} = \sum_{r=1}^{3} \gamma_r\, v^{(r)} = \frac{1}{30}\left(2v_{-2} - 13v_{-1} + 47v_{0} + 27v_{1} - 3v_{2}\right)$$

为在激波附近降低含振荡模板的权，引入基于光滑度指标的**非线性权**。第 $r$ 个模板的光滑度指标为：

$$\beta_r = \sum_{l=1}^{2} \Delta x^{2l-1} \int_{x_{i-1/2}}^{x_{i+1/2}} \left(\frac{\mathrm{d}^l p_r(x)}{\mathrm{d}x^l}\right)^2 \mathrm{d}x$$

其中 $p_r(x)$ 为第 $r$ 个模板上的重构多项式。具体地：

$$\beta_1 = \frac{13}{12}\left(v_{-2} - 2v_{-1} + v_{0}\right)^2 + \frac{1}{4}\left(v_{-2} - 4v_{-1} + 3v_{0}\right)^2$$
$$\beta_2 = \frac{13}{12}\left(v_{-1} - 2v_{0} + v_{1}\right)^2 + \frac{1}{4}\left(v_{-1} - v_{1}\right)^2$$
$$\beta_3 = \frac{13}{12}\left(v_{0} - 2v_{1} + v_{2}\right)^2 + \frac{1}{4}\left(3v_{0} - 4v_{1} + v_{2}\right)^2$$

非线性权定义为：

$$\omega_r = \frac{\tilde{\omega}_r}{\sum_{s=1}^{3}\tilde{\omega}_s}, \qquad \tilde{\omega}_r = \frac{\gamma_r}{\left(\varepsilon + \beta_r\right)^2}$$

式中 $\varepsilon$ 为防止分母为零的小量，通常取 $\varepsilon = 10^{-6}$。最终 WENO5 重构为：

$$v^{\mathrm{WENO}} = \sum_{r=1}^{3} \omega_r\, v^{(r)}$$

在光滑区 $\omega_r \to \gamma_r$，格式恢复五阶；在含间断模板上 $\beta_r$ 急剧增大，$\omega_r \to 0$，自动剔除振荡。

## 4. 通量分裂与特征分解

### 4.1 Lax–Friedrichs 通量分裂

为确定重构方向，对通量进行分裂。常用 Lax–Friedrichs 分裂：

$$f^{\pm}(\mathbf{U}) = \frac{1}{2}\left(\mathbf{F}(\mathbf{U}) \pm \alpha \mathbf{U}\right)$$

其中 $\alpha = \max_{\mathbf{U}} |\lambda(\mathbf{U})|$ 为通量雅可比矩阵谱半径的上界，$\lambda$ 为特征速度。$f^+$ 用 $x_{i+1/2}$ 左侧重构值，$f^-$ 用右侧重构值，界面通量为：

$$\hat{\mathbf{F}}_{i+1/2} = \hat{f}^{+}_{i+1/2,\mathrm{L}} + \hat{f}^{-}_{i+1/2,\mathrm{R}}$$

### 4.2 特征投影

对 Euler 方程组，在每个界面进行局部特征分解可显著提升激波分辨能力。设通量雅可比 $A = \partial \mathbf{F}/\partial \mathbf{U}$ 的右、左特征矩阵为 $R$、$L$（$L = R^{-1}$），将各分量的单元均值投影到特征空间：

$$\mathbf{w}_j = L\, \mathbf{U}_j, \qquad g_j = L\, \mathbf{F}_j$$

在特征变量 $\mathbf{w}$ 空间内逐分量进行 WENO5 重构，再投影回物理空间：

$$\hat{\mathbf{F}}_{i+1/2} = R\, \hat{\mathbf{g}}_{i+1/2}$$

特征投影计算量较大，但对强激波的稳健性显著优于逐分量重构。

## 5. 时间推进

半离散格式 (3) 得到常微分方程组，采用三阶 TVD Runge–Kutta 方法时间推进：

$$\mathbf{U}^{(1)} = \mathbf{U}^{n} + \Delta t\, \mathcal{L}(\mathbf{U}^{n})$$
$$\mathbf{U}^{(2)} = \frac{3}{4}\mathbf{U}^{n} + \frac{1}{4}\mathbf{U}^{(1)} + \frac{1}{4}\Delta t\, \mathcal{L}(\mathbf{U}^{(1)})$$
$$\mathbf{U}^{n+1} = \frac{1}{3}\mathbf{U}^{n} + \frac{2}{3}\mathbf{U}^{(2)} + \frac{2}{3}\Delta t\, \mathcal{L}(\mathbf{U}^{(2)})$$

其中 $\mathcal{L}(\mathbf{U}) = -\frac{1}{\Delta x}\left(\hat{\mathbf{F}}_{i+1/2} - \hat{\mathbf{F}}_{i-1/2}\right)$ 为空间算子。该 Runge–Kutta 格式保持 TVD 性质，与 WENO 空间离散配套使用，保证非线性稳定性。

CFL 条件为：

$$\mathrm{CFL} = \frac{(|u| + c)\Delta t}{\Delta x} \le \mathrm{CFL}_{\max}$$

其中 $c = \sqrt{\gamma p/\rho}$ 为声速，通常取 $\mathrm{CFL}_{\max} \approx 0.4 \sim 0.8$。

## 6. 算法流程

完整的 WENO5 求解 Euler 方程流程如下：

1. 初始化守恒变量 $\mathbf{U}_i^0$
2. 在每步循环中：
   - 计算界面 $x_{i+1/2}$ 处的特征矩阵 $R_{i+1/2}$、$L_{i+1/2}$
   - 对通量做 LF 分裂，并在特征空间投影
   - 对每个特征分量执行 WENO5 重构，得 $\hat{\mathbf{g}}_{i+1/2}$
   - 反投影得 $\hat{\mathbf{F}}_{i+1/2} = R\,\hat{\mathbf{g}}_{i+1/2}$
   - 计算残差 $\mathcal{L}(\mathbf{U})$
   - 三阶 TVD RK 推进至 $\mathbf{U}^{n+1}$
3. 重复至稳态或设定时刻

## 7. 小结

WENO5 格式通过多模板非线性加权，在光滑区保持五阶精度，在激波附近自动降权以避免振荡，是高分辨率可压缩流动模拟的常用工具。其与特征投影、LF 通量分裂、TVD Runge–Kutta 时间推进的组合，构成一套兼顾精度与稳健性的完整方案，广泛应用于激波管、绕流、爆轰等含强间断问题的数值模拟。
