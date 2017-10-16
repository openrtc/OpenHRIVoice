@echo off

@set PATH_ORG=%PATH%
@set PYTHON_BASE=%~d0\local\Python27
@set PATH=%PYTHON_BASE%;%PYTHON_BASE%\Scripts;%PYTHON_BASE%\Lib;%PYTHON_BASE%\Lib\site-packages\pywin32_system32;%PYTHON_BASE%\ffmpeg\3.3.3\bin;%PATH%
@set PYTHONPATH=%PYTHON_BASE%\Lib\site-packages;%PYTHON_BASE%\Lib\site-packages\rtctree\rtmidl\;%~dp0..

@echo on

%PYTHON_BASE%\python RecaiusSpeechRecogRTC\RecaiusSpeechRecogRTC.py

@set PATH=%PATH_ORG%
