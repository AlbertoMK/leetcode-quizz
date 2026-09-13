#!/usr/bin/env python3
"""
Script para descargar problemas de LeetCode con todos sus metadatos,
plantilla Java, casos de prueba y soluciones de la comunidad.
"""

import sys
import os
import json
import re
import datetime
from pathlib import Path
import urllib.request
import urllib.error

from config import Colors, PROBLEMS_DIR, sanitize_slug, set_active_problem, open_in_editor, load_config

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://leetcode.com"
}

def make_graphql_request(query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(LEETCODE_GRAPHQL_URL, data=payload, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "errors" in data and not data.get("data"):
                raise ValueError(f"Error GraphQL: {data['errors']}")
            return data.get("data", {})
    except urllib.error.URLError as e:
        raise RuntimeError(f"Error de red al conectar con LeetCode: {e}")

def resolve_slug_from_id(query_id: str) -> str | None:
    """Resuelve un número de problema al slug de LeetCode."""
    query = """
    query problemsetQuestionList($filters: QuestionListFilterInput) {
      problemsetQuestionList: questionList(categorySlug: "", limit: 10, filters: $filters) {
        questions: data {
          questionFrontendId
          titleSlug
        }
      }
    }
    """
    data = make_graphql_request(query, {"filters": {"searchKeywords": str(query_id)}})
    questions = data.get("problemsetQuestionList", {}).get("questions", [])
    for q in questions:
        if str(q.get("questionFrontendId")) == str(query_id):
            return q.get("titleSlug")
    return None

def fetch_problem_detail(slug: str) -> dict:
    """Descarga los detalles del problema."""
    query = """
    query getQuestionDetail($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionId
        questionFrontendId
        title
        titleSlug
        difficulty
        content
        sampleTestCase
        exampleTestcaseList
        hints
        topicTags {
          name
          slug
        }
        codeSnippets {
          lang
          langSlug
          code
        }
        stats
      }
    }
    """
    data = make_graphql_request(query, {"titleSlug": slug})
    question = data.get("question")
    if not question:
        raise ValueError(f"No se encontró el problema con slug '{slug}' en LeetCode.")
    return question

def fetch_community_solutions(slug: str, limit: int = 5) -> list:
    """Descarga las mejores soluciones de la comunidad con código Java."""
    query = """
    query questionSolutions($filters: QuestionSolutionsFilterInput!) {
      questionSolutions(filters: $filters) {
        totalNum
        solutions {
          id
          title
          post {
            id
            voteCount
            content
            author {
              username
            }
          }
        }
      }
    }
    """
    variables = {
        "filters": {
            "questionSlug": slug,
            "skip": 0,
            "first": limit,
            "orderBy": "most_votes",
            "query": "java"
        }
    }
    try:
        data = make_graphql_request(query, variables)
        raw_solutions = data.get("questionSolutions", {}).get("solutions", [])
        solutions = []
        for item in raw_solutions:
            post = item.get("post", {})
            solutions.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "votes": post.get("voteCount", 0),
                "author": post.get("author", {}).get("username", "Anónimo"),
                "content": post.get("content", "")
            })
        return solutions
    except Exception as e:
        print(f"{Colors.YELLOW}[!] Aviso: No se pudieron descargar las soluciones comunitarias: {e}{Colors.RESET}")
        return []

def clean_html(html_content: str) -> str:
    """Convierte HTML de LeetCode a Markdown / texto legible."""
    if not html_content:
        return ""
    text = html_content
    # Reemplazos de formato básicos
    text = re.sub(r'<sup>(.*?)</sup>', r'^\1', text)
    text = re.sub(r'<sub>(.*?)</sub>', r'_\1', text)
    text = re.sub(r'<code>(.*?)</code>', r'`\1`', text)
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text)
    text = re.sub(r'<p>(.*?)</p>', r'\1\n\n', text, flags=re.DOTALL)
    text = re.sub(r'<ul>(.*?)</ul>', r'\1\n', text, flags=re.DOTALL)
    text = re.sub(r'<li>(.*?)</li>', r'- \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<pre>(.*?)</pre>', r'```\n\1\n```\n', text, flags=re.DOTALL)
    
    # Entidades HTML
    text = text.replace("&nbsp;", " ")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&amp;", "&")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&le;", "<=")
    text = text.replace("&ge;", ">=")
    text = text.replace("&minus;", "-")
    
    # Quitar cualquier otra etiqueta residual
    text = re.sub(r'<[^>]+>', '', text)
    # Normalizar saltos de linea consecutivos
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def generate_solution_header(frontend_id: str, title: str, difficulty: str, tags: list[str], slug: str, desc_text: str) -> str:
    """Genera un bloque de comentarios Javadoc con el enunciado completo dentro de Solution.java."""
    divider = " * " + "=" * 76
    lines = [
        "/**",
        divider,
        f" * {frontend_id}. {title} [{difficulty}]",
        f" * URL: https://leetcode.com/problems/{slug}/",
    ]
    if tags:
        lines.append(f" * Tags: {', '.join(tags)}")
    lines.append(divider)
    lines.append(" *")
    lines.append(" * DESCRIPCION:")
    lines.append(" *")

    for raw_line in desc_text.strip().split("\n"):
        safe_line = raw_line.replace("*/", "* /")
        if safe_line.strip():
            lines.append(f" * {safe_line}")
        else:
            lines.append(" *")

    lines.append(" *")
    lines.append(" * COMANDOS RAPIDOS:")
    lines.append(" *   lc test       -> Ejecutar casos de prueba locales")
    lines.append(" *   lc hint       -> Solicitar una pista oficial (sin spoilers)")
    lines.append(" *   lc ai review  -> Revision de codigo por IA")
    lines.append(" *   lc submit     -> Enviar solucion a LeetCode")
    lines.append(" *   lc open       -> Abrir este archivo en tu editor")
    lines.append(divider)
    lines.append(" */")
    return "\n".join(lines)

def parse_test_cases(raw_examples: list, html_content: str) -> list:
    """Extrae pares (input, expected_output)."""
    cases = []
    # Buscar salidas esperadas considerando etiquetas como <strong>Output:</strong> <code>...</code>
    expected_outputs = re.findall(r'Output:</strong>\s*(?:<code>)?\s*([^<\n\r]+)', html_content or "")
    if not expected_outputs:
        # Fallback para problemas con formato alternativo
        expected_outputs = re.findall(r'Output:\s*([^\n<]+)', html_content or "")
    
    for i, raw_input in enumerate(raw_examples or []):
        exp = expected_outputs[i].strip() if i < len(expected_outputs) else ""
        cases.append({
            "id": i + 1,
            "input": raw_input,
            "expected_output": exp
        })
    return cases

def fetch_and_save_problem(target: str) -> Path:
    """Descarga el problema y lo estructura en su carpeta."""
    slug = sanitize_slug(target)
    
    # Si el target es puramente numérico, buscar por ID
    if slug.isdigit():
        print(f"{Colors.CYAN}[*] Buscando problema por ID #{slug}...{Colors.RESET}")
        resolved = resolve_slug_from_id(slug)
        if resolved:
            slug = resolved
            print(f"{Colors.CYAN}[*] Slug encontrado: '{slug}'{Colors.RESET}")
        else:
            print(f"{Colors.YELLOW}[!] No se pudo resolver por ID directamente, probando slug '{slug}'...{Colors.RESET}")

    print(f"{Colors.CYAN}[*] Descargando detalles de '{slug}' desde LeetCode...{Colors.RESET}")
    q = fetch_problem_detail(slug)
    
    frontend_id = q.get("questionFrontendId", "0")
    title = q.get("title", slug)
    difficulty = q.get("difficulty", "Unknown")
    tags = [t.get("name") for t in q.get("topicTags", [])]
    
    # Extraer starter code en Java
    java_snippet = ""
    for s in q.get("codeSnippets", []):
        if s.get("langSlug") == "java" or s.get("lang") == "Java":
            java_snippet = s.get("code", "")
            break
            
    if not java_snippet:
        java_snippet = "// No starter code found for Java\nclass Solution {\n\n}\n"

    # Descargar soluciones de la comunidad
    print(f"{Colors.CYAN}[*] Descargando mejores soluciones de la comunidad (Java)...{Colors.RESET}")
    solutions = fetch_community_solutions(slug, limit=5)
    
    # Crear carpeta de destino con formato: 0001-two-sum
    folder_name = f"{frontend_id.zfill(4)}-{slug}"
    problem_folder = PROBLEMS_DIR / folder_name
    problem_folder.mkdir(parents=True, exist_ok=True)
    
    # 1. metadata.json
    now = datetime.datetime.now().isoformat()
    existing_meta = {}
    meta_path = problem_folder / "metadata.json"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                existing_meta = json.load(f)
        except Exception:
            pass

    metadata = {
        "id": q.get("questionId"),
        "frontend_id": frontend_id,
        "title": title,
        "slug": slug,
        "difficulty": difficulty,
        "tags": tags,
        "url": f"https://leetcode.com/problems/{slug}/",
        "status": existing_meta.get("status", "NEW"),
        "created_at": existing_meta.get("created_at", now),
        "updated_at": now,
        "best_runtime": existing_meta.get("best_runtime"),
        "best_memory": existing_meta.get("best_memory"),
        "hints_used": existing_meta.get("hints_used", 0),
        "hints_log": existing_meta.get("hints_log", []),
        "official_hints": q.get("hints", []),
        "submissions": existing_meta.get("submissions", [])
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # 2. README.md
    desc_markdown = clean_html(q.get("content", ""))
    hints = q.get("hints", [])
    
    readme_content = [
        f"# {frontend_id}. {title}",
        "",
        f"**Dificultad:** `{difficulty}` | **Tags:** `{', '.join(tags)}`  ",
        f"**LeetCode URL:** [{f'https://leetcode.com/problems/{slug}/'}]({f'https://leetcode.com/problems/{slug}/'})",
        "",
        "---",
        "",
        "## Descripción",
        "",
        desc_markdown,
        ""
    ]
    
    if hints:
        readme_content.append("## Pistas")
        readme_content.append(f"Hay {len(hints)} pistas disponibles para este problema.")
        readme_content.append("Usa 'lc hint' desde tu terminal para desbloquearlas una a una sin spoilers.")
        readme_content.append("")

    with open(problem_folder / "README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(readme_content))

    # 3. Solution.java (no sobreescribir si el usuario ya escribió código)
    solution_file = problem_folder / "Solution.java"
    if not solution_file.exists():
        header_comment = generate_solution_header(frontend_id, title, difficulty, tags, slug, desc_markdown)
        java_header = f"""import java.util.*;
import common.*;

{header_comment}
{java_snippet}
"""
        with open(solution_file, "w", encoding="utf-8") as f:
            f.write(java_header)
        print(f"{Colors.GREEN}[+] Creado Solution.java con plantilla y enunciado integrado.{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}[!] Solution.java ya existe, no se sobrescribio para no perder cambios.{Colors.RESET}")

    # 4. test_cases.json
    cases = parse_test_cases(q.get("exampleTestcaseList", []), q.get("content", ""))
    with open(problem_folder / "test_cases.json", "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2, ensure_ascii=False)

    # 5. solutions.md
    sol_md = [
        f"# Soluciones de la Comunidad - {title}",
        "",
        f"Top {len(solutions)} soluciones más votadas con implementaciones en Java:",
        ""
    ]
    for s in solutions:
        sol_md.append(f"## [{s['votes']} votos] {s['title']} (por @{s['author']})")
        sol_md.append("")
        clean_sol_content = s["content"].replace("\\n", "\n").replace("\\t", "\t")
        sol_md.append(clean_sol_content)
        sol_md.append("\n---\n")

    with open(problem_folder / "solutions.md", "w", encoding="utf-8") as f:
        f.write("\n".join(sol_md))

    # Guardar como problema activo
    set_active_problem(folder_name)

    print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Problema #{frontend_id} descargado con exito en:{Colors.RESET}")
    print(f"  {Colors.BOLD}{problem_folder}{Colors.RESET}")
    print(f"  |-- Solution.java    (tu codigo y enunciado integrado)")
    print(f"  |-- README.md        (enunciado limpio)")
    print(f"  |-- test_cases.json  (casos de prueba)")
    print(f"  |-- solutions.md     (soluciones mas votadas de la comunidad)")
    print(f"  \\-- metadata.json    (estado, tags y metricas)")
    print(f"\n{Colors.CYAN}[*] Problema activo: {folder_name}{Colors.RESET}")

    # Abrir automaticamente en el editor
    cfg = load_config()
    if cfg.get("auto_open", True):
        print(f"{Colors.CYAN}[*] Abriendo Solution.java en tu editor...{Colors.RESET}\n")
        open_in_editor(solution_file)
    else:
        print(f"{Colors.GRAY}    (Puedes abrirlo con 'lc open'){Colors.RESET}\n")

    return problem_folder

def fetch_random_problem(difficulty: str | None = None) -> Path:
    """Busca un problema aleatorio en LeetCode (filtrable por dificultad) y lo descarga."""
    import random
    
    diff_filter = None
    if difficulty:
        diff_lower = difficulty.lower().strip()
        if diff_lower in ["easy", "ez", "e", "facil", "fácil"]:
            diff_filter = "EASY"
        elif diff_lower in ["medium", "med", "m", "medio", "media"]:
            diff_filter = "MEDIUM"
        elif diff_lower in ["hard", "h", "dificil", "difícil"]:
            diff_filter = "HARD"
        else:
            print(f"{Colors.RED}[!] Dificultad inválida: '{difficulty}'. Opciones permitidas: easy, medium, hard (o e, med, h).{Colors.RESET}")
            sys.exit(1)

    print(f"\n{Colors.CYAN}{Colors.BOLD}[*] Buscando un problema aleatorio{' (' + diff_filter + ')' if diff_filter else ''}...{Colors.RESET}")
    
    query = """
    query problemsetQuestionList($limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      problemsetQuestionList: questionList(categorySlug: "", limit: $limit, skip: $skip, filters: $filters) {
        total: totalNum
        questions: data {
          questionFrontendId
          titleSlug
          title
          difficulty
          isPaidOnly
        }
      }
    }
    """
    filters = {}
    if diff_filter:
        filters["difficulty"] = diff_filter

    # Obtener total de problemas disponibles
    data = make_graphql_request(query, {"limit": 1, "skip": 0, "filters": filters})
    total = data.get("problemsetQuestionList", {}).get("total", 0)
    if total == 0:
        raise RuntimeError("No se encontraron problemas con los filtros seleccionados.")

    # Elegir un offset aleatorio y traer candidatos
    batch_size = 35
    rand_skip = random.randint(0, max(0, total - batch_size))
    data2 = make_graphql_request(query, {"limit": batch_size, "skip": rand_skip, "filters": filters})
    questions = data2.get("problemsetQuestionList", {}).get("questions", [])

    # Filtrar problemas gratuitos
    candidates = [q for q in questions if not q.get("isPaidOnly")]
    if not candidates:
        data2 = make_graphql_request(query, {"limit": 50, "skip": 0, "filters": filters})
        candidates = [q for q in data2.get("problemsetQuestionList", {}).get("questions", []) if not q.get("isPaidOnly")]

    # Priorizar problemas que todavía no hayamos descargado
    existing_slugs = set()
    if PROBLEMS_DIR.exists():
        for d in PROBLEMS_DIR.iterdir():
            if d.is_dir():
                parts = d.name.split("-", 1)
                if len(parts) > 1:
                    existing_slugs.add(parts[1].lower())

    new_candidates = [q for q in candidates if q.get("titleSlug").lower() not in existing_slugs]
    chosen = random.choice(new_candidates if new_candidates else candidates)

    slug = chosen.get("titleSlug")
    print(f"{Colors.GREEN}[+] Seleccionado: #{chosen.get('questionFrontendId')} - {chosen.get('title')} [{chosen.get('difficulty')}]{Colors.RESET}")
    
    return fetch_and_save_problem(slug)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"{Colors.RED}Uso: python3 fetch.py <slug_o_id_o_url | random> [dificultad]{Colors.RESET}")
        sys.exit(1)
    if sys.argv[1].lower() == "random":
        diff = sys.argv[2] if len(sys.argv) >= 3 else None
        fetch_random_problem(diff)
    else:
        fetch_and_save_problem(sys.argv[1])
