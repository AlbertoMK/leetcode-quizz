#!/usr/bin/env python3
"""
Módulo para recopilar estadísticas de los problemas resueltos y
visualizarlas de forma clara y visual en la terminal.
"""

import os
import json
from pathlib import Path
from collections import Counter

from config import Colors, PROBLEMS_DIR

def render_progress_bar(current: int, total: int, width: int = 20, color: str = Colors.GREEN) -> str:
    """Genera una barra de progreso visual con caracteres de bloque."""
    if total == 0:
        pct = 0.0
        filled = 0
    else:
        pct = (current / total) * 100.0
        filled = int((current / total) * width)
    
    empty = width - filled
    bar = f"{color}{'█' * filled}{Colors.GRAY}{'░' * empty}{Colors.RESET}"
    return f"[{bar}] {current:>2}/{total:<2} ({pct:>5.1f}%)"

def show_statistics():
    """Recorre todos los problemas en PROBLEMS_DIR y genera el panel de estadísticas."""
    if not PROBLEMS_DIR.exists():
        print(f"{Colors.YELLOW}[!] No se encontró el directorio de problemas.{Colors.RESET}")
        return

    problems = []
    for folder in sorted(PROBLEMS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        meta_file = folder / "metadata.json"
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    meta["folder_name"] = folder.name
                    problems.append(meta)
            except Exception:
                pass

    if not problems:
        print(f"\n{Colors.YELLOW}[!] No hay problemas descargados todavía.{Colors.RESET}")
        print(f"    💡 Comienza descargando uno con:")
        print(f"       • {Colors.CYAN}lc fetch <slug_o_id>{Colors.RESET}   (ej: lc fetch two-sum)")
        print(f"       • {Colors.CYAN}lc random [dificultad]{Colors.RESET} (ej: lc random easy)\n")
        return

    total_problems = len(problems)
    solved_count = sum(1 for p in problems if p.get("status") == "SOLVED")
    attempted_count = sum(1 for p in problems if p.get("status") == "ATTEMPTED")
    new_count = sum(1 for p in problems if p.get("status") == "NEW")

    total_submissions = sum(len(p.get("submissions", [])) for p in problems)

    # Desglose por dificultad
    diff_stats = {
        "Easy": {"total": 0, "solved": 0},
        "Medium": {"total": 0, "solved": 0},
        "Hard": {"total": 0, "solved": 0}
    }
    tag_counter = Counter()
    solved_tags = Counter()

    for p in problems:
        diff = p.get("difficulty", "Easy")
        if diff not in diff_stats:
            diff_stats[diff] = {"total": 0, "solved": 0}
        diff_stats[diff]["total"] += 1
        is_solved = p.get("status") == "SOLVED"
        if is_solved:
            diff_stats[diff]["solved"] += 1

        for tag in p.get("tags", []):
            tag_counter[tag] += 1
            if is_solved:
                solved_tags[tag] += 1

    # DIBUJAR DASHBOARD
    print()
    print(f"{Colors.CYAN}{Colors.BOLD}+---------------------------------------------------------------------------+")
    print(f"{Colors.CYAN}{Colors.BOLD}|                     PANEL DE ESTADISTICAS LEETCODE                        |")
    print(f"{Colors.CYAN}{Colors.BOLD}+---------------------------------------------------------------------------+{Colors.RESET}")
    print()

    # Resumen general
    total_bar = render_progress_bar(solved_count, total_problems, width=30, color=Colors.GREEN)
    print(f"  {Colors.BOLD}Progreso Global:{Colors.RESET}   {total_bar}")
    print(f"  {Colors.GREEN}[+] Resueltos (Solved):{Colors.RESET}   {solved_count:<4} "
          f"{Colors.YELLOW}[-] En progreso (Attempted):{Colors.RESET} {attempted_count:<4} "
          f"{Colors.GRAY}[ ] Sin empezar (New):{Colors.RESET} {new_count}")
    print(f"  {Colors.BOLD}Total de envíos:{Colors.RESET}       {total_submissions}")
    print()

    # Dificultad
    print(f"  {Colors.BOLD}Por Dificultad:{Colors.RESET}")
    easy = diff_stats.get("Easy", {"total": 0, "solved": 0})
    med = diff_stats.get("Medium", {"total": 0, "solved": 0})
    hard = diff_stats.get("Hard", {"total": 0, "solved": 0})

    print(f"    {Colors.GREEN}{'Easy':<8}{Colors.RESET} {render_progress_bar(easy['solved'], easy['total'], width=20, color=Colors.GREEN)}")
    print(f"    {Colors.YELLOW}{'Medium':<8}{Colors.RESET} {render_progress_bar(med['solved'], med['total'], width=20, color=Colors.YELLOW)}")
    print(f"    {Colors.RED}{'Hard':<8}{Colors.RESET} {render_progress_bar(hard['solved'], hard['total'], width=20, color=Colors.RED)}")
    print()

    # Top tags más practicadas
    if tag_counter:
        print(f"  {Colors.BOLD}Categorías más frecuentes:{Colors.RESET}")
        top_tags = tag_counter.most_common(5)
        tag_line = []
        for tag, count in top_tags:
            s_count = solved_tags.get(tag, 0)
            tag_line.append(f"{Colors.CYAN}{tag}{Colors.RESET}: {s_count}/{count}")
        print("    " + "  |  ".join(tag_line))
        print()

    # Métricas de Pistas (Hints)
    total_hints_used = sum(p.get("hints_used", 0) for p in problems)
    solved_problems = [p for p in problems if p.get("status") == "SOLVED"]
    solved_pure = sum(1 for p in solved_problems if p.get("hints_used", 0) == 0)
    
    print(f"  {Colors.BOLD}Uso de Pistas (Hints):{Colors.RESET}")
    if solved_count > 0:
        pure_bar = render_progress_bar(solved_pure, solved_count, width=20, color=Colors.CYAN)
        print(f"    {Colors.CYAN}Resueltos sin pistas (Solo):{Colors.RESET} {pure_bar}")
    print(f"    Total de pistas consultadas en todos los problemas: {Colors.YELLOW}{total_hints_used}{Colors.RESET}")
    print()

    # TABLA DE PROBLEMAS
    print(f"{Colors.BOLD}+------+----------------------------------+------------+-------------+--------+--------------+---------+{Colors.RESET}")
    print(f"{Colors.BOLD}| #    | Titulo                           | Dificultad | Estado      | Pistas | Mejor Tiempo | Envios  |{Colors.RESET}")
    print(f"{Colors.BOLD}+------+----------------------------------+------------+-------------+--------+--------------+---------+{Colors.RESET}")

    # Ordenar por ID numérico si es posible
    def sort_key(p):
        try:
            return int(p.get("frontend_id", 0))
        except ValueError:
            return 999999

    for p in sorted(problems, key=sort_key):
        fid = str(p.get("frontend_id", p.get("id", "?"))).ljust(4)
        raw_title = p.get("title", p.get("slug", "Unknown"))
        title = (raw_title[:30] + "..") if len(raw_title) > 32 else raw_title.ljust(32)
        
        diff = p.get("difficulty", "Easy")
        if diff == "Easy":
            diff_fmt = f"{Colors.GREEN}{diff:<10}{Colors.RESET}"
        elif diff == "Medium":
            diff_fmt = f"{Colors.YELLOW}{diff:<10}{Colors.RESET}"
        else:
            diff_fmt = f"{Colors.RED}{diff:<10}{Colors.RESET}"

        status = p.get("status", "NEW")
        if status == "SOLVED":
            status_fmt = f"{Colors.GREEN}SOLVED     {Colors.RESET}"
        elif status == "ATTEMPTED":
            status_fmt = f"{Colors.YELLOW}ATTEMPTED  {Colors.RESET}"
        else:
            status_fmt = f"{Colors.GRAY}NEW        {Colors.RESET}"

        hints_used = p.get("hints_used", 0)
        hints_fmt = str(hints_used).ljust(6)

        runtime = p.get("best_runtime") or "-"
        runtime_fmt = str(runtime).ljust(12)
        subs = str(len(p.get("submissions", []))).ljust(7)

        print(f"| {fid} | {title} | {diff_fmt} | {status_fmt} | {hints_fmt} | {runtime_fmt} | {subs} |")

    print(f"{Colors.BOLD}+------+----------------------------------+------------+-------------+--------+--------------+---------+{Colors.RESET}")
    print()

if __name__ == "__main__":
    show_statistics()
