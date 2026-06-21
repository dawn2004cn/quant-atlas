# HTML 国际化 (i18n) 执行计划

## 目标
将 HTML 模板中的硬编码中文文本提取到 `locales/zh.json`，支持多语言切换，避免乱码。

## 1. 关键命名规范

```javascript
// key 格式: {页面}_{区块}_{内容}
// 示例:
"index_header_title"       // 首页 - 头部 - 标题
"nav_home"              // 导航 - 首页
"market_shanghai"       // 市场 - 上证指数
"btn_submit"          // 按钮 - 提交
```

### 页面前缀 (page)
| 前缀 | 页面 |
|------|------|
| `nav` | 导航栏 |
| `index` | 首页 |
| `portfolio` | 组合页 |
| `watchlist` | 自选页 |
| `stock` | 股票详情 |
| `strategy` | 策略页 |
| `backtest` | 回测页 |
| `signal` | 信号页 |
| `analysis` | 分析页 |
| `profile` | 个人页 |
| `auth` | 登录/注册 |
| `admin` | 管理页 |
| `error` | 错误页 |

### 区块后缀 (section)
| 后缀 | 含义 |
|------|------|
| `_header` | 头部 |
| `_footer` | 底部 |
| `_sidebar` | 侧边栏 |
| `_nav` | 导航 |
| `_title` | 标题 |
| `_label` | 标签 |
| `_btn` | 按钮 |
| `_text` | 正文 |
| `_placeholder` | 输入框占位 |
| `_tooltip` | 提示 |
| `_empty` | 空状态 |
| `_error` | 错误信息 |

---

## 2. 页面分组 (按优先级)

### P0 - 核心页面 (必须)
1. **base.html** - 基础模板 (导航/页脚)
2. **index.html** - 首页
3. **login.html** / **register.html** - 登录注册
4. **stock_detail.html** - 股票详情
5. **portfolio.html** - 投资组合

### P1 - 重要功能页面
6. **watchlist.html** - 自选股
7. **strategy_compare.html** - 策略对比
8. **backtest.html** - 回测
9. **signal_flag.html** - 信号管理
10. **moments.html** - 动态
11. **market_panorama.html** - 市场全景

### P2 - 次要页面
12. 其他管理页面和工具页面

---

## 3. 实施步骤

### Step 1: 定义基础 key (已完)
- `locales/zh.json` 基础结构
- `app/core/i18n.py` 加载器

### Step 2: 更新 HTML 模板
```html
<!-- Jinja2 模板使用 -->
<h1>{{ t('index_title') }}</h1>
<button>{{ t('btn_submit') }}</button>

<!-- 或使用 block -->
{% block title %}{{ t('nav_home') }}{% endblock %}
```

### Step 3: 添加 JavaScript 端点
```javascript
// 页面加载时获取翻译
fetch('/api/i18n')
  .then(r => r.json())
  .then(data => window.i18n = data);
```

### Step 4: 创建 API 端点
```python
# app/presentation/api/routes_i18n.py
@bp.route('/api/i18n')
def get_i18n():
    return jsonify(get_all_translations())
```

### Step 5: 英文翻译 (可选)
创建 `locales/en.json`

---

## 4. 提取模板示例

### 原始 HTML
```html
<h1>散户智能投研平台</h1>
<button onclick="submit()">提交</button>
<div>暂无数据</div>
```

### 国际化后
```html
<h1>{{ t('app_name') }}</h1>
<button onclick="submit()">{{ t('btn_submit') }}</button>
<div>{{ t('common_empty') }}</div>
```

### zh.json
```json
{
  "app_name": "散户智能投研平台",
  "btn_submit": "提交",
  "common_empty": "暂无数据"
}
```

---

## 5. 工作量估算

| 页面数 | 预计文本条目 | 预估时间 |
|--------|-------------|----------|
| P0 (5页) | ~500 | 2小时 |
| P1 (6页) | ~400 | 2小时 |
| P2 (30+页) | ~1000 | 4小时 |
| **总计** | ~1900 | **8小时** |

---

## 6. 相关文件

```
quant-atlas/
├── locales/
│   ├── zh.json          # 中文翻译 (已有)
│   └── en.json          # 英文翻译 (待创建)
├── app/
│   ├── core/
│   │   └── i18n.py     # 加载器 (已有)
│   └── presentation/
│       ├── api/
│       │   └── routes_i18n.py  # API端点 (待创建)
│       └── web/
│           └── templates/   # HTML模板 (修改)
```

---

## 7. 执行建议

1. **先完成后完美**: 基础 key 先覆盖，日后逐步完善
2. **保持一致性**: 同一术语使用相同 key
3. **版本控制**: 中文 key 在 JSON 中，修改后其他语言自动生效
4. **测试验证**: 每次修改后检查页面显示

需要我开始执行某个页面的文本提取吗？