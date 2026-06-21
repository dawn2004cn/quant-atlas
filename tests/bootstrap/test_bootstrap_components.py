from types import SimpleNamespace

from app.bootstrap_components.background import resolve_background_policy


def test_background_policy_disables_scanner_when_feature_off():
    settings = SimpleNamespace(
        enable_background_scanner=False,
        enable_celery=False,
        scanner_force_threads=False,
        enable_basic_data_scheduler=False,
    )

    policy = resolve_background_policy(settings)

    assert policy == {
        "scanner_enabled": False,
        "scanner_use_celery": False,
        "basic_data_scheduler_enabled": False,
    }


def test_background_policy_prefers_threads_when_celery_disabled():
    settings = SimpleNamespace(
        enable_background_scanner=True,
        enable_celery=False,
        scanner_force_threads=False,
        enable_basic_data_scheduler=True,
    )

    policy = resolve_background_policy(settings)

    assert policy["scanner_enabled"] is True
    assert policy["scanner_use_celery"] is False
    assert policy["basic_data_scheduler_enabled"] is True

