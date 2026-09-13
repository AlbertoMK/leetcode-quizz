#!/usr/bin/env python3
"""
Módulo para consultar pistas oficiales de LeetCode y registrar su uso
en los metadatos del problema.
"""

import sys
import json
import time
import re
from pathlib import Path

from config import Colors, resolve_target

def clean_hint_text(text: str) -> str:
    """Limpia etiquetas HTML básicas de la pista."""
    text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)
    text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def get_or_reveal_hint(target: str | None = None, hint_num: int | None = None):
    """Muestra una pista oficial y registra su uso en metadata.json."""
    folder, problem_name = resolve_target(target)
    if not folder:
        print(f"{Colors.RED}[!] No hay ningun problema activo ni se encontro '{target}'.{Colors.RESET}")
        print(f"    Usa 'lc fetch <id|slug>' o especifica uno: 'lc hint <id|slug> [num]'\n")
        return

    meta_file = folder / "metadata.json"
    if not meta_file.exists():
        print(f"{Colors.RED}[!] No se encontró metadata.json en {folder}{Colors.RESET}")
        return

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    official_hints = meta.get("official_hints", [])
    
    # Si no están en metadata.json, intentar extraerlas de README.md
    if not official_hints:
        readme_file = folder / "README.md"
        if readme_file.exists():
            with open(readme_file, "r", encoding="utf-8") as f:
                r_content = f.read()
            official_hints = re.findall(r'<details><summary>Pista \d+</summary>\s*\n\n(.*?)\n</details>', r_content, flags=re.DOTALL)

    if not official_hints:
        print(f"\n{Colors.YELLOW}[!] Este problema no tiene pistas oficiales cargadas.{Colors.RESET}")
        print(f"    Puedes usar el tutor IA para obtener pistas con: {Colors.CYAN}lc ai hint{Colors.RESET}\n")
        return

    total_hints = len(official_hints)
    
    # Determinar qué pista mostrar
    hints_log = meta.get("hints_log", [])
    official_consulted = [h.get("hint_number") for h in hints_log if h.get("type") == "official"]
    
    if hint_num is None:
        # Siguiente pista no vista
        next_hint = 1
        for i in range(1, total_hints + 1):
            if i not in official_consulted:
                next_hint = i
                break
            next_hint = total_hints
        target_idx = next_hint - 1
    else:
        if hint_num < 1 or hint_num > total_hints:
            print(f"{Colors.RED}[!] Número de pista inválido. Hay {total_hints} pistas disponibles (1..{total_hints}).{Colors.RESET}")
            return
        target_idx = hint_num - 1

    hint_text = clean_hint_text(official_hints[target_idx])
    hint_display_num = target_idx + 1

    # Registrar el uso en metadata.json
    meta["hints_used"] = meta.get("hints_used", 0) + 1
    hints_log.append({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "type": "official",
        "hint_number": hint_display_num,
        "total_available": total_hints
    })
    meta["hints_log"] = hints_log
    meta["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    title_str = meta.get('title', problem_name or 'Problema')[:32]
    print(f"\n{Colors.YELLOW}{Colors.BOLD}+----------------------------------------------------------------+")
    print(f"| PISTA OFICIAL {hint_display_num} de {total_hints} - {title_str:<36} |")
    print(f"+----------------------------------------------------------------+{Colors.RESET}\n")
    print(f"  {hint_text}\n")
    print(f"{Colors.GRAY}  (Pistas consultadas en este problema: {meta['hints_used']}){Colors.RESET}\n")

if __name__ == "__main__":
    target = None
    h_num = None
    if len(sys.argv) >= 2:
        if sys.argv[1].isdigit():
            h_num = int(sys.argv[1])
        else:
            target = sys.argv[1]
            if len(sys.argv) >= 3 and sys.argv[2].isdigit():
                h_num = int(sys.argv[2])
    get_or_reveal_hint(target, h_num)
