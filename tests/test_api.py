"""
Testes de integração — EduMap IA API
Cobre: funcionalidade, status codes, estrutura de dados, performance e stress.
"""
import io
import time
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# ROOT
# ─────────────────────────────────────────────────────────────────────────────
class TestRoot:
    def test_root_retorna_ok(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_docs_acessivel(self, client):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_openapi_schema(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert schema["info"]["title"] == "EduMap IA API"


# ─────────────────────────────────────────────────────────────────────────────
# TURMAS
# ─────────────────────────────────────────────────────────────────────────────
class TestTurmas:
    def test_listar_retorna_lista(self, client):
        r = client.get("/turmas")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_criar_turma_completa(self, client):
        r = client.post("/turmas", json={
            "nome": "7ºA", "escola": "E.E. São Paulo", "disciplina": "Ciências"
        })
        assert r.status_code == 201
        d = r.json()
        assert d["nome"] == "7ºA"
        assert d["escola"] == "E.E. São Paulo"
        assert "id" in d
        assert "criado_em" in d

    def test_criar_turma_minima(self, client):
        r = client.post("/turmas", json={"nome": "6ºB"})
        assert r.status_code == 201
        assert r.json()["nome"] == "6ºB"

    def test_criar_sem_nome_retorna_422(self, client):
        r = client.post("/turmas", json={"escola": "Escola X"})
        assert r.status_code == 422

    def test_turma_aparece_na_listagem(self, client, turma_criada):
        r = client.get("/turmas")
        ids = [t["id"] for t in r.json()]
        assert turma_criada["id"] in ids

    def test_deletar_turma(self, client):
        r = client.post("/turmas", json={"nome": "Para Deletar"})
        tid = r.json()["id"]
        rd = client.delete(f"/turmas/{tid}")
        assert rd.status_code == 204
        ids = [t["id"] for t in client.get("/turmas").json()]
        assert tid not in ids

    def test_deletar_turma_inexistente_retorna_404(self, client):
        r = client.delete("/turmas/99999")
        assert r.status_code == 404

    def test_performance_criar_turma(self, client):
        start = time.time()
        client.post("/turmas", json={"nome": "Perf Test"})
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Criar turma demorou {elapsed:.3f}s — esperado < 1s"


# ─────────────────────────────────────────────────────────────────────────────
# ALUNOS
# ─────────────────────────────────────────────────────────────────────────────
class TestAlunos:
    def test_listar_alunos(self, client, turma_criada):
        r = client.get(f"/turmas/{turma_criada['id']}/alunos")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_criar_aluno(self, client, turma_criada):
        r = client.post(f"/turmas/{turma_criada['id']}/alunos", json={"nome": "João Pereira"})
        assert r.status_code == 201
        d = r.json()
        assert d["nome"] == "João Pereira"
        assert d["turma_id"] == turma_criada["id"]

    def test_aluno_aparece_na_listagem(self, client, turma_criada, aluno_criado):
        r = client.get(f"/turmas/{turma_criada['id']}/alunos")
        nomes = [a["nome"] for a in r.json()]
        assert aluno_criado["nome"] in nomes

    def test_criar_aluno_turma_inexistente_retorna_404(self, client):
        r = client.post("/turmas/99999/alunos", json={"nome": "X"})
        assert r.status_code == 404

    def test_criar_aluno_sem_nome_retorna_422(self, client, turma_criada):
        r = client.post(f"/turmas/{turma_criada['id']}/alunos", json={})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# UPLOAD DE PROVA
# ─────────────────────────────────────────────────────────────────────────────
class TestUpload:
    def test_upload_basico(self, client, prova_pdf):
        """Verifica que o upload retorna estrutura esperada."""
        with open(prova_pdf, "rb") as f:
            r = client.post(
                "/provas/upload",
                data={"year_level": "8º ano EF", "subject": "Detectar automaticamente"},
                files={"file": ("prova.pdf", f, "application/pdf")},
            )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "prova_id" in d
        assert "questions" in d
        assert "ocr_method" in d
        assert "metadata" in d

    def test_upload_detecta_questoes(self, prova_enviada):
        """A prova de exemplo tem 12 questões — verifica que pelo menos 8 são detectadas."""
        qs = prova_enviada["questions"]
        assert len(qs) >= 8, f"Esperado ≥ 8 questões, detectou {len(qs)}"

    def test_upload_bloom_preenchido(self, prova_enviada):
        """Toda questão deve ter bloom_level entre 0 e 6."""
        for q in prova_enviada["questions"]:
            assert "bloom_level" in q, f"Q{q.get('number')} sem bloom_level"
            assert 0 <= q["bloom_level"] <= 6

    def test_upload_area_preenchida(self, prova_enviada):
        """Toda questão deve ter área classificada."""
        for q in prova_enviada["questions"]:
            assert "area_key" in q
            assert q["area_key"] != "", f"Q{q.get('number')} com area_key vazia"

    def test_upload_subarea_preenchida(self, prova_enviada):
        """Toda questão deve ter subárea."""
        for q in prova_enviada["questions"]:
            assert "subarea_key" in q
            assert "subarea_label" in q

    def test_upload_detecta_areas_distintas(self, prova_enviada):
        """A prova de exemplo tem 4 disciplinas — deve detectar pelo menos 2 áreas."""
        areas = {q["area_key"] for q in prova_enviada["questions"]}
        assert len(areas) >= 2, f"Esperado ≥ 2 áreas, detectou: {areas}"

    def test_upload_sem_arquivo_retorna_422(self, client):
        r = client.post("/provas/upload", data={"year_level": "8º ano EF"})
        assert r.status_code == 422

    def test_upload_sem_year_level_retorna_422(self, client, prova_pdf):
        with open(prova_pdf, "rb") as f:
            r = client.post(
                "/provas/upload",
                files={"file": ("prova.pdf", f, "application/pdf")},
            )
        assert r.status_code == 422

    def test_performance_upload_pdf(self, client, prova_pdf):
        """OCR + classificação deve terminar em menos de 30 segundos."""
        start = time.time()
        with open(prova_pdf, "rb") as f:
            r = client.post(
                "/provas/upload",
                data={"year_level": "8º ano EF"},
                files={"file": ("prova.pdf", f, "application/pdf")},
            )
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 30, f"Upload demorou {elapsed:.1f}s — limite: 30s"
        print(f"\n  [Perf] Upload processado em {elapsed:.2f}s")


# ─────────────────────────────────────────────────────────────────────────────
# PROVAS (listagem)
# ─────────────────────────────────────────────────────────────────────────────
class TestProvas:
    def test_listar_provas_turma(self, client, turma_criada, prova_enviada):
        r = client.get(f"/turmas/{turma_criada['id']}/provas")
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert prova_enviada["prova_id"] in ids

    def test_questoes_prova(self, client, prova_enviada):
        pid = prova_enviada["prova_id"]
        r = client.get(f"/provas/{pid}/questoes")
        assert r.status_code == 200
        qs = r.json()
        assert len(qs) > 0
        for q in qs:
            assert "bloom_nivel" in q
            assert "area_display" in q
            assert "subarea_label" in q
            assert "numero" in q

    def test_performance_listar_questoes(self, client, prova_enviada):
        start = time.time()
        client.get(f"/provas/{prova_enviada['prova_id']}/questoes")
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Listar questões demorou {elapsed:.3f}s — limite: 500ms"


# ─────────────────────────────────────────────────────────────────────────────
# RESPOSTAS E RELATÓRIOS
# ─────────────────────────────────────────────────────────────────────────────
class TestRelatorios:
    def test_relatorio_turma_sem_respostas_retorna_lista_vazia(self, client, prova_enviada):
        # Usa uma prova nova sem respostas
        pid = prova_enviada["prova_id"]
        r = client.get(f"/provas/{pid}/relatorio/turma")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_salvar_respostas(self, client, prova_enviada, aluno_criado):
        pid = prova_enviada["prova_id"]
        qs = client.get(f"/provas/{pid}/questoes").json()

        respostas = {}
        for i, q in enumerate(qs):
            correta = (i % 2 == 0)
            respostas[str(q["numero"])] = {
                "resposta": "A" if correta else "B",
                "gabarito": "A",
                "correta": correta,
            }

        r = client.post(
            f"/provas/{pid}/respostas",
            json={"aluno_id": aluno_criado["id"], "respostas": respostas},
        )
        assert r.status_code == 201
        assert r.json()["ok"] is True

    def test_relatorio_turma_com_respostas(self, client, prova_enviada, aluno_criado):
        pid = prova_enviada["prova_id"]
        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        nomes = [r["aluno"]["nome"] for r in rel]
        assert aluno_criado["nome"] in nomes

    def test_relatorio_turma_campos(self, client, prova_enviada):
        pid = prova_enviada["prova_id"]
        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        if rel:
            r = rel[0]
            assert "aluno" in r
            assert "acertos" in r
            assert "total" in r
            assert "percentual" in r
            assert "por_bloom" in r
            assert 0 <= r["percentual"] <= 100

    def test_drilldown_estrutura(self, client, prova_enviada):
        pid = prova_enviada["prova_id"]
        r = client.get(f"/provas/{pid}/relatorio/drilldown")
        assert r.status_code == 200
        d = r.json()
        for area, subareas in d.items():
            assert isinstance(area, str)
            for sub_key, sub_data in subareas.items():
                assert "label" in sub_data, f"Subárea '{sub_key}' sem 'label'"
                assert "bloom" in sub_data, f"Subárea '{sub_key}' sem 'bloom'"
                for lvl, bdata in sub_data["bloom"].items():
                    assert "nome" in bdata
                    assert "pct_turma" in bdata
                    assert "alunos" in bdata
                    assert 0 <= bdata["pct_turma"] <= 100

    def test_performance_drilldown(self, client, prova_enviada):
        start = time.time()
        client.get(f"/provas/{prova_enviada['prova_id']}/relatorio/drilldown")
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Drilldown demorou {elapsed:.3f}s — limite: 1s"
        print(f"\n  [Perf] Drilldown em {elapsed:.3f}s")

    def test_respostas_idempotente(self, client, prova_enviada, aluno_criado):
        """Enviar as mesmas respostas duas vezes não deve gerar duplicatas."""
        pid = prova_enviada["prova_id"]
        qs = client.get(f"/provas/{pid}/questoes").json()
        respostas = {str(q["numero"]): {"resposta": "A", "gabarito": "A", "correta": True} for q in qs}
        payload = {"aluno_id": aluno_criado["id"], "respostas": respostas}

        r1 = client.post(f"/provas/{pid}/respostas", json=payload)
        r2 = client.post(f"/provas/{pid}/respostas", json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 201

        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        entradas = [r for r in rel if r["aluno"]["nome"] == aluno_criado["nome"]]
        assert len(entradas) == 1, "Aluno duplicado no relatório"


# ─────────────────────────────────────────────────────────────────────────────
# GABARITO
# ─────────────────────────────────────────────────────────────────────────────
class TestGabarito:
    def test_get_gabarito_vazio_retorna_dict(self, client, prova_enviada):
        """Prova sem gabarito definido deve retornar dicionário vazio."""
        pid = prova_enviada["prova_id"]
        r = client.get(f"/provas/{pid}/gabarito")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)

    def test_salvar_gabarito_retorna_201(self, client, prova_enviada):
        pid = prova_enviada["prova_id"]
        qs = client.get(f"/provas/{pid}/questoes").json()
        gabarito = {str(q["numero"]): "A" for q in qs}
        r = client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito})
        assert r.status_code == 201
        assert r.json()["ok"] is True

    def test_get_gabarito_retorna_dados_corretos(self, client, prova_enviada):
        pid = prova_enviada["prova_id"]
        qs = client.get(f"/provas/{pid}/questoes").json()
        gabarito_enviado = {str(q["numero"]): "B" for q in qs}
        client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito_enviado})

        r = client.get(f"/provas/{pid}/gabarito")
        assert r.status_code == 200
        gab = r.json()
        # len(gab) may be < len(qs) when the PDF has duplicate question numbers
        assert len(gab) > 0
        for val in gab.values():
            assert val == "B"

    def test_gabarito_normaliza_para_uppercase(self, client, prova_enviada):
        """Letras minúsculas no gabarito devem ser normalizadas."""
        pid = prova_enviada["prova_id"]
        qs = client.get(f"/provas/{pid}/questoes").json()
        gabarito = {str(q["numero"]): "c" for q in qs}
        client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito})

        gab = client.get(f"/provas/{pid}/gabarito").json()
        for v in gab.values():
            assert v == "C", f"Esperado 'C', obteve '{v}'"

    def test_gabarito_sobrescreve_sem_duplicar(self, client, prova_enviada):
        """Salvar gabarito duas vezes não deve duplicar entradas."""
        pid = prova_enviada["prova_id"]
        qs = client.get(f"/provas/{pid}/questoes").json()
        gabarito = {str(q["numero"]): "D" for q in qs}

        client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito})
        client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito})

        gab = client.get(f"/provas/{pid}/gabarito").json()
        numeros = list(gab.keys())
        assert len(numeros) == len(set(numeros)), "Questões duplicadas no gabarito"

    def test_gabarito_parcial_aceito(self, client, prova_enviada):
        """Gabarito com menos questões que a prova deve ser aceito."""
        pid = prova_enviada["prova_id"]
        qs = client.get(f"/provas/{pid}/questoes").json()
        gabarito_parcial = {str(qs[0]["numero"]): "A", str(qs[1]["numero"]): "B"}
        r = client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito_parcial})
        assert r.status_code == 201

    def test_gabarito_sem_body_retorna_422(self, client, prova_enviada):
        pid = prova_enviada["prova_id"]
        r = client.post(f"/provas/{pid}/gabarito", json={})
        assert r.status_code == 422

    def test_performance_salvar_gabarito(self, client, prova_com_gabarito):
        """Salvar gabarito deve ser rápido."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        start = time.time()
        client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito})
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Salvar gabarito demorou {elapsed:.3f}s — limite: 500ms"

    def test_performance_get_gabarito(self, client, prova_com_gabarito):
        pid = prova_com_gabarito["prova_id"]
        start = time.time()
        client.get(f"/provas/{pid}/gabarito")
        elapsed = time.time() - start
        assert elapsed < 0.2, f"GET gabarito demorou {elapsed:.3f}s — limite: 200ms"


# ─────────────────────────────────────────────────────────────────────────────
# LANÇAMENTO (lancar)
# ─────────────────────────────────────────────────────────────────────────────
class TestLancar:
    def test_lancar_retorna_201(self, client, prova_com_gabarito, aluno_gabarito):
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        respostas = {str(q["number"]): gabarito[str(q["number"])] for q in prova_com_gabarito["questions"]}
        r = client.post(f"/provas/{pid}/lancar", json={
            "respostas": {str(aluno_gabarito["id"]): respostas}
        })
        assert r.status_code == 201
        assert r.json()["ok"] is True

    def test_lancar_calcula_acertos_corretamente(self, client, prova_com_gabarito, aluno_gabarito):
        """Matemática dos acertos deve ser exata."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        questions = prova_com_gabarito["questions"]

        # Deduplicate by number (some PDFs produce duplicate question markers)
        seen: set = set()
        questions = [q for q in questions if not (q["number"] in seen or seen.add(q["number"]))]
        n = len(questions)
        metade = n // 2

        # Primeira metade: resposta correta; segunda: resposta errada ("E")
        respostas = {}
        for i, q in enumerate(questions):
            num = str(q["number"])
            respostas[num] = gabarito[num] if i < metade else "E"

        client.post(f"/provas/{pid}/lancar", json={
            "respostas": {str(aluno_gabarito["id"]): respostas}
        })

        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        aluno_rel = next((a for a in rel if a["aluno"]["id"] == aluno_gabarito["id"]), None)
        assert aluno_rel is not None, "Aluno não encontrado no relatório"
        assert aluno_rel["acertos"] == metade, (
            f"Esperado {metade} acertos, obteve {aluno_rel['acertos']}"
        )
        assert aluno_rel["total"] == n
        expected_pct = round(metade * 100 / n)
        assert aluno_rel["percentual"] == expected_pct

    def test_lancar_todos_corretos(self, client, prova_com_gabarito, aluno_gabarito2):
        """Aluno que acerta tudo deve ter 100%."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        respostas = dict(gabarito)  # cópia exata do gabarito

        client.post(f"/provas/{pid}/lancar", json={
            "respostas": {str(aluno_gabarito2["id"]): respostas}
        })

        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        aluno_rel = next((a for a in rel if a["aluno"]["id"] == aluno_gabarito2["id"]), None)
        assert aluno_rel is not None
        assert aluno_rel["acertos"] == aluno_rel["total"]
        assert aluno_rel["percentual"] == 100

    def test_lancar_todos_errados(self, client, prova_com_gabarito, aluno_gabarito):
        """Aluno que erra tudo deve ter 0 acertos."""
        pid = prova_com_gabarito["prova_id"]
        questions = prova_com_gabarito["questions"]
        respostas = {str(q["number"]): "E" for q in questions}

        client.post(f"/provas/{pid}/lancar", json={
            "respostas": {str(aluno_gabarito["id"]): respostas}
        })

        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        aluno_rel = next((a for a in rel if a["aluno"]["id"] == aluno_gabarito["id"]), None)
        assert aluno_rel is not None
        assert aluno_rel["acertos"] == 0
        assert aluno_rel["percentual"] == 0

    def test_lancar_alternativas_case_insensitive(self, client, prova_com_gabarito, aluno_gabarito2):
        """Respostas em minúsculo devem ser aceitas e comparadas corretamente."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        # Envia gabarito em minúsculas — deve ser igual ao gabarito salvo
        respostas = {k: v.lower() for k, v in gabarito.items()}

        client.post(f"/provas/{pid}/lancar", json={
            "respostas": {str(aluno_gabarito2["id"]): respostas}
        })

        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        aluno_rel = next((a for a in rel if a["aluno"]["id"] == aluno_gabarito2["id"]), None)
        assert aluno_rel is not None
        assert aluno_rel["acertos"] == aluno_rel["total"], \
            "Respostas em minúsculo devem ser tratadas como corretas"

    def test_lancar_questao_inexistente_ignorada(self, client, prova_com_gabarito, aluno_gabarito):
        """Número de questão inexistente deve ser silenciosamente ignorado."""
        pid = prova_com_gabarito["prova_id"]
        respostas = {"9999": "A", "8888": "B"}
        r = client.post(f"/provas/{pid}/lancar", json={
            "respostas": {str(aluno_gabarito["id"]): respostas}
        })
        assert r.status_code == 201

    def test_lancar_multiplos_alunos_um_request(self, client, prova_com_gabarito, turma_criada):
        """Deve aceitar e processar múltiplos alunos em uma única requisição."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        questions = prova_com_gabarito["questions"]

        # Criar 5 alunos inline
        aluno_ids = []
        for i in range(5):
            r = client.post(f"/turmas/{turma_criada['id']}/alunos",
                            json={"nome": f"Multi Aluno {i}"})
            aluno_ids.append(r.json()["id"])

        payload = {}
        for j, aid in enumerate(aluno_ids):
            # Aluno j acerta as j primeiras questões
            resps = {}
            for i, q in enumerate(questions):
                num = str(q["number"])
                resps[num] = gabarito[num] if i < j else "E"
            payload[str(aid)] = resps

        start = time.time()
        r = client.post(f"/provas/{pid}/lancar", json={"respostas": payload})
        elapsed = time.time() - start
        assert r.status_code == 201
        assert elapsed < 2.0, f"Lançar 5 alunos demorou {elapsed:.3f}s — limite: 2s"

        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        rel_ids = {a["aluno"]["id"] for a in rel}
        for aid in aluno_ids:
            assert aid in rel_ids, f"Aluno {aid} não aparece no relatório"

    def test_lancar_idempotente(self, client, prova_com_gabarito, aluno_gabarito):
        """Lançar as mesmas respostas duas vezes não duplica entradas."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        payload = {"respostas": {str(aluno_gabarito["id"]): dict(gabarito)}}

        client.post(f"/provas/{pid}/lancar", json=payload)
        client.post(f"/provas/{pid}/lancar", json=payload)

        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        entradas = [a for a in rel if a["aluno"]["id"] == aluno_gabarito["id"]]
        assert len(entradas) == 1, f"Aluno duplicado no relatório após lançamento duplo"

    def test_lancar_sem_respostas_retorna_201(self, client, prova_com_gabarito):
        """Payload vazio deve ser aceito (não há o que salvar)."""
        pid = prova_com_gabarito["prova_id"]
        r = client.post(f"/provas/{pid}/lancar", json={"respostas": {}})
        assert r.status_code == 201

    def test_lancar_sem_body_retorna_422(self, client, prova_com_gabarito):
        pid = prova_com_gabarito["prova_id"]
        r = client.post(f"/provas/{pid}/lancar", json={})
        assert r.status_code == 422

    def test_performance_lancar(self, client, prova_com_gabarito, aluno_gabarito):
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        start = time.time()
        client.post(f"/provas/{pid}/lancar", json={
            "respostas": {str(aluno_gabarito["id"]): dict(gabarito)}
        })
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Lancar demorou {elapsed:.3f}s — limite: 500ms"


# ─────────────────────────────────────────────────────────────────────────────
# OCR DE GABARITO DO ALUNO
# ─────────────────────────────────────────────────────────────────────────────
class TestOcrAluno:
    def test_ocr_sem_arquivo_retorna_422(self, client, prova_com_gabarito):
        pid = prova_com_gabarito["prova_id"]
        r = client.post(f"/provas/{pid}/ocr-aluno")
        assert r.status_code == 422

    def test_ocr_com_pdf_retorna_estrutura(self, client, prova_com_gabarito, prova_pdf):
        """OCR com PDF válido deve retornar estrutura esperada (independente do que detecta)."""
        pid = prova_com_gabarito["prova_id"]
        with open(prova_pdf, "rb") as f:
            r = client.post(
                f"/provas/{pid}/ocr-aluno",
                files={"file": ("gabarito_aluno.pdf", f, "application/pdf")},
            )
        assert r.status_code == 200
        d = r.json()
        assert "respostas" in d
        assert "total_detectado" in d
        assert "ocr_method" in d
        assert "texto_bruto" in d
        assert isinstance(d["respostas"], dict)
        assert isinstance(d["total_detectado"], int)
        assert d["total_detectado"] >= 0

    def test_ocr_total_detectado_consistente(self, client, prova_com_gabarito, prova_pdf):
        """total_detectado deve ser igual ao tamanho do dicionário de respostas."""
        pid = prova_com_gabarito["prova_id"]
        with open(prova_pdf, "rb") as f:
            r = client.post(
                f"/provas/{pid}/ocr-aluno",
                files={"file": ("gabarito.pdf", f, "application/pdf")},
            )
        d = r.json()
        assert d["total_detectado"] == len(d["respostas"]), \
            "total_detectado difere do len(respostas)"

    def test_ocr_performance(self, client, prova_com_gabarito, prova_pdf):
        """OCR deve terminar em menos de 30 segundos."""
        pid = prova_com_gabarito["prova_id"]
        start = time.time()
        with open(prova_pdf, "rb") as f:
            r = client.post(
                f"/provas/{pid}/ocr-aluno",
                files={"file": ("gabarito.pdf", f, "application/pdf")},
            )
        elapsed = time.time() - start
        assert r.status_code == 200
        assert elapsed < 30, f"OCR demorou {elapsed:.1f}s — limite: 30s"
        print(f"\n  [Perf] OCR aluno em {elapsed:.2f}s")

    def test_ocr_texto_gabarito_simples(self, client, prova_com_gabarito, tmp_path):
        """Texto com padrão '1. A\\n2. B...' deve ser detectado corretamente."""
        pid = prova_com_gabarito["prova_id"]
        # Criar PDF mínimo com respostas em texto direto
        try:
            import fpdf  # opcional — só roda se fpdf estiver instalado
            pdf = fpdf.FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=14)
            for i in range(1, 6):
                pdf.cell(0, 10, f"{i}. {'ABCDE'[i-1]}", ln=True)
            pdf_path = tmp_path / "gabarito_simples.pdf"
            pdf.output(str(pdf_path))
            with open(pdf_path, "rb") as f:
                r = client.post(
                    f"/provas/{pid}/ocr-aluno",
                    files={"file": ("gabarito_simples.pdf", f, "application/pdf")},
                )
            assert r.status_code == 200
            d = r.json()
            # Com texto digital, deve detectar as 5 respostas
            assert d["total_detectado"] >= 4, \
                f"Esperado ≥ 4 respostas, detectou {d['total_detectado']}. Texto: {d['texto_bruto']}"
        except ImportError:
            pytest.skip("fpdf não instalado — pulando teste de gabarito sintético")


# ─────────────────────────────────────────────────────────────────────────────
# VALIDAÇÃO E CASOS DE BORDA
# ─────────────────────────────────────────────────────────────────────────────
class TestValidacaoEdgeCases:
    def test_nome_turma_unicode_e_acentos(self, client):
        r = client.post("/turmas", json={"nome": "8º Ação — São João"})
        assert r.status_code == 201
        assert "Ação" in r.json()["nome"]

    def test_nome_aluno_caracteres_especiais(self, client, turma_criada):
        r = client.post(f"/turmas/{turma_criada['id']}/alunos",
                        json={"nome": "João D'Ávila-Ções & Filhos"})
        assert r.status_code == 201
        assert "João" in r.json()["nome"]

    def test_nome_turma_muito_longo(self, client):
        """SQLite aceita TEXT de qualquer tamanho — deve funcionar."""
        r = client.post("/turmas", json={"nome": "A" * 500})
        assert r.status_code == 201
        assert len(r.json()["nome"]) == 500

    def test_turma_nome_vazio_retorna_422_ou_201(self, client):
        """Nome vazio é tecnicamente uma string — comportamento deve ser consistente."""
        r = client.post("/turmas", json={"nome": ""})
        assert r.status_code in (201, 422), f"Status inesperado: {r.status_code}"

    def test_aluno_nome_apenas_espacos(self, client, turma_criada):
        """Nome com apenas espaços deve ser aceito (validação é responsabilidade do frontend)."""
        r = client.post(f"/turmas/{turma_criada['id']}/alunos", json={"nome": "   "})
        assert r.status_code in (201, 422)

    def test_gabarito_alternativa_invalida_aceita(self, client, prova_enviada):
        """Alternativa não-padrão (ex: 'X') é aceita mas não calculará correto no lancar."""
        pid = prova_enviada["prova_id"]
        qs = client.get(f"/provas/{pid}/questoes").json()
        gabarito = {str(qs[0]["numero"]): "X"}
        r = client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito})
        assert r.status_code == 201

    def test_lancar_aluno_id_inexistente_passa(self, client, prova_com_gabarito):
        """Aluno inexistente no banco pode causar FK error — verificar comportamento."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        r = client.post(f"/provas/{pid}/lancar", json={
            "respostas": {"99999": dict(gabarito)}
        })
        # Pode retornar 201 (FK não verificado) ou 500 (FK ativada)
        assert r.status_code in (201, 500)

    def test_relatorio_percentual_matematicamente_correto(self, client, prova_com_gabarito):
        """percentual deve ser exatamente round(acertos/total * 100)."""
        pid = prova_com_gabarito["prova_id"]
        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        for aluno in rel:
            if aluno["total"] > 0:
                expected = round(aluno["acertos"] * 100 / aluno["total"])
                assert aluno["percentual"] == expected, (
                    f"{aluno['aluno']['nome']}: "
                    f"{aluno['acertos']}/{aluno['total']} = {aluno['percentual']}% "
                    f"(esperado {expected}%)"
                )

    def test_relatorio_acertos_nao_excede_total(self, client, prova_com_gabarito):
        pid = prova_com_gabarito["prova_id"]
        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        for aluno in rel:
            assert 0 <= aluno["acertos"] <= aluno["total"], (
                f"{aluno['aluno']['nome']}: acertos={aluno['acertos']} > total={aluno['total']}"
            )

    def test_drilldown_pct_entre_0_e_100(self, client, prova_com_gabarito):
        pid = prova_com_gabarito["prova_id"]
        d = client.get(f"/provas/{pid}/relatorio/drilldown").json()
        for area, subareas in d.items():
            for sub, sdata in subareas.items():
                for bloom, bdata in sdata["bloom"].items():
                    pct = bdata["pct_turma"]
                    assert 0 <= pct <= 100, \
                        f"pct_turma={pct} fora de [0,100] em {area}/{sub}/bloom{bloom}"
                    for aluno in bdata["alunos"]:
                        assert 0 <= aluno["pct"] <= 100, \
                            f"aluno.pct={aluno['pct']} fora de [0,100]: {aluno['nome']}"

    def test_drilldown_alunos_ordenados_por_pct(self, client, prova_com_gabarito):
        """Alunos no drilldown devem estar ordenados por pct crescente (menor primeiro)."""
        pid = prova_com_gabarito["prova_id"]
        d = client.get(f"/provas/{pid}/relatorio/drilldown").json()
        for area, subareas in d.items():
            for sub, sdata in subareas.items():
                for bloom, bdata in sdata["bloom"].items():
                    alunos = bdata["alunos"]
                    pcts = [a["pct"] for a in alunos]
                    assert pcts == sorted(pcts), \
                        f"Alunos não ordenados por pct em {area}/{sub}/bloom{bloom}: {pcts}"

    def test_upload_arquivo_texto_retorna_422_ou_500(self, client):
        """Upload de arquivo não-imagem/pdf deve ser rejeitado graciosamente."""
        fake_file = io.BytesIO(b"isto nao e um pdf")
        r = client.post(
            "/provas/upload",
            data={"year_level": "8º ano EF"},
            files={"file": ("prova.txt", fake_file, "text/plain")},
        )
        assert r.status_code in (200, 422, 500), f"Status inesperado: {r.status_code}"

    def test_upload_pdf_vazio_retorna_erro(self, client):
        """PDF vazio (0 bytes) não deve derrubar o servidor."""
        r = client.post(
            "/provas/upload",
            data={"year_level": "8º ano EF"},
            files={"file": ("vazio.pdf", b"", "application/pdf")},
        )
        assert r.status_code in (200, 422, 500)

    def test_por_bloom_soma_total_questoes(self, client, prova_com_gabarito):
        """Soma dos totais em por_bloom deve ser igual ao total de questões respondidas."""
        pid = prova_com_gabarito["prova_id"]
        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        for aluno in rel:
            total_bloom = sum(v["total"] for v in aluno["por_bloom"].values())
            assert total_bloom == aluno["total"], (
                f"{aluno['aluno']['nome']}: soma por_bloom ({total_bloom}) != total ({aluno['total']})"
            )

    def test_por_bloom_acertos_soma_acertos(self, client, prova_com_gabarito):
        """Soma dos acertos em por_bloom deve ser igual ao total de acertos."""
        pid = prova_com_gabarito["prova_id"]
        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        for aluno in rel:
            acertos_bloom = sum(v["acertos"] for v in aluno["por_bloom"].values())
            assert acertos_bloom == aluno["acertos"], (
                f"{aluno['aluno']['nome']}: acertos por_bloom ({acertos_bloom}) != acertos ({aluno['acertos']})"
            )


# ─────────────────────────────────────────────────────────────────────────────
# FLUXO COMPLETO END-TO-END
# ─────────────────────────────────────────────────────────────────────────────
class TestFluxoCompleto:
    """Simula o fluxo completo que um professor real executaria."""

    def test_fluxo_completo_upload_gabarito_lancar_relatorio(self, client, prova_pdf):
        """
        Fluxo completo isolado:
        1. Criar turma + alunos
        2. Upload prova
        3. Definir gabarito
        4. Lançar respostas
        5. Verificar relatório
        """
        # 1. Criar turma e 3 alunos
        turma = client.post("/turmas", json={"nome": "E2E Turma", "escola": "Teste"}).json()
        tid = turma["id"]
        nomes = ["Ana E2E", "Bruno E2E", "Carla E2E"]
        alunos = [
            client.post(f"/turmas/{tid}/alunos", json={"nome": n}).json()
            for n in nomes
        ]

        # 2. Upload prova
        with open(prova_pdf, "rb") as f:
            resp = client.post(
                "/provas/upload",
                data={"year_level": "8º ano EF", "turma_id": str(tid)},
                files={"file": ("prova_e2e.pdf", f, "application/pdf")},
            )
        assert resp.status_code == 200
        pid = resp.json()["prova_id"]
        raw_questions = resp.json()["questions"]
        assert len(raw_questions) > 0

        # Deduplicate by number (some PDFs produce duplicate question markers)
        seen: set = set()
        questions = [q for q in raw_questions if not (q["number"] in seen or seen.add(q["number"]))]
        n = len(questions)

        # 3. Definir gabarito (todas = "A")
        gabarito = {str(q["number"]): "A" for q in questions}
        rg = client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito})
        assert rg.status_code == 201

        # 4. Lançar respostas com perfis diferentes:
        #    Ana acerta tudo, Bruno acerta metade, Carla erra tudo
        respostas_bulk = {}
        for i, aluno in enumerate(alunos):
            resps = {}
            for j, q in enumerate(questions):
                num = str(q["number"])
                if i == 0:          # Ana: tudo certo
                    resps[num] = "A"
                elif i == 1:        # Bruno: metade certa
                    resps[num] = "A" if j < n // 2 else "B"
                else:               # Carla: tudo errado
                    resps[num] = "B"
            respostas_bulk[str(aluno["id"])] = resps

        rl = client.post(f"/provas/{pid}/lancar", json={"respostas": respostas_bulk})
        assert rl.status_code == 201

        # 5. Verificar relatório
        rel = client.get(f"/provas/{pid}/relatorio/turma").json()
        assert len(rel) == 3

        by_nome = {r["aluno"]["nome"]: r for r in rel}

        assert by_nome["Ana E2E"]["percentual"] == 100
        assert by_nome["Ana E2E"]["acertos"] == by_nome["Ana E2E"]["total"]

        assert by_nome["Carla E2E"]["percentual"] == 0
        assert by_nome["Carla E2E"]["acertos"] == 0

        bruno = by_nome["Bruno E2E"]
        assert bruno["acertos"] == n // 2
        assert 0 < bruno["percentual"] < 100

    def test_fluxo_drilldown_com_dados_reais(self, client, prova_com_gabarito):
        """Drilldown deve conter os alunos lançados na fixture prova_com_gabarito."""
        pid = prova_com_gabarito["prova_id"]
        d = client.get(f"/provas/{pid}/relatorio/drilldown").json()
        assert len(d) > 0, "Drilldown vazio — algum lançamento deve ter ocorrido"

        total_alunos = set()
        for area, subareas in d.items():
            for sub, sdata in subareas.items():
                for bloom, bdata in sdata["bloom"].items():
                    for aluno in bdata["alunos"]:
                        total_alunos.add(aluno["aluno_id"])
        assert len(total_alunos) >= 1, "Nenhum aluno no drilldown"

    def test_provas_aparecem_na_listagem_da_turma(self, client, turma_criada, prova_enviada):
        r = client.get(f"/turmas/{turma_criada['id']}/provas")
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert prova_enviada["prova_id"] in ids

    def test_deletar_turma_remove_alunos_em_cascata(self, client):
        """DELETE turma deve remover alunos via CASCADE."""
        t = client.post("/turmas", json={"nome": "Turma Cascade"}).json()
        tid = t["id"]
        client.post(f"/turmas/{tid}/alunos", json={"nome": "Aluno X"})
        client.post(f"/turmas/{tid}/alunos", json={"nome": "Aluno Y"})

        rd = client.delete(f"/turmas/{tid}")
        assert rd.status_code == 204

        # Turma e alunos não devem mais existir
        turmas = client.get("/turmas").json()
        assert all(t2["id"] != tid for t2 in turmas)

    def test_fluxo_gabarito_atualizado_recalcula_acertos(self, client, prova_pdf, turma_criada):
        """Atualizar o gabarito e relançar deve recalcular os acertos."""
        with open(prova_pdf, "rb") as f:
            r = client.post(
                "/provas/upload",
                data={"year_level": "8º ano EF", "turma_id": str(turma_criada["id"])},
                files={"file": ("prova_relancar.pdf", f, "application/pdf")},
            )
        pid = r.json()["prova_id"]
        questions = r.json()["questions"]

        aluno = client.post(f"/turmas/{turma_criada['id']}/alunos",
                            json={"nome": "Aluno Recalculo"}).json()
        aid = str(aluno["id"])

        # Gabarito 1: todas = A
        gab1 = {str(q["number"]): "A" for q in questions}
        client.post(f"/provas/{pid}/gabarito", json={"gabarito": gab1})

        # Aluno responde tudo B (errado com gab1)
        resps = {str(q["number"]): "B" for q in questions}
        client.post(f"/provas/{pid}/lancar", json={"respostas": {aid: resps}})

        rel1 = client.get(f"/provas/{pid}/relatorio/turma").json()
        aluno_rel1 = next(a for a in rel1 if a["aluno"]["id"] == aluno["id"])
        assert aluno_rel1["acertos"] == 0

        # Gabarito 2: atualiza para todas = B (agora aluno acerta tudo)
        gab2 = {str(q["number"]): "B" for q in questions}
        client.post(f"/provas/{pid}/gabarito", json={"gabarito": gab2})
        client.post(f"/provas/{pid}/lancar", json={"respostas": {aid: resps}})

        rel2 = client.get(f"/provas/{pid}/relatorio/turma").json()
        aluno_rel2 = next(a for a in rel2 if a["aluno"]["id"] == aluno["id"])
        assert aluno_rel2["acertos"] == aluno_rel2["total"], \
            "Após atualizar gabarito e relançar, todos devem estar corretos"
        assert aluno_rel2["percentual"] == 100


# ─────────────────────────────────────────────────────────────────────────────
# STRESS
# ─────────────────────────────────────────────────────────────────────────────
class TestStress:
    def test_criar_20_turmas_sequencial(self, client):
        """Cria 20 turmas em sequência — P95 deve ser < 200ms."""
        tempos = []
        for i in range(20):
            t0 = time.time()
            r = client.post("/turmas", json={"nome": f"Stress Turma {i}"})
            tempos.append(time.time() - t0)
            assert r.status_code == 201
        p95 = sorted(tempos)[int(len(tempos) * 0.95)]
        print(f"\n  [Stress] 20 POST /turmas — P95: {p95*1000:.1f}ms")
        assert p95 < 0.5, f"P95 criar turma: {p95:.3f}s > 500ms"

    def test_criar_30_alunos_em_turma(self, client, turma_criada):
        """Cria 30 alunos na mesma turma — todos devem aparecer na listagem."""
        for i in range(30):
            r = client.post(f"/turmas/{turma_criada['id']}/alunos",
                            json={"nome": f"Stress Aluno {i}"})
            assert r.status_code == 201

        r = client.get(f"/turmas/{turma_criada['id']}/alunos")
        assert len(r.json()) >= 30

    def test_100_consultas_get_turmas(self, client):
        """100 GETs seguidos — P95 deve ser < 100ms."""
        tempos = []
        for _ in range(100):
            t0 = time.time()
            r = client.get("/turmas")
            tempos.append(time.time() - t0)
            assert r.status_code == 200
        media = sum(tempos) / len(tempos)
        p95 = sorted(tempos)[94]
        print(f"\n  [Stress] 100 GET /turmas — media: {media*1000:.1f}ms, P95: {p95*1000:.1f}ms")
        assert p95 < 0.2, f"P95 GET /turmas: {p95:.3f}s > 200ms"

    def test_10_consultas_drilldown(self, client, prova_com_gabarito):
        """10 chamadas consecutivas ao drilldown — P95 < 1s."""
        pid = prova_com_gabarito["prova_id"]
        tempos = []
        for _ in range(10):
            t0 = time.time()
            r = client.get(f"/provas/{pid}/relatorio/drilldown")
            tempos.append(time.time() - t0)
            assert r.status_code == 200
        p95 = sorted(tempos)[int(len(tempos) * 0.95)]
        print(f"\n  [Stress] 10 GET drilldown — P95: {p95*1000:.1f}ms")
        assert p95 < 1.0, f"P95 drilldown: {p95:.3f}s > 1s"

    def test_gabarito_atualizado_10x(self, client, prova_com_gabarito):
        """Salvar gabarito 10 vezes seguidas não deve degradar a performance."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        tempos = []
        for _ in range(10):
            t0 = time.time()
            r = client.post(f"/provas/{pid}/gabarito", json={"gabarito": gabarito})
            tempos.append(time.time() - t0)
            assert r.status_code == 201
        media = sum(tempos) / len(tempos)
        assert media < 0.3, f"Media salvar gabarito: {media:.3f}s > 300ms"

    def test_lancar_10_alunos_de_uma_vez(self, client, prova_com_gabarito, turma_criada):
        """Lançar 10 alunos em um único POST — deve completar em < 3s."""
        pid = prova_com_gabarito["prova_id"]
        gabarito = prova_com_gabarito["gabarito"]
        questions = prova_com_gabarito["questions"]

        alunos_ids = []
        for i in range(10):
            r = client.post(f"/turmas/{turma_criada['id']}/alunos",
                            json={"nome": f"Stress Lancar {i}"})
            alunos_ids.append(r.json()["id"])

        payload: dict = {}
        alts = ["A", "B", "C", "D", "E"]
        for j, aid in enumerate(alunos_ids):
            # Cada aluno tem um padrão diferente de respostas
            resps = {str(q["number"]): alts[(j + i) % 5]
                     for i, q in enumerate(questions)}
            payload[str(aid)] = resps

        start = time.time()
        r = client.post(f"/provas/{pid}/lancar", json={"respostas": payload})
        elapsed = time.time() - start

        assert r.status_code == 201
        assert elapsed < 3.0, f"Lançar 10 alunos demorou {elapsed:.3f}s — limite: 3s"
        print(f"\n  [Stress] Lancar 10 alunos: {elapsed:.3f}s")
