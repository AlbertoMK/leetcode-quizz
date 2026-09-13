# LeetCode-Quizz (Java Edition)

Entorno CLI local para descargar problemas de LeetCode, resolverlos en Java 21, ejecutarlos contra casos de prueba locales y enviarlos a la plataforma oficial con seguimiento de estadisticas en tiempo real.

---

## Flujo Lineal y Problema Activo

A diferencia de otras herramientas que requieren navegar manualmente por el sistema de archivos, copiar rutas y alternar entre multiples pestañas para leer el enunciado y escribir el codigo, LeetCode-Quizz implementa un flujo continuo y lineal centrado en un unico archivo:

1. **Enunciado integrado en Solution.java**: Al descargar o seleccionar un problema, la descripcion completa, ejemplos, restricciones y comandos rapidos se insertan automaticamente como un bloque Javadoc (`/** ... */`) en la cabecera de `Solution.java`. No necesitas abrir navegadores ni archivos markdown adicionales.
2. **Contexto de Problema Activo**: Cada vez que descargas un problema con `lc fetch` o `lc random`, este pasa a ser el problema activo de tu sesion.
3. **Comandos sin argumentos repetitivos**: Todos los comandos (`lc test`, `lc hint`, `lc ai`, `lc submit`, `lc open`) operan por defecto sobre el problema activo. No necesitas recordar ni escribir el slug o ID en cada paso.
4. **Pistas sin spoilers bajo demanda**: El enunciado descargado no contiene las soluciones ni las pistas visibles. Las pistas oficiales se desbloquean una a una de forma intencional con `lc hint`, registrando su uso en tus estadisticas de resolucion.
5. **Apertura automatica del editor**: Tras descargar un problema, se abre directamente en tu editor configurado (`$EDITOR`, VS Code, Neovim, etc.).

---

## Requisitos Previos

- **Java 21 (OpenJDK)**: `javac` y `java` deben estar disponibles en tu `PATH`.
- **Python 3.10+**: Con librerias estandar (no requiere dependencias pesadas de terceros).

---

## Instalacion Global

Para utilizar el comando `lc` globalmente desde cualquier directorio de tu terminal, sigue las instrucciones de tu sistema operativo:

### Linux y macOS

1. Clona el repositorio:
   ```bash
   git clone https://github.com/AlbertoMK/leetcode-quizz.git
   cd leetcode-quizz
   ```

2. Asigna permisos de ejecucion al script principal:
   ```bash
   chmod +x lc.py
   ```

3. Crea un enlace simbolico en un directorio de tu `PATH` (por ejemplo, `~/.local/bin` o `/usr/local/bin`):
   ```bash
   ln -s "$(pwd)/lc.py" ~/.local/bin/lc
   ```

4. Asegurate de que `~/.local/bin` forme parte de tu variable de entorno `PATH` en tu archivo de configuracion de shell (`~/.bashrc`, `~/.zshrc`, etc.):
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

### Windows

1. Clona el repositorio en una carpeta de tu eleccion:
   ```cmd
   git clone https://github.com/AlbertoMK/leetcode-quizz.git
   cd leetcode-quizz
   ```

2. **Opcion A (CMD / Batch)**: Crea un archivo `lc.cmd` dentro de la carpeta del proyecto o en un directorio incluido en tus Variables de Entorno del Sistema (`PATH`):
   ```cmd
   @echo off
   python "%~dp0lc.py" %*
   ```

3. **Opcion B (PowerShell)**: Añade una funcion en tu perfil de PowerShell (`$PROFILE`):
   ```powershell
   function lc { python C:\ruta\completa\a\leetcode-quizz\lc.py @args }
   ```

4. Reinicia tu terminal o ventana de comandos y comprueba que `lc help` funciona correctamente.

---

## Configuracion de Credenciales (para Envio a LeetCode)

Para enviar tus soluciones oficiales a LeetCode mediante `lc submit`, necesitas configurar tus cookies de sesion:

1. Ejecuta:
   ```bash
   lc login
   ```
2. La herramienta te solicitara interactivamente los valores de:
   - `LEETCODE_SESSION`
   - `LEETCODE_CSRF_TOKEN` (o `csrftoken`)
3. Puedes obtener estos valores desde tu navegador iniciando sesion en `https://leetcode.com`, pulsando `F12` -> pestaña **Application** (o **Almacenamiento**) -> **Cookies** -> `https://leetcode.com`.
4. Los valores se guardan localmente en `config.json` (archivo ignorado por git por seguridad).

---

## Guia de Comandos

```bash
# Iniciar un problema aleatorio por dificultad (easy, medium, hard)
lc random medium

# Descargar un problema especifico por ID, slug o URL de LeetCode
lc fetch two-sum
lc fetch 1
lc fetch https://leetcode.com/problems/add-two-numbers/

# Abrir el archivo Solution.java del problema activo en tu editor
lc open

# Ejecutar las pruebas locales en Java contra los casos de prueba oficiales
lc test

# Probar tu solucion con un caso personalizado sin modificar archivos
lc test -c "[4,5,10,2]\n14"

# Desvelar la siguiente pista oficial sin spoilers (registra uso en tus metricas)
lc hint
lc hint 1        # Ver una pista especifica

# Tutor IA local (requiere Antigravity CLI 'agy' instalado)
lc ai hint       # Pistas conceptuales progresivas
lc ai review     # Revision critica de tu Solution.java
lc ai explain    # Explicacion intuitiva del enfoque optimo
lc ai solve      # Genera solucion comentada

# Enviar tu solucion oficial a LeetCode y evaluar todos los casos
lc submit

# Cambiar manualmente el problema activo
lc select two-sum

# Ver el panel de estadisticas y progreso
lc stats

# Listar todos los problemas descargados y ver el estado de cada uno
lc list

# Mostrar la ayuda general
lc help
```

---

## Estructura del Proyecto

```text
leetcode-quizz/
|-- lc.py               # CLI principal unificado y router de comandos
|-- fetch.py            # Descarga de problemas, generador de Javadoc y soluciones
|-- test_runner.py      # Compilador y ejecutor local en Java 21 (Harness dinamico)
|-- submit.py           # Envio a LeetCode y gestion de veredictos
|-- stats.py            # Panel de estadisticas y metricas de rendimiento
|-- config.py           # Gestion de configuracion, deteccion de contexto y editor
|-- config.example.json # Plantilla de configuracion limpia para nuevos usuarios
|-- common/             # Clases auxiliares para Java (ListNode, TreeNode)
|-- prompts/            # Plantillas de prompts para el tutor IA
\-- problems/           # Carpeta donde se almacenan los problemas descargados
    \-- .gitkeep        # Mantiene la carpeta en git sin incluir soluciones personales
```

---

## Configuracion Opcional (`config.json`)

Puedes personalizar las opciones en `config.json` (basandote en `config.example.json`):

- `active_problem`: Nombre de la carpeta del problema actualmente activo.
- `editor`: Comando de tu editor preferido (ej: `code`, `nvim`, `nano`). Si no se define, se detecta automaticamente mediante `$VISUAL`, `$EDITOR` o ejecutables del sistema.
- `auto_open`: Booleano (`true` o `false`). Si es `true`, abre automaticamente `Solution.java` al hacer `fetch` o `random`. Por defecto es `true`.
- `LEETCODE_SESSION`: Cookie de sesion para envios.
- `LEETCODE_CSRF_TOKEN`: Token CSRF para envios.

---

## Licencia

Este proyecto esta disponible bajo la licencia MIT.
