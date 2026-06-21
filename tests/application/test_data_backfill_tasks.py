"""存量回填与 qlib 全量种子（无网络）。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.infrastructure.messaging.task_message_store import task_label
from app.tasks.qlib_data_update import full_qlib_kline_cache_and_bin_if_empty


def test_full_qlib_skips_when_export_has_csv(tmp_path, monkeypatch) -> None:
    exp = tmp_path / "qlib_export"
    exp.mkdir(parents=True)
    (exp / "SH600519.csv").write_text("date,open\n", encoding="utf-8")
    mock_svc = MagicMock()
    mock_svc.export_dir = str(exp)
    monkeypatch.setattr(
        "app.tasks.qlib_data_update.create_default_qlib_pipeline_service",
        lambda: mock_svc,
    )
    r = full_qlib_kline_cache_and_bin_if_empty()
    assert r.get("skipped") is True
    assert r.get("reason") == "qlib_export_has_csv"
    mock_svc.ingest_symbols.assert_not_called()


def test_full_qlib_runs_ingest_and_dump_when_empty(tmp_path, monkeypatch) -> None:
    exp = tmp_path / "qlib_export"
    exp.mkdir(parents=True)
    meta = MagicMock()
    meta.to_dict.return_value = {"instruments": ["SH600519"]}
    mock_svc = MagicMock()
    mock_svc.export_dir = str(exp)
    mock_svc.ingest_symbols.return_value = meta
    mock_svc.dump_to_qlib_bin.return_value = {"ok": True}
    monkeypatch.setattr(
        "app.tasks.qlib_data_update.create_default_qlib_pipeline_service",
        lambda: mock_svc,
    )
    r = full_qlib_kline_cache_and_bin_if_empty(symbols=["600519"], period="5d")
    assert r.get("skipped") is False
    assert r.get("ok") is True
    mock_svc.ingest_symbols.assert_called_once()
    mock_svc.dump_to_qlib_bin.assert_called_once()
    call_kw = mock_svc.dump_to_qlib_bin.call_args[1]
    assert call_kw.get("incremental") is False


def test_task_labels_for_backfill_tasks() -> None:
    assert "龙虎榜" in task_label("app.tasks.data_backfill_tasks.backfill_longhu_if_empty")
    assert "龙虎榜" in task_label("app.tasks.data_backfill_tasks.backfill_longhu_full")
    assert "研报" in task_label("app.tasks.data_backfill_tasks.backfill_yanbao_full")
    assert "财报" in task_label("app.tasks.data_backfill_tasks.backfill_financial_stash_if_empty")
    assert "K线" in task_label("app.tasks.data_backfill_tasks.backfill_qlib_kline_if_empty")
    assert "新闻" in task_label("app.tasks.news_backfill_tasks.backfill_news_archive_for_codes")
    assert "RD-Agent" in task_label("rdagent.run_factor_generation")
