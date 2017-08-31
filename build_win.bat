@echo off

@set PATH_ORG=%PATH%
@set PYTHON_BASE=%~d0\local\Python27
@set PATH=%PYTHON_BASE%;%PYTHON_BASE%\Scripts;%PYTHON_BASE%\Lib;%PYTHON_BASE%\Lib\site-packages\pywin32_system32;%PATH%
@set PYTHONPATH=%PYTHON_BASE%\Lib\site-packages;%PYTHON_BASE%\Lib\site-packages\rtctree\rtmidl\;%~dp0..

@set RoboCopy=C:\Windows\System32\Robocopy.exe

@echo on

%PYTHON_BASE%\python.exe setup2.py py2exe

copy openhrivoice\*.conf dist 
%RoboCopy% /S openhrivoice\doc dist\doc

@echo off
@set PATH=%PATH_ORG%
@echo on
