import chardet

files = [
    'scripts/templates/index.html',
    'scripts/templates/backtest.html',
    'scripts/templates/base.html'
]

for file_path in files:
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            result = chardet.detect(content)
            print(f'{file_path}: {result}')
    except Exception as e:
        print(f'{file_path}: Error - {e}')
