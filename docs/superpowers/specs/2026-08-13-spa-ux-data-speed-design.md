# SPA 体验：有数据、快、局部刷新

> 日期：2026-08-13  
> 状态：按用户验收标准实施（有数据 / 速度快 / 界面美观 / 切换只局部刷新）

## 目标

自测并修好主轨 React SPA（`/app`），使登录后的操盘台与核心页：

1. **有数据**：行情源空/失败时仍展示可识别的演示样本，并标明 `data_mode=demo`
2. **快**：沿用性能快赢（短 TTL 缓存、图表分包、实时默认关）；SWR 保留上一页数据
3. **好看**：顶栏/内容区视觉对齐，导航高亮当前页
4. **局部刷新**：顶栏 Layout 常驻；路由用 `Link`；内容区 KeepAlive（最近 N 页隐藏而非卸载）

## 非目标

- 不上 MkDocs；不重做全部 80+ 页视觉
- 不把演示行情写成实盘 SLA
- 不引入 react-activation 等新框架依赖

## 验收

- 空行情源时 `build_snapshot` 仍有 watchlist / 指数 / 宽度数字
- `CoreWorkflowStrip.tsx` 非空，导出 `Link` 导航
- Layout 使用 KeepAliveOutlet，切换路径不整页 `window.location`
- 登录成功跳转 SPA 相对路径 `/`，而不是 `/app/app`
- 空列表页展示带「演示」标注的样本行（自选…委员会仪表盘/任务中心/Swarm/研究管线/研究画板/Agent 中心/系统能力/语音简报）
