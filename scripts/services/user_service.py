#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户服务
"""

import json
import os
import hashlib
from typing import List, Dict


class UserService:
    """用户服务"""
    
    def __init__(self):
        self.users_file = os.path.join(os.path.dirname(__file__), '..', 'users.json')
        self.roles = {
            'admin': {
                'name': '管理员',
                'permissions': ['read', 'create', 'update', 'delete', 'manage_users', 'change_all_passwords']
            },
            'developer': {
                'name': '开发者',
                'permissions': ['read', 'create', 'update', 'change_own_password']
            },
            'viewer': {
                'name': '访客',
                'permissions': ['read', 'change_own_password']
            }
        }
    
    def get_users(self) -> Dict:
        """
        获取用户数据
        
        Returns:
            Dict: 用户数据
        """
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    users = json.load(f)
                    return users
            except:
                pass
        
        # 默认用户数据
        return {
            'admin': {
                'password': hashlib.sha256('changeme'.encode()).hexdigest(),  # 默认密码: admin123
                'id': 1,
                'role': 'admin'
            },
            'developer': {
                'password': hashlib.sha256('dev123'.encode()).hexdigest(),  # 默认密码: dev123
                'id': 2,
                'role': 'developer'
            },
            'viewer': {
                'password': hashlib.sha256('view123'.encode()).hexdigest(),  # 默认密码: view123
                'id': 3,
                'role': 'viewer'
            }
        }
    
    def save_users(self, users: Dict):
        """
        保存用户数据
        
        Args:
            users: 用户数据
        """
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def create_user(self, username: str, password: str, role: str, users: Dict) -> bool:
        """
        创建新用户
        
        Args:
            username: 用户名
            password: 密码
            role: 角色
            users: 当前用户数据
            
        Returns:
            bool: 是否创建成功
        """
        if username in users:
            return False
        
        if role not in self.roles:
            return False
        
        # 创建用户
        new_id = max([u['id'] for u in users.values()]) + 1
        users[username] = {
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'id': new_id,
            'role': role
        }
        
        self.save_users(users)
        return True
    
    def delete_user(self, username: str, users: Dict, current_username: str) -> bool:
        """
        删除用户
        
        Args:
            username: 要删除的用户名
            users: 当前用户数据
            current_username: 当前登录用户名
            
        Returns:
            bool: 是否删除成功
        """
        if username not in users:
            return False
        
        if username == 'admin':
            return False
        
        if username == current_username:
            return False
        
        del users[username]
        self.save_users(users)
        return True
    
    def change_password(self, target_user: str, old_password: str, new_password: str, 
                       confirm_password: str, users: Dict, current_user: object) -> bool:
        """
        修改密码
        
        Args:
            target_user: 目标用户名
            old_password: 旧密码
            new_password: 新密码
            confirm_password: 确认密码
            users: 当前用户数据
            current_user: 当前用户对象
            
        Returns:
            bool: 是否修改成功
        """
        # 验证新密码
        if not new_password:
            return False
        
        if len(new_password) < 6:
            return False
        
        if new_password != confirm_password:
            return False
        
        # 权限检查
        if not current_user.can_change_password(target_user):
            return False
        
        # 修改自己的密码需要验证旧密码
        if target_user == current_user.username and not current_user.has_permission('change_all_passwords'):
            old_hash = hashlib.sha256(old_password.encode()).hexdigest()
            if old_hash != users[target_user]['password']:
                return False
        
        # 修改密码
        if target_user not in users:
            return False
        
        users[target_user]['password'] = hashlib.sha256(new_password.encode()).hexdigest()
        self.save_users(users)
        return True
    
    def get_roles(self) -> List[Dict]:
        """
        获取角色列表
        
        Returns:
            List[Dict]: 角色列表
        """
        roles_list = []
        for role_id, role_data in self.roles.items():
            roles_list.append({
                'id': role_id,
                'name': role_data['name'],
                'permissions': role_data['permissions']
            })
        return roles_list
