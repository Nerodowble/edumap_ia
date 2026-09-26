"""Segmentação de questões (checklist A11)."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from classifier.segmenter import segment_questions  # noqa: E402


def test_questao_por_extenso_sozinha_na_linha():
    texto = """Questão 1
Quanto é dois mais dois, somando os números?
A) 3
B) 4
Questão 2
Qual é a capital do Brasil nos dias de hoje?
A) Rio
B) Brasília
"""
    qs = segment_questions(texto)
    assert [q["number"] for q in qs] == [1, 2]
    assert "capital" in qs[1]["stem"] and "capital" not in qs[0]["stem"]


def test_ordinal_questao_sozinha_na_linha():
    texto = "1ª Questão\nExplique o ciclo da água com suas palavras.\n2ª Questão\nDescreva o processo de fotossíntese.\n"
    assert [q["number"] for q in segment_questions(texto)] == [1, 2]


def test_lista_numerada_no_enunciado_nao_vira_questao():
    texto = """1. Qual a soma de 10 com 15, considerando os valores inteiros?
A) 20
B) 25
2. Qual o resultado de 3 vezes 4 em uma multiplicação simples?
A) 12
B) 7
3. Leia as afirmações abaixo sobre o sistema solar e responda:
1. O Sol é uma estrela do tipo anã amarela da sequência principal.
2. A Terra é o terceiro planeta a partir do Sol no sistema.
Quais estão corretas segundo a astronomia moderna?
A) Só a primeira
B) Ambas
"""
    qs = segment_questions(texto)
    assert [q["number"] for q in qs] == [1, 2, 3]
    assert "soma de 10" in qs[0]["stem"]          # Q1 real não foi substituída
    assert "Sol é uma estrela" in qs[2]["stem"]   # lista ficou dentro da Q3


def test_salto_pequeno_de_numeracao_aceito():
    """OCR que perdeu a questão 2: a 3 ainda é reconhecida."""
    texto = "1. Primeira pergunta com texto suficiente aqui?\n3. Terceira pergunta com texto suficiente aqui?\n"
    assert [q["number"] for q in segment_questions(texto)] == [1, 3]
