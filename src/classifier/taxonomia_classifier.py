"""
Classificador taxonômico profundo.

Dado o enunciado de uma questão e a matéria (informada pelo professor),
busca na árvore taxonômica do banco o nó mais específico que bate com
o texto, usando match de palavras-chave.

Algoritmo:
  1. Normaliza o enunciado (lowercase, remove acentos).
  2. Carrega todos os nós da matéria/etapa do banco.
  3. Para cada nó, conta quantas palavras-chave aparecem no enunciado.
  4. Escolhe o nó com maior score: (matches * 10) + nível.
     → Mais matches ganha; em caso de empate, nó mais profundo vence.
  5. Monta o caminho completo do nó raiz até o nó escolhido.
"""
import re
import unicodedata
from typing import Dict, List, Optional

from database.db import _conn


# ── Utils ─────────────────────────────────────────────────────────────────────

_MIN_KEYWORD_LEN = 3  # ignora keywords muito curtos (ex: "à", "a") — evita falsos-positivos


def _normalize(text: str) -> str:
    """Lowercase + remove acentos (NFD → stripa combinantes)."""
    if not text:
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def _parse_keywords(csv: Optional[str]) -> List[str]:
    if not csv:
        return []
    out = []
    for raw in csv.split(","):
        kw = _normalize(raw.strip())
        if len(kw) >= _MIN_KEYWORD_LEN:
            out.append(kw)
    return out


def _count_matches(kws: List[str], stem_norm: str) -> int:
    """
    Match com word boundary (\\b) + tolerância a plural com 's' final.
    Ex: kw 'triangulo' bate em 'triangulo' e 'triangulos' mas não em 'retriangular'.
    """
    count = 0
    for kw in kws:
        pattern = r"\b" + re.escape(kw) + r"s?\b"
        if re.search(pattern, stem_norm):
            count += 1
    return count


def _score(matches: int, nivel: int) -> int:
    """Pondera profundidade 3x para preferir leaves quando pai e filho têm match."""
    return matches * 2 + nivel * 3


# ── Carregamento da árvore ────────────────────────────────────────────────────

def _load_tree(materia: str, etapa: str = "ef2") -> List[Dict]:
    with _conn() as con:
        nodes = con.execute(
            """SELECT id, codigo, label, nivel, parent_id, palavras_chave
               FROM taxonomia
               WHERE etapa=? AND materia=?
               ORDER BY nivel""",
            (etapa, materia),
        ).fetchall()
        # Fallback: se a etapa padrão não tem a matéria, tenta qualquer etapa
        if not nodes:
            row = con.execute(
                "SELECT DISTINCT etapa FROM taxonomia WHERE materia=? LIMIT 1",
                (materia,),
            ).fetchone()
            if row:
                nodes = con.execute(
                    """SELECT id, codigo, label, nivel, parent_id, palavras_chave
                       FROM taxonomia
                       WHERE etapa=? AND materia=?
                       ORDER BY nivel""",
                    (row["etapa"], materia),
                ).fetchall()
        return nodes


# ── Classificador ─────────────────────────────────────────────────────────────

def classify(stem: str, materia: str, etapa: str = "ef2") -> Optional[Dict]:
    """
    Classifica o enunciado no nó mais específico da árvore taxonômica.

    Retorna:
        None se não houver nenhum match, ou dict com:
          - codigo:  código completo do nó (ex: ef2.matematica.geometria...)
          - label:   nome legível
          - nivel:   profundidade (1..6)
          - caminho: lista de nós do raiz até o escolhido
          - matches: quantas palavras-chave do nó bateram no enunciado
    """
    if not stem or not materia:
        return None

    stem_norm = _normalize(stem)
    nodes = _load_tree(materia, etapa)
    if not nodes:
        return None

    by_id = {n["id"]: n for n in nodes}

    best = None
    best_score = 0
    best_matches = 0

    for node in nodes:
        kws = _parse_keywords(node.get("palavras_chave"))
        if not kws:
            continue
        matches = _count_matches(kws, stem_norm)
        if matches == 0:
            continue
        # Prioriza matches, desempata pelo nível (mais profundo vence)
        score = _score(matches, node["nivel"])
        if score > best_score:
            best_score = score
            best_matches = matches
            best = node

    if not best:
        return None

    # Monta caminho do raiz até o nó escolhido
    caminho: List[Dict] = []
    cur = best
    while cur is not None:
        caminho.append({
            "codigo": cur["codigo"],
            "label":  cur["label"],
            "nivel":  cur["nivel"],
        })
        pid = cur.get("parent_id")
        cur = by_id.get(pid) if pid else None
    caminho.reverse()

    return {
        "codigo":  best["codigo"],
        "label":   best["label"],
        "nivel":   best["nivel"],
        "caminho": caminho,
        "matches": best_matches,
    }


def classify_across_all(stem: str) -> Optional[Dict]:
    """
    Classifica o enunciado tentando TODAS as matérias/etapas da taxonomia.

    Estratégia em 2 fases:
      1. Soma matches por matéria (sinal agregado) para escolher a melhor
      2. Dentro da matéria vencedora, escolhe o nó mais específico que bateu

    Assim um único match em um nó profundo de matéria errada não rouba
    uma questão que tem 5 matches distribuídos na matéria correta.
    """
    if not stem:
        return None
    stem_norm = _normalize(stem)
    if not stem_norm:
        return None

    with _conn() as con:
        nodes = con.execute(
            """SELECT id, codigo, label, nivel, parent_id, palavras_chave, materia, etapa
               FROM taxonomia"""
        ).fetchall()
    if not nodes:
        return None

    by_id = {n["id"]: n for n in nodes}

    # Fase 1: matches por nó + total acumulado por matéria
    node_matches: Dict[int, int] = {}
    materia_total: Dict[tuple, int] = {}

    for node in nodes:
        kws = _parse_keywords(node.get("palavras_chave"))
        if not kws:
            continue
        matches = _count_matches(kws, stem_norm)
        if matches == 0:
            continue
        node_matches[node["id"]] = matches
        key = (node["materia"], node["etapa"])
        materia_total[key] = materia_total.get(key, 0) + matches

    if not materia_total:
        return None

    # Escolhe a matéria com maior total de matches
    best_materia_key = max(materia_total.items(), key=lambda kv: kv[1])[0]
    best_materia, best_etapa = best_materia_key

    # Fase 2: dentro da matéria vencedora, pega o nó com melhor score individual
    best_node = None
    best_score = 0
    best_matches_in_node = 0

    for node in nodes:
        if node["materia"] != best_materia or node["etapa"] != best_etapa:
            continue
        m = node_matches.get(node["id"], 0)
        if m == 0:
            continue
        s = _score(m, node["nivel"])
        if s > best_score:
            best_score = s
            best_matches_in_node = m
            best_node = node

    if not best_node:
        return None

    caminho: List[Dict] = []
    cur = best_node
    while cur is not None:
        caminho.append({
            "codigo": cur["codigo"],
            "label":  cur["label"],
            "nivel":  cur["nivel"],
        })
        pid = cur.get("parent_id")
        cur = by_id.get(pid) if pid else None
    caminho.reverse()

    return {
        "codigo":  best_node["codigo"],
        "label":   best_node["label"],
        "nivel":   best_node["nivel"],
        "caminho": caminho,
        "matches": best_matches_in_node,
        "materia": best_materia,
        "etapa":   best_etapa,
        "materia_total_matches": materia_total[best_materia_key],
    }


def classify_many(stems: List[str], materia: str, etapa: str = "ef2") -> List[Optional[Dict]]:
    """Classifica múltiplos enunciados reutilizando a mesma árvore (mais rápido)."""
    nodes = _load_tree(materia, etapa)
    if not nodes:
        return [None] * len(stems)

    by_id = {n["id"]: n for n in nodes}
    resultados: List[Optional[Dict]] = []

    for stem in stems:
        if not stem:
            resultados.append(None)
            continue
        stem_norm = _normalize(stem)
        best = None
        best_score = 0
        best_matches = 0
        for node in nodes:
            kws = _parse_keywords(node.get("palavras_chave"))
            if not kws:
                continue
            matches = _count_matches(kws, stem_norm)
            if matches == 0:
                continue
            score = _score(matches, node["nivel"])
            if score > best_score:
                best_score = score
                best_matches = matches
                best = node

        if not best:
            resultados.append(None)
            continue

        caminho = []
        cur = best
        while cur is not None:
            caminho.append({
                "codigo": cur["codigo"],
                "label":  cur["label"],
                "nivel":  cur["nivel"],
            })
            pid = cur.get("parent_id")
            cur = by_id.get(pid) if pid else None
        caminho.reverse()

        resultados.append({
            "codigo":  best["codigo"],
            "label":   best["label"],
            "nivel":   best["nivel"],
            "caminho": caminho,
            "matches": best_matches,
        })

    return resultados
