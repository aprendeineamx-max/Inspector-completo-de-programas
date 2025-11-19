@echo off
setlocal
echo === Restore template for DemoApp ===
echo Customize the commands below before running on the target machine.

REM === Copy directory trees ===
REM Remove 'REM ' prefix once destinations look correct.
REM robocopy "%~dp0ProgramFiles\DemoApp" "%ProgramFiles%\DemoApp" /MIR /COPYALL /R:2 /W:2 /NFL /NDL /NP
REM robocopy "%~dp0ProgramData\DemoApp" "%ProgramData%\DemoApp" /MIR /COPYALL /R:2 /W:2 /NFL /NDL /NP
REM robocopy "%~dp0ProgramData\AppData\Roaming\DemoApp" "%AppData%\Roaming\DemoApp" /MIR /COPYALL /R:2 /W:2 /NFL /NDL /NP

echo Template complete. Remove REM lines after customizing.
pause
