# 修复特定文件的编码问题

def fix_file(file_path):
    print('Fixing ' + file_path + '...')
    try:
        # 读取文件内容（二进制模式）
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # 尝试用GBK解码（常见的中文编码）
        decoded_content = content.decode('gbk')
        
        # 用UTF-8重新编码写入
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(decoded_content)
        
        print('Successfully converted ' + file_path + ' to UTF-8')
        return True
    except Exception as e:
        print('Error fixing ' + file_path + ': ' + str(e))
        return False

# 修复指定的文件
files_to_fix = [
    'scripts/templates/index.html',
    'scripts/templates/backtest.html'
]

for file_path in files_to_fix:
    fix_file(file_path)

print('\nFix completed!')
