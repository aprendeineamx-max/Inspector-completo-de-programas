Portable Migration Workflow
===========================

Use this workflow to capture everything that Uninstall Tool/Geek Uninstaller detect during “Install and Trace” and turn it into a portable package.

1. **Generar la traza**
   - Ejecuta `UninstallToolPortable.exe` y usa la opción *Install and Trace* para instalar o registrar el programa objetivo.
   - Cuando termines, exporta la traza como XML (menú *Traced Data → View as XML*). Ese XML te dirá qué carpetas, archivos y claves de registro participan en la instalación.

2. **Construir el archivo de configuración**
   - Usa `trace_xml_to_config.py traced.xml --output my_app_config.json --app-name "Mi App"` para generar un borrador a partir del XML exportado (ver `samples/traced_sample.xml`).
   - Revisa y ajusta la salida (copias adicionales, rutas especiales, atajos, etc.).
   - Alternativamente, copia `portable_config.sample.json` y actualiza manualmente:
     - `directories`: cada carpeta que debas mover. Usa `type` = `program` para archivos de aplicación y `type` = `data` para `ProgramData`, `%AppData%`, etc. El campo `target` define la subcarpeta destino dentro de `ProgramFiles` o `ProgramData`.
     - `files`: archivos sueltos fuera de esas carpetas.
     - `registry_keys`: claves que quieres exportar (`HKLM\...` y `HKCU\...`).
     - `services` y `scheduled_tasks`: nombres tal como aparecen en `services.msc` o `schtasks /query`.
     - `shortcuts`: rutas a `.lnk` que quieras conservar.

3. **Empaquetar**
   ```powershell
   python portable_packager.py my_app_config.json --output C:\PortableApps\MyApp
   ```
   - Usa `--dry-run` para validar antes de copiar.
   - El script crea:
     ```
     PortableRoot/
       ProgramFiles/
       ProgramData/
       Registry/*.reg
       Services/*.txt
       Tasks/*.xml
       Shortcuts/
       manifest.json
       Restore_Template.cmd
     ```

4. **Restaurar en otra PC**
   - Copia `PortableRoot` a la PC destino.
   - Revisa `Restore_Template.cmd`, añade los comandos específicos (por ejemplo `reg import Registry\HKLM_SOFTWARE_Example.reg` o `schtasks /create /tn ... /xml Tasks\... /f`).
   - Ejecuta el script con privilegios elevados para reinstalar servicios/tareas y restaurar las claves.

5. **(Opcional) Interceptar eliminaciones**
   - Si deseas ejecutar `UninstallToolPortable.exe` pero capturar los archivos justo antes de que los borre, crea un *shim* con EasyHook/Detours que intercepte `DeleteFileW`, `RemoveDirectoryW`, etc. Guarda el destino en una carpeta y luego cancela la operación devolviendo un error al proceso llamador.
   - Otra alternativa es usar Process Monitor para generar un log y alimentar ese log al script anterior mediante un conversor simple que traduzca los eventos en JSON.

6. **Validación**
   - Compara el contenido del paquete con el inventario del XML original (`diff -r` o `robocopy /L`) para asegurarte de que no falten archivos ocultos.
   - Importa los `.reg` en una VM y lanza el ejecutable desde `ProgramFiles` para confirmar que corre sin instalador.
