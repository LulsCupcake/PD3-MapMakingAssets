@echo off


cd "%~dp0"

cd ..

taskkill /f /im "tempo.exe" > nul 2>&1

set exe_file="C:\Users\meowc\OneDrive\Desktop\Tutorial\Tempo\tempo_cli.exe"
set settings_json="C:\Users\meowc\OneDrive\Desktop\Tutorial\Tempo\presets\default\settings.json"
set arg=package

%exe_file% %arg% --settings_json %settings_json%
%exe_file% run_game --settings_json %settings_json%

exit /b
