# main.py

import warnings



import yfinance as yf



from app.core.logger import get_logger



warnings.filterwarnings('ignore')



logger = get_logger(__name__)



# 导入我们刚刚写的引擎

from core.engine import MarketRegimeManager, HolyGrailEnsembleEngine



# 导入我们分类好的模型库

from models import (

    TREND_BREAKOUT_MODELS,

    MEAN_REVERSION_MODELS,

    PANIC_BOTTOM_MODELS,

    INSTITUTIONAL_MODELS

)





def main():

    logger.info("=" * 60)

    logger.info("华尔街圣杯量化系统启动")

    logger.info("=" * 60)



    logger.info("正在获取大盘环境数据...")

    index_df = yf.download('000300.SS', period="2y", progress=False)

    index_df.columns = index_df.columns.droplevel('Ticker')



    regime_manager = MarketRegimeManager(index_df)

    current_regime = regime_manager.get_current_regime()

    logger.info("当前大盘温度计: %s", current_regime)



    engine = HolyGrailEnsembleEngine()



    if current_regime == "牛市":

        logger.info("趋势完好，全军出击 (挂载: 趋势突破 + 机构资金)")

        engine.load_models(TREND_BREAKOUT_MODELS + INSTITUTIONAL_MODELS)



    elif current_regime == "熊市":

        logger.info("市场严冬，防守反击 (挂载: 恐慌抄底 + 均值回归)")

        engine.load_models(PANIC_BOTTOM_MODELS + MEAN_REVERSION_MODELS)



    else:

        logger.info("震荡市，高抛低吸 (挂载: 均值回归 + 机构资金)")

        engine.load_models(MEAN_REVERSION_MODELS + INSTITUTIONAL_MODELS)



    logger.info("正在拉取股票池数据...")

    watchlist = ['600519.SS', '000858.SZ', '300750.SZ', '002594.SZ', '601127.SS', '601899.SS']



    stock_data_dict = {}

    for ticker in watchlist:

        df = yf.download(ticker, period="1y", progress=False)

        if not df.empty:

            df.columns = df.columns.droplevel('Ticker')

            stock_data_dict[ticker] = df



    report = engine.run_market_scan(stock_data_dict)



    logger.info("=" * 80)

    logger.info("量化共振选股报告 (今日最优操作指南)")

    logger.info("=" * 80)



    if report.empty:

        logger.info("当前市场环境下，未发现符合顶级安全边际的交易机会。建议空仓观望。")

    else:

        import pandas as pd

        pd.set_option('display.max_columns', None)

        pd.set_option('display.max_colwidth', 100)

        pd.set_option('display.unicode.east_asian_width', True)

        logger.info("\n%s", report.to_string(index=False))





if __name__ == "__main__":

    main()

