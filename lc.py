#!/usr/bin/env python3
"""
CLI Principal de LeetCode: fetch, test, submit, stats, hint, ai, open y gestion de problemas.
"""

import sys
import os
from pathlib import Path

# Añadir el directorio del script a sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from config import (
    Colors,
    PROBLEMS_DIR,
    find_problem_folder,
    get_active_problem,
    set_active_problem,
    resolve_target,
    open_in_editor
)
from fetch import fetch_and_save_problem
from test_runner import run_local_tests
from submit import submit_solution, setup_credentials_interactive
from stats import show_statistics

def print_banner():
    banner = rf"""{Colors.CYAN}{Colors.BOLD}
 _              _    ____          _        
| |    ___  ___| |_ / ___|___   __| | ___   
| |   / _ \/ _ \ __| |   / _ \ / _` |/ _ \  
| |__|  __/  __/ |_| |__| (_) | (_| |  __/  
|_____\___|\___|\__|\____\___/ \__,_|\___|  {Colors.YELLOW}[Java Edition]{Colors.RESET}
"""
    print(banner)

def print_help():
    print_banner()
    active = get_active_problem()
    if active:
        print(f"  {Colors.BOLD}Problema activo:{Colors.RESET} {Colors.GREEN}{active}{Colors.RESET}\n")
    else:
        print(f"  {Colors.GRAY}Sin problema activo seleccionado.{Colors.RESET}\n")

    print(f"{Colors.BOLD}USO:{Colors.RESET}")
    print(f"  lc <comando> [argumentos]\n")
    print(f"{Colors.BOLD}COMANDOS DISPONIBLES:{Colors.RESET}")
    print(f"  {Colors.GREEN}fetch{Colors.RESET}  <id | slug | url>       Descarga el problema y abre Solution.java en tu editor")
    print(f"  {Colors.GREEN}random{Colors.RESET} [easy | med | hard]    Descarga un problema aleatorio y lo activa")
    print(f"  {Colors.GREEN}open{Colors.RESET}   [id | slug]             Abre Solution.java del problema activo en tu editor")
    print(f"  {Colors.GREEN}test{Colors.RESET}   [id | slug] [-c input]  Ejecuta pruebas locales en Java del problema activo")
    print(f"  {Colors.GREEN}hint{Colors.RESET}   [id | slug] [num]       Muestra la siguiente pista oficial sin spoilers")
    print(f"  {Colors.GREEN}ai{Colors.RESET}     [id | slug] [modo]      Tutor IA local (hint, review, explain, solve)")
    print(f"  {Colors.GREEN}submit{Colors.RESET} [id | slug]             Sube la solucion activa a LeetCode")
    print(f"  {Colors.GREEN}select{Colors.RESET} <id | slug>             Establece manualmente el problema activo")
    print(f"  {Colors.GREEN}list{Colors.RESET}                           Lista todos los problemas descargados localmente")
    print(f"  {Colors.GREEN}stats{Colors.RESET}                          Muestra el panel de progreso y estadisticas")
    print(f"  {Colors.GREEN}login{Colors.RESET}                          Configura credenciales de LeetCode para submit")
    print(f"  {Colors.GREEN}help{Colors.RESET}                           Muestra esta ayuda\n")
    print(f"{Colors.BOLD}FLUJO LINEAL (PROBLEMA ACTIVO):{Colors.RESET}")
    print(f"  Al descargar un problema ('fetch' o 'random'), queda guardado como el problema activo.")
    print(f"  Puedes ejecutar 'lc test', 'lc hint', 'lc ai' o 'lc submit' directamente sin volver a")
    print(f"  especificar el nombre del problema.\n")
    print(f"{Colors.BOLD}EJEMPLOS:{Colors.RESET}")
    print(f"  lc random medium")
    print(f"  lc test")
    print(f"  lc hint")
    print(f"  lc ai review")
    print(f"  lc submit\n")

def list_local_problems():
    """Lista rápida de problemas descargados."""
    if not PROBLEMS_DIR.exists():
        print(f"{Colors.YELLOW}[!] No hay problemas descargados.{Colors.RESET}")
        return
    folders = sorted([f for f in PROBLEMS_DIR.iterdir() if f.is_dir()])
    if not folders:
        print(f"{Colors.YELLOW}[!] No hay problemas descargados.{Colors.RESET}")
        return

    active_name = get_active_problem()
    print(f"\n{Colors.BOLD}Problemas disponibles localmente ({len(folders)}):{Colors.RESET}\n")
    for f in folders:
        status_label = "[NEW]      "
        meta_file = f / "metadata.json"
        if meta_file.exists():
            try:
                import json
                with open(meta_file, "r") as mf:
                    st = json.load(mf).get("status")
                    if st == "SOLVED":
                        status_label = f"{Colors.GREEN}[SOLVED]   {Colors.RESET}"
                    elif st == "ATTEMPTED":
                        status_label = f"{Colors.YELLOW}[ATTEMPTED]{Colors.RESET}"
            except Exception:
                pass

        active_tag = f" {Colors.CYAN}<- ACTIVO{Colors.RESET}" if f.name == active_name else ""
        print(f"  {status_label} {Colors.BOLD}{f.name}{Colors.RESET}{active_tag}")
    print()

def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd in ["help", "-h", "--help"]:
        print_help()

    elif cmd == "fetch":
        if len(sys.argv) < 3:
            print(f"{Colors.RED}Uso: lc fetch <slug_o_id_o_url>{Colors.RESET}")
            sys.exit(1)
        target = sys.argv[2]
        fetch_and_save_problem(target)

    elif cmd in ["random", "rand"]:
        diff = sys.argv[2] if len(sys.argv) >= 3 else None
        from fetch import fetch_random_problem
        fetch_random_problem(diff)

    elif cmd == "open":
        target = sys.argv[2] if len(sys.argv) >= 3 else None
        folder, name = resolve_target(target)
        if not folder:
            print(f"{Colors.RED}[!] No hay ningun problema activo ni se encontro '{target}'.{Colors.RESET}")
            print(f"    Descarga uno con 'lc fetch <target>' o selecciónalo con 'lc select <target>'.")
            sys.exit(1)
        sol_file = folder / "Solution.java"
        if not sol_file.exists():
            print(f"{Colors.RED}[!] No existe Solution.java en {folder}{Colors.RESET}")
            sys.exit(1)
        print(f"{Colors.CYAN}[*] Abriendo Solution.java ({folder.name})...{Colors.RESET}")
        open_in_editor(sol_file)

    elif cmd in ["select", "use"]:
        if len(sys.argv) < 3:
            print(f"{Colors.RED}Uso: lc select <id | slug>{Colors.RESET}")
            sys.exit(1)
        target = sys.argv[2]
        folder, name = resolve_target(target)
        if not folder:
            print(f"{Colors.RED}[!] No se encontro el problema '{target}'.{Colors.RESET}")
            sys.exit(1)
        print(f"{Colors.GREEN}[+] Problema activo establecido en: {folder.name}{Colors.RESET}")

    elif cmd == "test":
        target = None
        custom = None
        args = sys.argv[2:]
        if args:
            if args[0] in ["-c", "--custom"]:
                custom = args[1] if len(args) > 1 else ""
            else:
                target = args[0]
                if len(args) >= 3 and args[1] in ["-c", "--custom"]:
                    custom = args[2]
        run_local_tests(target, custom)

    elif cmd == "submit":
        target = sys.argv[2] if len(sys.argv) >= 3 else None
        submit_solution(target)

    elif cmd == "stats":
        show_statistics()

    elif cmd == "list":
        list_local_problems()

    elif cmd == "ai":
        target = None
        mode = "hint"
        args = sys.argv[2:]
        modes = ["hint", "review", "explain", "solve"]
        if len(args) == 1:
            if args[0].lower() in modes:
                mode = args[0].lower()
            else:
                target = args[0]
        elif len(args) >= 2:
            target = args[0]
            mode = args[1].lower()
        from ai import ai_assistant
        ai_assistant(target, mode)

    elif cmd == "hint":
        target = None
        h_num = None
        args = sys.argv[2:]
        if len(args) == 1:
            if args[0].isdigit():
                h_num = int(args[0])
            else:
                target = args[0]
        elif len(args) >= 2:
            target = args[0]
            if args[1].isdigit():
                h_num = int(args[1])
        from hints import get_or_reveal_hint
        get_or_reveal_hint(target, h_num)

    elif cmd == "login":
        setup_credentials_interactive()

    else:
        # Si el primer argumento es un slug o id existente, sugerir o ejecutar test
        folder = find_problem_folder(cmd)
        if folder:
            set_active_problem(folder.name)
            print(f"{Colors.CYAN}[*] Problema detectado: {folder.name}{Colors.RESET}")
            print(f"    Ejecutando pruebas locales...")
            run_local_tests(cmd)
        else:
            print(f"{Colors.RED}[!] Comando desconocido: '{cmd}'{Colors.RESET}")
            print_help()
            sys.exit(1)

if __name__ == "__main__":
    main()
