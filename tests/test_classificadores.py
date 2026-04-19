"""
Testes unitários dos classificadores — EduMap IA
Verifica qualidade das classificações de Bloom, Área e Subárea.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from classifier.bloom_classifier import classify_bloom
from classifier.area_classifier import classify_area
from classifier.subarea_classifier import classify_subarea


# ─────────────────────────────────────────────────────────────────────────────
# BLOOM TAXONOMY
# ─────────────────────────────────────────────────────────────────────────────
class TestBloomClassifier:
    """
    Testa detecção de nível cognitivo via verbos.
    Bloom revisado: 1=Lembrar, 2=Compreender, 3=Aplicar,
                    4=Analisar, 5=Avaliar, 6=Criar
    """

    @pytest.mark.parametrize("texto,nivel,nome", [
        ("Defina o conceito de equação do primeiro grau.", 1, "Lembrar"),
        ("Cite três exemplos de mamíferos encontrados no Brasil.", 1, "Lembrar"),
        ("Liste as capitais dos estados do Brasil.", 1, "Lembrar"),
        ("Identifique o substantivo próprio na frase.", 1, "Lembrar"),
        ("Nomeie os planetas do sistema solar.", 1, "Lembrar"),
    ])
    def test_bloom_1_lembrar(self, texto, nivel, nome):
        lvl, nm, verb = classify_bloom(texto)
        assert lvl == nivel, f"Texto: '{texto}'\n  Esperado: {nivel} ({nome})\n  Obtido: {lvl} ({nm}) [verbo: {verb}]"

    @pytest.mark.parametrize("texto,nivel,nome", [
        ("Explique o processo de fotossíntese com suas próprias palavras.", 2, "Compreender"),
        ("Descreva as principais causas da Proclamação da República.", 2, "Compreender"),
        ("Resuma o texto lido indicando a ideia principal.", 2, "Compreender"),
        ("Interprete o gráfico e indique a tendência observada.", 2, "Compreender"),
    ])
    def test_bloom_2_compreender(self, texto, nivel, nome):
        lvl, nm, verb = classify_bloom(texto)
        assert lvl == nivel, f"Texto: '{texto}'\n  Esperado: {nivel} ({nome})\n  Obtido: {lvl} ({nm}) [verbo: {verb}]"

    @pytest.mark.parametrize("texto,nivel,nome", [
        ("Calcule a área do retângulo com base 12 cm e altura 5 cm.", 3, "Aplicar"),
        ("Resolva a equação: 3x - 9 = 15", 3, "Aplicar"),
        ("Use a fórmula de Bhaskara para encontrar as raízes da equação.", 3, "Aplicar"),
        ("Demonstre como calcular o volume do cubo.", 3, "Aplicar"),
    ])
    def test_bloom_3_aplicar(self, texto, nivel, nome):
        lvl, nm, verb = classify_bloom(texto)
        assert lvl == nivel, f"Texto: '{texto}'\n  Esperado: {nivel} ({nome})\n  Obtido: {lvl} ({nm}) [verbo: {verb}]"

    @pytest.mark.parametrize("texto,nivel,nome", [
        ("Compare as duas equações e analise as diferenças entre elas.", 4, "Analisar"),
        ("Examine os dados e diferencie os tipos de energia apresentados.", 4, "Analisar"),
        ("Investigue as causas da Segunda Guerra Mundial.", 4, "Analisar"),
        ("Decomponha a frase em seus constituintes sintáticos.", 4, "Analisar"),
    ])
    def test_bloom_4_analisar(self, texto, nivel, nome):
        lvl, nm, verb = classify_bloom(texto)
        assert lvl == nivel, f"Texto: '{texto}'\n  Esperado: {nivel} ({nome})\n  Obtido: {lvl} ({nm}) [verbo: {verb}]"

    @pytest.mark.parametrize("texto,nivel,nome", [
        ("Avalie e justifique se a frase está correta do ponto de vista gramatical.", 5, "Avaliar"),
        ("Julgue a pertinência dos argumentos apresentados no texto.", 5, "Avaliar"),
        ("Critique a solução proposta e defenda sua posição com argumentos.", 5, "Avaliar"),
    ])
    def test_bloom_5_avaliar(self, texto, nivel, nome):
        lvl, nm, verb = classify_bloom(texto)
        assert lvl == nivel, f"Texto: '{texto}'\n  Esperado: {nivel} ({nome})\n  Obtido: {lvl} ({nm}) [verbo: {verb}]"

    @pytest.mark.parametrize("texto,nivel,nome", [
        ("Crie um problema matemático original envolvendo equações.", 6, "Criar"),
        ("Elabore um texto argumentativo sobre o tema proposto.", 6, "Criar"),
        ("Proponha um experimento para testar a hipótese apresentada.", 6, "Criar"),
        ("Formule uma solução inovadora para o problema ambiental descrito.", 6, "Criar"),
    ])
    def test_bloom_6_criar(self, texto, nivel, nome):
        lvl, nm, verb = classify_bloom(texto)
        assert lvl == nivel, f"Texto: '{texto}'\n  Esperado: {nivel} ({nome})\n  Obtido: {lvl} ({nm}) [verbo: {verb}]"

    def test_bloom_sem_verbo_retorna_default(self):
        """Texto sem verbo cognitivo retorna o default do classificador (Compreender)."""
        lvl, _, verb = classify_bloom("A B C D")
        assert lvl in (0, 2), f"Esperado 0 ou 2 (default), obteve {lvl}"

    def test_bloom_retorna_verbo_detectado(self):
        lvl, nome, verbo = classify_bloom("Calcule a raiz da equação.")
        assert lvl == 3
        assert verbo != "", "Verbo não deve ser vazio quando nível > 0"


# ─────────────────────────────────────────────────────────────────────────────
# ÁREA DO CONHECIMENTO
# ─────────────────────────────────────────────────────────────────────────────
class TestAreaClassifier:

    @pytest.mark.parametrize("texto,area", [
        ("Calcule a equação do segundo grau com coeficientes a b c", "matematica"),
        ("Resolva o sistema de equações lineares com duas incógnitas", "matematica"),
        ("Determine a área do triângulo retângulo com catetos de 3 e 4 cm", "matematica"),
    ])
    def test_matematica(self, texto, area):
        key, conf, _ = classify_area(texto)
        assert key == area, f"Esperado '{area}', obteve '{key}' — conf={conf:.2f}"
        assert conf > 0

    @pytest.mark.parametrize("texto,area", [
        ("A fotossíntese é o processo pelo qual as plantas produzem glicose usando luz solar e CO2", "ciencias"),
        ("A célula é a unidade básica da vida formada por membrana núcleo e citoplasma", "ciencias"),
        ("A fotossíntese realiza-se nas folhas através da clorofila e produz oxigênio", "ciencias"),
    ])
    def test_ciencias(self, texto, area):
        key, conf, _ = classify_area(texto)
        assert key == area, f"Esperado '{area}', obteve '{key}' — conf={conf:.2f}"

    @pytest.mark.parametrize("texto,area", [
        ("Identifique o substantivo próprio e o verbo na oração", "portugues"),
        ("A concordância verbal e nominal são regras gramaticais essenciais", "portugues"),
        ("O texto dissertativo-argumentativo exige coesão e coerência", "portugues"),
    ])
    def test_portugues(self, texto, area):
        key, conf, _ = classify_area(texto)
        assert key == area, f"Esperado '{area}', obteve '{key}' — conf={conf:.2f}"

    @pytest.mark.parametrize("texto,area", [
        ("A Proclamação da República brasileira ocorreu em 1889", "historia"),
        ("A abolição da escravatura foi um marco histórico do Segundo Reinado", "historia"),
        ("Analise as causas da Revolução Francesa e seus impactos na Europa", "historia"),
    ])
    def test_historia(self, texto, area):
        key, conf, _ = classify_area(texto)
        assert key == area, f"Esperado '{area}', obteve '{key}' — conf={conf:.2f}"

    def test_confianca_range_valido(self):
        """Confiança deve estar entre 0 e 1."""
        _, conf, _ = classify_area("calcule a equação")
        assert 0.0 <= conf <= 1.0

    def test_texto_vazio_nao_quebra(self):
        """Texto vazio não deve lançar exceção."""
        key, conf, _ = classify_area("")
        assert isinstance(key, str)
        assert isinstance(conf, float)


# ─────────────────────────────────────────────────────────────────────────────
# SUBÁREA
# ─────────────────────────────────────────────────────────────────────────────
class TestSubareaClassifier:

    @pytest.mark.parametrize("texto,area,subarea_key", [
        ("resolva a equação incógnita fatoração polinômio", "matematica", "algebra"),
        ("calcule área triângulo ângulos hipotenusa volume", "matematica", "geometria"),
        ("média moda mediana probabilidade frequência gráfico", "matematica", "estatistica"),
        ("fração porcentagem potência mmc mdc números inteiros", "matematica", "aritmetica"),
    ])
    def test_subarea_matematica(self, texto, area, subarea_key):
        key, label = classify_subarea(texto, area)
        assert key == subarea_key, (
            f"Área: {area} | Texto: '{texto[:40]}…'\n"
            f"  Esperado: '{subarea_key}'\n"
            f"  Obtido:   '{key}' ({label})"
        )

    @pytest.mark.parametrize("texto,area,subarea_key", [
        ("substantivo adjetivo pronome verbo concordância", "portugues", "gramatica"),
        ("texto dissertativo argumentativo coesão coerência redação", "portugues", "interpretacao"),
        ("leitura interpretação inferência compreensão textual", "portugues", "interpretacao"),
    ])
    def test_subarea_portugues(self, texto, area, subarea_key):
        key, label = classify_subarea(texto, area)
        assert key == subarea_key, (
            f"Área: {area} | Texto: '{texto[:40]}…'\n"
            f"  Esperado: '{subarea_key}'\n"
            f"  Obtido:   '{key}' ({label})"
        )

    def test_subarea_retorna_label_nao_vazio(self):
        key, label = classify_subarea("equação raiz polinômio", "matematica")
        assert label != "", "Label da subárea não deve ser vazio"

    def test_subarea_area_desconhecida(self):
        """Área desconhecida deve retornar geral sem quebrar."""
        key, label = classify_subarea("qualquer texto", "area_inexistente")
        assert isinstance(key, str)
        assert isinstance(label, str)


# ─────────────────────────────────────────────────────────────────────────────
# QUALIDADE GERAL
# ─────────────────────────────────────────────────────────────────────────────
class TestQualidadeGeral:
    """Testa a prova de exemplo completa e mede qualidade das classificações."""

    QUESTOES_PROVA = [
        # (enunciado, bloom_esperado, area_esperada)
        ("Defina o que é uma equação do 1 grau e escreva um exemplo", 1, "matematica"),
        ("Resolva a equação abaixo e encontre o valor de x: 3x - 9 = 15", 3, "matematica"),
        ("Calcule a área do retângulo com base 12 cm e altura 5 cm", 3, "matematica"),
        ("Analise as duas equações e compare os resultados", 4, "matematica"),
        ("Qual das alternativas apresenta um substantivo próprio", 1, "portugues"),
        ("Leia o trecho e explique em suas próprias palavras a ideia principal", 2, "portugues"),
        ("Avalie e justifique se a frase está correta do ponto de vista da concordância", 5, "portugues"),
        ("Assinale a alternativa que define corretamente fotossíntese", 1, "ciencias"),
        ("Descreva o que acontecerá com a fotossíntese e o desenvolvimento da planta", 2, "ciencias"),
        ("Em que ano foi proclamada a República do Brasil", 1, "historia"),
        ("Analise as principais causas que levaram à Proclamação da República", 4, "historia"),
        ("Avalie a importância da abolição da escravatura para a Proclamação da República", 5, "historia"),
    ]

    def test_bloom_accuracy(self):
        """Taxa de acerto do Bloom deve ser ≥ 70% na prova de exemplo."""
        acertos = 0
        for enunciado, bloom_esp, _ in self.QUESTOES_PROVA:
            lvl, _, _ = classify_bloom(enunciado)
            if lvl == bloom_esp:
                acertos += 1

        taxa = acertos / len(self.QUESTOES_PROVA)
        print(f"\n  [Bloom] accuracy: {acertos}/{len(self.QUESTOES_PROVA)} = {taxa:.0%}")
        assert taxa >= 0.70, (
            f"Bloom accuracy abaixo do esperado: {taxa:.0%} (mínimo: 70%)\n"
            "  → Considere ampliar o dicionário de verbos em verbos_bloom.json"
        )

    def test_area_accuracy(self):
        """Taxa de acerto de área deve ser ≥ 80% na prova de exemplo."""
        acertos = 0
        for enunciado, _, area_esp in self.QUESTOES_PROVA:
            key, _, _ = classify_area(enunciado)
            if key == area_esp:
                acertos += 1

        taxa = acertos / len(self.QUESTOES_PROVA)
        print(f"\n  [Area] accuracy: {acertos}/{len(self.QUESTOES_PROVA)} = {taxa:.0%}")
        assert taxa >= 0.80, (
            f"Área accuracy abaixo do esperado: {taxa:.0%} (mínimo: 80%)\n"
            "  → Considere ampliar vocabulário_areas.json"
        )
