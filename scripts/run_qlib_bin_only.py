"""只执行 QLib Bin 转换的程序"""

from app.infrastructure.repositories.deps import create_default_qlib_pipeline_service


def main():
    """执行 QLib Bin 转换"""
    # 创建 QlibPipelineService 实例
    qlib_service = create_default_qlib_pipeline_service()
    
    # 执行 QLib Bin 转换
    # 参数说明：
    # - max_workers: 并行处理的最大工作线程数
    # - overwrite: 是否覆盖已有数据
    # - incremental: 是否增量更新
    result = qlib_service.dump_to_qlib_bin(
        max_workers=2,  # 减少工作线程数以减少内存使用
        overwrite=False,  # 不覆盖已有数据
        incremental=True  # 增量更新
    )
    
    # 输出结果
    print("QLib Bin 转换结果:")
    print(f"状态: {'成功' if result['ok'] else '失败'}")
    if not result['ok']:
        print(f"错误: {result.get('error', '未知错误')}")
        print(f"错误信息: {result.get('message', '')}")
    else:
        print(f"QLib Bin 目录: {result.get('qlib_bin_dir', '')}")
        print(f"转换模式: {result.get('mode', '')}")


if __name__ == "__main__":
    main()
