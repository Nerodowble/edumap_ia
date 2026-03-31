from typing import Dict, List, Optional

import plotly.graph_objects as go

BLOOM_COLORS = {1: "#3498DB", 2: "#2ECC71", 3: "#F1C40F", 4: "#E67E22", 5: "#E74C3C", 6: "#9B59B6"}
BLOOM_NAMES = {1: "Lembrar", 2: "Compreender", 3: "Aplicar", 4: "Analisar", 5: "Avaliar", 6: "Criar"}


def create_bloom_chart(questions: List[Dict]) -> go.Figure:
    counts = {i: 0 for i in range(1, 7)}
    for q in questions:
        lvl = q.get("bloom_level", 0)
        if lvl in counts:
            counts[lvl] += 1

    fig = go.Figure(
        go.Bar(
            x=[BLOOM_NAMES[l] for l in range(1, 7)],
            y=[counts[l] for l in range(1, 7)],
            marker_color=[BLOOM_COLORS[l] for l in range(1, 7)],
            text=[counts[l] for l in range(1, 7)],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Distribuição por Nível Cognitivo (Bloom)",
        xaxis_title="Nível",
        yaxis_title="Questões",
        plot_bgcolor="white",
        yaxis=dict(gridcolor="#f0f0f0", rangemode="tozero"),
        height=340,
        margin=dict(t=50, b=40),
    )
    return fig


def create_area_chart(questions: List[Dict]) -> go.Figure:
    counts: Dict[str, int] = {}
    for q in questions:
        area = q.get("area_display", "Indefinida")
        counts[area] = counts.get(area, 0) + 1

    fig = go.Figure(
        go.Pie(
            labels=list(counts.keys()),
            values=list(counts.values()),
            hole=0.4,
            textinfo="label+percent",
        )
    )
    fig.update_layout(
        title="Distribuição por Área do Conhecimento",
        height=340,
        margin=dict(t=50, b=40),
    )
    return fig


def create_heatmap(students: List[Dict], questions: List[Dict]) -> Optional[go.Figure]:
    if not students or not questions:
        return None

    levels = list(range(1, 7))
    level_qs: Dict[int, List] = {l: [] for l in levels}
    for q in questions:
        lvl = q.get("bloom_level", 0)
        if lvl in level_qs:
            level_qs[lvl].append(q["number"])

    matrix = []
    for student in students:
        row = []
        for lvl in levels:
            qs = level_qs[lvl]
            if not qs:
                row.append(None)
                continue
            correct = sum(1 for n in qs if student["answers"].get(n) == "correct")
            row.append(round(correct * 100 / len(qs)))
        matrix.append(row)

    text_matrix = [
        [f"{v}%" if v is not None else "—" for v in row] for row in matrix
    ]

    fig = go.Figure(
        go.Heatmap(
            z=matrix,
            x=[BLOOM_NAMES[l] for l in levels],
            y=[s["name"] for s in students],
            colorscale="RdYlGn",
            zmin=0,
            zmax=100,
            text=text_matrix,
            texttemplate="%{text}",
            showscale=True,
        )
    )
    fig.update_layout(
        title="Desempenho por Nível Cognitivo (%)",
        height=max(300, 70 * len(students) + 100),
        margin=dict(t=50, b=40),
    )
    return fig
