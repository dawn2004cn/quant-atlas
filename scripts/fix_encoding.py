import os
import chardet

templates_dir = 'scripts/templates'

for filename in os.listdir(templates_dir):
    if filename.endswith('.html'):
        file_path = os.path.join(templates_dir, filename)
        try:
            # 读取文件内容
            with open(file_path, 'rb') as f:
                content = f.read()
            
            # 检测编码
            result = chardet.detect(content)
            encoding = result['encoding']
            confidence = result['confidence']
            
            print(f'Processing {filename}: detected {encoding} with {confidence:.2f} confidence')
            
            # 如果不是UTF-8，转换为UTF-8
            if encoding and encoding.lower() != 'utf-8':
                try:
                    # 尝试用检测到的编码解码
                    decoded_content = content.decode(encoding)
                    # 用UTF-8重新编码
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(decoded_content)
                    print(f'✓ Converted {filename} to UTF-8')
                except Exception as e:
                    print(f'✗ Error converting {filename}: {e}')
                    # 尝试用GBK解码（常见的中文编码）
                    try:
                        decoded_content = content.decode('gbk')
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(decoded_content)
                        print(f'✓ Converted {filename} to UTF-8 using GBK fallback')
                    except Exception as e2:
                        print(f'✗ Failed to convert {filename} even with GBK fallback: {e2}')
            else:
                print(f'✓ {filename} is already UTF-8')
                
        except Exception as e:
            print(f'✗ Error processing {filename}: {e}')

print('\nEncoding fix completed!')
