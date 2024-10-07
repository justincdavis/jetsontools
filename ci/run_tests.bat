@echo off
setlocal enabledelayedexpansion

@REM python3 -m pytest --log-cli-level=WARNING -rP .\tests\iterable_video\test_read.py || exit /b 1
@REM python3 -m pytest --log-cli-level=WARNING -rP .\tests\iterable_video\test_same.py || exit /b 1
@REM python3 -m pytest --log-cli-level=WARNING -rP .\tests\iterable_video\test_sequential.py || exit /b 1

python3 -m pytest --log-cli-level=WARNING -rP tests/ || exit /b 1

endlocal
