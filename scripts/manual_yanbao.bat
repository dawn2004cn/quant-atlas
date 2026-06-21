@echo off
chcp 65001 >nul
echo ========================================
echo 手动触发研报数据更新
echo ========================================
echo.

REM 检查虚拟环境
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [使用虚拟环境]
) else (
    echo [使用系统Python]
)

REM 检查参数
if "%1"=="" (
    echo 用法:
    echo   manual_yanbao.bat        - 同步执行
    echo   manual_yanbao.bat async  - 异步执行(Celery)
    echo.
    echo 示例:
    echo   manual_yanbao.bat
    echo   manual_yanbao.bat async
    echo.
    python scripts\manual_yanbao.py
    goto :end
)

if "%1"=="async" (
    echo [异步模式 - 使用Celery]
    python scripts\manual_yanbao.py --async
    goto :end
)

if "%1"=="sync" (
    echo [同步模式]
    python scripts\manual_yanbao.py
    goto :end
)

echo 未知参数: %1
echo.
echo 用法:
echo   manual_yanbao.bat        - 同步执行
echo   manual_yanbao.bat async  - 异步执行(Celery)

:end
pause