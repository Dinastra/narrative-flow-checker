import json
import sys
import re


def add_issue(issues, level, code, message, path):
    """Adiciona um problema encontrado na lista."""
    issues.append({
        "level": level,   # ERROR | WARNING | INFO
        "code": code,
        "message": message,
        "path": path
    })


def load_json_file(file_path):
    """Abre e lê o JSON."""
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def dfs(start_node, edges):
    """
    DFS = busca em profundidade.
    Serve para descobrir quais nós são alcançáveis a partir do start.
    """
    visited = set()
    stack = [start_node]

    while stack:
        current = stack.pop()

        if current in visited:
            continue

        visited.add(current)

        for neighbor in edges.get(current, []):
            if neighbor not in visited:
                stack.append(neighbor)

    return visited


def validate_dialogue(data):
    issues = []

    # 1) Validar estrutura básica do JSON
    if not isinstance(data, dict):
        add_issue(issues, "ERROR", "ROOT_TYPE", "O JSON raiz precisa ser um objeto.", "$")
        return issues

    start = data.get("start")
    nodes = data.get("nodes")
    flags = data.get("flags", [])

    if not isinstance(start, str) or not start.strip():
        add_issue(issues, "ERROR", "MISSING_START", "Campo 'start' ausente ou inválido.", "$.start")

    if not isinstance(nodes, dict) or len(nodes) == 0:
        add_issue(issues, "ERROR", "NODES_INVALID", "Campo 'nodes' ausente, vazio ou inválido.", "$.nodes")
        return issues

    if not isinstance(flags, list):
        add_issue(issues, "ERROR", "FLAGS_TYPE", "Campo 'flags' deve ser uma lista.", "$.flags")
        flags = []

    declared_flags = set()
    for i, flag in enumerate(flags):
        if isinstance(flag, str) and flag.strip():
            declared_flags.add(flag.strip())
        else:
            add_issue(issues, "ERROR", "FLAG_INVALID", "Flag inválida em $.flags", f"$.flags[{i}]")

    # 2) Verificar se start existe em nodes
    if isinstance(start, str) and start not in nodes:
        add_issue(issues, "ERROR", "START_NOT_FOUND", f"O nó inicial '{start}' não existe.", "$.start")

    # 3) Preparar grafo (conexões entre nós)
    edges = {}
    set_flags_used = set()
    requires_flags_used = set()

    for node_id in nodes:
        edges[node_id] = []

    # 4) Validar cada nó
    for node_id, node_data in nodes.items():
        path = f"$.nodes.{node_id}"

        if not isinstance(node_data, dict):
            add_issue(issues, "ERROR", "NODE_TYPE", "Cada nó precisa ser um objeto.", path)
            continue

        # --- next ---
        next_node = node_data.get("next")
        if next_node is not None:
            if not isinstance(next_node, str):
                add_issue(issues, "ERROR", "NEXT_TYPE", "'next' deve ser string.", f"{path}.next")
            else:
                edges[node_id].append(next_node)
                if next_node not in nodes:
                    add_issue(
                        issues,
                        "ERROR",
                        "TARGET_NOT_FOUND",
                        f"'next' aponta para nó inexistente: '{next_node}'.",
                        f"{path}.next"
                    )

        # --- choices ---
        choices = node_data.get("choices")
        if choices is not None:
            if not isinstance(choices, list):
                add_issue(issues, "ERROR", "CHOICES_TYPE", "'choices' deve ser lista.", f"{path}.choices")
            else:
                for i, choice in enumerate(choices):
                    choice_path = f"{path}.choices[{i}]"

                    if not isinstance(choice, dict):
                        add_issue(issues, "ERROR", "CHOICE_TYPE", "Cada choice deve ser objeto.", choice_path)
                        continue

                    # Texto da escolha
                    if not isinstance(choice.get("text"), str):
                        add_issue(issues, "ERROR", "CHOICE_TEXT", "Choice sem 'text' válido.", f"{choice_path}.text")

                    # Destino da escolha
                    choice_next = choice.get("next")
                    if not isinstance(choice_next, str):
                        add_issue(issues, "ERROR", "CHOICE_NEXT", "Choice sem 'next' válido.", f"{choice_path}.next")
                    else:
                        edges[node_id].append(choice_next)
                        if choice_next not in nodes:
                            add_issue(
                                issues,
                                "ERROR",
                                "TARGET_NOT_FOUND",
                                f"Choice aponta para nó inexistente: '{choice_next}'.",
                                f"{choice_path}.next"
                            )

                    # Flags requeridas
                    requires = choice.get("requires", [])
                    if not isinstance(requires, list):
                        add_issue(issues, "ERROR", "REQUIRES_TYPE", "'requires' deve ser lista.", f"{choice_path}.requires")
                    else:
                        for j, flag in enumerate(requires):
                            if not isinstance(flag, str) or not flag.strip():
                                add_issue(
                                    issues,
                                    "ERROR",
                                    "FLAG_INVALID",
                                    "Flag inválida em 'requires'.",
                                    f"{choice_path}.requires[{j}]"
                                )
                            else:
                                clean_flag = flag.strip()
                                requires_flags_used.add(clean_flag)

                                # Se o arquivo declarou flags, valida se essa existe
                                if len(declared_flags) > 0 and clean_flag not in declared_flags:
                                    add_issue(
                                        issues,
                                        "ERROR",
                                        "FLAG_NOT_DECLARED",
                                        f"Flag '{clean_flag}' usada em 'requires' mas não foi declarada.",
                                        f"{choice_path}.requires[{j}]"
                                    )

        # --- set_flags ---
        set_flags = node_data.get("set_flags", [])
        if set_flags is not None:
            if not isinstance(set_flags, list):
                add_issue(issues, "ERROR", "SET_FLAGS_TYPE", "'set_flags' deve ser lista.", f"{path}.set_flags")
            else:
                for i, flag in enumerate(set_flags):
                    if not isinstance(flag, str) or not flag.strip():
                        add_issue(
                            issues,
                            "ERROR",
                            "FLAG_INVALID",
                            "Flag inválida em 'set_flags'.",
                            f"{path}.set_flags[{i}]"
                        )
                    else:
                        clean_flag = flag.strip()
                        set_flags_used.add(clean_flag)

                        if len(declared_flags) > 0 and clean_flag not in declared_flags:
                            add_issue(
                                issues,
                                "ERROR",
                                "FLAG_NOT_DECLARED",
                                f"Flag '{clean_flag}' usada em 'set_flags' mas não foi declarada.",
                                f"{path}.set_flags[{i}]"
                            )

        # --- Nó terminal sem end ---
        has_next = isinstance(next_node, str)
        has_choices = isinstance(choices, list) and len(choices) > 0
        is_end = node_data.get("end") is True

        if not has_next and not has_choices and not is_end:
            add_issue(
                issues,
                "WARNING",
                "TERMINAL_NO_END",
                "Nó terminal sem 'end: true'.",
                path
            )

    # 5) Nós órfãos (não alcançáveis a partir do start)
    if isinstance(start, str) and start in nodes:
        reachable_nodes = dfs(start, edges)

        for node_id in nodes:
            if node_id not in reachable_nodes:
                add_issue(
                    issues,
                    "WARNING",
                    "ORPHAN_NODE",
                    f"Nó órfão (não alcançável a partir de '{start}').",
                    f"$.nodes.{node_id}"
                )

    # 6) Flags requeridas mas nunca setadas
    never_set = requires_flags_used - set_flags_used
    for flag in sorted(never_set):
        add_issue(
            issues,
            "WARNING",
            "FLAG_REQUIRED_NEVER_SET",
            f"A flag '{flag}' é requerida em uma choice, mas nunca é setada.",
            "$.nodes"
        )

    return issues


# ============================================================
# Mapeamento de Path -> Linha (para mostrar no relatório)
# ============================================================

def _read_lines(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.readlines()


def _find_line_index(lines, pattern, start=0, end=None):
    """Retorna índice 0-based da primeira linha que bater com o regex."""
    if end is None:
        end = len(lines)
    rx = re.compile(pattern)
    for i in range(start, end):
        if rx.search(lines[i]):
            return i
    return None


def _find_first_line(lines, pattern, start=0, end=None):
    """Retorna número da linha (1-based) da primeira ocorrência."""
    idx = _find_line_index(lines, pattern, start, end)
    return (idx + 1) if idx is not None else None


def _find_object_block(lines, key_name, start=0, end=None):
    """
    Encontra bloco { ... } de uma chave de objeto, ex: "room": { ... }
    Retorna (start_idx, end_idx) em 0-based.
    """
    if end is None:
        end = len(lines)

    key_pattern = rf'"\s*{re.escape(key_name)}\s*"\s*:\s*\{{'
    start_idx = _find_line_index(lines, key_pattern, start, end)
    if start_idx is None:
        return None

    brace_count = 0
    started = False

    for i in range(start_idx, end):
        for ch in lines[i]:
            if ch == "{":
                brace_count += 1
                started = True
            elif ch == "}":
                brace_count -= 1

        if started and brace_count == 0:
            return (start_idx, i)

    return (start_idx, end - 1)


def _find_array_block(lines, key_name, start=0, end=None):
    """
    Encontra bloco [ ... ] de uma chave, ex: "choices": [ ... ]
    Retorna (start_idx, end_idx) em 0-based.
    """
    if end is None:
        end = len(lines)

    key_pattern = rf'"\s*{re.escape(key_name)}\s*"\s*:\s*\['
    start_idx = _find_line_index(lines, key_pattern, start, end)
    if start_idx is None:
        return None

    bracket_count = 0
    started = False

    for i in range(start_idx, end):
        for ch in lines[i]:
            if ch == "[":
                bracket_count += 1
                started = True
            elif ch == "]":
                bracket_count -= 1

        if started and bracket_count == 0:
            return (start_idx, i)

    return (start_idx, end - 1)


def _find_choice_object_blocks(lines, choices_start, choices_end):
    """
    Dentro de um array 'choices', encontra cada objeto choice { ... }.
    Retorna lista de tuplas (start_idx, end_idx).
    """
    blocks = []
    brace_count = 0
    obj_start = None

    for i in range(choices_start, choices_end + 1):
        line = lines[i]

        for ch in line:
            if ch == "{":
                if brace_count == 0:
                    obj_start = i
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0 and obj_start is not None:
                    blocks.append((obj_start, i))
                    obj_start = None

    return blocks


def _line_for_issue_path(path, file_path):
    """
    Tenta mapear o path lógico (ex: $.nodes.room.choices[0].next)
    para uma linha do arquivo JSON.
    """
    try:
        lines = _read_lines(file_path)
    except Exception:
        return None

    # Casos raiz
    if path == "$":
        return 1
    if path == "$.start":
        return _find_first_line(lines, r'"\s*start\s*"\s*:')
    if path == "$.flags":
        return _find_first_line(lines, r'"\s*flags\s*"\s*:')
    if path.startswith("$.flags["):
        return _find_first_line(lines, r'"\s*flags\s*"\s*:')
    if path == "$.nodes":
        return _find_first_line(lines, r'"\s*nodes\s*"\s*:')

    # Precisa começar com $.nodes.
    if not path.startswith("$.nodes."):
        return None

    rest = path[len("$.nodes."):]  # ex: intro_01.choices[0].next
    if "." in rest:
        node_id, remainder = rest.split(".", 1)
    else:
        node_id, remainder = rest, ""

    # acha linha do nó
    node_block = _find_object_block(lines, node_id)
    if node_block is None:
        # fallback para a linha de "nodes"
        return _find_first_line(lines, r'"\s*nodes\s*"\s*:')

    node_start, node_end = node_block

    if remainder == "":
        return node_start + 1

    # campo simples dentro do nó (speaker, text, next, end, set_flags, choices etc)
    simple_field_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)", remainder)
    if simple_field_match:
        field = simple_field_match.group(1)
        line = _find_first_line(lines, rf'"\s*{re.escape(field)}\s*"\s*:', node_start, node_end + 1)
        return line if line is not None else (node_start + 1)

    # set_flags[0]
    if re.fullmatch(r"set_flags\[\d+\]", remainder):
        line = _find_first_line(lines, r'"\s*set_flags\s*"\s*:', node_start, node_end + 1)
        return line if line is not None else (node_start + 1)

    # next / text / speaker / end com subcaminho improvável (fallback)
    if remainder.startswith(("speaker", "text", "next", "end")):
        field = remainder.split(".")[0].split("[")[0]
        line = _find_first_line(lines, rf'"\s*{re.escape(field)}\s*"\s*:', node_start, node_end + 1)
        return line if line is not None else (node_start + 1)

    # choices[n].campo ou choices[n].requires[m]
    m_choice = re.fullmatch(r"choices\[(\d+)\]\.([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?", remainder)
    if m_choice:
        choice_index = int(m_choice.group(1))
        field_name = m_choice.group(2)

        choices_block = _find_array_block(lines, "choices", node_start, node_end + 1)
        if choices_block is None:
            return node_start + 1

        choices_start, choices_end = choices_block
        choice_blocks = _find_choice_object_blocks(lines, choices_start, choices_end)

        if 0 <= choice_index < len(choice_blocks):
            c_start, c_end = choice_blocks[choice_index]
            line = _find_first_line(lines, rf'"\s*{re.escape(field_name)}\s*"\s*:', c_start, c_end + 1)
            return line if line is not None else (c_start + 1)

        # fallback para linha de choices
        return choices_start + 1

    # fallback: tenta achar primeiro campo citado
    first_field = remainder.split(".")[0].split("[")[0]
    line = _find_first_line(lines, rf'"\s*{re.escape(first_field)}\s*"\s*:', node_start, node_end + 1)
    return line if line is not None else (node_start + 1)


def attach_line_numbers_to_issues(issues, file_path):
    """
    Adiciona issue["line"] quando conseguir mapear o Path para linha.
    """
    for issue in issues:
        path = issue.get("path")
        if not path:
            continue
        line_number = _line_for_issue_path(path, file_path)
        if line_number is not None:
            issue["line"] = line_number
    return issues


def print_report(issues):
    if len(issues) == 0:
        print("✅ Nenhum problema encontrado.")
        return

    # Ordenar por severidade
    order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
    issues.sort(key=lambda x: (order.get(x["level"], 99), x["code"], x["path"]))

    error_count = sum(1 for i in issues if i["level"] == "ERROR")
    warning_count = sum(1 for i in issues if i["level"] == "WARNING")
    info_count = sum(1 for i in issues if i["level"] == "INFO")

    print("\n=== RELATÓRIO DE VALIDAÇÃO ===")
    print(f"Erros: {error_count} | Avisos: {warning_count} | Info: {info_count}\n")

    icons = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}

    for issue in issues:
        icon = icons.get(issue["level"], "•")
        print(f"{icon} [{issue['level']}] {issue['code']}")
        print(f"   {issue['message']}")
        print(f"   Path: {issue['path']}")
        if "line" in issue:
            print(f"   Linha: {issue['line']}")
        print()


def main():
    # Se rodar sem argumento, tenta abrir "dialogues.json"
    file_path = "dialogues.json"

    # Se passar arquivo no terminal, usa o arquivo passado
    if len(sys.argv) > 1:
        file_path = sys.argv[1]

    try:
        data = load_json_file(file_path)
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {file_path}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ JSON inválido: {e.msg} | Linha {e.lineno}, Coluna {e.colno}")
        return

    issues = validate_dialogue(data)
    attach_line_numbers_to_issues(issues, file_path)
    print_report(issues)


if __name__ == "__main__":
    main()