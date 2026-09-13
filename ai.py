#!/usr/bin/env python3
"""
Módulo de integración con Antigravity IA (subproceso agy -p)
para tutoría inteligente en LeetCode (pistas, revisiones, explicaciones y soluciones).
"""

import sys
import subprocess
import shutil
import re
from pathlib import Path

from config import Colors, resolve_target, PROMPTS_DIR

def extract_community_java_solution(folder: Path) -> str:
    """Extrae una solución en Java de la comunidad desde solutions.md."""
    sol_file = folder / "solutions.md"
    if not sol_file.exists():
        return "// No hay solución comunitaria guardada para este problema."
    
    content = sol_file.read_text(encoding="utf-8").replace("\\n", "\n").replace("\\t", "\t")
    
    # Buscar bloques de código Java (ej: ```Java ... ``` o ```java ... ```)
    java_blocks = re.findall(r'```(?:Java|java)[^\n]*\n(.*?)```', content, re.DOTALL)
    if java_blocks:
        for b in java_blocks:
            b_clean = b.strip()
            if "class Solution" in b_clean and len(b_clean) > 60:
                return b_clean
        return java_blocks[0].strip()

    # Si no hay bloque formal de código Java, devolver la primera sección
    sections = content.split("## 🏆")
    if len(sections) > 1:
        first = sections[1]
        if "\n---\n" in first:
            first = first.split("\n---\n")[0]
        return first.strip()[:1500]

    return content[:1000]

def check_agy_available() -> bool:
    """Verifica si agy está instalado en el PATH."""
    return shutil.which("agy") is not None

def run_ai_prompt(prompt: str, effort: str = "high") -> str:
    """Ejecuta el prompt como subproceso one-shot en Antigravity local."""
    if not check_agy_available():
        raise RuntimeError("El ejecutable 'agy' no se encuentra en el PATH.")
    
    cmd = [
        "agy",
        "-p", prompt,
        "--output-format", "text",
        "--model", "gemini-3.8-flash-high",
        "--effort", effort,
        "--disable-slash-commands"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return res.stdout.strip()

def ai_assistant(target: str | None = None, mode: str = "hint"):
    """
    Asistente de IA para el problema especificado.
    Carga el prompt desde prompts/<mode>.txt y reemplaza los placeholders:
      - {description}
      - {user_code}
      - {problem_name}
    """
    folder, problem_name = resolve_target(target)
    if not folder:
        print(f"{Colors.RED}[!] No hay ningun problema activo ni se encontro '{target}'.{Colors.RESET}")
        print(f"    Usa 'lc fetch <id|slug>' o especifica uno: 'lc ai <id|slug> [modo]'\n")
        return

    mode = mode.lower()
    prompt_file = PROMPTS_DIR / f"{mode}.txt"

    if not prompt_file.exists():
        available = [p.stem for p in sorted(PROMPTS_DIR.glob("*.txt"))]
        print(f"{Colors.RED}[!] Modo desconocido: '{mode}'. Modos disponibles en prompts/: {', '.join(available)}{Colors.RESET}")
        return

    readme_file = folder / "README.md"
    solution_file = folder / "Solution.java"

    desc = ""
    if readme_file.exists():
        with open(readme_file, "r", encoding="utf-8") as f:
            desc = f.read()

    user_code = ""
    if solution_file.exists():
        with open(solution_file, "r", encoding="utf-8") as f:
            user_code = f.read()

    if mode == "hint":
        # Registrar uso de pista en metadata.json
        meta_file = folder / "metadata.json"
        if meta_file.exists():
            try:
                import json
                import time
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["hints_used"] = meta.get("hints_used", 0) + 1
                h_log = meta.get("hints_log", [])
                h_log.append({
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "type": "ai_tutor",
                    "action": "intelligent_hints"
                })
                meta["hints_log"] = h_log
                meta["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    print(f"\n{Colors.CYAN}{Colors.BOLD}[IA TUTOR] Ejecutando prompt '{mode}' para {folder.name}...{Colors.RESET}\n")

    # Leer plantilla y reemplazar placeholders
    with open(prompt_file, "r", encoding="utf-8") as f:
        template = f.read()

    community_sol = extract_community_java_solution(folder)

    prompt = (
        template.replace("{description}", desc)
                .replace("{user_code}", user_code)
                .replace("{community_solution}", community_sol)
                .replace("{problem_name}", folder.name)
    )

    effort = "high" if mode == "hint" else "medium"

    try:
        response = run_ai_prompt(prompt, effort=effort)
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(response)
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    except Exception as e:
        print(f"{Colors.RED}[!] Error al comunicarse con el subproceso de Antigravity IA: {e}{Colors.RESET}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 ai.py <slug_o_id> [hint|review|explain|solve]")
        sys.exit(1)
    target = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) >= 3 else "hint"
    ai_assistant(target, mode)
