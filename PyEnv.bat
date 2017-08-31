@echo off

@set PATH_OEG=%PATH%
@set PYTHON_BASE=%~d0\local\Python27
@set PATH=%PYTHON_BASE%;%PYTHON_BASE%\Scripts;%PYTHON_BASE%\Lib;%PYTHON_BASE%\Lib\site-packages\pywin32_system32;%PATH%
@set PYTHONPATH=%PYTHON_BASE%\Lib\site-packages;%PYTHON_BASE%\Lib\site-packages\rtctree\rtmidl\;%~dp0..

@echo on
