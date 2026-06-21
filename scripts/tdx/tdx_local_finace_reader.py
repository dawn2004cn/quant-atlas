from pytdx.reader.history_financial_reader import HistoryFinancialReader

# 财务数据文件路径
file_path = "E:\\tdx\\通达信金融终端(开心果交易版)V2024.02\\vipdoc\\cw\\gpcw20260331.dat"

reader = HistoryFinancialReader()
# get_df 会自动处理解压和格式转换
df = reader.get_df(file_path)
df.to_csv("gpcw20260331.csv", index=True, encoding="utf-8-sig")
print(df.head())