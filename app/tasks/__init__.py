"""Celery 任务包（由 ``app.celery_app`` 加载）。

新增定时/长任务时请：在本包下建模块并用 ``@celery.task(name="app.tasks....")`` 注册；
Worker 启动时由 ``app.celery_app`` 扫描 ``app.tasks.*`` 模块并注册任务（跳过 ``task_wiring`` 等辅助模块）；
在 ``app/celery_app.py`` 的 ``_beat_schedule`` 中追加条目（或按条件追加）；
在 ``task_message_store.task_label`` 的 ``_LABELS`` 中为 ``name`` 配中文简称。
全局 ``task_*`` 信号会把开始/成功/失败写入消息中心。
"""
