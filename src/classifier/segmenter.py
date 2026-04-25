import re
from typing import Dict, List

_PATTERNS = [
    re.compile(r"^\s*(\d{1,2})\s*[.)]\s+\S"),
    re.compile(r"^[Qq]uestão\s+n?[°º]?\s*(\d{1,2})", re.IGNORECASE),
    re.compile(r"^[Qq]\s*\.?\s*(\d{1,2})\s*[.)]\s*", re.IGNORECASE),
    re.compile(r"^\((\d{1,2})\)\s+\S"),
    re.compile(r"^(\d{1,2})\s*[ªa]\s+[Qq]uestão", re.IGNORECASE),
]

_ALT_PATTERN = re.compile(
    r"^\s*[\[(]?\s*[AaBbCcDdEe]\s*[\])]?\s*[-.)]\s+\S", re.MULTILINE
)

# Palavras típicas de cabeçalho que NÃO são questões
_HEADER_WORDS = re.compile(
    r"\b(escola|turma|nome|aluno|data|ano|série|bimestre|avaliação|prova|"
    r"nota|professor|disciplina|instrução|instruções|página)\b",
    re.IGNORECASE,
)


def _match_question(line: str):
    # Exige ao menos 15 caracteres depois do marcador (cabeçalhos são curtos)
    for pat in _PATTERNS:
        m = pat.match(line)
        if m:
            rest = line[m.end():].strip()
            if len(rest) < 10:
                continue
            # Rejeita se a linha tem cara de cabeçalho
            if _HEADER_WORDS.search(line) and len(line.strip()) < 60:
                continue
            try:
                return int(m.group(1))
            except (IndexError, ValueError):
                return -1
    return None


def _split_stem_alts(text: str) -> Dict:
    lines = text.splitlines()
    stem, alts = [], []
    in_alts = False
    for line in lines:
        if _ALT_PATTERN.match(line):
            in_alts = True
        (alts if in_alts else stem).append(line)
    return {
        "stem": "\n".join(stem).strip(),
        "alternatives": [a.strip() for a in alts if a.strip()],
    }


def _detect_tipo(stem: str, alternatives: List[str]) -> str:
    """Detecta se a questão é multipla_escolha ou verdadeiro_falso.
    Critérios:
      - Alternativas são exatamente V/F ou Verdadeiro/Falso
      - OU stem menciona claramente 'verdadeiro e falso' / 'V ou F'
    """
    # Limpa as alternativas: remove "(A)", "(B)" etc do início e normaliza
    alts_clean = []
    for a in alternatives:
        # remove prefixo letra (ex: "(A) Verdadeiro" -> "Verdadeiro")
        cleaned = re.sub(r"^\s*\(?[A-Ea-e]\)?\s*[-.)]?\s*", "", a).strip().lower()
        alts_clean.append(cleaned)

    vf_words = {"v", "f", "verdadeiro", "falso", "verdadeira", "falsa"}
    if alts_clean and all(a in vf_words for a in alts_clean):
        return "verdadeiro_falso"

    stem_lower = stem.lower()
    # Marcadores típicos de instrução V/F
    vf_indicators = [
        "verdadeiro ou falso",
        "verdadeiro (v) ou falso (f)",
        "marque v",
        "marque (v)",
        "assinale v",
        "(v) para verdadeiro",
        " v ou f ",
        "v para verdadeiro",
    ]
    for indicator in vf_indicators:
        if indicator in stem_lower:
            return "verdadeiro_falso"

    return "multipla_escolha"


def segment_questions(text: str) -> List[Dict]:
    """Split raw OCR text into individual question dicts."""
    lines = text.splitlines()
    chunks: List[Dict] = []
    current_lines: List[str] = []
    current_num = None

    for line in lines:
        num = _match_question(line.strip())
        if num is not None:
            # Só salva chunk anterior se já tivemos um marcador de questão.
            # Isso descarta o cabeçalho (linhas antes da 1ª questão).
            if current_lines and current_num is not None:
                chunks.append({"number": current_num, "raw": "\n".join(current_lines)})
            current_num = num if num > 0 else (len(chunks) + 1)
            current_lines = [line]
        else:
            current_lines.append(line)

    # Só anexa o último chunk se houve marcador (evita cabeçalho sem questão depois)
    if current_lines and current_num is not None:
        chunks.append({"number": current_num, "raw": "\n".join(current_lines)})

    # Fallback: treat full text as single question
    if not chunks:
        chunks = [{"number": 1, "raw": text.strip()}]

    # Renumber when detection gave -1
    for i, c in enumerate(chunks):
        if c["number"] is None or c["number"] < 0:
            c["number"] = i + 1

    # Deduplica por número: mantém o chunk com mais conteúdo
    seen: Dict[int, Dict] = {}
    for c in chunks:
        num = c["number"]
        if num not in seen or len(c["raw"]) > len(seen[num]["raw"]):
            seen[num] = c
    chunks = sorted(seen.values(), key=lambda c: c["number"] or 0)

    results = []
    for c in chunks:
        if not c["raw"].strip():
            continue
        parts = _split_stem_alts(c["raw"])
        # Descarta chunks sem conteúdo mínimo no stem (cabeçalhos residuais)
        if len((parts["stem"] or "").strip()) < 12 and not parts["alternatives"]:
            continue
        tipo = _detect_tipo(parts["stem"], parts["alternatives"])
        results.append(
            {
                "number": c["number"],
                "text": c["raw"],
                "stem": parts["stem"],
                "alternatives": parts["alternatives"],
                "tipo": tipo,
            }
        )

    # Re-number sequentially to fix any gaps
    for i, q in enumerate(results):
        if q["number"] is None or q["number"] < 0:
            q["number"] = i + 1

    return results
