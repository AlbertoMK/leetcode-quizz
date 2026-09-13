#!/usr/bin/env python3
"""
Ejecutor de pruebas locales en Java para problemas de LeetCode.
Compila la solución, ejecuta los casos de prueba (de test_cases.json o personalizados)
y muestra los resultados con formato visual y métricas de tiempo.
"""

import sys
import os
import json
import re
import time
import math
import shutil
import tempfile
import subprocess
from pathlib import Path

from config import Colors, PROJECT_DIR, COMMON_DIR, resolve_target

def check_java_environment() -> bool:
    """Verifica que javac y java estén disponibles."""
    javac_ok = shutil.which("javac") is not None
    java_ok = shutil.which("java") is not None
    return javac_ok and java_ok

def extract_solution_signature(java_code: str) -> tuple[str, str, list[tuple[str, str]]]:
    """
    Extrae (return_type, method_name, [(param_type, param_name), ...])
    del método principal de class Solution.
    """
    # Limpiar comentarios
    clean_code = re.sub(r'//.*', '', java_code)
    clean_code = re.sub(r'/\*.*?\*/', '', clean_code, flags=re.DOTALL)
    
    # Buscar el método público dentro de Solution
    # Ej: public int[] twoSum(int[] nums, int target)
    pattern = r'public\s+([A-Za-z0-9_<>,\[\]]+)\s+([A-Za-z0-9_]+)\s*\(([^)]*)\)'
    matches = re.findall(pattern, clean_code)
    
    for ret_type, method_name, raw_params in matches:
        if method_name in ["main", "equals", "hashCode", "toString"]:
            continue
        params = []
        if raw_params.strip():
            for p in raw_params.split(','):
                p = p.strip()
                if not p:
                    continue
                parts = p.split()
                if len(parts) >= 2:
                    p_type = " ".join(parts[:-1])
                    p_name = parts[-1]
                    params.append((p_type, p_name))
        return ret_type.strip(), method_name.strip(), params
        
    raise ValueError("No se encontró ningún método público en class Solution.")

def get_parser_expression(p_type: str, raw_var: str) -> str:
    """Genera la expresión Java para parsear el tipo de parámetro."""
    t = p_type.strip().replace(" ", "")
    if t == "int":
        return f"Integer.parseInt({raw_var}.trim())"
    elif t == "long":
        return f"Long.parseLong({raw_var}.trim())"
    elif t == "double":
        return f"Double.parseDouble({raw_var}.trim())"
    elif t == "boolean":
        return f"Boolean.parseBoolean({raw_var}.trim())"
    elif t == "char":
        return f"HarnessHelper.parseChar({raw_var})"
    elif t == "char[]":
        return f"HarnessHelper.parseCharArray({raw_var})"
    elif t == "char[][]":
        return f"HarnessHelper.parseCharMatrix({raw_var})"
    elif t == "String":
        return f"HarnessHelper.parseString({raw_var})"
    elif t == "int[]":
        return f"HarnessHelper.parseIntArray({raw_var})"
    elif t == "int[][]":
        return f"HarnessHelper.parseIntMatrix({raw_var})"
    elif t == "String[]":
        return f"HarnessHelper.parseStringArray({raw_var})"
    elif t == "ListNode":
        return f"HarnessHelper.parseListNode({raw_var})"
    elif t == "TreeNode":
        return f"HarnessHelper.parseTreeNode({raw_var})"
    elif "List<Integer>" in t:
        return f"HarnessHelper.parseListInteger({raw_var})"
    elif "List<String>" in t:
        return f"HarnessHelper.parseListString({raw_var})"
    elif "List<List<Integer>>" in t:
        return f"HarnessHelper.parseListOfListInteger({raw_var})"
    else:
        # Fallback genérico para String
        return f"{raw_var}.trim()"

def generate_harness_java(ret_type: str, method_name: str, params: list[tuple[str, str]]) -> str:
    """Genera el código Java del Driver/Harness para probar Solution."""
    param_parsers = []
    for i, (p_type, p_name) in enumerate(params):
        expr = get_parser_expression(p_type, f"lines.get({i})")
        param_parsers.append(f"{p_type} arg{i} = {expr};")
    
    args_call = ", ".join(f"arg{i}" for i in range(len(params)))

    code = f"""
import java.io.*;
import java.util.*;
import common.*;

class HarnessHelper {{
    public static String parseString(String s) {{
        s = s.trim();
        if (s.startsWith("\\\"") && s.endsWith("\\\"") && s.length() >= 2) {{
            return s.substring(1, s.length() - 1);
        }}
        return s;
    }}

    public static char parseChar(String s) {{
        s = s.trim();
        if (s.startsWith("\\\"") && s.endsWith("\\\"") && s.length() >= 3) return s.charAt(1);
        if (s.startsWith("'") && s.endsWith("'") && s.length() >= 3) return s.charAt(1);
        return s.isEmpty() ? ' ' : s.charAt(0);
    }}

    public static char[] parseCharArray(String s) {{
        String[] parts = parseStringArray(s);
        char[] res = new char[parts.length];
        for (int i = 0; i < parts.length; i++) {{
            res[i] = parts[i].isEmpty() ? ' ' : parts[i].charAt(0);
        }}
        return res;
    }}

    public static char[][] parseCharMatrix(String s) {{
        s = s.trim();
        if (s.startsWith("[")) s = s.substring(1);
        if (s.endsWith("]")) s = s.substring(0, s.length() - 1);
        s = s.trim();
        if (s.isEmpty()) return new char[0][0];
        List<char[]> rows = new ArrayList<>();
        MatcherHelper matcher = new MatcherHelper(s);
        for (String rowStr : matcher.splitArrays()) {{
            rows.add(parseCharArray(rowStr));
        }}
        return rows.toArray(new char[0][]);
    }}

    public static int[] parseIntArray(String s) {{
        s = s.trim();
        if (s.startsWith("[")) s = s.substring(1);
        if (s.endsWith("]")) s = s.substring(0, s.length() - 1);
        s = s.trim();
        if (s.isEmpty()) return new int[0];
        String[] parts = s.split(",");
        int[] res = new int[parts.length];
        for (int i = 0; i < parts.length; i++) {{
            res[i] = Integer.parseInt(parts[i].trim());
        }}
        return res;
    }}

    public static int[][] parseIntMatrix(String s) {{
        s = s.trim();
        if (s.startsWith("[")) s = s.substring(1);
        if (s.endsWith("]")) s = s.substring(0, s.length() - 1);
        s = s.trim();
        if (s.isEmpty()) return new int[0][0];
        List<int[]> rows = new ArrayList<>();
        MatcherHelper matcher = new MatcherHelper(s);
        for (String rowStr : matcher.splitArrays()) {{
            rows.add(parseIntArray(rowStr));
        }}
        return rows.toArray(new int[0][]);
    }}

    public static String[] parseStringArray(String s) {{
        s = s.trim();
        if (s.startsWith("[")) s = s.substring(1);
        if (s.endsWith("]")) s = s.substring(0, s.length() - 1);
        s = s.trim();
        if (s.isEmpty()) return new String[0];
        String[] parts = s.split(",");
        String[] res = new String[parts.length];
        for (int i = 0; i < parts.length; i++) {{
            res[i] = parseString(parts[i].trim());
        }}
        return res;
    }}

    public static ListNode parseListNode(String s) {{
        int[] arr = parseIntArray(s);
        if (arr.length == 0) return null;
        ListNode dummy = new ListNode(0);
        ListNode curr = dummy;
        for (int val : arr) {{
            curr.next = new ListNode(val);
            curr = curr.next;
        }}
        return dummy.next;
    }}

    public static TreeNode parseTreeNode(String s) {{
        s = s.trim();
        if (s.startsWith("[")) s = s.substring(1);
        if (s.endsWith("]")) s = s.substring(0, s.length() - 1);
        s = s.trim();
        if (s.isEmpty()) return null;
        String[] parts = s.split(",");
        if (parts.length == 0 || parts[0].trim().equals("null") || parts[0].trim().isEmpty()) return null;
        
        TreeNode root = new TreeNode(Integer.parseInt(parts[0].trim()));
        Queue<TreeNode> q = new LinkedList<>();
        q.add(root);
        int i = 1;
        while (!q.isEmpty() && i < parts.length) {{
            TreeNode curr = q.poll();
            if (curr != null) {{
                if (i < parts.length && !parts[i].trim().equals("null") && !parts[i].trim().isEmpty()) {{
                    curr.left = new TreeNode(Integer.parseInt(parts[i].trim()));
                    q.add(curr.left);
                }}
                i++;
                if (i < parts.length && !parts[i].trim().equals("null") && !parts[i].trim().isEmpty()) {{
                    curr.right = new TreeNode(Integer.parseInt(parts[i].trim()));
                    q.add(curr.right);
                }}
                i++;
            }}
        }}
        return root;
    }}

    public static List<Integer> parseListInteger(String s) {{
        int[] arr = parseIntArray(s);
        List<Integer> list = new ArrayList<>();
        for (int x : arr) list.add(x);
        return list;
    }}

    public static List<String> parseListString(String s) {{
        return Arrays.asList(parseStringArray(s));
    }}

    public static List<List<Integer>> parseListOfListInteger(String s) {{
        int[][] m = parseIntMatrix(s);
        List<List<Integer>> res = new ArrayList<>();
        for (int[] row : m) {{
            List<Integer> r = new ArrayList<>();
            for (int x : row) r.add(x);
            res.add(r);
        }}
        return res;
    }}

    public static String formatOutput(Object o) {{
        if (o == null) return "null";
        if (o instanceof int[]) {{
            int[] arr = (int[]) o;
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < arr.length; i++) {{
                sb.append(arr[i]);
                if (i < arr.length - 1) sb.append(",");
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (o instanceof int[][]) {{
            int[][] m = (int[][]) o;
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < m.length; i++) {{
                sb.append(formatOutput(m[i]));
                if (i < m.length - 1) sb.append(",");
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (o instanceof String[]) {{
            String[] arr = (String[]) o;
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < arr.length; i++) {{
                sb.append("\\\"").append(arr[i]).append("\\\"");
                if (i < arr.length - 1) sb.append(",");
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (o instanceof List<?>) {{
            List<?> list = (List<?>) o;
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < list.size(); i++) {{
                sb.append(formatOutput(list.get(i)));
                if (i < list.size() - 1) sb.append(",");
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (o instanceof char[]) {{
            char[] arr = (char[]) o;
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < arr.length; i++) {{
                sb.append("\\\"").append(arr[i]).append("\\\"");
                if (i < arr.length - 1) sb.append(",");
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (o instanceof char[][]) {{
            char[][] m = (char[][]) o;
            StringBuilder sb = new StringBuilder("[");
            for (int i = 0; i < m.length; i++) {{
                sb.append(formatOutput(m[i]));
                if (i < m.length - 1) sb.append(",");
            }}
            sb.append("]");
            return sb.toString();
        }}
        if (o instanceof boolean[]) return Arrays.toString((boolean[]) o).replace(" ", "");
        if (o instanceof long[]) return Arrays.toString((long[]) o).replace(" ", "");
        if (o instanceof double[]) return Arrays.toString((double[]) o).replace(" ", "");
        if (o instanceof float[]) return Arrays.toString((float[]) o).replace(" ", "");
        if (o instanceof String) return (String) o;
        return String.valueOf(o);
    }}
}}

class MatcherHelper {{
    private String s;
    public MatcherHelper(String s) {{ this.s = s; }}
    public List<String> splitArrays() {{
        List<String> list = new ArrayList<>();
        int depth = 0;
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {{
            if (c == '[') depth++;
            if (depth > 0) sb.append(c);
            if (c == ']') {{
                depth--;
                if (depth == 0) {{
                    list.add(sb.toString().trim());
                    sb.setLength(0);
                }}
            }}
        }}
        return list;
    }}
}}

public class TestHarness {{
    public static void main(String[] args) throws Exception {{
        BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
        List<String> lines = new ArrayList<>();
        String line;
        while ((line = br.readLine()) != null) {{
            lines.add(line);
        }}

        Solution solution = new Solution();
        {chr(10).join("        " + p for p in param_parsers)}

        long startTime = System.nanoTime();
        {f"solution.{method_name}({args_call});" + chr(10) + "        Object result = arg0;" if ret_type.strip() == "void" else f"{ret_type} result = solution.{method_name}({args_call});"}
        long endTime = System.nanoTime();

        double elapsedMs = (endTime - startTime) / 1_000_000.0;
        System.out.println("---OUTPUT---");
        System.out.println(HarnessHelper.formatOutput(result));
        System.out.println("---TIME---");
        System.out.printf(Locale.US, "%.3f\\n", elapsedMs);
    }}
}}
"""
    return code

def normalize_result(res: str) -> str:
    """Normaliza espacios y comas para comparar arrays y listas justamente."""
    if not res:
        return ""
    # Quitar todos los espacios en blanco
    s = re.sub(r'\s+', '', res.strip())
    # Normalizar booleanos en minúsculas
    if s.lower() in ["true", "false"]:
        return s.lower()
    return s

def clean_val_str(s: str) -> str:
    """Limpia comillas y espacios redundantes alrededor de un valor textual."""
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        if len(s) >= 2:
            s = s[1:-1]
    return s.strip()

def deep_compare(act, exp, tol: float = 1e-5) -> bool:
    """Compara recursivamente dos valores o estructuras con tolerancia para floats."""
    if isinstance(act, (int, float)) and isinstance(exp, (int, float)):
        return math.isclose(float(act), float(exp), rel_tol=tol, abs_tol=tol)

    if isinstance(act, list) and isinstance(exp, list):
        if len(act) != len(exp):
            return False
        return all(deep_compare(a, b, tol) for a, b in zip(act, exp))

    if isinstance(act, dict) and isinstance(exp, dict):
        if set(act.keys()) != set(exp.keys()):
            return False
        return all(deep_compare(act[k], exp[k], tol) for k in act)

    s_act = clean_val_str(str(act))
    s_exp = clean_val_str(str(exp))

    if s_act == s_exp:
        return True

    # Intento de parsear ambos como float si eran cadenas que representan números
    try:
        fa = float(s_act)
        fe = float(s_exp)
        return math.isclose(fa, fe, rel_tol=tol, abs_tol=tol)
    except (ValueError, TypeError):
        pass

    if s_act.lower() in ["true", "false"] and s_exp.lower() in ["true", "false"]:
        return s_act.lower() == s_exp.lower()

    return s_act == s_exp

def parse_comparable_value(s: str):
    """Parsea una cadena a estructura comparable (JSON, float, lista o string limpio)."""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return ""

    # 1. Intentar JSON estándar (números, booleanos, listas, null)
    try:
        return json.loads(s)
    except Exception:
        pass

    # 2. Formato de lista con comillas simples o sin comillas
    if s.startswith("[") and s.endswith("]"):
        try:
            return json.loads(s.replace("'", '"'))
        except Exception:
            pass
        inner = s[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip() for p in inner.split(",")]
        parsed_items = []
        for p in parts:
            try:
                parsed_items.append(json.loads(p))
            except Exception:
                parsed_items.append(clean_val_str(p))
        return parsed_items

    # 3. Número flotante suelto
    try:
        return float(s)
    except ValueError:
        pass

    return clean_val_str(s)

def compare_results(actual: str, expected: str, tol: float = 1e-5) -> bool:
    """Evalúa si la salida obtenida coincide con la esperada con tolerancia flotante."""
    if actual == expected:
        return True

    norm_a = normalize_result(actual)
    norm_e = normalize_result(expected)
    if norm_a == norm_e:
        return True

    parsed_a = parse_comparable_value(actual)
    parsed_e = parse_comparable_value(expected)

    return deep_compare(parsed_a, parsed_e, tol=tol)

def run_local_tests(target: str | None = None, custom_input: str | None = None) -> bool:
    """Ejecuta las pruebas en local contra Solution.java."""
    folder, problem_name = resolve_target(target)
    if not folder:
        print(f"{Colors.RED}[!] Error: No hay ningun problema activo ni se encontro '{target}'.{Colors.RESET}")
        print(f"    Descargalo con 'lc fetch <target>' o especifica uno: 'lc test <slug_o_id>'.")
        return False

    solution_file = folder / "Solution.java"
    if not solution_file.exists():
        print(f"{Colors.RED}[!] Error: No existe {solution_file}{Colors.RESET}")
        return False

    if not check_java_environment():
        print(f"{Colors.RED}[!] Error: 'javac' o 'java' no están disponibles en el PATH.{Colors.RESET}")
        print(f"    Instálalos o actívalos con: mise use -g java@openjdk-21")
        return False

    with open(solution_file, "r", encoding="utf-8") as f:
        code_content = f.read()

    try:
        ret_type, method_name, params = extract_solution_signature(code_content)
    except Exception as e:
        print(f"{Colors.RED}[!] Error al analizar Solution.java: {e}{Colors.RESET}")
        return False

    # Preparar casos de prueba
    if custom_input:
        cases = [{"id": "Custom", "input": custom_input, "expected_output": ""}]
    else:
        test_file = folder / "test_cases.json"
        if not test_file.exists():
            print(f"{Colors.YELLOW}[!] test_cases.json no existe. Usa -c '<input>' para probar.{Colors.RESET}")
            return False
        with open(test_file, "r", encoding="utf-8") as f:
            cases = json.load(f)

    if not cases:
        print(f"{Colors.YELLOW}[!] No hay casos de prueba para ejecutar.{Colors.RESET}")
        return False

    # Compilar en directorio temporal
    with tempfile.TemporaryDirectory() as build_dir:
        build_path = Path(build_dir)
        
        # Copiar dependencias de common/
        common_dest = build_path / "common"
        common_dest.mkdir(parents=True, exist_ok=True)
        for cf in COMMON_DIR.glob("*.java"):
            shutil.copy(cf, common_dest)

        # Copiar Solution.java
        shutil.copy(solution_file, build_path / "Solution.java")

        # Generar TestHarness.java
        harness_code = generate_harness_java(ret_type, method_name, params)
        with open(build_path / "TestHarness.java", "w", encoding="utf-8") as f:
            f.write(harness_code)

        print(f"{Colors.CYAN}[*] Compilando solución Java...{Colors.RESET}")
        compile_cmd = ["javac", "-cp", str(build_path), "common/ListNode.java", "common/TreeNode.java", "Solution.java", "TestHarness.java"]
        
        comp = subprocess.run(compile_cmd, cwd=build_path, capture_output=True, text=True)
        if comp.returncode != 0:
            print(f"\n{Colors.BG_RED}{Colors.WHITE}{Colors.BOLD} [!] ERROR DE COMPILACION {Colors.RESET}\n")
            print(Colors.RED + comp.stderr + Colors.RESET)
            # Actualizar metadata con intento fallido
            update_status(folder, "ATTEMPTED")
            return False

        print(f"{Colors.GREEN}[+] Compilacion exitosa.{Colors.RESET}\n")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD} EJECUTANDO CASOS DE PRUEBA: {folder.name} ({len(cases)} tests){Colors.RESET}")
        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

        all_passed = True
        total_time_ms = 0.0

        for case in cases:
            cid = case.get("id")
            raw_in = case.get("input", "")
            exp_out = case.get("expected_output", "")

            # Ejecutar TestHarness pasando input por stdin
            run_cmd = ["java", "-cp", str(build_path), "TestHarness"]
            try:
                proc = subprocess.run(run_cmd, input=raw_in, text=True, capture_output=True, timeout=5)
            except subprocess.TimeoutExpired:
                print(f"  {Colors.RED}[FAIL] Caso {cid}: TIME LIMIT EXCEEDED (> 5000 ms){Colors.RESET}")
                print(f"     Entrada: {raw_in.replace(chr(10), ' | ')}")
                all_passed = False
                continue

            if proc.returncode != 0:
                print(f"  {Colors.RED}[FAIL] Caso {cid}: RUNTIME ERROR{Colors.RESET}")
                print(f"     Entrada: {raw_in.replace(chr(10), ' | ')}")
                print(f"     Error: {proc.stderr.strip()[:300]}")
                all_passed = False
                continue

            # Parsear salida
            stdout = proc.stdout
            actual_out = ""
            elapsed = 0.0

            if "---OUTPUT---" in stdout:
                parts = stdout.split("---OUTPUT---")[1]
                if "---TIME---" in parts:
                    out_part, time_part = parts.split("---TIME---")
                    actual_out = out_part.strip()
                    try:
                        elapsed = float(time_part.strip())
                    except ValueError:
                        pass
                else:
                    actual_out = parts.strip()

            total_time_ms += elapsed
            norm_actual = normalize_result(actual_out)
            norm_expected = normalize_result(exp_out)

            # Si no hay expected_output (ej: caso custom), solo mostramos la salida
            if not exp_out:
                print(f"  {Colors.CYAN}[INFO] Caso {cid} (Custom): EJECUTADO ({elapsed:.2f} ms){Colors.RESET}")
                print(f"     Entrada: {raw_in.replace(chr(10), ' | ')}")
                print(f"     Salida : {Colors.BOLD}{actual_out}{Colors.RESET}\n")
                continue

            if compare_results(actual_out, exp_out):
                print(f"  {Colors.GREEN}[PASS] Caso {cid}: PASSED{Colors.RESET} {Colors.GRAY}({elapsed:.2f} ms){Colors.RESET}")
                print(f"     Entrada:  {raw_in.replace(chr(10), ' | ')}")
                print(f"     Salida:   {Colors.GREEN}{actual_out}{Colors.RESET}\n")
            else:
                print(f"  {Colors.RED}[FAIL] Caso {cid}: FAILED{Colors.RESET} {Colors.GRAY}({elapsed:.2f} ms){Colors.RESET}")
                print(f"     Entrada:  {raw_in.replace(chr(10), ' | ')}")
                print(f"     Obtenido: {Colors.RED}{actual_out}{Colors.RESET}")
                print(f"     Esperado: {Colors.GREEN}{exp_out}{Colors.RESET}\n")
                all_passed = False

        print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
        if all_passed and not custom_input:
            print(f"{Colors.GREEN}{Colors.BOLD} [OK] TODOS LOS CASOS DE PRUEBA LOCALES PASARON ({total_time_ms:.2f} ms){Colors.RESET}")
            print(f"{Colors.CYAN}    Listo para enviar a LeetCode: lc submit{Colors.RESET}\n")
        elif not all_passed:
            print(f"{Colors.RED}{Colors.BOLD} [!] Algunos tests fallaron. Revisa tu solucion antes de enviar.{Colors.RESET}\n")
            update_status(folder, "ATTEMPTED")

        return all_passed

def update_status(folder: Path, new_status: str):
    """Actualiza el estado en metadata.json si es necesario."""
    meta_path = folder / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("status") != "SOLVED":
                meta["status"] = new_status
                meta["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"{Colors.RED}Uso: python3 test_runner.py <slug_o_id> [-c \"custom_input\"]{Colors.RESET}")
        sys.exit(1)

    target = sys.argv[1]
    custom = None
    if len(sys.argv) >= 4 and sys.argv[2] in ["-c", "--custom"]:
        custom = sys.argv[3]

    run_local_tests(target, custom)
