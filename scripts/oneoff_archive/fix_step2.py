import os
os.chdir('E:\\project\\workspace\\myrepo\\quant-atlas')

# Fix DailyWorkbenchService - add market_regime_service param
with open('app/application/services/analytics/daily_workbench_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'health_banner_service: Any | None = None,',
    'health_banner_service: Any | None = None,\n          market_regime_service: Any | None = None,'
)

content = content.replace(
    'self._health_banner_service = health_banner_service',
    'self._health_banner_service = health_banner_service\n        self._market_regime_service = market_regime_service or __import__("app.domain.services.market_regime_service", fromlist=["MarketRegimeService"]).MarketRegimeService()'
)

with open('app/application/services/analytics/daily_workbench_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
py_compile.compile('app/application/services/analytics/daily_workbench_service.py', doraise=True)
print('DailyWorkbenchService fixed')
