import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import os
import time
import warnings

warnings.filterwarnings('ignore')

# ====================== 配置 ======================
CSV_INPUT = "stock_list.csv"  # 你的6位股票代码列表
OUTPUT_DIR = "financial_analysis"
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ====================== 辅助函数 ======================
def get_stock_list():
    df = pd.read_csv(CSV_INPUT)
    possible_cols = ['code', 'Code', 'symbol', '股票代码', '代码']
    code_col = next((col for col in possible_cols if col in df.columns), None)
    if not code_col:
        raise ValueError("未找到代码列！")
    return df[code_col].astype(str).str.strip().str.zfill(6).tolist()


def get_latest_price(code: str):
    """使用你之前的三个接口获取最新收盘价（取 Close）"""
    try:
        # 优先用你已有的最新数据函数（推荐复用）
        from update_daily_latest import get_latest_trading_day  # 如果已集成
        df_latest, _ = get_latest_trading_day(code)
        if df_latest is not None and not df_latest.empty:
            return df_latest['Close'].iloc[0]
    except:
        pass
    return None


# ====================== 主分析函数 ======================
def analyze_single_stock(code: str):
    print(f"正在分析 {code} ...")
    results = {'code': code, 'analysis_date': datetime.today().strftime('%Y-%m-%d')}

    try:
        # 1. 财务摘要（包含部分关键指标）
        abstract = ak.stock_financial_abstract(symbol=code)
        if not abstract.empty:
            latest_abstract = abstract.iloc[0]  # 最新一期
            results.update({
                '每股净资产': latest_abstract.get('每股净资产-摊薄/期末股数'),
                '每股收益': latest_abstract.get('基本每股收益'),
                '净利润': latest_abstract.get('净利润'),
                '主营业务收入': latest_abstract.get('主营业务收入'),
            })

        # 2. 利润表（用于成长性、净利率）
        profit = ak.stock_financial_report_sina(stock=code, symbol="利润表")
        if not profit.empty:
            profit = profit.sort_values('报告日期', ascending=False)
            latest_profit = profit.iloc[0]
            prev_profit = profit.iloc[1] if len(profit) > 1 else None

            results['净利润（最新）'] = latest_profit.get('净利润')
            results['营业收入（最新）'] = latest_profit.get('营业收入')
            results['净利率'] = (
                        latest_profit.get('净利润') / latest_profit.get('营业收入') * 100) if latest_profit.get(
                '营业收入') else None

            # 成长性指标
            if prev_profit is not None:
                results['净利润增长率(%)'] = ((latest_profit.get('净利润') - prev_profit.get('净利润')) /
                                              abs(prev_profit.get('净利润')) * 100) if prev_profit.get(
                    '净利润') else None
                results['营收增长率(%)'] = ((latest_profit.get('营业收入') - prev_profit.get('营业收入')) /
                                            abs(prev_profit.get('营业收入')) * 100) if prev_profit.get(
                    '营业收入') else None

        # 3. 资产负债表（用于 ROE、杜邦分析）
        balance = ak.stock_financial_report_sina(stock=code, symbol="资产负债表")
        if not balance.empty:
            balance = balance.sort_values('报告日期', ascending=False)
            latest_balance = balance.iloc[0]

            roe = None
            if '净利润' in latest_profit and '股东权益合计' in latest_balance:
                roe = (latest_profit.get('净利润') / latest_balance.get('股东权益合计') * 100)
                results['ROE(%)'] = roe

            # 杜邦分析三因素
            if '净利润' in latest_profit and '营业收入' in latest_profit and '总资产' in latest_balance and '股东权益合计' in latest_balance:
                net_margin = latest_profit.get('净利润') / latest_profit.get('营业收入')  # 净利率
                asset_turnover = latest_profit.get('营业收入') / latest_balance.get('总资产')  # 资产周转率
                equity_multiplier = latest_balance.get('总资产') / latest_balance.get('股东权益合计')  # 权益乘数

                results.update({
                    '净利率(%)': net_margin * 100,
                    '资产周转率': asset_turnover,
                    '权益乘数': equity_multiplier,
                    '杜邦ROE(%)': net_margin * asset_turnover * equity_multiplier * 100
                })

        # 4. PE & PEG（需要最新股价）
        price = get_latest_price(code)
        eps = results.get('每股收益')
        if price and eps and eps != 0:
            pe = price / eps
            results['动态PE'] = pe

            # PEG（简化版：使用最近净利润增长率）
            growth = results.get('净利润增长率(%)')
            if growth and growth != 0:
                results['PEG'] = pe / (growth)  # 常见简化公式：PE / 增长率(%)

        # 保存单只股票结果
        df_single = pd.DataFrame([results])
        df_single.to_csv(os.path.join(OUTPUT_DIR, f"financial_{code}.csv"), index=False, encoding='utf-8-sig')

        return results

    except Exception as e:
        print(f"{code} 分析失败: {e}")
        return {'code': code, 'error': str(e)}


# ====================== 批量分析 ======================
def batch_financial_analysis():
    codes = get_stock_list()
    print(f"开始批量财务分析，共 {len(codes)} 只股票...\n")

    all_results = []
    for code in codes:
        result = analyze_single_stock(code)
        all_results.append(result)
        time.sleep(1.2)  # 避免接口限流

    # 保存汇总结果
    summary_df = pd.DataFrame(all_results)
    summary_file = os.path.join(OUTPUT_DIR, f"financial_summary_{datetime.today().strftime('%Y%m%d')}.csv")
    summary_df.to_csv(summary_file, index=False, encoding='utf-8-sig')

    print("\n" + "=" * 60)
    print(f"财务分析完成！汇总文件已保存：{summary_file}")
    print("\n关键指标预览（部分股票）：")
    cols = ['code', '动态PE', 'PEG', 'ROE(%)', '净利润增长率(%)', '净利率(%)']
    print(summary_df[cols].head(10).round(2))

    return summary_df


if __name__ == "__main__":
    # 首次运行请安装：
    # pip install akshare pandas
    batch_financial_analysis()