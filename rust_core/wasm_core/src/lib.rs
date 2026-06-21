extern crate wasm_bindgen;
use wasm_bindgen::prelude::*;

/// Simple Moving Average — pure Rust, no stdlib dependency
#[wasm_bindgen]
pub fn calculate_sma(data: &[f64], window: usize) -> Vec<f64> {
    if window == 0 || data.len() < window {
        return vec![0.0; data.len()];
    }
    let mut result = vec![0.0; data.len()];
    for i in (window - 1)..data.len() {
        let sum: f64 = data[i + 1 - window..=i].iter().sum();
        result[i] = sum / window as f64;
    }
    result
}

/// Exponential Moving Average
#[wasm_bindgen]
pub fn calculate_ema(data: &[f64], window: usize) -> Vec<f64> {
    if window == 0 || data.is_empty() {
        return vec![0.0; data.len()];
    }
    let alpha = 2.0 / (window as f64 + 1.0);
    let mut result = vec![0.0; data.len()];
    result[0] = data[0];
    for i in 1..data.len() {
        result[i] = data[i] * alpha + result[i - 1] * (1.0 - alpha);
    }
    result
}

/// Average True Range
#[wasm_bindgen]
pub fn calculate_atr(highs: &[f64], lows: &[f64], closes: &[f64], window: usize) -> Vec<f64> {
    let n = highs.len().min(lows.len()).min(closes.len());
    if n < window + 1 {
        return vec![0.0; n];
    }
    let mut tr = vec![0.0; n];
    tr[0] = highs[0] - lows[0];
    for i in 1..n {
        let hl = highs[i] - lows[i];
        let hpc = (highs[i] - closes[i - 1]).abs();
        let lpc = (lows[i] - closes[i - 1]).abs();
        tr[i] = hl.max(hpc).max(lpc);
    }
    // SMA of TR
    let mut atr = vec![0.0; n];
    for i in (window - 1)..n {
        let sum: f64 = tr[i + 1 - window..=i].iter().sum();
        atr[i] = sum / window as f64;
    }
    atr
}

/// Z-Score normalization
#[wasm_bindgen]
pub fn calculate_zscore(data: &[f64], window: usize) -> Vec<f64> {
    let mut result = vec![0.0; data.len()];
    for i in (window - 1)..data.len() {
        let slice = &data[i + 1 - window..=i];
        let mean = slice.iter().sum::<f64>() / window as f64;
        let variance = slice.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / window as f64;
        result[i] = if variance > 0.0 { (data[i] - mean) / variance.sqrt() } else { 0.0 };
    }
    result
}

/// Sharpe Ratio (annualized)
#[wasm_bindgen]
pub fn calculate_sharpe_ratio(portfolio_values: &[f64]) -> f64 {
    if portfolio_values.len() < 2 { return 0.0; }
    let n = portfolio_values.len() - 1;
    let mut returns = vec![0.0; n];
    for i in 0..n {
        if portfolio_values[i] > 0.0 {
            returns[i] = (portfolio_values[i + 1] - portfolio_values[i]) / portfolio_values[i];
        }
    }
    let mean = returns.iter().sum::<f64>() / n as f64;
    let denom = if n > 1 { (n - 1) as f64 } else { n as f64 };
    let variance = returns.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / denom;
    if variance > 0.0 { mean / variance.sqrt() * 252.0_f64.sqrt() } else { 0.0 }
}

/// Max Drawdown percentage
#[wasm_bindgen]
pub fn calculate_max_drawdown(portfolio_values: &[f64]) -> f64 {
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

/// Batch calculate: returns JSON string of all results
#[wasm_bindgen]
pub fn batch_calculate(data: &[f64], indicators: &[JsValue]) -> JsValue {
    let indicator_names: Vec<String> = indicators.iter()
        .filter_map(|v| v.as_string())
        .collect();
    let mut results = Vec::new();
    for name in &indicator_names {
        let r = match name.as_str() {
            "sma_5" => calculate_sma(data, 5),
            "sma_10" => calculate_sma(data, 10),
            "sma_20" => calculate_sma(data, 20),
            "ema_5" => calculate_ema(data, 5),
            "ema_10" => calculate_ema(data, 10),
            "ema_20" => calculate_ema(data, 20),
            "zscore_20" => calculate_zscore(data, 20),
            _ => vec![0.0; data.len()],
        };
        results.push(r);
    }
    serde_wasm_bindgen::to_value(&results).unwrap_or(JsValue::NULL)
}
