@echo off
setlocal
echo === Restaurando ProtonPass desde paquete portable ===
echo Asegurate de ejecutar esta ventana con el usuario destino.

echo [1/3] Copiando archivos a %LocalAppData%\ProtonPass ...
robocopy "%~dp0ProgramData\AppData\Local\ProtonPass" "%LocalAppData%\ProtonPass" /MIR /COPYALL /R:2 /W:2 /NFL /NDL /NP
if %ERRORLEVEL% GEQ 8 (
    echo Error en robocopy. Revisa rutas y permisos.
    exit /b %ERRORLEVEL%
)

echo [2/3] Importando clave de registro de desinstalacion...
reg import "%~dp0Registry\HKCU_Software_Microsoft_Windows_CurrentVersion_Uninstall_ProtonPass.reg"
if errorlevel 1 (
    echo No se pudo importar el registro. Ejecuta esta ventana como el usuario correspondiente.
    exit /b 1
)

echo [3/3] Creando accesos directos del menu inicio...
set "SHORTCUT_DIR=%AppData%\Microsoft\Windows\Start Menu\Programs\Proton AG"
if not exist "%SHORTCUT_DIR%" mkdir "%SHORTCUT_DIR%"
copy "%~dp0Shortcuts\Proton Pass.lnk" "%SHORTCUT_DIR%\Proton Pass.lnk" /Y >nul

echo Listo. Abre %LocalAppData%\ProtonPass\ProtonPass.exe para usar la aplicacion.
pause
