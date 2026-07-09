@echo off
setlocal

:: Launch Ramses-Out from its project directory
pushd "%~dp0"

python -m ramses_out
set "EXITCODE=%ERRORLEVEL%"

popd

if %EXITCODE% neq 0 (
    echo.
    echo [Ramses-Out] exited with error code %EXITCODE%.
    pause
)

endlocal
