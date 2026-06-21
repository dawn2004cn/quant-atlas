#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests

print('Testing API...')
try:
    url = 'https://hqm.stock.sohu.com/gethqtop.up?cb=fortune_hq'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, timeout=10, headers=headers)
    print(f'Status code: {response.status_code}')
    print(f'Response length: {len(response.text)}')
    print(f'Response start: {response.text[:500]}')
except Exception as e:
    print(f'Error: {e}')
