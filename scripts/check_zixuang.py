#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Redis中的自选股分组数据
"""

import redis

if __name__ == '__main__':
    print('=== 检查Redis中的自选股分组数据 ===')
    
    # 连接Redis
    r = redis.Redis(host='192.168.8.103', port=6380, db=0, decode_responses=True)
    
    try:
        # 测试连接
        r.ping()
        print('✅ 成功连接到Redis')
        
        # 检查stock_groups键
        stock_groups_exists = r.exists('stock_groups')
        print('stock_groups键是否存在:', stock_groups_exists)
        
        if stock_groups_exists:
            # 获取所有分组
            all_groups = r.hgetall('stock_groups')
            print('所有分组:', all_groups)
            
            # 获取自选股分组ID
            zixuang_id = r.hget('stock_groups', '自选股')
            print('自选股分组ID:', zixuang_id)
            
            if zixuang_id:
                # 获取自选股分组信息
                group_info = r.hgetall('stock_group:' + zixuang_id)
                print('自选股分组信息:', group_info)
                
                # 获取自选股数量
                members_key = 'stock_group:' + zixuang_id + ':members'
                member_count = r.scard(members_key)
                print('自选股数量:', member_count)
                
                # 获取自选股列表
                members = list(r.smembers(members_key))
                print('自选股列表:', members)
                print('自选股列表长度:', len(members))
        else:
            print('❌ stock_groups键不存在')
            
    except Exception as e:
        print(f'❌ 检查Redis数据失败: {e}')
    finally:
        r.close()
