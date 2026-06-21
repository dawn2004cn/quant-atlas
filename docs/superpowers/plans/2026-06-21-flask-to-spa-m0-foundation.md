# Flask -> SPA M0 地基 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在动手迁移任何新页面之前，先把地基建好——双轨认证、OpenAPI 流水线、Playwright E2E 框架、CI 校验规则、迁移 PR 模板。

**架构：** 5 个相互独立的子系统并行建设：(1) JWT 双轨认证，(2) apispec + openapi-typescript 契约流水线，(3) 事件 model 范式 + events.md，(4) Playwright E2E 框架与 5 条核心流脚本，(5) CI 新增 e2e / openapi-check jobs + 迁移 PR 模板。

**技术栈：** Python 3.12 + Flask 3 + PyJWT + apispec / flask-smorest（视任务 0 决策）；Node 20 + Playwright + openapi-typescript；GitHub Actions。

**关联设计文档：** `docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md`

---

## 任务 0：M0 决策固化（开放问题收口）

**目的：** 设计文档第 10 节的 6 个开放问题在 M0 启动前必须明确，否则后续任务无法编码。本任务是一次设计评审，输出 ADR。

**文件：**

- 创建 docs/adr/0001-jwt-algorithm.md
- 创建 docs/adr/0002-openapi-tooling.md
- 创建 docs/adr/0003-jwt-refresh-strategy.md
- 创建 docs/adr/0004-playwright-ci-strategy.md
- 创建 docs/adr/0005-existing-spa-pages-coverage.md
- 创建 docs/adr/0006-public-share-routes.md

- [ ] **步骤 1：评审会议（人工）**，决定每个开放问题。每个 ADR 用 1 页篇幅记录：上下文 / 决策 / 后果。
- [ ] **步骤 2：commit ADR**

```bash
git add docs/adr/
git commit -m "docs: M0 ADR 0001-0006 (JWT, OpenAPI, refresh, Playwright, SPA coverage, share routes)"
```

**预期产出：** 后续任务的工具/算法选择有据可依。**任务 0 不通过则不进入任务 1。**

---

## 任务 0.5：Switcher 基础设施预埋（ADR-0007 触发）

**触发**：用户在 ADR 评审后追加"Flask 右上做新版 SPA 切换、Flask 也保留"的方向调整，决议三阶段灰度（switcher → 302 → 301）。M0 完整预埋基础设施，M1+ 每页只填入 URL 即可启用。

**预期工期**：0.5 天

**文件：**

- 修改 `app/presentation/web/templates/base.html`（line 29 `<nav class="app-nav">` 内末尾追加 `{% block spa_switcher %}{% endblock %}`）
- 修改 `frontend/src/components/Layout.tsx`（追加 `SpaSwitcherContext` Provider + `useSpaSwitcher()` hook）
- 创建 `frontend/src/lib/switcher-telemetry.ts`（埋点 SDK helper）
- 创建 `app/presentation/api/routes_v1_telemetry.py`（埋点端点）
- 创建 `tests/unit/test_switcher_telemetry.py`（单元测试）
- 创建 `tests/e2e/switcher.spec.ts`（E2E 测试占位，M1 第一页迁移时启用）
- 更新 `docs/spa-migration-runbook.md`（新文件，含"如何为新页面启用 switcher"小节）

**步骤：**

1. **Jinja 注入点**：在 `app/presentation/web/templates/base.html` 第 29 行 `<nav class="app-nav">` 内末尾追加：
   ```jinja
   {% block spa_switcher %}{% endblock %}
   ```
   默认空块，M1+ 每个迁移页面在自己的 Jinja 模板里重写：
   ```jinja
   {% block spa_switcher %}
   <a href="/app/dashboard" class="spa-switcher-link"
      data-switcher-page="dashboard"
      onclick="window.trackSwitcherClick && window.trackSwitcherClick('dashboard')">
     试试新版 →
   </a>
   {% endblock %}
   ```

2. **SPA 注入点**：在 `frontend/src/components/Layout.tsx` 添加 `SpaSwitcherContext`，子页面可通过 props 启用回跳口：
   ```tsx
   <Layout enableBackToClassic backToClassicUrl="/dashboard">
     <DashboardPage />
   </Layout>
   ```
   Layout 内部根据 `enableBackToClassic` 在右下角渲染"回到经典版 ←"链接。

3. **埋点端点**：`app/presentation/api/routes_v1_telemetry.py` 实现 `POST /api/v1/telemetry/switcher`：
   - 接受 `{event: "switch_to_spa"|"back_to_classic", page: str, user_id: str|null}`
   - 写入 `instance/telemetry.jsonl`（一行一记录，含 timestamp）
   - 无需鉴权（埋点 fire-and-forget），但有 IP 限流（每秒 10 条/IP）
   - 注册到 v1 蓝图，与其他 API 路由一致

4. **前端 SDK**：`frontend/src/lib/switcher-telemetry.ts` 导出：
   ```ts
   export function trackSwitcherClick(page: string): void;
   export function trackBackToClassic(page: string): void;
   ```
   实现：fetch POST `/api/v1/telemetry/switcher`，失败静默（埋点不阻塞用户）。
   **额外**：在 Jinja 端也注入 `window.trackSwitcherClick`，让 Jinja 页面的 switcher 链接 onclick 能直接调用。

5. **单元测试** `tests/unit/test_switcher_telemetry.py`：
   - 端点接受合法 POST，写入 JSONL，返回 204
   - 端点拒绝非法事件类型，返回 400
   - IP 限流生效（连续 11 条返回 429）

6. **E2E 测试占位** `tests/e2e/switcher.spec.ts`：写一个 `test.skip()` 占位，注释说明"M1 第一页迁移时启用，验证 switcher → 跳转 → 回跳完整链路"。

7. **Runbook 文档**：`docs/spa-migration-runbook.md` 新建，含三个小节：
   - "如何为新页面启用 switcher"（Jinja `{% block %}` + SPA `<Layout enableBackToClassic>` 两步示例）
   - "如何查看埋点数据"（`cat instance/telemetry.jsonl | jq` 命令示例）
   - "三阶段切换条件"（从 ADR-0007 摘要：主动切换率 ≥ 30% / 转化稳定率 ≥ 60% / SPA 错误率 < 0.5%）

**验证准则：**

- [ ] `python -c "import app; print('ok')"` 通过（埋点端点注册不破坏 app 启动）
- [ ] 跑 base.html 模板单测：渲染默认 base.html 不报错，且 `{% block spa_switcher %}` 占位符存在
- [ ] 跑 `tests/unit/test_switcher_telemetry.py` 全绿
- [ ] 前端 `npm run typecheck` 通过（Layout 接口变更不破坏现有 11 页 SPA）
- [ ] 手动验证：在浏览器打开 `/` Flask 首页，DevTools 看到 `<nav class="app-nav">` 末尾有空块（HTML 注释占位即可）
- [ ] 手动验证：访问 `/app/dashboard`，DevTools 看到 SPA 加载正常，无 console error

**预期产出：**

M1+ 每个迁移页面只需 0.5h 即可启用 switcher（填两处 URL），不再重新做基础设施。

**任务 0.5 不通过则不进入任务 1。**

---

## 任务 1：JWT 服务

**文件：**

- 创建 app/infrastructure/auth/jwt_service.py
- 创建 tests/unit/auth/test_jwt_service.py
- 修改 pyproject.toml（追加 PyJWT 依赖）

- [ ] **步骤 1：写失败测试**

```python
# tests/unit/auth/test_jwt_service.py
import time
import pytest
from app.infrastructure.auth.jwt_service import JwtService, TokenExpired, TokenInvalid


def test_encode_then_decode_returns_subject():
    svc = JwtService(secret="test-secret", algorithm="HS256", ttl_seconds=3600)
    token = svc.encode(subject="user-123")
    payload = svc.decode(token)
    assert payload["sub"] == "user-123"


def test_expired_token_raises():
    svc = JwtService(secret="test-secret", algorithm="HS256", ttl_seconds=1)
    token = svc.encode(subject="user-123")
    time.sleep(2)
    with pytest.raises(TokenExpired):
        svc.decode(token)


def test_tampered_token_raises():
    svc = JwtService(secret="test-secret", algorithm="HS256", ttl_seconds=3600)
    token = svc.encode(subject="user-123") + "x"
    with pytest.raises(TokenInvalid):
        svc.decode(token)
```

- [ ] **步骤 2：运行测试验证失败**

运行 `pytest tests/unit/auth/test_jwt_service.py -v`
预期：FAIL，ModuleNotFoundError: app.infrastructure.auth.jwt_service

- [ ] **步骤 3：实现 JwtService**

```python
# app/infrastructure/auth/jwt_service.py
from __future__ import annotations

import time
from dataclasses import dataclass

import jwt as pyjwt


class TokenExpired(Exception):
    pass


class TokenInvalid(Exception):
    pass


@dataclass
class JwtService:
    secret: str
    algorithm: str = "HS256"  # 由 ADR-0001 决定
    ttl_seconds: int = 3600

    def encode(self, *, subject: str, extra: dict | None = None) -> str:
        now = int(time.time())
        payload = {"sub": subject, "iat": now, "exp": now + self.ttl_seconds}
        if extra:
            payload.update(extra)
        return pyjwt.encode(payload, self.secret, algorithm=self.algorithm)

    def decode(self, token: str) -> dict:
        try:
            return pyjwt.decode(token, self.secret, algorithms=[self.algorithm])
        except pyjwt.ExpiredSignatureError as exc:
            raise TokenExpired(str(exc)) from exc
        except pyjwt.InvalidTokenError as exc:
            raise TokenInvalid(str(exc)) from exc
```

- [ ] **步骤 4：在 pyproject.toml 添加 PyJWT 依赖**

在 `[project] dependencies` 末尾追加 `"PyJWT>=2.8.0",`

- [ ] **步骤 5：安装依赖并验证测试通过**

运行 `pip install -e .` 然后 `pytest tests/unit/auth/test_jwt_service.py -v`
预期：3 个测试 PASS

- [ ] **步骤 6：Commit**

```bash
git add app/infrastructure/auth/jwt_service.py tests/unit/auth/test_jwt_service.py pyproject.toml
git commit -m "feat(auth): add JwtService for token encode/decode (M0 task 1)"
```

---
## 任务 2：认证中间件（双轨 before_request 钩子）

**文件：**

- 创建 app/presentation/api/auth_middleware.py
- 修改 app/__init__.py 或 app/bootstrap.py（注册 before_request 钩子；位置由实际 Flask app 工厂决定，先 grep 确认）
- 创建 tests/integration/test_dual_auth.py

- [ ] **步骤 1：定位 Flask app 工厂**

运行 `grep -rn "app = Flask\|create_app\|Flask(__name__)" app/ --include="*.py" | head -5`
确认中间件应在哪个文件注册 `before_request`。记录位置到本步骤评论。

- [ ] **步骤 2：写失败的集成测试**

```python
# tests/integration/test_dual_auth.py
import pytest
from app.bootstrap import create_app  # 实际位置以步骤 1 为准
from app.infrastructure.auth.jwt_service import JwtService


@pytest.fixture
def client():
    app = create_app(testing=True)
    return app.test_client()


@pytest.fixture
def jwt_token(app_jwt_secret):
    svc = JwtService(secret=app_jwt_secret, ttl_seconds=3600)
    return svc.encode(subject="test-user")


def test_jwt_bearer_auth_populates_current_user(client, jwt_token):
    resp = client.get("/api/v1/auth/whoami", headers={"Authorization": f"Bearer {jwt_token}"})
    assert resp.status_code == 200
    assert resp.get_json()["user_id"] == "test-user"


def test_cookie_session_still_works(client):
    # 走老的登录流程（POST /login 设 cookie）
    client.post("/login", data={"username": "test-user", "password": "test-pass"})
    resp = client.get("/api/v1/auth/whoami")
    assert resp.status_code == 200


def test_jwt_takes_priority_over_cookie(client, jwt_token):
    # cookie 已登录为 user-A，但 Bearer token 是 test-user，应优先 Bearer
    client.post("/login", data={"username": "user-A", "password": "pass"})
    resp = client.get("/api/v1/auth/whoami", headers={"Authorization": f"Bearer {jwt_token}"})
    assert resp.get_json()["user_id"] == "test-user"


def test_anonymous_when_no_credentials(client):
    resp = client.get("/api/v1/auth/whoami")
    assert resp.status_code == 401
```

- [ ] **步骤 3：运行测试验证失败**

运行 `pytest tests/integration/test_dual_auth.py -v`
预期：FAIL（端点 `/api/v1/auth/whoami` 不存在或不识别 Bearer）

- [ ] **步骤 4：实现 auth_middleware.py**

```python
# app/presentation/api/auth_middleware.py
from __future__ import annotations

from flask import g, request, current_app
from flask_login import current_user as flask_login_user

from app.infrastructure.auth.jwt_service import JwtService, TokenExpired, TokenInvalid


def install(app):
    """注册 before_request 钩子。"""

    @app.before_request
    def _resolve_identity():
        # 优先级 1：Authorization: Bearer
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[len("Bearer "):]
            svc: JwtService = app.extensions["jwt_service"]
            try:
                payload = svc.decode(token)
                g.identity_subject = payload["sub"]
                g.identity_source = "jwt"
                return
            except (TokenExpired, TokenInvalid):
                # 解码失败不抛——继续尝试 cookie
                pass

        # 优先级 2：cookie session（Flask-Login）
        if flask_login_user.is_authenticated:
            g.identity_subject = str(flask_login_user.get_id())
            g.identity_source = "cookie"
            return

        # 优先级 3：匿名
        g.identity_subject = None
        g.identity_source = None
```

- [ ] **步骤 5：在 app 工厂中初始化 JwtService 并安装中间件**

在步骤 1 定位到的 app 工厂中：

```python
from app.config import get_settings
from app.infrastructure.auth.jwt_service import JwtService
from app.presentation.api import auth_middleware

settings = get_settings()
jwt_service = JwtService(
    secret=settings.jwt_secret,  # 在 app/config.py 添加 jwt_secret 字段
    algorithm="HS256",  # 由 ADR-0001 决定
    ttl_seconds=settings.jwt_ttl_seconds,  # 在 app/config.py 添加，默认 3600
)
app.extensions["jwt_service"] = jwt_service
auth_middleware.install(app)
```

- [ ] **步骤 6：在 app/config.py 添加 jwt_secret / jwt_ttl_seconds 设置项**

在 `AppSettings` 模型中追加：

```python
jwt_secret: str = "dev-only-secret-change-me"
jwt_ttl_seconds: int = 3600
```

读取来源沿用项目现有 settings 加载方式（环境变量 `JWT_SECRET`、`JWT_TTL_SECONDS`）。

- [ ] **步骤 7：实现 /api/v1/auth/whoami 端点**

创建 `app/presentation/api/routes_v1_auth.py`（若已存在则在此添加路由）：

```python
from flask import Blueprint, g, jsonify

bp = Blueprint("auth_v1", __name__, url_prefix="/api/v1/auth")


@bp.get("/whoami")
def whoami():
    if not g.get("identity_subject"):
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({
        "user_id": g.identity_subject,
        "auth_source": g.identity_source,
    })
```

并在 app 工厂中 `app.register_blueprint(bp)`。

- [ ] **步骤 8：运行测试验证通过**

运行 `pytest tests/integration/test_dual_auth.py -v`
预期：4 个测试全 PASS

- [ ] **步骤 9：Commit**

```bash
git add app/presentation/api/auth_middleware.py app/presentation/api/routes_v1_auth.py app/config.py app/bootstrap.py tests/integration/test_dual_auth.py
git commit -m "feat(auth): dual-track authentication (cookie + JWT) middleware (M0 task 2)"
```

---

## 任务 3：登录端点同时设 cookie 和返回 JWT

**文件：**

- 修改 app/presentation/web/auth.py（line 92-138 的 login handler）
- 修改 tests/integration/test_dual_auth.py（追加测试）

- [ ] **步骤 1：写失败测试**

在 `tests/integration/test_dual_auth.py` 末尾追加：

```python
def test_login_returns_jwt_and_sets_cookie(client):
    resp = client.post("/login", data={"username": "test-user", "password": "test-pass"}, follow_redirects=False)
    # cookie 设置（Flask-Login session）
    cookies = resp.headers.getlist("Set-Cookie")
    assert any("session=" in c for c in cookies), "session cookie missing"
    # JSON Accept 时返回 JWT
    resp_json = client.post(
        "/login",
        json={"username": "test-user", "password": "test-pass"},
        headers={"Accept": "application/json"},
    )
    assert resp_json.status_code == 200
    data = resp_json.get_json()
    assert "access_token" in data
    assert data["token_type"] == "Bearer"
```

- [ ] **步骤 2：运行测试验证失败**

运行 `pytest tests/integration/test_dual_auth.py::test_login_returns_jwt_and_sets_cookie -v`
预期：FAIL（当前 login 不返回 access_token）

- [ ] **步骤 3：修改 login handler**

在 `app/presentation/web/auth.py` 的 `login()` 函数中，调用 `login_user(...)` 之后追加：

```python
# 在已有的 login_user(...) 之后
from flask import current_app, jsonify, request as flask_request

if flask_request.accept_mimetypes.best == "application/json" or flask_request.is_json:
    svc = current_app.extensions["jwt_service"]
    token = svc.encode(subject=str(user.id))
    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": svc.ttl_seconds,
    })
# 否则保持原有 redirect 行为
```

- [ ] **步骤 4：运行测试验证通过**

运行 `pytest tests/integration/test_dual_auth.py -v`
预期：5 个测试全 PASS

- [ ] **步骤 5：Commit**

```bash
git add app/presentation/web/auth.py tests/integration/test_dual_auth.py
git commit -m "feat(auth): login endpoint returns JWT in addition to setting cookie (M0 task 3)"
```

---
## 任务 4：OpenAPI 工具栈与基础设施

**前置：** ADR-0002（任务 0 决定 `apispec` vs `flask-smorest`）。本任务示例代码采用 `apispec` 路径——若 ADR 选 flask-smorest，调整步骤 3 的实现细节即可。

**文件：**

- 创建 app/presentation/api/openapi_setup.py
- 创建 scripts/generate_openapi.py
- 修改 pyproject.toml（追加 apispec, apispec-webframeworks）
- 创建 tests/test_openapi_consistency.py
- 创建 docs/openapi.json（初次由脚本生成，commit 进仓库）

- [ ] **步骤 1：写失败测试（一致性校验）**

```python
# tests/test_openapi_consistency.py
import json
import subprocess
from pathlib import Path


def test_openapi_json_is_up_to_date(tmp_path):
    """openapi.json must be regenerated whenever routes change."""
    output = tmp_path / "openapi.json"
    subprocess.run(
        ["python", "scripts/generate_openapi.py", "--output", str(output)],
        check=True,
    )
    actual = json.loads(output.read_text())
    committed = json.loads(Path("docs/openapi.json").read_text())
    assert actual == committed, (
        "docs/openapi.json is stale. Run: python scripts/generate_openapi.py"
    )


def test_openapi_covers_at_least_one_endpoint():
    spec = json.loads(Path("docs/openapi.json").read_text())
    assert len(spec.get("paths", {})) >= 1
```

- [ ] **步骤 2：运行测试验证失败**

运行 `pytest tests/test_openapi_consistency.py -v`
预期：FAIL（generate_openapi.py 不存在）

- [ ] **步骤 3：实现 openapi_setup.py**

```python
# app/presentation/api/openapi_setup.py
from __future__ import annotations

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin  # 占位；pydantic 适配下一步
from apispec_webframeworks.flask import FlaskPlugin


def build_spec(app) -> APISpec:
    spec = APISpec(
        title="QuantAtlas API",
        version="1.0.0",
        openapi_version="3.0.3",
        plugins=[FlaskPlugin(), MarshmallowPlugin()],
    )
    # 遍历所有 view function，注册到 spec
    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            view = app.view_functions.get(rule.endpoint)
            if view and hasattr(view, "_apispec_path"):
                spec.path(view=view)
    return spec
```

- [ ] **步骤 4：实现生成脚本**

```python
# scripts/generate_openapi.py
"""Generate docs/openapi.json from current Flask routes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 项目根加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bootstrap import create_app
from app.presentation.api.openapi_setup import build_spec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/openapi.json")
    args = parser.parse_args()

    app = create_app(testing=True)
    spec = build_spec(app)
    Path(args.output).write_text(json.dumps(spec.to_dict(), indent=2, sort_keys=True))
    print(f"OpenAPI spec written to {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **步骤 5：在 pyproject.toml 添加依赖**

`[project] dependencies` 末尾追加：

```toml
"apispec>=6.4.0",
"apispec-webframeworks>=1.0.0",
```

- [ ] **步骤 6：标注 whoami 端点（任务 2 创建的 /api/v1/auth/whoami）**

在 `app/presentation/api/routes_v1_auth.py` 的 `whoami` 上加 docstring（apispec 会从 docstring 解析）：

```python
@bp.get("/whoami")
def whoami():
    """Return current identity.
    ---
    get:
      tags: [auth]
      responses:
        200:
          description: Current identity
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id: {type: string}
                  auth_source: {type: string, enum: [jwt, cookie]}
        401:
          description: Unauthorized
    """
    if not g.get("identity_subject"):
        return jsonify({"error": "unauthorized"}), 401
    return jsonify({"user_id": g.identity_subject, "auth_source": g.identity_source})


whoami._apispec_path = True  # 标记为应纳入 OpenAPI 的端点
```

- [ ] **步骤 7：首次生成 openapi.json 并提交**

运行 `pip install -e .` 然后 `python scripts/generate_openapi.py`
检查 `docs/openapi.json` 包含 `/api/v1/auth/whoami` 路径

- [ ] **步骤 8：运行测试验证通过**

运行 `pytest tests/test_openapi_consistency.py -v`
预期：2 个测试 PASS

- [ ] **步骤 9：Commit**

```bash
git add app/presentation/api/openapi_setup.py scripts/generate_openapi.py docs/openapi.json tests/test_openapi_consistency.py pyproject.toml app/presentation/api/routes_v1_auth.py
git commit -m "feat(api): OpenAPI generation pipeline with apispec (M0 task 4)"
```

---

## 任务 5：前端 OpenAPI 类型生成

**文件：**

- 修改 frontend/package.json（追加 openapi-typescript devDep + npm script）
- 创建 frontend/src/api/types.ts（生成产物，commit 进仓库）
- 创建 frontend/src/api/client.ts（API 客户端骨架）

- [ ] **步骤 1：在 frontend/package.json 添加 openapi-typescript**

```bash
cd frontend
npm install --save-dev openapi-typescript@^7
```

并在 `scripts` 字段添加：

```json
"gen:api-types": "openapi-typescript ../docs/openapi.json -o src/api/types.ts"
```

- [ ] **步骤 2：首次生成类型**

运行 `cd frontend && npm run gen:api-types`
检查 `frontend/src/api/types.ts` 已生成且包含 `paths["/api/v1/auth/whoami"]`

- [ ] **步骤 3：实现 API client 骨架**

```typescript
// frontend/src/api/client.ts
import type { paths } from "./types";

type WhoamiResponse = paths["/api/v1/auth/whoami"]["get"]["responses"]["200"]["content"]["application/json"];

export async function whoami(): Promise<WhoamiResponse | null> {
  const resp = await fetch("/api/v1/auth/whoami", { credentials: "include" });
  if (resp.status === 401) return null;
  if (!resp.ok) throw new Error(`whoami failed: ${resp.status}`);
  return resp.json();
}
```

- [ ] **步骤 4：在 frontend/package.json 的 build 之前加 prebuild hook**

```json
"prebuild": "npm run gen:api-types"
```

确保每次 build 自动重新生成类型，避免漂移。

- [ ] **步骤 5：验证类型生成可重复**

运行 `cd frontend && rm -f src/api/types.ts && npm run gen:api-types && git diff --exit-code src/api/types.ts`
预期：exit 0（生成结果与 commit 一致）

- [ ] **步骤 6：Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/api/types.ts frontend/src/api/client.ts
git commit -m "feat(frontend): generate TS types from OpenAPI; whoami client (M0 task 5)"
```

---
## 任务 6：流式事件 model 范式 + events.md 骨架

**文件：**

- 创建 app/domain/events/__init__.py（如已存在则确认导出约定）
- 创建 app/domain/events/_example_watchlist.py（示例 model；M1/M2 时由真实事件替代）
- 创建 docs/events.md
- 创建 tests/unit/events/test_event_model_serializes.py

- [ ] **步骤 1：写失败测试**

```python
# tests/unit/events/test_event_model_serializes.py
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from app.domain.events._example_watchlist import WatchlistAnomalyDetectedEvent


def test_event_model_dump_to_dict():
    event = WatchlistAnomalyDetectedEvent(
        user_id="u1",
        symbol="AAPL",
        anomaly_type="price_spike",
        severity=3,
        detected_at=datetime(2026, 6, 21, tzinfo=timezone.utc),
    )
    payload = event.model_dump(mode="json")
    assert payload["symbol"] == "AAPL"
    assert payload["severity"] == 3
    assert payload["detected_at"].startswith("2026-06-21T")


def test_event_model_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        WatchlistAnomalyDetectedEvent(
            user_id="u1",
            symbol="AAPL",
            anomaly_type="price_spike",
            severity=99,  # 超出 1-5 范围
            detected_at=datetime.now(timezone.utc),
        )
```

- [ ] **步骤 2：运行测试验证失败**

运行 `pytest tests/unit/events/test_event_model_serializes.py -v`
预期：FAIL（模块不存在）

- [ ] **步骤 3：实现示例 event model**

```python
# app/domain/events/_example_watchlist.py
"""Example event model demonstrating the pattern.

This file is the M0 reference. M1/M2 will replace it with real events
discovered while migrating streaming-heavy pages.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WatchlistAnomalyDetectedEvent(BaseModel):
    """Triggered when watchlist agent detects price/volume/news anomaly."""

    user_id: str
    symbol: str
    anomaly_type: Literal["price_spike", "volume_spike", "news"]
    severity: int = Field(ge=1, le=5)
    detected_at: datetime
```

- [ ] **步骤 4：创建 docs/events.md 骨架**

写入以下内容到 `docs/events.md`：

    # 流式事件清单

    > 本文档列出所有 Socket.IO 事件与 SSE 帧。每个事件必须有对应的 pydantic model（见 app/domain/events/）。
    > 迁移流式页面时，把该页面消费的事件加到这里。

    ## 事件格式约定

    每个事件一段，按以下结构：

        ## <event-name> (Socket.IO | SSE)
        - payload: <ModelClassName> (app/domain/events/<file>.py)
        - 触发: <什么条件下发出>
        - 频率: <突发/周期/限流策略>
        - 消费方: <哪些前端页面 / Flutter 屏幕会订阅>

    ---

    ## watchlist.anomaly_detected (Socket.IO) — 示例

    - payload: WatchlistAnomalyDetectedEvent (app/domain/events/_example_watchlist.py)
    - 触发: 自选股 agent 检测到价格/量能/新闻异常
    - 频率: 突发，单用户单 symbol 5 分钟内最多一次
    - 消费方: 自选股页面、Jarvis 通知面板

    > 此条为 M0 范式示例。真实事件由 M1/M2 迁移流式页面时补充。

- [ ] **步骤 5：运行测试验证通过**

运行 `pytest tests/unit/events/test_event_model_serializes.py -v`
预期：2 个测试 PASS

- [ ] **步骤 6：Commit**

```bash
git add app/domain/events/_example_watchlist.py docs/events.md tests/unit/events/test_event_model_serializes.py
git commit -m "feat(events): pydantic event model pattern + events.md skeleton (M0 task 6)"
```

---
## 任务 7：Playwright E2E 框架与核心流脚本

**文件：**

- 创建 tests/e2e/package.json
- 创建 tests/e2e/playwright.config.ts
- 创建 tests/e2e/.gitignore
- 创建 tests/e2e/fixtures/test_user.ts
- 创建 tests/e2e/specs/01_login.spec.ts
- 创建 tests/e2e/specs/02_workbench.spec.ts
- 创建 tests/e2e/specs/03_stock_select.spec.ts
- 创建 tests/e2e/specs/04_backtest.spec.ts
- 创建 tests/e2e/specs/05_streaming.spec.ts

- [ ] **步骤 1：初始化 Playwright 工程**

```bash
mkdir -p tests/e2e
cd tests/e2e
npm init -y
npm install --save-dev @playwright/test@^1.45 typescript @types/node
npx playwright install --with-deps chromium
```

- [ ] **步骤 2：写 playwright.config.ts**

```typescript
// tests/e2e/playwright.config.ts
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./specs",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://127.0.0.1:5000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
```

- [ ] **步骤 3：写测试 fixture**

```typescript
// tests/e2e/fixtures/test_user.ts
export const TEST_USER = {
  username: process.env.E2E_USERNAME ?? "e2e-user",
  password: process.env.E2E_PASSWORD ?? "e2e-pass",
};
```

- [ ] **步骤 4：写 spec 01 登录流**

```typescript
// tests/e2e/specs/01_login.spec.ts
import { test, expect } from "@playwright/test";
import { TEST_USER } from "../fixtures/test_user";

test("login lands on /app dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[name="username"]', TEST_USER.username);
  await page.fill('input[name="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL(/\/app\/?$/);
  await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible();
});
```

- [ ] **步骤 5：写 spec 02 workbench**

```typescript
// tests/e2e/specs/02_workbench.spec.ts
import { test, expect } from "@playwright/test";
import { TEST_USER } from "../fixtures/test_user";

test.beforeEach(async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[name="username"]', TEST_USER.username);
  await page.fill('input[name="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
});

test("dashboard renders core cards", async ({ page }) => {
  await page.goto("/app");
  // 占位选择器；M1 迁 daily_workbench 时换为真实 data-testid
  await expect(page.locator('[data-testid="dashboard-root"]')).toBeVisible({ timeout: 10_000 });
});
```

- [ ] **步骤 6：写 spec 03 选股流（依赖 M1，初始 skip）**

```typescript
// tests/e2e/specs/03_stock_select.spec.ts
import { test, expect } from "@playwright/test";
import { TEST_USER } from "../fixtures/test_user";

test.beforeEach(async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[name="username"]', TEST_USER.username);
  await page.fill('input[name="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
});

test("market panorama -> stock detail", async ({ page }) => {
  await page.goto("/app/market-panorama");
  await page.locator('[data-testid="stock-row"]').first().click();
  await expect(page).toHaveURL(/\/app\/stock\//);
  await expect(page.locator('[data-testid="stock-detail-symbol"]')).toBeVisible();
});
```

- [ ] **步骤 7：写 spec 04 回测流**

```typescript
// tests/e2e/specs/04_backtest.spec.ts
import { test, expect } from "@playwright/test";
import { TEST_USER } from "../fixtures/test_user";

test.beforeEach(async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[name="username"]', TEST_USER.username);
  await page.fill('input[name="password"]', TEST_USER.password);
  await page.click('button[type="submit"]');
});

test("backtest submission shows up in run history", async ({ page }) => {
  await page.goto("/app/backtest");
  await page.click('[data-testid="run-backtest-btn"]');
  await expect(page.locator('[data-testid="run-status"]')).toContainText(
    /running|queued|completed/,
    { timeout: 30_000 },
  );
  await page.goto("/app/runs");
  await expect(page.locator('[data-testid="run-row"]').first()).toBeVisible();
});
```

- [ ] **步骤 8：写 spec 05 流式（M2 启用，初始 skip）**

```typescript
// tests/e2e/specs/05_streaming.spec.ts
import { test, expect } from "@playwright/test";

test("ai chat streams first SSE frame", async ({ page }) => {
  test.skip(true, "ai_chat 页面未迁移；M2 任务启用");
  // 占位实现保留供 M2 直接启用
});
```

- [ ] **步骤 9：写 .gitignore**

写入 `tests/e2e/.gitignore`：

    node_modules/
    playwright-report/
    test-results/
    playwright/.cache/

- [ ] **步骤 10：本地验证（开发者机器）**

终端 1 启动后端：`python -m flask run --port 5000`
终端 2 跑 E2E：`cd tests/e2e && npx playwright test`
预期：spec 01 通过；spec 02/03/04 取决于已迁页面是否带 data-testid（首次跑可能失败，记录待补）；spec 05 skip。

- [ ] **步骤 11：补 data-testid 到已迁的 SPA 页面**

逐个打开 `frontend/src/pages/{Dashboard,MarketPanorama,Backtest,RunHistory,StockDetail}.tsx`，给关键容器加上 spec 中引用的 `data-testid`：
- Dashboard 根容器：`data-testid="dashboard-root"`
- MarketPanorama 行：`data-testid="stock-row"`
- StockDetail symbol：`data-testid="stock-detail-symbol"`
- Backtest 按钮：`data-testid="run-backtest-btn"`、状态：`data-testid="run-status"`
- RunHistory 行：`data-testid="run-row"`

- [ ] **步骤 12：再次跑 E2E 验证全绿**

运行 `cd tests/e2e && npx playwright test`
预期：spec 01/02/03/04 全部 PASS，spec 05 SKIP

- [ ] **步骤 13：Commit**

```bash
git add tests/e2e/ frontend/src/pages/
git commit -m "feat(test): Playwright E2E framework + 4 core flows + skipped streaming (M0 task 7)"
```

---
## 任务 8：CI 新增 e2e job 与 openapi-check job

**文件：**

- 修改 .github/workflows/ci.yml
- 创建 scripts/seed_e2e_user.py

- [ ] **步骤 1：在 ci.yml 末尾追加 openapi-check job**

```yaml
  openapi-check:
    name: OpenAPI consistency
    runs-on: ubuntu-latest
    needs: [compile]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - name: Install dependencies
        run: |
          pip install --upgrade pip
          pip install -e ".[test]"
      - name: Verify openapi.json is up to date
        run: |
          python scripts/generate_openapi.py --output /tmp/openapi.json
          diff -u docs/openapi.json /tmp/openapi.json
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Verify TS types regenerate cleanly
        working-directory: frontend
        run: |
          npm ci
          npm run gen:api-types
          git diff --exit-code src/api/types.ts
```

- [ ] **步骤 2：在 ci.yml 末尾追加 e2e job**

```yaml
  e2e:
    name: Playwright E2E
    runs-on: ubuntu-latest
    needs: [test, frontend-security]
    services:
      mysql:
        image: mysql:8
        env:
          MYSQL_ROOT_PASSWORD: root
          MYSQL_DATABASE: quant_atlas
        ports:
          - 3306:3306
        options: --health-cmd "mysqladmin ping" --health-interval 10s --health-timeout 5s --health-retries 3
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install backend deps
        run: |
          pip install --upgrade pip
          pip install -e ".[test]"
      - name: Build frontend
        working-directory: frontend
        run: |
          npm ci
          npm run build
      - name: Install Playwright deps
        working-directory: tests/e2e
        run: |
          npm ci
          npx playwright install --with-deps chromium
      - name: Seed E2E user
        env:
          MYSQL_HOST: 127.0.0.1
          MYSQL_PORT: 3306
          MYSQL_USER: root
          MYSQL_PASSWORD: root
          MYSQL_DATABASE: quant_atlas
        run: python scripts/seed_e2e_user.py
      - name: Start backend in background
        env:
          MYSQL_HOST: 127.0.0.1
          MYSQL_PORT: 3306
          MYSQL_USER: root
          MYSQL_PASSWORD: root
          MYSQL_DATABASE: quant_atlas
          REDIS_URL: redis://127.0.0.1:6379/0
          FLASK_ENV: testing
          JWT_SECRET: e2e-secret
        run: |
          python -m flask --app app.bootstrap:create_app run --port 5000 &
          sleep 5
      - name: Run Playwright tests
        working-directory: tests/e2e
        env:
          E2E_BASE_URL: http://127.0.0.1:5000
          E2E_USERNAME: e2e-user
          E2E_PASSWORD: e2e-pass
        run: npx playwright test --reporter=github
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: tests/e2e/playwright-report/
          retention-days: 7
```

- [ ] **步骤 3：写 seed_e2e_user.py 脚本**

```python
# scripts/seed_e2e_user.py
"""Seed an E2E test user. Idempotent."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.bootstrap import create_app


def main():
    app = create_app(testing=True)
    with app.app_context():
        # 实际 user_service 名称在 M0 实施时根据 app/modules/user/services/ 调整
        svc = app.extensions["user_service"]
        username = os.environ.get("E2E_USERNAME", "e2e-user")
        password = os.environ.get("E2E_PASSWORD", "e2e-pass")
        try:
            svc.create_user(username=username, password=password)
            print(f"Created E2E user: {username}")
        except Exception as exc:
            if "exists" in str(exc).lower():
                print(f"E2E user already exists: {username}")
            else:
                raise


if __name__ == "__main__":
    main()
```

注：实际 `create_user` API 名称可能不同，步骤实施时需对照 `app/modules/user/services/user_service.py` 调整。

- [ ] **步骤 4：本地手动验证 ci.yml 语法**

运行 `actionlint .github/workflows/ci.yml`（需先安装 actionlint），或推送到分支让 GitHub 校验
预期：无 syntax error

- [ ] **步骤 5：Commit**

```bash
git add .github/workflows/ci.yml scripts/seed_e2e_user.py
git commit -m "ci: add openapi-check and e2e jobs (M0 task 8)"
```

- [ ] **步骤 6：推到 PR 验证 CI 全绿**

推送分支并开 PR；预期所有 job 全部通过：compile / lint / smoke / test / frontend-security / openapi-check / e2e。

---
## 任务 9：页面迁移 PR 模板

**文件：**

- 创建 .github/PULL_REQUEST_TEMPLATE/page_migration.md
- 创建 docs/superpowers/migration-pr-checklist.md

- [ ] **步骤 1：写 PR 模板**

写入 `.github/PULL_REQUEST_TEMPLATE/page_migration.md`：

    # Page Migration: <jinja-page-name>

    ## 迁移基本信息

    - Jinja 路径: /<path>
    - SPA 路径: /app/<path>
    - 里程碑: M1 / M2 / M3
    - 关联设计: docs/superpowers/specs/2026-06-21-flask-to-spa-migration-design.md

    ## 必须项检查清单

    ### 后端
    - [ ] 该页面消费的所有 API 端点已加 pydantic schema
    - [ ] 已运行 `python scripts/generate_openapi.py` 并提交 docs/openapi.json 变更
    - [ ] 该页面如使用流式接口，事件已加 pydantic model 并在 docs/events.md 登记
    - [ ] Jinja 路由替换为 redirect("/app/<path>", code=302)（302 灰度阶段，1 周后切 301）

    ### 前端
    - [ ] React 页面在 frontend/src/pages/ 下实装
    - [ ] 在 frontend/src/App.tsx 注册路由
    - [ ] 已运行 `cd frontend && npm run gen:api-types` 并提交 frontend/src/api/types.ts 变更
    - [ ] 关键容器加 data-testid 以便 E2E

    ### 测试
    - [ ] 如属于 5 条核心流之一，对应 Playwright spec 已更新并通过
    - [ ] 长尾页面（M3）：附 5 张以上截图

    ### 上线步骤（合并后）
    - [ ] PR 合并并部署到 staging 后，运行 `curl -I http://staging/<old-path>` 确认 302 与 Location 正确
    - [ ] 灰度 1 周观察日志，无回归后开后续 PR 把 302 改 301

- [ ] **步骤 2：写人工核对清单**

写入 `docs/superpowers/migration-pr-checklist.md`，与 PR 模板内容一致但带详细的"为什么要做这一步"解释，便于团队培训。例如：

- 为什么 302 灰度而非直接 301：见设计文档第 2.2 节、风险 R3
- 为什么 events.md 登记：见设计文档第 6 节
- 为什么 data-testid：避免 E2E spec 因 className 变更而频繁返工

- [ ] **步骤 3：Commit**

```bash
git add .github/PULL_REQUEST_TEMPLATE/page_migration.md docs/superpowers/migration-pr-checklist.md
git commit -m "docs: page migration PR template + checklist (M0 task 9)"
```

---

## 任务 10：M0 退出验证

**文件：** 无（验收任务，无文件变更）

- [ ] **步骤 1：本地全套验证**

```bash
# 后端
pytest tests/unit/auth tests/integration/test_dual_auth.py tests/test_openapi_consistency.py tests/unit/events -v

# 前端 build
cd frontend && npm run build && cd ..

# 重新生成 openapi & types 应无 diff
python scripts/generate_openapi.py
git diff --exit-code docs/openapi.json
cd frontend && npm run gen:api-types && git diff --exit-code src/api/types.ts && cd ..

# E2E（需要本地 mysql/redis 运行）
cd tests/e2e && npx playwright test
```

预期：全部通过，无 diff。

- [ ] **步骤 2：CI 全绿**

确认 GitHub Actions 所有 job 通过：compile / lint / smoke / test / frontend-security / openapi-check / e2e

- [ ] **步骤 3：M0 退出会议（人工）**

确认设计文档第 8 节 M0 退出条件已满足：

- JWT 双轨认证已生效
- apispec/openapi 流水线已跑通
- Playwright 框架 + 5 条核心 E2E 已建立（其中 ai_chat 流 skip 至 M2）
- frontend api/ 目录骨架就位
- 事件 pydantic model 范式已建立
- CI 校验规则上线
- 已迁 11 个页面回归通过
- 新页面迁移 PR 模板可用

- [ ] **步骤 4：宣告 M1 启动**

在团队周会宣布 M0 完成；M1 计划文件由项目所有者重新触发 brainstorming → writing-plans 流程产出（无需重做设计文档，复用现有设计文档第 3.2 节的 15 个核心流页面清单）。

---

## 附录：M0 与设计文档第 9 节风险的对应关系

| 风险 | M0 中的缓解措施 |
|---|---|
| R1 双轨认证逻辑漂移 | 任务 2 步骤 2 的 4 个集成测试即基线 |
| R3 301 缓存写错 | 任务 9 PR 模板强制要求 302 灰度阶段 |
| R4 OpenAPI schema 跟不上 | 任务 8 openapi-check job + 任务 9 PR 模板检查项 |
| R6 流式 token 通过 URL 暴露 | 留待 M2 第一条流式页面迁移时实现一次性 token 端点 |
| R7 Flutter 契约不友好 | 任务 0 ADR-0001 / 0002 / 0003 中应明确移动端约束清单 |

---

## 执行交接

**计划已完成并保存到 `docs/superpowers/plans/2026-06-21-flask-to-spa-m0-foundation.md`。两种执行方式：**

**1. 子代理驱动（推荐）** — 每个任务调度一个新的子代理，任务间审查，快速迭代

**2. 内联执行** — 在当前会话中使用 executing-plans 技能执行任务，批量执行并设有检查点

**M1/M2/M3/M4 计划：** M0 收尾时由项目所有者重新触发 brainstorming → writing-plans 流程产出对应里程碑的实现计划（无需重做设计文档）。