#!/usr/bin/env python3
"""
Módulo para subir soluciones a LeetCode de forma interactiva,
esperar la evaluación y gestionar todos los veredictos posibles.
"""

import sys
import os
import json
import time
import re
import urllib.request
import urllib.error
from pathlib import Path

from config import Colors, PROJECT_DIR, resolve_target, get_credentials, save_config, load_config

def setup_credentials_interactive():
    """Guía interactiva para configurar las credenciales de LeetCode."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}=== CONFIGURACIÓN DE CREDENCIALES DE LEETCODE ==={Colors.RESET}")
    print("Para subir soluciones y ejecutar la batería completa de tests en los servidores")
    print("de LeetCode, necesitas tu cookie de sesión:\n")
    print(" 1. Inicia sesión en https://leetcode.com con tu navegador.")
    print(" 2. Pulsa F12 (Herramientas de Desarrollador) -> pestaña 'Application' o 'Almacenamiento'.")
    print(" 3. En el panel izquierdo, despliega 'Cookies' -> https://leetcode.com")
    print(" 4. Copia los valores de 'LEETCODE_SESSION' y 'csrftoken'.\n")

    session = input(f"{Colors.BOLD}Introduce LEETCODE_SESSION: {Colors.RESET}").strip()
    csrf = input(f"{Colors.BOLD}Introduce csrftoken: {Colors.RESET}").strip()

    if not session or not csrf:
        print(f"{Colors.RED}[!] Ambos valores son obligatorios para autenticarse.{Colors.RESET}")
        return None, None

    cfg = load_config()
    cfg["LEETCODE_SESSION"] = session
    cfg["LEETCODE_CSRF_TOKEN"] = csrf
    save_config(cfg)
    print(f"{Colors.GREEN}[+] Credenciales guardadas en config.json.{Colors.RESET}\n")
    return session, csrf

def clean_code_for_submission(code: str) -> str:
    """Elimina imports locales como 'import common.*;' que LeetCode no reconoce."""
    lines = []
    for line in code.splitlines():
        if re.match(r'^\s*import\s+common\..*', line):
            continue
        lines.append(line)
    return "\n".join(lines)

def submit_solution(target: str | None = None, interactive: bool = True) -> bool:
    """Sube Solution.java a LeetCode y procesa el resultado."""
    folder, problem_name = resolve_target(target)
    if not folder:
        print(f"{Colors.RED}[!] No hay ningun problema activo ni se encontro la carpeta para '{target}'.{Colors.RESET}")
        return False

    solution_file = folder / "Solution.java"
    meta_file = folder / "metadata.json"

    if not solution_file.exists() or not meta_file.exists():
        print(f"{Colors.RED}[!] Falta Solution.java o metadata.json en {folder}{Colors.RESET}")
        return False

    with open(meta_file, "r", encoding="utf-8") as f:
        meta = json.load(f)

    with open(solution_file, "r", encoding="utf-8") as f:
        raw_code = f.read()

    code_to_submit = clean_code_for_submission(raw_code)
    question_id = meta.get("id")
    slug = meta.get("slug")
    title = meta.get("title", slug)

    session, csrf = get_credentials()
    if not session or not csrf:
        if interactive:
            session, csrf = setup_credentials_interactive()
            if not session or not csrf:
                return False
        else:
            print(f"{Colors.RED}[!] Credenciales no configuradas. Ejecuta: lc login{Colors.RESET}")
            return False

    submit_url = f"https://leetcode.com/problems/{slug}/submit/"
    headers = {
        "Content-Type": "application/json",
        "x-csrftoken": csrf,
        "Cookie": f"LEETCODE_SESSION={session}; csrftoken={csrf}",
        "Origin": "https://leetcode.com",
        "Referer": f"https://leetcode.com/problems/{slug}/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    payload = json.dumps({
        "lang": "java",
        "question_id": str(question_id),
        "typed_code": code_to_submit
    }).encode("utf-8")

    print(f"\n{Colors.CYAN}[*] Enviando solución de '{title}' a LeetCode...{Colors.RESET}")
    req = urllib.request.Request(submit_url, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            submission_id = data.get("submission_id")
            if not submission_id:
                print(f"{Colors.RED}[!] Respuesta inesperada de LeetCode: {data}{Colors.RESET}")
                return False
    except urllib.error.HTTPError as e:
        if e.code in [401, 403]:
            print(f"{Colors.RED}[!] Error 403/401: Sesión de LeetCode inválida o expirada.{Colors.RESET}")
            print(f"    Vuelve a configurar tus cookies con: lc login")
        else:
            print(f"{Colors.RED}[!] Error HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}{Colors.RESET}")
        return False
    except Exception as e:
        print(f"{Colors.RED}[!] Error al conectar con LeetCode: {e}{Colors.RESET}")
        return False

    print(f"{Colors.GREEN}[+] Envío aceptado por LeetCode (ID de envío: {submission_id}).{Colors.RESET}")
    print(f"{Colors.CYAN}[*] Esperando veredicto de la batería de pruebas...{Colors.RESET}\n")

    # Polling interactivo a /submissions/detail/{id}/check/
    check_url = f"https://leetcode.com/submissions/detail/{submission_id}/check/"
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    start_time = time.time()
    max_wait = 45  # 45 segundos de timeout

    result_data = None
    while time.time() - start_time < max_wait:
        spin = spinner[idx % len(spinner)]
        idx += 1
        sys.stdout.write(f"\r  {Colors.YELLOW}{spin}{Colors.RESET} Evaluando casos de prueba... ({int(time.time() - start_time)}s)")
        sys.stdout.flush()
        
        check_req = urllib.request.Request(check_url, headers=headers)
        try:
            with urllib.request.urlopen(check_req, timeout=10) as c_resp:
                res = json.loads(c_resp.read().decode("utf-8"))
                state = res.get("state")
                if state == "SUCCESS":
                    result_data = res
                    break
        except Exception:
            pass

        time.sleep(1.2)

    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()

    if not result_data:
        print(f"{Colors.YELLOW}[!] Tiempo de espera agotado. Puedes revisar tu envío manualmente en:{Colors.RESET}")
        print(f"    https://leetcode.com/submissions/detail/{submission_id}/")
        return False

    return handle_submission_result(folder, meta, result_data, submission_id)

def handle_submission_result(folder: Path, meta: dict, data: dict, submission_id: int) -> bool:
    """Procesa e imprime todos los posibles estados de retorno de LeetCode."""
    status_msg = data.get("status_msg", "Unknown")
    total_correct = data.get("total_correct", 0)
    total_testcases = data.get("total_testcases", 0)
    meta_path = folder / "metadata.json"

    submission_record = {
        "submission_id": submission_id,
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": status_msg,
        "total_correct": total_correct,
        "total_testcases": total_testcases
    }

    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

    if status_msg == "Accepted":
        runtime = data.get("status_runtime", "N/A")
        runtime_perc = data.get("runtime_percentile")
        memory = data.get("status_memory", "N/A")
        memory_perc = data.get("memory_percentile")

        print(f"{Colors.BG_GREEN}{Colors.WHITE}{Colors.BOLD} [ACCEPTED] SOLUCION CORRECTA {Colors.RESET}\n")
        print(f"  {Colors.GREEN}[+] Casos aprobados:{Colors.RESET} {total_correct} / {total_testcases}")
        if runtime_perc:
            print(f"  {Colors.GREEN}Tiempo de ejecucion:{Colors.RESET} {runtime} (Mejor que el {runtime_perc:.1f}% en Java)")
        else:
            print(f"  {Colors.GREEN}Tiempo de ejecucion:{Colors.RESET} {runtime}")
            
        if memory_perc:
            print(f"  {Colors.GREEN}Uso de memoria:{Colors.RESET}    {memory} (Mejor que el {memory_perc:.1f}% en Java)")
        else:
            print(f"  {Colors.GREEN}Uso de memoria:{Colors.RESET}    {memory}")

        meta["status"] = "SOLVED"
        meta["best_runtime"] = runtime
        meta["best_memory"] = memory
        submission_record["runtime"] = runtime
        submission_record["runtime_percentile"] = runtime_perc
        submission_record["memory"] = memory
        submission_record["memory_percentile"] = memory_perc

    elif status_msg == "Wrong Answer":
        print(f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} [WRONG ANSWER] {Colors.RESET}\n")
        print(f"  {Colors.RED}Progreso:{Colors.RESET} {total_correct} / {total_testcases} casos pasados")
        
        last_input = data.get("input_formatted") or data.get("last_testcase", "")
        code_out = data.get("code_output", "")
        expected_out = data.get("expected_output", "")
        std_out = data.get("std_output", "")

        print(f"  {Colors.BOLD}Entrada fallida:{Colors.RESET}")
        print(f"    {last_input.replace(chr(10), ' | ')}")
        print(f"  {Colors.RED}Tu salida:{Colors.RESET}       {code_out}")
        print(f"  {Colors.GREEN}Salida esperada:{Colors.RESET} {expected_out}")
        if std_out:
            print(f"  {Colors.GRAY}Salida stdout:{Colors.RESET}   {std_out.strip()}")

        meta["status"] = "ATTEMPTED"
        prompt_add_failing_test(folder, last_input, expected_out)

    elif status_msg == "Time Limit Exceeded":
        print(f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} [TIME LIMIT EXCEEDED] {Colors.RESET}\n")
        print(f"  {Colors.RED}Progreso:{Colors.RESET} {total_correct} / {total_testcases} casos pasados")
        last_input = data.get("last_testcase", "")
        if last_input:
            truncated = last_input[:200] + ("..." if len(last_input) > 200 else "")
            print(f"  {Colors.BOLD}Entrada que causo el timeout:{Colors.RESET}")
            print(f"    {truncated}")
        print(f"\n  {Colors.YELLOW}Sugerencia: Revisa la complejidad Big-O de tu algoritmo.{Colors.RESET}")
        meta["status"] = "ATTEMPTED"

    elif status_msg == "Compile Error":
        print(f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} [ERROR DE COMPILACION EN LEETCODE] {Colors.RESET}\n")
        print(Colors.RED + data.get("full_compile_error", "Error desconocido") + Colors.RESET)
        meta["status"] = "ATTEMPTED"

    elif status_msg == "Runtime Error":
        print(f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} [ERROR DE EJECUCION / RUNTIME ERROR] {Colors.RESET}\n")
        print(f"  {Colors.RED}Progreso:{Colors.RESET} {total_correct} / {total_testcases} casos pasados")
        print(Colors.RED + data.get("full_runtime_error", "Excepcion no especificada") + Colors.RESET)
        last_input = data.get("last_testcase", "")
        if last_input:
            print(f"  {Colors.BOLD}En el caso:{Colors.RESET} {last_input.replace(chr(10), ' | ')}")
        meta["status"] = "ATTEMPTED"

    elif status_msg == "Memory Limit Exceeded":
        print(f"{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} [MEMORY LIMIT EXCEEDED] {Colors.RESET}\n")
        print(f"  {Colors.RED}Progreso:{Colors.RESET} {total_correct} / {total_testcases} casos pasados")
        meta["status"] = "ATTEMPTED"

    else:
        print(f"{Colors.YELLOW}[!] Veredicto: {status_msg}{Colors.RESET}")
        meta["status"] = "ATTEMPTED"

    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

    # Guardar en historial de metadata.json
    submissions = meta.get("submissions", [])
    submissions.append(submission_record)
    meta["submissions"] = submissions
    meta["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return status_msg == "Accepted"

def prompt_add_failing_test(folder: Path, failing_input: str, expected_output: str):
    """Ofrece guardar el caso fallido en test_cases.json para depurarlo en local."""
    if not failing_input:
        return
    test_file = folder / "test_cases.json"
    if not test_file.exists():
        return
    try:
        with open(test_file, "r", encoding="utf-8") as f:
            cases = json.load(f)
        # Verificar si ya existe
        for c in cases:
            if c.get("input") == failing_input:
                return
        print(f"\n{Colors.CYAN}[?] ¿Quieres añadir este caso fallido a tus 'test_cases.json' locales? (s/n): {Colors.RESET}", end="")
        choice = input().strip().lower()
        if choice in ["s", "si", "y", "yes"]:
            cases.append({
                "id": len(cases) + 1,
                "input": failing_input,
                "expected_output": expected_output
            })
            with open(test_file, "w", encoding="utf-8") as f:
                json.dump(cases, f, indent=2, ensure_ascii=False)
            print(f"{Colors.GREEN}[+] Caso añadido a test_cases.json. Puedes probarlo con: lc test{Colors.RESET}")
    except Exception:
        pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"{Colors.RED}Uso: python3 submit.py <slug_o_id>{Colors.RESET}")
        sys.exit(1)
    submit_solution(sys.argv[1])
