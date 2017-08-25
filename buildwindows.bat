@rem ==========
@set PYTHON_DIR=C:\Python27
@set GRAPHVIZ_DIR=C:\Program Files (x86)\Graphviz2.38
@set RoboCopy=C:\Windows\System32\Robocopy.exe

@rem ====== Clean up
@set /P X=Cleaning up dist/ and build/ ...
@rmdir /S /Q dist
@rmdir /S /Q build
@echo done.

@rem ======= RUN py2exe
%PYTHON_DIR%\python.exe setup.py py2exe

@rem === Copy to dist/
copy openhrivoice\*.xsd dist
copy "%GRAPHVIZ_DIR%\bin\*.dll" dist

@rem === Cleanup dist/Qt*.dll
del dist\Qt*.dll

copy "%GRAPHVIZ_DIR%\bin\dot.exe" dist
copy "%PYTHON_DIR%\Lib\site-packages\gtk-2.0\runtime\bin\*.dll" dist
%RoboCopy% /S "%PYTHON_DIR%\Lib\site-packages\gtk-2.0\runtime\share" dist\share
%RoboCopy% /S "%PYTHON_DIR%\Lib\site-packages\gtk-2.0\runtime\etc" dist\etc

@rem === check dot.exe
cd dist
dot.exe -c

@rem === cleanup document files
cd ..
rmdir /S /Q dist\share\doc
rmdir /S /Q dist\share\gtk-doc
rmdir /S /Q dist\share\man
