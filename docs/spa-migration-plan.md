# Quant Atlas SPA 迁移计划

> 基于 `tmp/design/` 设计体系，将 113 个 Flask Jinja2 模板渐进迁移到 React SPA

---

## 1. 核心设计体系

### 1.1 设计 Token（取自 tmp/design/quant-atlas.css）

```css
/* 深色模式（默认） */
--bg: #07111f;
--fg: #eef6ff;
--muted: #91a3b8;
--surface: rgba(255,255,255,.075);
--panel: rgba(5,10,18,.82);
--bar: rgba(14,20,31,.86);
--accent: #55e48b (绿)
--accent-2: #5aa7ff (蓝)
--danger: #ff6b6b
--warn: #ffd166
--radius-sm: 12px
--radius-md: 16px
--radius-lg: 22px
--radius-xl: 28px
--f: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif
--m: ui-monospace, Menlo, Consolas, monospace

/* 浅色模式（html[data-theme="light"]） */
--bg: #F6F8FB
--fg: #0F172A
--muted: #64748B
--surface: #FFFFFF
--accent: #0E7A43
--accent-2: #2563EB
--danger: #DC2626
```

### 1.2 布局骨架（三栏响应式）

```
桌面 (>1200px):   rail(238px) | main(flex)     | side(294px)
平板 (768-1200px): rail(64px collapsed) | main   | (side 作为抽屉)
移动 (<768px):      bottom nav | main (全宽)
```

### 1.3 响应断点

| 断点 | 宽度 | 布局 |
|------|------|------|
| `desktop` | ≥ 1200px | 三栏展开 |
| `tablet` | 768–1199px | Rail 折叠为图标、Side 抽屉式 |
| `mobile` | < 768px | 全宽、底部导航、卡片堆叠 |

---

## 2. 迁移策略

### 2.1 阶段划分（5 轮，每轮 ~20 页）

| 阶段 | 内容 | 页面数 | 工作量 |
|------|------|--------|--------|
| **S0: 基础设施** | 设计 Token → Tailwind theme, Layout shell, 主题切换, 三栏响应式 | — | 1 轮 |
| **S1: 行情监控** | 全球资产雷达、盘口磁贴、多源行情校验、行业热力图、波动率曲面、价量异动榜、市场宽度仪表、涨停分析、龙虎榜 | ~15 | 2 轮 |
| **S2: 因子研究** | 因子库总览、IC 衰减曲线、暴露矩阵、因子组合器、分层收益板、相关性清洗、Qlib 回测、风格漂移 | ~15 | 2 轮 |
| **S3: 风控+组合** | 回撤防线、净敞口控制、止损队列、VaR 压力测试、流动性雷达、仓位红线、组合驾驶舱、交易篮子、收益归因 | ~25 | 3 轮 |
| **S4: AI 投研+工具** | AI 投委会、RD-Agent 任务、研报摘要器、信号旗扫描、策略生成、提示词实验室、自然语言回测、投资经理 Copilot、设置页 | ~20 | 2 轮 |
| **S5: 旧版保留** | 低频率页面（admin + 回调页面）保留 Jinja2 直到被访问替代 | ~38 | 持续 |

### 2.2 渐进策略

```
1. 新路由走 React（路由前缀 /app/）
2. Flask 路由保留，301 或并行存在
3. React SPA 内嵌 iframe 兼容未迁移的 Jinja2 页面（过渡期）
4. base.html 的导航链接逐步指向 /app/ 前缀
```

---

## 3. 技术实现

### 3.1 Tailwind Theme（映射 design token）

```js
// tailwind.config.js 新增
theme: {
  extend: {
    colors: {
      quant: {
        bg: '#07111f',
        fg: '#eef6ff',
        muted: '#91a3b8',
        accent: '#55e48b',
        'accent-2': '#5aa7ff',
        danger: '#ff6b6b',
        warn: '#ffd166',
        surface: 'rgba(255,255,255,.075)',
        panel: 'rgba(5,10,18,.82)',
        bar: 'rgba(14,20,31,.86)',
      }
    },
    borderRadius: {
      'quant-sm': '12px',
      'quant-md': '16px',
      'quant-lg': '22px',
      'quant-xl': '28px',
    },
    fontFamily: {
      quant: ['-apple-system', 'BlinkMacSystemFont', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
      quant-mono: ['ui-monospace', 'Menlo', 'Consolas', 'monospace'],
    }
  }
}
```

### 3.2 Layout Shell（三栏自适应）

```
frontend/src/
├── components/layout/
│   ├── AppShell.tsx         ← 三栏骨架容器
│   ├── Rail.tsx             ← 左侧导航栏（桌面展开/平板折叠）
│   ├── Topbar.tsx           ← 顶栏（搜索、主题切换、用户）
│   └── SidePanel.tsx        ← 右侧面板（桌面固定/移动抽屉）
├── hooks/
│   ├── useBreakpoint.ts     ← 响应式断点检测
│   └── useTheme.ts          ← 日间/夜间模式切换
├── themes/
│   ├── dark.css             ← 深色主题变量
│   └── light.css            ← 浅色主题变量
```

### 3.3 日间/夜间模式

```tsx
// useTheme.ts
const [theme, setTheme] = useState<'dark' | 'light'>(
  localStorage.getItem('quant-theme') as 'dark' | 'light' ?? 'dark'
);
useEffect(() => {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('quant-theme', theme);
}, [theme]);
```

### 3.4 组件迁移优先级

每个页面的迁移模板：

```tsx
export function PageX() {
  return (
    <AppShell>
      <Rail />           {/* 左侧导航 */}
      <main>              {/* 主内容区 */}
        <Topbar />        {/* 顶栏 */}
        <PageContent />   {/* 业务组件 */}
      </main>
      <SidePanel />       {/* 右侧面板 */}
    </AppShell>
  );
}
```

---

## 4. 响应式断点实现

```tsx
// useBreakpoint.ts
export type Breakpoint = 'mobile' | 'tablet' | 'desktop';

export function useBreakpoint(): Breakpoint {
  const [bp, setBp] = useState<Breakpoint>('desktop');
  useEffect(() => {
    const mq = () => {
      const w = window.innerWidth;
      if (w < 768) setBp('mobile');
      else if (w < 1200) setBp('tablet');
      else setBp('desktop');
    };
    mq();
    window.addEventListener('resize', mq);
    return () => window.removeEventListener('resize', mq);
  }, []);
  return bp;
}
```

三栏布局自适应：

```tsx
// AppShell.tsx
const bp = useBreakpoint();
return (
  <div className="app" data-breakpoint={bp}>
    {bp !== 'mobile' && <Rail collapsed={bp === 'tablet'} />}
    <main>{children}</main>
    {bp === 'desktop' && <SidePanel />}
    {/* mobile: SidePanel 作为 drawer */}
    {bp === 'mobile' && <BottomNav />}
  </div>
);
```

---

## 5. 页面迁移优先级矩阵

| 优先级 | 页面 | 阶段 | 频次 | 复杂度 |
|--------|------|------|------|--------|
| P0 | 首页行情概览 | S1 | 高频 | 中等 |
| P0 | 股票详情 | S1 | 高频 | 高 |
| P0 | 自选股 | S1 | 高频 | 中等 |
| P1 | 因子库 | S2 | 中频 | 高 |
| P1 | 因子回测 | S2 | 中频 | 高 |
| P1 | 组合驾驶舱 | S3 | 中频 | 高 |
| P2 | AI 投委会 | S4 | 低频 | 高 |
| P2 | 策略生成器 | S4 | 低频 | 高 |
| P3 | Admin 面板 | S5 | 极低频 | 低 |

---

## 6. 执行计划

```
S0 (本轮):  Infrastructure — Layout, Theme, Breakpoints          → 1 会话
S1 (轮 1):  Market pages (15 pages)                              → 2 会话
S1 (轮 2):  Market depth + alerts (15 pages)                     → 2 会话
S2 (轮 3):  Factor research (15 pages)                           → 2 会话
S3 (轮 4):  Risk + Portfolio (25 pages)                          → 3 会话
S4 (轮 5):  AI + Tools (20 pages)                                → 2 会话
S5 (持续):  Legacy Jinja2 retirement process                     → 按需
```

---

## 7. 验证标准

- [ ] 每个迁移的页面在 desktop/tablet/mobile 三种宽度下视觉完整
- [ ] 深色/浅色模式切换无闪烁、无样式断裂
- [ ] Tailwind quant-* 类名与 tmp/design/ 色值一致（△E < 2）
- [ ] 小屏下单手操作区（底部导航）无死区
- [ ] 迁移后的 SPA 路由与 Flask 路由无冲突
- [ ] `base.html` 导航链接不少于 80% 指向 `/app/` 前缀
- [ ] 旧 Jinja2 页面的 301 重定向到位