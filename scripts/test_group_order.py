#!/usr/bin/env python3
"""测试分组顺序和默认选中"""
from redis_cache import RedisCache

# 初始化Redis缓存
cache = RedisCache()

# 测试1: 检查Redis中的分组数据
print("测试1: 检查Redis中的分组数据")
print("=" * 60)

# 获取所有分组
stock_groups = cache.redis_client.hgetall("stock_groups")
print(f"stock_groups: {stock_groups}")

# 获取每个分组的详细信息
for name, group_id in stock_groups.items():
    group_info = cache.redis_client.hgetall(f"stock_group:{group_id}")
    print(f"\n分组 {name} (ID: {group_id}):")
    print(f"  详细信息: {group_info}")

# 测试2: 检查get_stock_groups方法返回的顺序
print("\n测试2: 检查get_stock_groups方法返回的顺序")
print("=" * 60)

groups = cache.get_stock_groups()
print(f"分组数量: {len(groups)}")
print("\n分组顺序:")
for i, group in enumerate(groups):
    print(f"  {i+1}. {group['name']} (ID: {group['id']})")

# 测试3: 检查默认分组ID
print("\n测试3: 检查默认分组ID")
print("=" * 60)

default_group_id = cache.get_default_group_id()
print(f"默认分组ID: {default_group_id}")

# 查找默认分组
default_group = None
for group in groups:
    if group['id'] == default_group_id:
        default_group = group
        break

if default_group:
    print(f"默认分组: {default_group['name']} (ID: {default_group['id']})")
else:
    print("未找到默认分组")

print("\n测试完成！")
