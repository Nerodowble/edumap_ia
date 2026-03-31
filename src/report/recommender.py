from typing import Dict, List

_BLOOM_NAMES = {1: "Lembrar", 2: "Compreender", 3: "Aplicar", 4: "Analisar", 5: "Avaliar", 6: "Criar"}

_BLOOM_TIPS = {
    1: "Revise o conteúdo teórico básico com a turma antes de avançar.",
    2: "Trabalhe interpretação com leituras variadas e discussão em grupo.",
    3: "Pratique com exercícios contextualizados usando situações do dia a dia.",
    4: "Proponha atividades de comparação, debate e organização de ideias.",
    5: "Estimule argumentação escrita e oral com critérios explícitos de avaliação.",
    6: "Crie espaço para projetos, produções originais e resolução de problemas abertos.",
}


def generate_recommendations(
    questions: List[Dict], students: List[Dict] = None
) -> List[Dict]:
    recs: List[Dict] = []
    total = len(questions)
    if total == 0:
        return recs

    bloom_counts = {}
    for q in questions:
        lvl = q.get("bloom_level", 0)
        bloom_counts[lvl] = bloom_counts.get(lvl, 0) + 1

    area_counts: Dict[str, int] = {}
    for q in questions:
        a = q.get("area_display", "Indefinida")
        area_counts[a] = area_counts.get(a, 0) + 1

    low = sum(bloom_counts.get(i, 0) for i in [1, 2])
    high = sum(bloom_counts.get(i, 0) for i in [4, 5, 6])

    # Warning: only low-order questions
    if total >= 3 and low / total > 0.70:
        recs.append({
            "type": "warning",
            "title": "Prova concentrada em níveis básicos de Bloom",
            "detail": (
                f"{low} de {total} questões ({low * 100 // total}%) avaliam apenas Lembrar/Compreender. "
                "Considere incluir questões de Aplicar ou Analisar para um diagnóstico mais completo."
            ),
        })

    # Info: no higher-order questions
    if high == 0:
        recs.append({
            "type": "info",
            "title": "Nenhuma questão de ordem superior (Analisar / Avaliar / Criar)",
            "detail": (
                "A prova não avalia pensamento crítico ou criatividade. "
                "Questões de ordem superior diferenciam estudantes de alta proficiência."
            ),
        })

    # Success: good balance
    if 0.20 <= low / total <= 0.60 and high > 0:
        recs.append({
            "type": "success",
            "title": "Boa distribuição de níveis cognitivos",
            "detail": "A prova cobre múltiplos níveis de Bloom, permitindo diagnóstico abrangente.",
        })

    # Info: area concentration (for multi-subject context only)
    if area_counts:
        max_area_count = max(area_counts.values())
        dominant_area = max(area_counts, key=area_counts.get)
        if len(area_counts) > 1 and max_area_count / total > 0.80:
            recs.append({
                "type": "info",
                "title": f"Prova fortemente concentrada em {dominant_area}",
                "detail": (
                    f"{max_area_count} de {total} questões são de {dominant_area}. "
                    "Outras áreas da BNCC não foram avaliadas nesta aplicação."
                ),
            })

    # Warning: very few questions detected
    if total < 4:
        recs.append({
            "type": "warning",
            "title": "Poucas questões identificadas",
            "detail": (
                "O sistema identificou apenas algumas questões. "
                "Verifique o texto extraído pelo OCR na aba 'Por Questão' — "
                "a formatação da prova pode ter dificultado a leitura."
            ),
        })

    # Student-based recommendations
    if students:
        _add_student_recs(recs, questions, students)

    return recs


def _add_student_recs(recs: List[Dict], questions: List[Dict], students: List[Dict]):
    level_stats: Dict[int, Dict] = {i: {"ok": 0, "total": 0} for i in range(1, 7)}

    for q in questions:
        lvl = q.get("bloom_level", 0)
        if lvl not in level_stats:
            continue
        for s in students:
            ans = s["answers"].get(q["number"])
            if ans is not None:
                level_stats[lvl]["total"] += 1
                if ans == "correct":
                    level_stats[lvl]["ok"] += 1

    for lvl, stat in level_stats.items():
        if stat["total"] < 2:
            continue
        error_rate = 1.0 - stat["ok"] / stat["total"]
        if error_rate >= 0.60:
            recs.append({
                "type": "critical",
                "title": f'Alto índice de erros em "{_BLOOM_NAMES.get(lvl, "")}" ({error_rate * 100:.0f}%)',
                "detail": _BLOOM_TIPS.get(lvl, "Revise a abordagem para este nível."),
            })
