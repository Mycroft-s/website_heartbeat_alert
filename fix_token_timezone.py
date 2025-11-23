#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复gmail_token.json的时区问题
在服务器上运行此脚本来修复token的时区问题

Usage:
    python3 fix_token_timezone.py
"""

import json
import os
from datetime import datetime, timezone

TOKEN_JSON_FILE = "gmail_token.json"

def fix_token_timezone():
    """修复token文件的时区问题"""
    if not os.path.exists(TOKEN_JSON_FILE):
        print(f"❌ Error: {TOKEN_JSON_FILE} not found")
        return False
    
    try:
        # 读取token文件
        print(f"Reading {TOKEN_JSON_FILE}...")
        with open(TOKEN_JSON_FILE, 'r', encoding='utf-8') as f:
            token_data = json.load(f)
        
        print("Current expiry:", token_data.get('expiry', 'N/A'))
        
        # 修复expiry时区
        if 'expiry' in token_data and token_data['expiry']:
            expiry_str = token_data['expiry']
            print(f"Processing expiry: {expiry_str}")
            
            # 处理Z后缀
            if expiry_str.endswith('Z'):
                expiry_str = expiry_str[:-1] + '+00:00'
            
            # 解析日期
            expiry_dt = datetime.fromisoformat(expiry_str)
            print(f"Parsed datetime: {expiry_dt}, tzinfo: {expiry_dt.tzinfo}")
            
            # 确保时区为UTC
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                print("Added UTC timezone")
            else:
                expiry_dt = expiry_dt.astimezone(timezone.utc)
                print("Converted to UTC timezone")
            
            # 保存为ISO格式（Z后缀）
            token_data['expiry'] = expiry_dt.isoformat().replace('+00:00', 'Z')
            print(f"Fixed expiry: {token_data['expiry']}")
        else:
            print("No expiry found in token data")
        
        # 备份原文件
        backup_file = TOKEN_JSON_FILE + '.backup'
        print(f"Creating backup: {backup_file}")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2, ensure_ascii=False)
        
        # 保存修复后的token
        print(f"Saving fixed token to {TOKEN_JSON_FILE}...")
        with open(TOKEN_JSON_FILE, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, indent=2, ensure_ascii=False)
        
        print("✅ Token timezone fixed successfully!")
        print(f"   Backup saved to: {backup_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error fixing token: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Gmail Token Timezone Fix Script")
    print("=" * 60)
    print()
    
    if fix_token_timezone():
        print()
        print("=" * 60)
        print("✅ Fix completed! Please restart the heartbeat monitor.")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ Fix failed! Please check the error messages above.")
        print("=" * 60)

