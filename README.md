## Inspector de Programas y Creador de Portables

Herramientas para convertir instalaciones de software en paquetes portables totalmente documentados. El flujo cubre desde la exportación de datos trazados (por ejemplo con *Uninstall Tool* o *Geek Uninstaller*), la conversión automática a archivos de configuración y la generación de carpetas listas para mover de PC a PC junto con scripts de restauración.

### Características principales
- **`trace_xml_to_config.py`** transforma el XML producido por “Install and Trace”/“Traced Data → View as XML…” en un JSON listo para empaquetar.
- **`portable_packager.py`** copia carpetas, archivos sueltos, claves de registro, servicios, tareas programadas y accesos directos en una carpeta portable y crea un `Restore_Template.cmd` personalizable.
- **Ejemplos reales**: trazas de ProtonPass y un demo sintético sirven como referencia para entender la estructura del JSON.
- **Documentación guiada**: `PORTABLE_WORKFLOW.md` explica paso a paso cómo capturar, exportar y restaurar una aplicación.
- **Git LFS**: los ejecutables pesados (>100 MB) se almacenan con LFS para que el repositorio siga siendo ligero.

### Requisitos
- Windows 10/11 con PowerShell o CMD.
- Python 3.10+ (los scripts usan solo biblioteca estándar).
- Git con [Git LFS](https://git-lfs.github.com/) inicializado (`git lfs install`).
- Herramienta de trazado (Uninstall Tool, Geek Uninstaller, etc.) para generar el XML de entrada.
- (Opcional) [Qt for Python / PySide6](https://doc.qt.io/qtforpython/) para usar la interfaz gráfica (`pip install -r requirements.txt`).

### Estructura del repositorio
```
portable_packager.py          # Empaquetador principal
trace_xml_to_config.py        # Conversor de XML a JSON
portable_config.sample.json   # Plantilla de configuración manual
PORTABLE_WORKFLOW.md          # Documento detallado del proceso
languages/                    # Traducciones del UI original
samples/                      # Archivos de ejemplo (incluye traced_sample.xml)
demo_source/, demo_portable/  # Entorno sintético usado en pruebas
protonpass_config.json        # Configuración real usada para ProtonPass
protonpass_portable/          # Paquete portable resultante (archivos grandes en LFS)
RemoveService.cmd, *.exe/dat  # Herramientas originales analizadas
```

### Uso rápido
1. **Generar XML de traza**  
   Ejecuta Uninstall Tool/Geek Uninstaller en modo *Install and Trace* y exporta los resultados a XML (`Traced Data → View as XML…`).

2. **Convertir el XML a JSON**  
   ```powershell
   python trace_xml_to_config.py traced.xml --output mi_app.json --app-name "Mi App"
   ```
   Revisa `mi_app.json`, añade rutas adicionales (AppData, accesos directos, servicios, tareas) y elimina lo que no necesites. También puedes partir del `portable_config.sample.json`.

3. **Crear el paquete portable**  
   ```powershell
   python portable_packager.py mi_app.json --output MiApp_Portable
   ```
   - Usa `--dry-run` para validar rutas sin copiar.
   - El script genera `ProgramFiles/`, `ProgramData/`, `Registry/`, `Services/`, `Tasks/`, `Shortcuts/`, un `manifest.json` y un `Restore_Template.cmd`.

4. **Personalizar y ejecutar la restauración**  
   Edita `Restore_Template.cmd`, elimina los `REM` y ajusta nombres de servicios/tareas. Cópialo junto a la carpeta portable y ejecútalo en la PC destino (preferiblemente con privilegios elevados) para recrear la instalación.

### Ejemplo: ProtonPass
- `protonpass_traced.xml` y `protonpass_config.json` muestran cómo capturar una app real instalada en `%LocalAppData%`.
- `protonpass_portable/` contiene el resultado final, incluyendo los archivos en LFS y un `Restore_Template.cmd` que automatiza:
  1. Copiar `%LocalAppData%\ProtonPass`.
  2. Importar la clave `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\ProtonPass`.
  3. Restaurar el acceso directo del menú inicio.

Para inspeccionar el contenido sin descargar los binarios completos, usa `git lfs fetch --recent` o navega directamente en GitHub.

### Demo sintético
`demo_source/`, `demo_config.json` y `demo_portable/` sirven como ejemplo autocontenido con archivos muy pequeños. Puedes repetir el flujo (`python portable_packager.py demo_config.json --output demo_portable --dry-run`) para comprobar que tu entorno y permisos funcionan correctamente.

### Interfaz gráfica moderna (Qt for Python + QML)
Si prefieres evitar la terminal, el repositorio incluye una GUI construida con PySide6 + QML:

1. Instala dependencias: `pip install -r requirements.txt`.
2. Ejecuta `python gui_app/main.py`.
3. Usa las dos pestañas disponibles:
   - **Convertir XML**: selecciona el archivo exportado desde Uninstall Tool, define dónde guardar el JSON y pulsa “Convertir XML”.
   - **Generar paquete portable**: apunta al JSON, define la carpeta destino y ejecuta el empaquetado (con opción *dry-run*).
4. El panel inferior muestra el log en tiempo real; puedes abrir el JSON o la carpeta de salida con un clic.

La GUI utiliza los mismos módulos (`trace_xml_to_config` y `portable_packager`) por lo que cualquier mejora en los scripts se refleja automáticamente.

### Consejos y buenas prácticas
- Ejecuta los scripts en una consola con permisos acordes (especialmente para exportar claves de registro o consultar servicios).
- Mantén separado el directorio de trabajo y el directorio de salida; el empaquetador exige que la carpeta destino esté vacía para prevenir sobrescrituras accidentales.
- Usa `git lfs track` antes de añadir cualquier ejecutable >100 MB. Este repositorio ya rastrea los binarios de ProtonPass.
- Para auditorías o revisiones de seguridad, consulta `manifest.json` y el historial de commits (`git log --stat`).

### Licencia y soporte
Los scripts se distribuyen sin garantía; úsalos bajo tu propia responsabilidad. Si encuentras errores o necesitas ampliar funcionalidades (por ejemplo soporte para drivers o servicios de kernel), abre un issue o un pull request describiendo el escenario.
