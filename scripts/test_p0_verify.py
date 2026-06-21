import os
path = r'C:\Users\dawn2\AppData\Roaming\Python\Python312\site-packages\pytdx\crawler\history_financial_crawler.py'
with open(path, 'rb') as f:
    data = f.read()
# Try utf-8 with replace
text = data.decode('utf-8', errors='replace')
print(text[:8000])