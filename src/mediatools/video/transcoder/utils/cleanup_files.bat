@echo off
setlocal enabledelayedexpansion

echo Waiting for app to fully exit...
timeout /t 5 /nobreak >nul

echo Starting cleanup of %* patterns...

set "total_deleted=0"

:process_base
if "%~1"=="" goto done

set "base_pattern=%~1*.*"
set "folder_path=%~dp1"
set "base_name=%~n1"

echo.
echo Cleaning up: !base_name!

:: Change to the folder containing the files
cd /d "!folder_path!" 2>nul
if !errorlevel! neq 0 (
    echo ✗ Folder not found: !folder_path!
    shift
    goto process_base
)

:: Delete all files matching the base pattern
set "base_deleted=0"
for %%f in ("!base_name!*.*") do (
    if exist "%%f" (
        echo Deleting: %%~nxf
        del "%%f" /q >nul 2>&1
        if !errorlevel! equ 0 (
            echo ✓ Deleted: %%~nxf
            set /a base_deleted+=1
            set /a total_deleted+=1
        ) else (
            echo ✗ Failed: %%~nxf
        )
    )
)

if !base_deleted! equ 0 (
    echo No files found for: !base_name!
)

shift
goto process_base

:done
echo.
echo Cleanup completed! Total files deleted: !total_deleted!
timeout /t 2 /nobreak >nul
