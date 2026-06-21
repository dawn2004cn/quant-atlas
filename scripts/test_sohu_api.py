#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试搜狐 API 数据获取和解析
"""

import requests
import json

url = 'https://hqm.stock.sohu.com/gethqtop.up?cb=fortune_hq'
headers = {'User-Agent': 'Mozilla/5.0'}

print("🔍 测试搜狐 API...")
try:
    response = requests.get(url, timeout=10, headers=headers)
    print(f"✅ API 响应状态: {response.status_code}")
    
    # 确保使用正确的编码
    response.encoding = 'utf-8'
    response_text = response.text
    print(f"📄 响应长度: {len(response_text)} 字符")
    print(f"📝 响应开头: {response_text[:200]}...")
    
    # 移除JSONP包装
    if response_text.startswith('fortune_hq(') and response_text.endswith(');'):
        json_str = response_text[11:-2]
        print(f"📄 JSON 长度: {len(json_str)} 字符")
        
        try:
            # 尝试直接解析
            print("🔄 尝试直接解析 JSON...")
            data = json.loads(json_str)
            print("✅ 直接解析成功!")
        except json.JSONDecodeError as e:
            print(f"❌ 直接解析失败: {e}")
            # 尝试处理编码问题
            try:
                print("🔄 尝试处理编码问题...")
                json_str = json_str.encode('latin1').decode('utf-8')
                data = json.loads(json_str)
                print("✅ 编码处理后解析成功!")
            except Exception as e2:
                print(f"❌ 编码处理后解析失败: {e2}")
                exit(1)
    else:
        print("❌ API 响应格式错误")
        exit(1)
    
    # 检查数据结构
    print("\n📊 数据结构检查:")
    print(f"✅ 数据类型: {type(data)}")
    print(f"✅ 包含的键: {list(data.keys())}")
    
    # 检查 dxjl 字段
    if 'dxjl' in data:
        dxjl_data = data['dxjl']
        print(f"\n📈 dxjl 数据:")
        print(f"✅ dxjl 类型: {type(dxjl_data)}")
        print(f"✅ dxjl 长度: {len(dxjl_data)}")
        
        if dxjl_data:
            print(f"\n📋 第一条数据:")
            print(f"✅ 类型: {type(dxjl_data[0])}")
            print(f"✅ 数据: {dxjl_data[0]}")
        else:
            print("❌ dxjl 数据为空")
    else:
        print("❌ 没有 dxjl 字段")
        print(f"📋 所有键: {list(data.keys())}")
        print(f"📋 rmbk 长度: {len(data.get('rmbk', []))}")
        
        if 'rmbk' in data and data['rmbk']:
            print(f"📋 rmbk 第一条: {data['rmbk'][0]}")
            
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
