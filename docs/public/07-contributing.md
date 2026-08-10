# 07 · 贡献指南

欢迎贡献代码与文档。请先阅读 [架构](./02-architecture.md) 与 [快速开始](./03-getting-started.md)。

## 分支与提交

- 从团队主开发分支拉取功能分支（云代理约定形如 `cursor/<topic>-****`）  
- 提交信息清晰、聚焦单一意图（推荐 Conventional Commits 风格）  
- 大范围无关格式化请避免  

## 分层与代码风格

- 表现层不写业务规则；领域层不依赖基础设施  
- 新服务放 `app/modules/<context>/services/`，经 factory / `wire()` 注册  
- Python：UTF-8、类型注解、Ruff 格式；避免 `print` 打生产日志  
- 使用项目 `get_logger(__name__)`  

```bash
ruff check app/
ruff format app/
# 可选
mypy app/
```

## 测试期望

```bash
pytest -q
# 涉及路由时
python scripts/audit_api_routes.py
pytest tests/api/test_api_contract.py tests/api/test_public_api_contract.py -q
```

- 行为变更请附测试  
- 公开 API 白名单变更必须同步 `public_api_paths.py` 与契约测试  

## Agent / 工具贡献

- LangChain / 内部工具：`@tool`，返回结构含 **evidence**、**confidence**  
- 平台能力：`@register_capability`  
- 优先复用现有行情、回测、用户数据服务，勿平行造轮子  

## 文档贡献

- **对外**：只改 `docs/public/`（本门户）与根 README 的对外链接  
- **内部**：plan / 审计放原目录，勿链进 `docs/public/README.md` 主导航  

## 安全

- 禁止提交密钥、会话 Cookie、客户持仓数据  
- 实盘相关改动需标明风险与默认关闭行为  

## 获取帮助

- 架构细节：`app/README.md`  
- API 契约：`docs/API_ROUTE_CONTRACT.md`  
- 依赖说明：`docs/dependencies.md`
