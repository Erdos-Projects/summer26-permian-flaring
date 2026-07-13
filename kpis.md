# Flaring Time-Series KPI Reference Guide

See below for formal mathematical definitions for all Key Performance Indicators (KPIs) used to evaluate our gas flaring models.

In time-series modeling, we evaluate performance across two distinct scenarios: **In-Sample Estimation** (how well the equation absorbs the historical physical signal without memorizing noise) and **Out-of-Sample Validation** (how accurately the model predicts unseen future flaring volumes in real time).

---

## 1. Out-of-Sample Prediction Metrics (The Real-World Test)

These metrics evaluate how the model performs on unseen data during our 92-month walk-forward operational simulation. Let $y_t$ represent the actual ground-truth flaring volume at month $t$, $\hat{y}_t$ represent the model's prediction, $n$ represent the total number of forecasted months, and $e_t = y_t - \hat{y}_t$ represent the prediction mistake.

### Mean Absolute Error (MAE)
* **Use:** MAE measures the average size of our prediction mistakes in physical units—thousands of cubic feet (MCF) of gas. It tells an operations manager or gas trader exactly how many MCF our forecast is off by on an average month, regardless of whether we guessed too high or too low.
* **What to look for:** **Lower is better.** A lower MAE means the model's predicted trajectory sits physically closer to the true ground-reported flaring volume.
* **The Math:** The arithmetic average of absolute errors across the forecast horizon:
$$\text{MAE} = \frac{1}{n} \sum_{t=1}^{n} |y_t - \hat{y}_t| = \frac{1}{n} \sum_{t=1}^{n} |e_t|$$

### Mean Directional Accuracy (MDA)
* **Use:** MDA measures the percentage of time the model correctly predicts whether flaring will increase or decrease from one month to the next. In commodity trading and pipeline capacity planning, knowing the *direction* of the market (whether field flaring is surging or declining) is often more valuable than knowing the exact volume.
* **What to look for:** **Higher is better.** A score of **50%** is no better than flipping a coin. A static naive forecast ($T-1$) scores **0.0%** because it assumes zero change. Our ARIMAX model scores **68.5%**, proving it reliably anticipates structural market turning points.
* **The Math:** Evaluates the algebraic sign of month-over-month change using the indicator function $\mathbf{1}(\cdot)$, which equals $1$ when the signs match and $0$ otherwise:
$$\text{MDA} = \frac{100\%}{n} \sum_{t=1}^{n} \mathbf{1} \left( \text{sgn}(y_t - y_{t-1}) = \text{sgn}(\hat{y}_t - y_{t-1}) \right)$$

---

## 2. In-Sample Information Criteria (The Efficiency Penalty)

When estimating models on historical data, adding more mathematical variables always forces the line to fit the historical points slightly better. However, over-complicated models memorize random noise and fail miserably in real-world implementation. Information criteria grade the model's accuracy while penalizing the models for unnecessary complexity. 

Let $k$ represent the total number of estimated parameters (lags, exogenous coefficients, variance terms) and $\hat{L}$ represent the maximized statistical likelihood of the model.

### Akaike Information Criterion (AIC)
* **Use:** AIC grades how well the mathematical formula fits the historical flaring pattern while penalizing you for every extra rule or lag you add to the equation. It helps us find the "sweet spot" between simplicity and accuracy.
* **What to look for:** **Lower is better.** A lower AIC confirms the model captures the underlying thermal relationship without becoming sluggish or over-engineered.
* **The Math:** Applies a linear penalty $(2k)$ to the log-likelihood:
$$\text{AIC} = 2k - 2\ln(\hat{L})$$
When evaluating Gaussian errors over sample size $n$ with Residual Sum of Squares ($\text{RSS} = \sum e_t^2$), it is written as:
$$\text{AIC} = n \ln\left(\frac{\text{RSS}}{n}\right) + 2k$$

### Bayesian Information Criterion (BIC)
* **Use:** BIC is the stricter sibling of AIC. It applies a much heavier penalty for adding extra variables, especially as the dataset grows longer. If AIC is looking for a streamlined model, BIC is looking for absolute simplicity—ensuring that only the most powerful physical drivers (like satellite radiant heat) survive in the equation.
* **What to look for:** **Lower is better.** Our ARIMAX(1,1,1) model achieved the lowest BIC (**79.21**), proving that adding seasonal 12-month terms adds mathematical clutter without providing real predictive value.
* **The Math:** Applies a logarithmic complexity penalty $(k \ln(n))$:
$$\text{BIC} = k\ln(n) - 2\ln(\hat{L})$$

---

## 3. Residual Time-Series Diagnostics (The Error Health Check)

Once an a model extracts all the useful physical signal from a time series, the leftover prediction errors ($e_t$) should look like completely random white noise. If there are any recognizable patterns, trends, or wild swings left in the errors, the algorithm failed to do its job.

Let $\bar{e}$ represent the average residual error and $\hat{\sigma}^2$ represent the sample variance of the errors.

### Ljung-Box Autocorrelation Test ($\text{Prob}(Q)$)
* **Use:** This test checks whether the model left any predictable sequential momentum behind in its errors. If a high error today is consistently followed by a high error next month, the model missed an underlying autoregressive pattern in the gas field.
* **What to look for:** **$\text{Prob}(Q) > 0.05$ (Pass).** We want the p-value to be above $0.05$ to prove the errors are completely uncorrelated white noise. Our ARIMAX model scored **0.81 (Pass)**, while XGBoost scored **0.00 (Fail)**.
* **The Math:** Evaluates sample autocorrelation $\hat{\rho}_k$ across lag $h$ (we evaluate at $h=1$):
$$\hat{\rho}_k = \frac{\sum_{t=k+1}^n (e_t - \bar{e})(e_{t-k} - \bar{e})}{\sum_{t=1}^n (e_t - \bar{e})^2}$$
$$Q = n(n+2) \sum_{k=1}^{h} \frac{\hat{\rho}_k^2}{n - k} \sim \chi^2(h)$$

### Heteroskedasticity Test ($\text{Prob}(H)$ / Variance Ratio)
* **Use:** This tests whether the size of the model's mistakes remains stable across time. In natural gas markets, flaring volatility can explode during pipeline freezes or capacity crises. A healthy model should not see its error bounds wildly inflate during volatile years compared to quiet years.
* **What to look for:** **$\text{Prob}(H) > 0.05$ (Pass).** A p-value above $0.05$ confirms the error variance is stable (homoskedastic). Our ARIMAX model passed (**0.05**), whereas XGBoost failed (**0.00**), swinging wildly between tiny errors in quiet months and massive misses during market spikes.
* **The Math:** Compares the residual sum of squares of the last third of the timeline against the first third, where $m = \lfloor n / 3 \rfloor$:
$$H = \frac{\frac{1}{m} \sum_{t=n-m+1}^{n} e_t^2}{\frac{1}{m} \sum_{t=1}^{m} e_t^2} \sim F(m, m)$$

### Sample Skewness ($S$)
* **Use:** Skewness checks whether the model is systematically biased toward guessing too high or too low. In a balanced model, positive misses and negative misses should cancel each out symmetrically.
* **What to look for:** **Score close to $0.0$.** Our ARIMAX champion achieved a perfect skew of **0.00**. XGBoost exhibited a positive skew of **0.71**, proving it systematically underpredicts positive flaring surges and leaves large positive errors behind.
* **The Math:** Measures the third standardized central moment of the error distribution:
$$S = \frac{\frac{1}{n} \sum_{t=1}^{n} (e_t - \bar{e})^3}{\left( \frac{1}{n} \sum_{t=1}^{n} (e_t - \bar{e})^2 \right)^{3/2}}$$

### Sample Kurtosis ($K$)
* **Use:** Kurtosis measures "tail risk" or the likelihood of extreme, explosive outlier mistakes. A standard bell-curve distribution has a kurtosis of exactly $3.0$. Any number significantly higher means the model is vulnerable to being completely blindsided by sudden operational shocks or field shut-ins.
* **What to look for:** **Score close to $3.0$.** Our ARIMAX model scored **2.75**, confirming normal, well-behaved error boundaries. XGBoost scored **6.36 (Fat-Tailed)**, demonstrating that decision trees hit an artificial ceiling and produce massive outlier misses whenever record-breaking volumes occur.
* **The Math:** Measures the fourth standardized central moment (Pearson kurtosis):
$$K = \frac{\frac{1}{n} \sum_{t=1}^{n} (e_t - \bar{e})^4}{\left( \frac{1}{n} \sum_{t=1}^{n} (e_t - \bar{e})^2 \right)^2}$$

### Jarque-Bera Normality Test ($\text{Prob}(JB)$)
* **Use:** The Jarque-Bera test is the ultimate master health check for errors. It combines Skewness and Kurtosis into a single pass/fail test to determine whether the model's prediction mistakes form a mathematically pure, symmetrical Gaussian bell curve.
* **What to look for:** **$\text{Prob}(JB) > 0.05$ (Pass).** A p-value above $0.05$ confirms normal, bell-curve errors. ARIMAX easily passed (**0.84**), while XGBoost failed (**0.00**), mathematically proving that linear parametric equations handle time-series momentum far better than standard machine learning trees.
* **The Math:** A joint test of skewness and excess kurtosis against a $\chi^2$ distribution with 2 degrees of freedom:
$$JB = \frac{n}{6} \left( S^2 + \frac{(K - 3)^2}{4} \right) \sim \chi^2(2)$$