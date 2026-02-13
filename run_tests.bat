@echo off
REM Run all Ramses-Out tests

echo ===============================================
echo Running Ramses-Out Test Suite
echo ===============================================
echo.

cd /d "%~dp0"

REM Run individual test modules
echo Running scanner tests...
python -m unittest tests.test_scanner
if errorlevel 1 goto :error

echo.
echo Running tracker tests...
python -m unittest tests.test_tracker
if errorlevel 1 goto :error

echo.
echo Running collector tests...
python -m unittest tests.test_collector
if errorlevel 1 goto :error

echo.
echo Running models tests...
python -m unittest tests.test_models
if errorlevel 1 goto :error

echo.
echo Running config tests...
python -m unittest tests.test_config
if errorlevel 1 goto :error

echo.
echo Running integration tests...
python -m unittest tests.test_integration
if errorlevel 1 goto :error

echo.
echo ===============================================
echo All tests passed!
echo ===============================================
goto :end

:error
echo.
echo ===============================================
echo Tests failed!
echo ===============================================
exit /b 1

:end
