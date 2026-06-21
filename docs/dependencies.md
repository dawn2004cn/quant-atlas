# 依赖管理约定



> 阶段 F（2026-06-16）更新 · 可选 extras 与 requirements-*.txt 双向对齐



## 单一事实源



| 类型 | 权威文件 | 说明 |

|------|----------|------|

| Python 运行时依赖 | `requirements.txt` ↔ `pyproject.toml` `[project.dependencies]` | pip / Docker / CI 主入口 |

| 可选计算栈 | `[compute]` extra ↔ `requirements-compute.txt` | Polars、VectorBT |

| Qlib 栈 | `[qlib]` extra ↔ `requirements-qlib.txt` | pyqlib（`rdagent` 保留在主运行时依赖） |

| 测试工具链 | `[test]` extra | pytest、ruff（CI 仍可直接 `pip install`） |

| Python 工具链配置 | `pyproject.toml` | pytest、ruff、coverage |



## 安装方式



```bash

# 最小运行时（与 requirements.txt 等价）

pip install -r requirements.txt

# 或

pip install -e .



# 全量可选栈

pip install -e ".[compute,qlib]"



# 开发 + 测试

pip install -e ".[test]"

```



遗留 `requirements-compute.txt` / `requirements-qlib.txt` 保留为兼容入口；内容须与 extras 一致，由 `scripts/check_dependency_drift.py` 校验。



## 前端 lock



- **权威**：根目录 `package-lock.json`（npm）

- 不使用 `bun.lock` / `bun.lockb`



## CI 安全扫描



- Python：`pip-audit`（`.github/workflows/ci.yml` → `security` job）

- 前端：`npm audit --audit-level=high`（`frontend-security` job）

- 依赖漂移：`python scripts/check_dependency_drift.py`（`lint` job）



## 变更流程



1. 修改 `requirements.txt` 时同步 `pyproject.toml` `[project.dependencies]`

2. 修改可选栈时同步对应 extra 与 `requirements-*.txt`

3. 本地 `python scripts/check_dependency_drift.py && pytest -m "not slow" -q`

4. `pip-audit` 无 CRITICAL/HIGH

5. 在 `REFACTORING_LOG.md` 记录重大版本升级



## 覆盖率阈值



| 配置位置 | `fail_under` | 说明 |

|----------|--------------|------|

| `pyproject.toml` `[tool.coverage.report]` | 30 | 本地 coverage 报告 |

| `.github/workflows/ci.yml` pytest | `--cov-fail-under=50` | CI gate |



提升至更高阈值前须在本地 `pytest --cov=app` 实测通过。



## 阶段三 profile



| Profile | 服务 |

|---------|------|

| `observability` | prometheus + grafana |

| `sidecar` | market-sidecar (FastAPI :8001) |

