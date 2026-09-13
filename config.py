"""
Configuración central y utilidades comunes para el gestor de LeetCode.
"""

import os
import json
import re
from pathlib import Path

# Rutas base
PROJECT_DIR = Path(__file__).resolve().parent
PROBLEMS_DIR = PROJECT_DIR / "problems"
CONFIG_FILE = PROJECT_DIR / "config.json"
COMMON_DIR = PROJECT_DIR / "common"
PROMPTS_DIR = PROJECT_DIR / "prompts"

# Asegurar directorios
PROBLEMS_DIR.mkdir(parents=True, exist_ok=True)
COMMON_DIR.mkdir(parents=True, exist_ok=True)
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

# Colores ANSI para terminal
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    # Texto
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"
    
    # Fondo
    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_BLUE = "\033[44m"
    BG_DARK = "\033[100m"

def load_config() -> dict:
    """Carga la configuración de usuario (cookies de sesión, etc.)."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(data: dict):
    """Guarda la configuración de usuario."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_credentials() -> tuple[str | None, str | None]:
    """Retorna (session, csrf_token)."""
    cfg = load_config()
    session = os.environ.get("LEETCODE_SESSION") or cfg.get("LEETCODE_SESSION")
    csrf = os.environ.get("LEETCODE_CSRF_TOKEN") or cfg.get("LEETCODE_CSRF_TOKEN")
    return session, csrf

def sanitize_slug(text: str) -> str:
    """Extrae el slug de un ID, nombre o URL completa de LeetCode."""
    text = text.strip()
    # Si es URL: https://leetcode.com/problems/two-sum/...
    match = re.search(r"leetcode\.com/problems/([^/]+)", text)
    if match:
        return match.group(1).lower()
    return text.lower().replace(" ", "-")

def find_problem_folder(target: str) -> Path | None:
    """Encuentra la carpeta del problema dado su ID o slug."""
    target = target.strip().lower()
    if not PROBLEMS_DIR.exists():
        return None
    
    # Búsqueda exacta por nombre de directorio
    for folder in PROBLEMS_DIR.iterdir():
        if not folder.is_dir():
            continue
        meta_file = folder / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if (
                    str(meta.get("id")) == target
                    or str(meta.get("frontend_id")) == target
                    or meta.get("slug", "").lower() == target
                    or folder.name.lower() == target
                ):
                    return folder
            except Exception:
                pass
        # Comprobar si el nombre de carpeta coincide (ej: 0001-two-sum)
        if folder.name.lower() == target or folder.name.lower().endswith(f"-{target}"):
            return folder
            
    return None

def get_active_problem() -> str | None:
    """
    Retorna el identificador o nombre de carpeta del problema activo.
    Prioridad:
    1. Si el directorio actual (CWD) es una carpeta de problema o está dentro de ella.
    2. Si no, busca en config.json -> 'active_problem'.
    """
    try:
        cwd = Path.cwd().resolve()
        probs = PROBLEMS_DIR.resolve()
        if cwd != probs and probs in cwd.parents:
            curr = cwd
            while curr.parent != probs and curr.parent != curr:
                curr = curr.parent
            if curr.parent == probs and curr.is_dir():
                return curr.name
    except Exception:
        pass

    cfg = load_config()
    active = cfg.get("active_problem")
    if active:
        folder = find_problem_folder(str(active))
        if folder:
            return folder.name
    return None

def set_active_problem(target: str) -> str | None:
    """Guarda el problema como activo en config.json."""
    folder = find_problem_folder(target)
    active_name = folder.name if folder else target
    cfg = load_config()
    cfg["active_problem"] = active_name
    save_config(cfg)
    return active_name

def resolve_target(target: str | None = None) -> tuple[Path | None, str | None]:
    """
    Resuelve la carpeta del problema y su identificador.
    Si se proporciona target, lo busca y actualiza el problema activo.
    Si no se proporciona, utiliza el problema activo detectado.
    """
    if target:
        folder = find_problem_folder(target)
        if folder:
            set_active_problem(folder.name)
            return folder, folder.name
        return None, target

    active = get_active_problem()
    if active:
        folder = find_problem_folder(active)
        if folder:
            return folder, active
    return None, None

def open_in_editor(file_path: Path, interactive: bool = True) -> bool:
    """Abre un archivo en el editor configurado o detectado en el sistema."""
    import shutil
    import subprocess
    import sys
    import shlex

    cfg = load_config()
    editor_str = cfg.get("editor") or os.environ.get("VISUAL") or os.environ.get("EDITOR")
    
    if not editor_str:
        for candidate in ["code", "cursor", "nvim", "vim", "nano", "gedit"]:
            if shutil.which(candidate):
                editor_str = candidate
                break

    if not editor_str:
        if sys.platform == "darwin":
            editor_str = "open"
        elif sys.platform.startswith("linux"):
            if shutil.which("xdg-open"):
                editor_str = "xdg-open"
        elif sys.platform == "win32":
            editor_str = "notepad"

    if not editor_str:
        print(f"{Colors.YELLOW}[!] No se detecto un editor en el sistema. Abre el archivo manualmente:{Colors.RESET}")
        print(f"    {file_path}")
        return False

    try:
        cmd_parts = shlex.split(editor_str)
        cmd = cmd_parts + [str(file_path)]
        exe = cmd_parts[0]
        exe_base = Path(exe).name.lower()

        term_editors = ["nvim", "vim", "nano", "vi", "emacs", "hx", "helix", "micro"]
        is_term_editor = (
            any(exe_base == te or exe_base.startswith(te) for te in term_editors)
            or ("--inline" in cmd_parts)
        )

        if is_term_editor:
            if sys.stdin.isatty():
                subprocess.run(cmd)
            else:
                if "omarchy-launch-editor" in exe:
                    alt_cmd = [c for c in cmd_parts if c != "--inline"] + [str(file_path)]
                    subprocess.Popen(alt_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"{Colors.YELLOW}[!] No se pudo abrir el editor ({editor_str}): {e}{Colors.RESET}")
        return False

