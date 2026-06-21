import adata

# 获取北交所个股行情 (以华岭股份 920002 为例)
start_date='2026-01-01'
res_df = adata.stock.market.get_market(stock_code='920002', k_type=1 , start_date=start_date,
            adjust_type=1    )
print(res_df)