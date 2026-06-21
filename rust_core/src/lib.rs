use pyo3::prelude::*;

/// Simple Moving Average
#[pyfunction]
fn calculate_sma(data: Vec<f64>, window: usize) -> PyResult<Vec<f64>> {
    if window == 0 || data.len() < window { return Ok(vec![0.0; data.len()]); }
    let mut result = vec![0.0; data.len()];
    for i in (window - 1)..data.len() {
        let sum: f64 = data[i + 1 - window..=i].iter().sum();
        result[i] = sum / window as f64;
    }
    Ok(result)
}

/// Exponential Moving Average
#[pyfunction]
fn calculate_ema(data: Vec<f64>, window: usize) -> PyResult<Vec<f64>> {
    if window == 0 || data.is_empty() { return Ok(vec![0.0; data.len()]); }
    let alpha = 2.0 / (window as f64 + 1.0);
    let mut result = vec![0.0; data.len()];
    result[0] = data[0];
    for i in 1..data.len() { result[i] = data[i] * alpha + result[i - 1] * (1.0 - alpha); }
    Ok(result)
}

/// Average True Range
#[pyfunction]
fn calculate_atr(highs: Vec<f64>, lows: Vec<f64>, closes: Vec<f64>, window: usize) -> PyResult<Vec<f64>> {
    let mut tr = vec![0.0; highs.len()];
    tr[0] = highs[0] - lows[0];
    for i in 1..highs.len() {
        let hl = highs[i] - lows[i];
        let hpc = (highs[i] - closes[i - 1]).abs();
        let lpc = (lows[i] - closes[i - 1]).abs();
        tr[i] = hl.max(hpc).max(lpc);
    }
    calculate_sma(tr, window)
}

/// Z-Score
#[pyfunction]
fn calculate_zscore(data: Vec<f64>, window: usize) -> PyResult<Vec<f64>> {
    let mut result = vec![0.0; data.len()];
    for i in (window - 1)..data.len() {
        let slice = &data[i + 1 - window..=i];
        let mean = slice.iter().sum::<f64>() / window as f64;
        let variance = slice.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / window as f64;
        result[i] = if variance > 0.0 { (data[i] - mean) / variance.sqrt() } else { 0.0 };
    }
    Ok(result)
}

/// Spread between two series
#[pyfunction]
fn calculate_spread(a: Vec<f64>, b: Vec<f64>) -> PyResult<Vec<f64>> {
    let spread: Vec<f64> = a.iter().zip(b.iter()).map(|(x, y)| x - y).collect();
    Ok(spread)
}

/// Full Z-Score (including initial window)
#[pyfunction]
fn calculate_zscore_full(data: Vec<f64>, window: usize) -> PyResult<Vec<f64>> {
    let mut result = vec![0.0; data.len()];
    for i in 0..data.len() {
        if i < window - 1 {
            result[i] = 0.0;
        } else {
            let slice = &data[i + 1 - window..=i];
            let mean = slice.iter().sum::<f64>() / window as f64;
            let variance = slice.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / window as f64;
            result[i] = if variance > 0.0 { (data[i] - mean) / variance.sqrt() } else { 0.0 };
        }
    }
    Ok(result)
}

/// Matrix orthogonalization (Gram-Schmidt)
#[pyfunction]
fn fast_orthogonalize(matrix: Vec<Vec<f64>>) -> PyResult<Vec<Vec<f64>>> {
    if matrix.is_empty() { return Ok(matrix); }
    let n = matrix.len();
    let m = matrix[0].len();
    let mut q = vec![vec![0.0; m]; n];
    for i in 0..n {
        let mut v = matrix[i].clone();
        for j in 0..i {
            let dot: f64 = matrix[i].iter().zip(q[j].iter()).map(|(a, b)| a * b).sum();
            for k in 0..m { v[k] -= dot * q[j][k]; }
        }
        let norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm > 1e-10 { for k in 0..m { q[i][k] = v[k] / norm; } }
    }
    Ok(q)
}

/// Sharpe Ratio from portfolio-values series (annualized, risk-free=0)
#[pyfunction]
fn calculate_sharpe_ratio(portfolio_values: Vec<f64>) -> f64 {
    if portfolio_values.len() < 2 { return 0.0; }
    let n = portfolio_values.len() - 1;
    let mut returns = vec![0.0; n];
    for i in 0..n {
        if portfolio_values[i] > 0.0 {
            returns[i] = (portfolio_values[i + 1] - portfolio_values[i]) / portfolio_values[i];
        }
    }
    let mean = returns.iter().sum::<f64>() / n as f64;
    // Sample std (ddof=1) — align with NumPy/pandas CFA convention.
    let denom = if n > 1 { (n - 1) as f64 } else { n as f64 };
    let variance = returns.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / denom;
    if variance > 0.0 { mean / variance.sqrt() * 252.0_f64.sqrt() } else { 0.0 }
}

/// Maximum Drawdown (percentage) from portfolio-values series
#[pyfunction]
fn calculate_max_drawdown(portfolio_values: Vec<f64>) -> f64 {
    if portfolio_values.is_empty() { return 0.0; }
    let mut peak = portfolio_values[0];
    let mut max_dd = 0.0;
    for &v in &portfolio_values[1..] {
        if v > peak { peak = v; }
        let dd = (peak - v) / peak * 100.0;
        if dd > max_dd { max_dd = dd; }
    }
    max_dd
}

/// Annualized return (percentage) from initial/final values and total days
#[pyfunction]
fn calculate_annual_return(initial_capital: f64, final_value: f64, total_days: f64) -> f64 {
    if initial_capital <= 0.0 || total_days <= 0.0 { return 0.0; }
    ((final_value / initial_capital).powf(250.0 / total_days) - 1.0) * 100.0
}

/// Batch calculate multiple indicators
#[pyfunction]
fn batch_calculate(data: Vec<f64>, indicators: Vec<String>) -> PyResult<Vec<Vec<f64>>> {
    let mut results: Vec<Vec<f64>> = Vec::new();
    for indicator in indicators {
        let result = match indicator.as_str() {
            "sma_5" => calculate_sma(data.clone(), 5).unwrap_or_default(),
            "sma_10" => calculate_sma(data.clone(), 10).unwrap_or_default(),
            "sma_20" => calculate_sma(data.clone(), 20).unwrap_or_default(),
            "ema_5" => calculate_ema(data.clone(), 5).unwrap_or_default(),
            "ema_10" => calculate_ema(data.clone(), 10).unwrap_or_default(),
            "ema_20" => calculate_ema(data.clone(), 20).unwrap_or_default(),
            "zscore_20" => calculate_zscore(data.clone(), 20).unwrap_or_default(),
            _ => vec![0.0; data.len()],
        };
        results.push(result);
    }
    Ok(results)
}



/// Calculate chip distribution metrics from price/volume data.
///
/// Args:
///     prices: Historical closing prices
///     volumes: Historical volumes matching prices length
///     total_shares: Total circulating shares
///
/// Returns a dict as Vec<f64>: [profit_ratio, avg_cost, concentration_90, concentration_70]
#[pyfunction]
fn calculate_chip_distribution(
    prices: Vec<f64>,
    volumes: Vec<f64>,
    total_shares: f64,
) -> PyResult<Vec<f64>> {
    if prices.is_empty() || volumes.is_empty() || total_shares <= 0.0 {
        return Ok(vec![0.0; 4]);
    }

    let n = prices.len().min(volumes.len());

    // 1. Estimate cost basis per price level (weighted by volume)
    //    Using a simplified model: each price level contributes proportionally
    let total_volume: f64 = volumes.iter().sum();
    if total_volume <= 0.0 {
        return Ok(vec![0.0; 4]);
    }

    // Weighted average cost
    let avg_cost: f64 = prices.iter()
        .zip(volumes.iter())
        .take(n)
        .map(|(p, v)| p * v)
        .sum::<f64>() / total_volume;

    // 2. Profit ratio: percentage of shares in profit (price < current close)
    let current_price = prices[n - 1];
    let profitable_volume: f64 = prices.iter()
        .zip(volumes.iter())
        .take(n)
        .filter(|(p, _)| **p <= current_price)
        .map(|(_, v)| v)
        .sum();
    let profit_ratio = (profitable_volume / total_volume) * 100.0;

    // 3. Concentration: estimate dispersion around avg_cost
    //    90% concentration = 90th percentile distance from avg_cost
    //    70% concentration = 70th percentile distance from avg_cost
    let mut deviations: Vec<f64> = prices.iter()
        .take(n)
        .map(|p| (p - avg_cost).abs())
        .collect();
    deviations.sort_by(|a, b| a.partial_cmp(b).unwrap());

    let concentration_90 = if n > 0 {
        let idx = ((n as f64) * 0.90) as usize;
        (deviations[idx.min(n - 1)] / avg_cost.max(1.0)) * 100.0
    } else {
        0.0
    };

    let concentration_70 = if n > 0 {
        let idx = ((n as f64) * 0.70) as usize;
        (deviations[idx.min(n - 1)] / avg_cost.max(1.0)) * 100.0
    } else {
        0.0
    };

    Ok(vec![profit_ratio, avg_cost, concentration_90, concentration_70])
}

#[pymodule]
fn quant_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(calculate_sma, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_ema, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_atr, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_zscore, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_spread, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_zscore_full, m)?)?;
    m.add_function(wrap_pyfunction!(fast_orthogonalize, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_sharpe_ratio, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_max_drawdown, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_annual_return, m)?)?;
    m.add_function(wrap_pyfunction!(batch_calculate, m)?)?;
    m.add_function(wrap_pyfunction!(calculate_chip_distribution, m)?)?;
    Ok(())
}
