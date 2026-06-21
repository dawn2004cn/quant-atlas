"""CSV to qlib_bin 补齐脚本 - 带进度显示"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
from app.config import get_settings
from app.infrastructure.repositories.common.deps import create_default_qlib_pipeline_service
import pandas as pd


def csv_to_bin_with_progress(svc):
    """从 CSV 文件同步数据到 Qlib 二进制目录 - 带进度显示"""
    bin_dir = svc.qlib_bin_dir
    export_dir = svc.export_dir
    features = ["open", "high", "low", "close", "volume", "amount"]

    # 获取所有 CSV 文件和已有的 bin
    csv_files = list(export_dir.glob("*.csv"))
    csv_codes = set(f.stem for f in csv_files)

    bin_features_dir = bin_dir / "features"
    bin_codes = set()
    if bin_features_dir.exists():
        for d in bin_features_dir.iterdir():
            if d.is_dir() and d.name != "amount":
                bin_codes.add(d.name)

    # 需要处理的股票
    missing_codes = csv_codes - bin_codes
    total = len(missing_codes)

    if total == 0:
        print("✅ 所有 CSV 文件都已导出到 qlib_bin")
        return {"ok": True, "synced": 0, "total": 0}

    print(f"需要导出 {total} 只股票到 qlib_bin...")

    # 获取日期列表（从第一个 CSV 文件提取）
    sample_df = pd.read_csv(csv_files[0])
    dates = sorted(sample_df["date"].unique().tolist())

    # 写入日历
    cal_dir = bin_dir / "calendars"
    cal_dir.mkdir(parents=True, exist_ok=True)
    (cal_dir / "day.txt").write_text("\n".join(dates), encoding="utf-8")

    date_to_idx = {d: i for i, d in enumerate(dates)}
    total_days = len(dates)

    synced = 0
    failed = 0

    for i, stock_code in enumerate(sorted(missing_codes), 1):
        csv_path = export_dir / f"{stock_code}.csv"
        if not csv_path.exists():
            continue

        try:
            df = pd.read_csv(csv_path)
            rows = df.to_dict("records")

            # 转换数据
            adjusted = []
            for row in rows:
                r = {
                    "date": str(row["date"]),
                    "open": row.get("open", 0),
                    "high": row.get("high", 0),
                    "low": row.get("low", 0),
                    "close": row.get("close", 0),
                    "volume": row.get("volume", 0),
                    "amount": row.get("amount", 0),
                }
                adjusted.append(r)

            svc._write_stock_to_bin(
                stock_code, adjusted, bin_dir, export_dir,
                features, date_to_idx, total_days, export_csv=False,
            )
            synced += 1

            # 每 100 只打印一次进度
            if i % 100 == 0 or i == total:
                print(f"  进度: {i}/{total} ({synced} 成功, {failed} 失败)")

        except Exception as e:
            failed += 1
            if failed <= 5:
                print(f"  ⚠️ 失败 {stock_code}: {e}")

    print(f"\n✅ 完成: 成功 {synced}, 失败 {failed}")
    return {"ok": True, "synced": synced, "failed": failed, "total": total}


def main():
    print("=" * 50)
    print("CSV to qlib_bin 补齐任务")
    print("=" * 50)

    # 初始化服务
    settings = get_settings()
    bind_application_infrastructure(settings)
    svc = create_default_qlib_pipeline_service()

    # 执行导出
    result = csv_to_bin_with_progress(svc)
    print(f"\n结果: {result}")


if __name__ == "__main__":
    main()
