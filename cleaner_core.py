from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_DISPONIVEL = True
except ImportError:
    fuzz = None
    process = None
    RAPIDFUZZ_DISPONIVEL = False


ARQUIVO_ENTRADA_PADRAO = "banco_questoes.js"
ARQUIVO_SAIDA_JS_PADRAO = "banco_questoes_limpo.js"
ARQUIVO_SAIDA_REMOVIDAS_PADRAO = "questoes_removidas.txt"
ARQUIVO_SAIDA_CONFLITOS_PADRAO = "questoes_conflitantes.txt"
ARQUIVO_SAIDA_CONFLITOS_RESOLVIDOS_PADRAO = "questoes_conflitantes_resolvidas.txt"
ARQUIVO_SAIDA_POSSIVEIS_PADRAO = "questoes_possiveis_duplicatas.txt"
ARQUIVO_SAIDA_POSSIVEIS_RESOLVIDOS_PADRAO = "questoes_possiveis_duplicatas_resolvidas.txt"

DECISAO_DUPLICADA = "DUPLICADA"
DECISAO_NAO_DUPLICADA = "NAO_DUPLICADA"
DECISAO_REVISAR = "REVISAR"
DECISOES_VALIDAS = {DECISAO_DUPLICADA, DECISAO_NAO_DUPLICADA}
DECISOES_POSSIVEIS_VALIDAS = {DECISAO_DUPLICADA, DECISAO_NAO_DUPLICADA, DECISAO_REVISAR}

# Limiares de detecção.
# DUPLICATA DE ALTA CONFIANÇA: pode ser removida automaticamente.
# Para isso, exigimos enunciado e alternativas essencialmente idênticos e
# gabarito equivalente. Metadados diferentes (ex.: banca/ano ausente) não
# impedem a remoção.
LIMIAR_AUTO_PERGUNTA = 0.98
LIMIAR_AUTO_OPCOES = 0.98
LIMIAR_AUTO_GABARITO = 0.98

# Candidatos fortes: revisão humana, salvo se também satisfizerem os critérios
# acima de alta confiança.
LIMIAR_FORTE = 0.93
LIMIAR_POSSIVEL = 0.84
LIMIAR_GRUPO_FORTE = 0.93

ROTULOS_BANCA = re.compile(
    r"^\s*\(?[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9][^\)]{0,80}\b(20\d{2}|19\d{2})\)?\s*",
    re.IGNORECASE,
)


class ErroDecisaoConflito(ValueError):
    """Erro em uma decisão escrita pelo usuário no relatório de conflitos."""


def normalizar_texto(texto: Any, remover_identificacao_banca: bool = False) -> str:
    texto = "" if texto is None else str(texto)
    texto = unicodedata.normalize("NFKC", texto)
    texto = texto.replace("\u00A0", " ")
    texto = texto.replace("–", "-").replace("—", "-").replace("−", "-")
    if remover_identificacao_banca:
        # Remove marcadores comuns no início do enunciado: (ENARE 2022),
        # (USP-SP 2025), (UFRJ 2024), etc. Isso não altera o texto original.
        texto = ROTULOS_BANCA.sub("", texto)
    texto = re.sub(r"\s+", " ", texto)
    texto = re.sub(r"[\u2018\u2019]", "'", texto)
    texto = re.sub(r'[\u201C\u201D]', '"', texto)
    return texto.strip().casefold()


def normalizar_pergunta(texto: Any) -> str:
    return normalizar_texto(texto, remover_identificacao_banca=False)


def assinatura_objeto(questao: dict[str, Any]) -> str:
    return json.dumps(
        questao,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def id_grupo_conflito(grupo: list[dict[str, Any]]) -> str:
    # Compatibilidade: quando todas as questões do grupo possuem exatamente
    # a mesma pergunta normalizada, preservamos o esquema antigo de ID,
    # permitindo reaproveitar decisões já feitas pelo usuário.
    chaves = [normalizar_pergunta(item["questao"].get("pergunta", "")) for item in grupo]
    if chaves and len(set(chaves)) == 1:
        return id_grupo_por_texto(chaves[0])

    # Para grupos novos (similaridade), o ID incorpora posições e conteúdo.
    material = "|".join(
        f"{item['indice']}:{normalizar_pergunta(item['questao'].get('pergunta', ''))}"
        for item in grupo
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:10].upper()
    return f"CONFLITO-{digest}"


def id_grupo_por_texto(chave: str) -> str:
    digest = hashlib.sha256(chave.encode("utf-8")).hexdigest()[:10].upper()
    return f"CONFLITO-{digest}"


def id_possivel_por_par(indice_a: int, indice_b: int) -> str:
    a, b = sorted((indice_a, indice_b))
    material = f"{a}:{b}"
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:10].upper()
    return f"POSSIVEL-{digest}"


def validar_indice_par(par: str) -> tuple[int, int]:
    try:
        a_str, b_str = par.split("-")
        a, b = int(a_str), int(b_str)
    except Exception as erro:
        raise ValueError(f"Par inválido: {par}") from erro
    if a == b or a < 1 or b < 1:
        raise ValueError(f"Par inválido: {par}")
    return tuple(sorted((a, b)))


def rotulo_ocorrencia(indice_zero_based: int) -> str:
    numero = indice_zero_based + 1
    letras = ""
    while numero:
        numero, resto = divmod(numero - 1, 26)
        letras = chr(ord("A") + resto) + letras
    return letras


def extrair_lista_js(conteudo: str) -> list[dict[str, Any]]:
    inicio = conteudo.find("[")
    fim = conteudo.rfind("]")
    if inicio == -1 or fim == -1 or fim < inicio:
        raise ValueError("Não foi possível localizar a lista de questões entre '[' e ']'.")
    json_str = conteudo[inicio : fim + 1]
    try:
        banco = json.loads(json_str)
    except json.JSONDecodeError as erro:
        raise ValueError(
            "O conteúdo entre '[' e ']' não é um JSON válido. "
            f"Linha {erro.lineno}, coluna {erro.colno}: {erro.msg}"
        ) from erro
    if not isinstance(banco, list):
        raise ValueError("A estrutura encontrada no arquivo não é uma lista.")
    for indice, questao in enumerate(banco, start=1):
        if not isinstance(questao, dict):
            raise ValueError(f"A questão na posição {indice} não é um objeto JSON.")
    return banco


def formatar_valor(valor: Any) -> str:
    if valor is None:
        return "N/A"
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, indent=2)
    return str(valor)


def similaridade_strings(a: Any, b: Any, remover_identificacao_banca: bool = False) -> float:
    a_norm = normalizar_texto(a, remover_identificacao_banca)
    b_norm = normalizar_texto(b, remover_identificacao_banca)
    if not a_norm and not b_norm:
        return 1.0
    if not a_norm or not b_norm:
        return 0.0
    if a_norm == b_norm:
        return 1.0
    if fuzz is not None:
        return fuzz.ratio(a_norm, b_norm) / 100.0
    import difflib
    return difflib.SequenceMatcher(None, a_norm, b_norm, autojunk=False).ratio()


def flatten_options(valor: Any) -> list[str]:
    if not isinstance(valor, list):
        return [] if valor in (None, "") else [normalizar_texto(valor)]
    return [normalizar_texto(v) for v in valor]


def similaridade_opcoes(a: Any, b: Any) -> float:
    op_a = flatten_options(a)
    op_b = flatten_options(b)
    if not op_a and not op_b:
        return 1.0
    if not op_a or not op_b:
        return 0.0
    # Comparação ordenada: preserva a posição das alternativas, mas permite
    # pequenas diferenças de redação em cada opção.
    n = max(len(op_a), len(op_b))
    soma = 0.0
    for i in range(n):
        if i >= len(op_a) or i >= len(op_b):
            soma += 0.0
        else:
            soma += similaridade_strings(op_a[i], op_b[i])
    return soma / n


def normalizar_gabarito(valor: Any) -> str:
    texto = normalizar_texto(valor)
    # "gabarito oficial: opção D" ≈ "opção d"
    texto = re.sub(r"\bgabarito\s+oficial\s*:\s*", "", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def similaridade_gabarito(a: Any, b: Any) -> float:
    a_norm = normalizar_gabarito(a)
    b_norm = normalizar_gabarito(b)
    if a_norm == b_norm:
        return 1.0
    if not a_norm or not b_norm:
        return 0.0
    if fuzz is not None:
        return fuzz.ratio(a_norm, b_norm) / 100.0
    # Fallback sem dependência externa. Mais lento, mas funcional.
    import difflib
    return difflib.SequenceMatcher(None, a_norm, b_norm, autojunk=False).ratio()


def similaridade_lista(a: Any, b: Any) -> float:
    la = [normalizar_texto(x) for x in a] if isinstance(a, list) else []
    lb = [normalizar_texto(x) for x in b] if isinstance(b, list) else []
    if not la and not lb:
        return 1.0
    if not la or not lb:
        return 0.0
    # Jaccard em tokens/listas para temas e classificações.
    sa, sb = set(la), set(lb)
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


def comparar_questoes(qa: dict[str, Any], qb: dict[str, Any]) -> dict[str, float | str]:
    pergunta = similaridade_strings(
        qa.get("pergunta", ""), qb.get("pergunta", ""), remover_identificacao_banca=True
    )
    opcoes = similaridade_opcoes(qa.get("opcoes"), qb.get("opcoes"))
    gabarito = similaridade_gabarito(qa.get("gabarito"), qb.get("gabarito"))
    temas = similaridade_lista(qa.get("temas"), qb.get("temas"))
    area = similaridade_strings(qa.get("grandeArea", ""), qb.get("grandeArea", ""))

    # O enunciado e as alternativas dominam a pontuação; gabarito/tema/área
    # servem como confirmação estrutural, não como decisão isolada.
    geral = (
        pergunta * 0.50
        + opcoes * 0.35
        + gabarito * 0.10
        + temas * 0.03
        + area * 0.02
    )

    if geral >= LIMIAR_FORTE:
        classificacao = "FORTE CANDIDATA A DUPLICATA"
    elif geral >= LIMIAR_POSSIVEL:
        classificacao = "POSSÍVEL DUPLICATA"
    else:
        classificacao = "BAIXA SEMELHANÇA"

    return {
        "geral": geral,
        "pergunta": pergunta,
        "opcoes": opcoes,
        "gabarito": gabarito,
        "temas": temas,
        "area": area,
        "classificacao": classificacao,
    }


def e_duplicata_alta_confianca(analise: dict[str, float | str]) -> bool:
    """Classifica como duplicata automática somente quando os elementos centrais
    da questão são praticamente iguais.

    Isso permite remover casos como:
    - uma versão com '(ENARE 2022)' e outra sem a identificação da banca;
    - diferenças de grandeArea, bloco ou outros metadados;
    - pequenas diferenças editoriais que não alteram o conteúdo da questão.
    """
    return (
        float(analise["pergunta"]) >= LIMIAR_AUTO_PERGUNTA
        and float(analise["opcoes"]) >= LIMIAR_AUTO_OPCOES
        and float(analise["gabarito"]) >= LIMIAR_AUTO_GABARITO
    )


def qualidade_questao(questao: dict[str, Any]) -> tuple[int, int, int]:
    """Pontuação simples para escolher qual ocorrência preservar automaticamente.

    Priorizamos a questão que contém mais informação útil no banco, sem
    alterar o conteúdo de nenhuma ocorrência.
    """
    campos = (
        "bloco",
        "temas",
        "tipo",
        "grandeArea",
        "informacoesComplementares",
    )
    preenchidos = sum(bool(questao.get(c)) for c in campos)
    tamanho_info = sum(len(str(questao.get(c, ""))) for c in campos)
    tamanho_total = len(assinatura_objeto(questao))
    return preenchidos, tamanho_info, tamanho_total


def construir_chave_exata(questao: dict[str, Any]) -> str:
    return normalizar_pergunta(questao.get("pergunta", ""))


def limpar_automatico_integral(
    banco: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    unicas: list[dict[str, Any]] = []
    removidas: list[dict[str, Any]] = []
    assinaturas_vistas: dict[str, int] = {}
    for indice, questao in enumerate(banco, start=1):
        assinatura = assinatura_objeto(questao)
        if assinatura in assinaturas_vistas:
            removidas.append(
                {
                    "indice_original": indice,
                    "indice_mantida": assinaturas_vistas[assinatura],
                    "motivo": "Questão integralmente idêntica a uma ocorrência anterior.",
                    "questao": questao,
                }
            )
            continue
        assinaturas_vistas[assinatura] = indice
        unicas.append(questao)
    return unicas, removidas


def imprimir_progresso(etapa: str, atual: int, total: int, inicio: float, extra: str = "") -> None:
    percentual = (atual / total * 100.0) if total else 100.0
    decorrido = time.perf_counter() - inicio
    sufixo = f" | {extra}" if extra else ""
    print(
        f"\r  {etapa}: {atual}/{total} ({percentual:5.1f}%) "
        f"| {decorrido:6.1f}s{sufixo}",
        end="",
        flush=True,
    )


def encerrar_linha_progresso() -> None:
    print()


def gerar_pares_candidatos_por_pergunta(
    banco: list[dict[str, Any]],
    score_cutoff: float,
    limite_por_questao: int | None = None,
    etapa: str = "Busca de candidatos",
) -> list[tuple[int, int, float]]:
    """Localiza pares promissores com progresso visível e sem fallback silencioso caro."""
    chaves = [
        normalizar_texto(q.get("pergunta", ""), remover_identificacao_banca=True)
        for q in banco
    ]
    total = len(chaves)
    inicio = time.perf_counter()
    pares: set[tuple[int, int]] = set()
    scores: dict[tuple[int, int], float] = {}

    if process is not None and fuzz is not None:
        escolhas = {i: chaves[i] for i in range(total) if chaves[i]}
        limite = limite_por_questao if limite_por_questao is not None else len(escolhas)
        for i, chave in enumerate(chaves):
            if not chave:
                continue
            resultados = process.extract(
                chave,
                escolhas,
                scorer=fuzz.ratio,
                score_cutoff=score_cutoff * 100.0,
                limit=limite + 1,
            )
            for _, score, j in resultados:
                j = int(j)
                if j == i:
                    continue
                a, b = sorted((i, j))
                if a == b:
                    continue
                chave_par = (a, b)
                pares.add(chave_par)
                scores[chave_par] = max(scores.get(chave_par, 0.0), score / 100.0)

            if (i + 1) % 10 == 0 or i == total - 1:
                imprimir_progresso(etapa, i + 1, total, inicio, f"pares candidatos: {len(pares)}")
        encerrar_linha_progresso()
        return [(a, b, scores[(a, b)]) for a, b in sorted(pares)]

    # Fallback explícito: bloqueio por tokens + SequenceMatcher somente nos pares
    # que compartilham termos relevantes. Isso evita a explosão combinatória.
    indice_tokens: dict[str, set[int]] = {}
    for i, chave in enumerate(chaves):
        tokens = {t for t in re.findall(r"\b[\wÀ-ÿ]{5,}\b", chave) if len(t) >= 5}
        for token in tokens:
            indice_tokens.setdefault(token, set()).add(i)

    print("  AVISO: RapidFuzz não está instalado; usando modo de fallback por tokens.")
    print("  Para máxima velocidade, instale com: pip install rapidfuzz")

    for i, chave in enumerate(chaves):
        if not chave:
            if (i + 1) % 10 == 0 or i == total - 1:
                imprimir_progresso(etapa, i + 1, total, inicio, f"pares candidatos: {len(pares)}")
            continue
        tokens = {t for t in re.findall(r"\b[\wÀ-ÿ]{5,}\b", chave) if len(t) >= 5}
        vizinhos: set[int] = set()
        for token in tokens:
            vizinhos.update(indice_tokens.get(token, ()))
        for j in vizinhos:
            if j <= i:
                continue
            score = similaridade_strings(chaves[i], chaves[j], False)
            if score >= score_cutoff:
                par = (i, j)
                pares.add(par)
                scores[par] = score
        if (i + 1) % 10 == 0 or i == total - 1:
            imprimir_progresso(etapa, i + 1, total, inicio, f"pares candidatos: {len(pares)}")
    encerrar_linha_progresso()
    return [(a, b, scores[(a, b)]) for a, b in sorted(pares)]


def limpar_automatico_alta_confianca(
    banco: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[list[dict[str, Any]]]]:
    """Remove duplicatas de alta confiança usando busca de candidatos otimizada."""
    n = len(banco)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Primeiro agrupamos perguntas que ficam exatamente iguais após a
    # normalização e remoção da identificação da banca. Isso captura casos
    # como "(ENARE 2022) ..." versus "..." sem qualquer busca difusa.
    pares: list[tuple[int, int, float]] = []
    por_chave: dict[str, list[int]] = {}
    for i, q in enumerate(banco):
        chave = normalizar_texto(q.get("pergunta", ""), remover_identificacao_banca=True)
        if chave:
            por_chave.setdefault(chave, []).append(i)
    for indices in por_chave.values():
        if len(indices) > 1:
            base = indices[0]
            for j in indices[1:]:
                pares.append((base, j, 1.0))

    pares_existentes = {(a, b) for a, b, _ in pares}
    restantes = [i for i in range(len(banco)) if len(por_chave.get(normalizar_texto(banco[i].get("pergunta", ""), True), [])) <= 1]
    if restantes:
        banco_restante = [banco[i] for i in restantes]
        pares_restantes = gerar_pares_candidatos_por_pergunta(
            banco_restante, LIMIAR_AUTO_PERGUNTA, limite_por_questao=20, etapa="Alta confiança"
        )
        for a, b, score in pares_restantes:
            pares.append((restantes[a], restantes[b], score))


    for i, j, _ in pares:
        analise = comparar_questoes(banco[i], banco[j])
        if e_duplicata_alta_confianca(analise):
            union(i, j)

    grupos_indices: dict[int, list[int]] = {}
    for idx in range(n):
        grupos_indices.setdefault(find(idx), []).append(idx)

    remocoes: set[int] = set()
    removidas: list[dict[str, Any]] = []
    grupos_auto: list[list[dict[str, Any]]] = []

    for indices in grupos_indices.values():
        if len(indices) <= 1:
            continue

        indices = sorted(indices)
        grupo = [{"indice": i + 1, "questao": banco[i]} for i in indices]
        grupos_auto.append(grupo)

        mantida_idx = max(indices, key=lambda i: (qualidade_questao(banco[i]), -i))
        for i in indices:
            if i == mantida_idx:
                continue
            remocoes.add(i)
            removidas.append({
                "indice_original": i + 1,
                "indice_mantida": mantida_idx + 1,
                "motivo": (
                    "Duplicata de alta confiança: enunciado, alternativas e gabarito "
                    "são essencialmente equivalentes; diferenças de metadados não "
                    "impediram a identificação."
                ),
                "questao": banco[i],
            })

    novo_banco = [q for i, q in enumerate(banco) if i not in remocoes]
    grupos_auto.sort(key=lambda g: g[0]["indice"])
    removidas.sort(key=lambda x: x["indice_original"])
    return novo_banco, removidas, grupos_auto

def construir_candidatos_similaridade(
    banco: list[dict[str, Any]],
) -> tuple[list[list[dict[str, Any]]], list[dict[str, Any]]]:
    """Encontra pares semelhantes usando busca otimizada de candidatos."""
    candidatos: list[dict[str, Any]] = []
    n = len(banco)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Localiza apenas candidatos com enunciado >= 78%.
    pares = gerar_pares_candidatos_por_pergunta(
        banco, 0.78, limite_por_questao=30, etapa="Possíveis duplicatas"
    )

    for i, j, pergunta_rapida in pares:
        qa, qb = banco[i], banco[j]
        if assinatura_objeto(qa) == assinatura_objeto(qb):
            continue
        analise = comparar_questoes(qa, qb)
        if analise["geral"] >= LIMIAR_POSSIVEL:
            candidatos.append({
                "a": i + 1,
                "b": j + 1,
                **analise,
            })
        if analise["geral"] >= LIMIAR_GRUPO_FORTE:
            union(i, j)

    grupos_por_raiz: dict[int, list[int]] = {}
    for idx in range(n):
        raiz = find(idx)
        grupos_por_raiz.setdefault(raiz, []).append(idx + 1)

    grupos = []
    for posicoes in grupos_por_raiz.values():
        if len(posicoes) <= 1:
            continue
        grupo = [
            {"indice": pos, "questao": banco[pos - 1]}
            for pos in sorted(posicoes)
        ]
        grupos.append(grupo)

    grupos.sort(key=lambda g: g[0]["indice"])
    candidatos.sort(key=lambda c: (-float(c["geral"]), c["a"], c["b"]))
    return grupos, candidatos

def escrever_relatorio_possiveis(
    caminho: Path,
    candidatos: list[dict[str, Any]],
    grupos_conflitos: list[list[dict[str, Any]]],
    banco: list[dict[str, Any]],
    decisoes_existentes: dict[str, dict[str, str]],
) -> None:
    """Gera um segundo arquivo de decisões, inicialmente em [REVISAR]."""
    pares_fortes: set[tuple[int, int]] = set()
    for grupo in grupos_conflitos:
        posicoes = [item["indice"] for item in grupo]
        for i in range(len(posicoes)):
            for j in range(i + 1, len(posicoes)):
                pares_fortes.add((posicoes[i], posicoes[j]))

    restantes = [
        c for c in candidatos
        if (min(c["a"], c["b"]), max(c["a"], c["b"])) not in pares_fortes
    ]

    with caminho.open("w", encoding="utf-8") as arquivo:
        arquivo.write("ARQUIVO DE DECISÕES — POSSÍVEIS DUPLICATAS\n")
        arquivo.write("=" * 100 + "\n")
        arquivo.write(
            "INSTRUÇÕES:\n"
            "1. Cada bloco apresenta duas questões que podem ser duplicadas, mas cuja semelhança não foi suficiente para remoção automática.\n"
            "2. O padrão é [REVISAR]. Nesse estado, nenhuma questão será removida.\n"
            "3. Se forem duplicadas, altere para [DUPLICADA] e escolha MANTER [A] ou [B].\n"
            "4. Se forem diferentes, altere para [NAO_DUPLICADA].\n"
            "5. Não altere o ID DA POSSÍVEL DUPLICATA.\n"
            "6. Para aplicar essas decisões, execute com --aplicar-possiveis.\n\n"
        )
        arquivo.write(f"Total de pares candidatos: {len(restantes)}\n")
        arquivo.write("=" * 100 + "\n\n")
        if not restantes:
            arquivo.write("Nenhuma possível duplicata adicional encontrada.\n")
            return

        for numero, candidato in enumerate(restantes, start=1):
            qa_pos = candidato["a"]
            qb_pos = candidato["b"]
            qa = banco[qa_pos - 1]
            qb = banco[qb_pos - 1]
            possivel_id = id_possivel_por_par(qa_pos, qb_pos)
            valores = decisoes_existentes.get(
                possivel_id, {"decisao": DECISAO_REVISAR, "manter": ""}
            )
            decisao = valores.get("decisao", DECISAO_REVISAR)
            manter = valores.get("manter", "")
            if decisao == DECISAO_DUPLICADA and manter not in {"A", "B"}:
                raise ErroDecisaoConflito(
                    f"O par {possivel_id} está como [DUPLICADA], mas MANTER deve ser [A] ou [B]."
                )
            if decisao != DECISAO_DUPLICADA:
                manter = ""

            arquivo.write("#" * 100 + "\n")
            arquivo.write(f"POSSÍVEL DUPLICATA {numero}\n")
            arquivo.write(f"ID DA POSSÍVEL DUPLICATA: {possivel_id}\n")
            arquivo.write(f"DECISÃO: [{decisao}]\n")
            arquivo.write(f"MANTER: [{manter}]\n")
            arquivo.write(f"QUESTÃO A: posição {qa_pos}\n")
            arquivo.write(f"QUESTÃO B: posição {qb_pos}\n")
            arquivo.write("#" * 100 + "\n\n")
            arquivo.write(f"Classificação: {candidato['classificacao']}\n")
            arquivo.write(f"Similaridade geral: {candidato['geral']:.1%}\n")
            arquivo.write(f"Enunciado: {candidato['pergunta']:.1%}\n")
            arquivo.write(f"Alternativas: {candidato['opcoes']:.1%}\n")
            arquivo.write(f"Gabarito: {candidato['gabarito']:.1%}\n")
            arquivo.write(f"Temas: {candidato['temas']:.1%}\n")
            arquivo.write(f"Grande área: {candidato['area']:.1%}\n\n")
            for rotulo, qpos in (("A", qa_pos), ("B", qb_pos)):
                questao = banco[qpos - 1]
                arquivo.write(f"QUESTÃO {rotulo}\n")
                arquivo.write(f"Posição no banco: {qpos}\n")
                arquivo.write(f"Bloco: {formatar_valor(questao.get('bloco'))}\n")
                arquivo.write(f"Área: {formatar_valor(questao.get('grandeArea'))}\n")
                arquivo.write(f"Temas: {formatar_valor(questao.get('temas'))}\n")
                arquivo.write(f"Tipo: {formatar_valor(questao.get('tipo'))}\n")
                arquivo.write(f"Pergunta: {formatar_valor(questao.get('pergunta'))}\n")
                arquivo.write(f"Opções: {formatar_valor(questao.get('opcoes'))}\n")
                arquivo.write(f"Gabarito: {formatar_valor(questao.get('gabarito'))}\n")
                arquivo.write(f"Informações complementares:\n{formatar_valor(questao.get('informacoesComplementares'))}\n")
                arquivo.write("-" * 100 + "\n\n")


def ler_decisoes_existentes(caminho: Path) -> dict[str, dict[str, str]]:
    if not caminho.exists():
        return {}
    texto = caminho.read_text(encoding="utf-8-sig")
    linhas = texto.splitlines()
    decisoes: dict[str, dict[str, str]] = {}
    grupo_id = None
    decisao = None
    manter = None

    def salvar_grupo_atual() -> None:
        nonlocal grupo_id, decisao, manter
        if grupo_id is None:
            return
        if decisao is None:
            raise ErroDecisaoConflito(
                f"O grupo {grupo_id} não possui uma linha 'DECISÃO: [...]'."
            )
        decisoes[grupo_id] = {"decisao": decisao, "manter": manter or ""}
        grupo_id = None
        decisao = None
        manter = None

    padrao_id = re.compile(r"^ID DO GRUPO:\s*(\S+)\s*$", re.IGNORECASE)
    padrao_decisao = re.compile(r"^DECISÃO:\s*\[([^\]]+)\]\s*$", re.IGNORECASE)
    padrao_manter = re.compile(r"^MANTER:\s*\[([^\]]+)\]\s*$", re.IGNORECASE)
    for linha in linhas:
        linha_limpa = linha.strip()
        m = padrao_id.match(linha_limpa)
        if m:
            salvar_grupo_atual()
            grupo_id = m.group(1).strip()
            continue
        m = padrao_decisao.match(linha_limpa)
        if m and grupo_id:
            decisao = m.group(1).strip().upper()
            continue
        m = padrao_manter.match(linha_limpa)
        if m and grupo_id:
            manter = m.group(1).strip().upper()
    salvar_grupo_atual()

    for grupo, valores in decisoes.items():
        if valores["decisao"] not in DECISOES_VALIDAS:
            raise ErroDecisaoConflito(
                f"Decisão inválida para {grupo}: [{valores['decisao']}]. "
                "Use [DUPLICADA] ou [NAO_DUPLICADA]."
            )
        if valores["decisao"] == DECISAO_DUPLICADA and not valores["manter"]:
            raise ErroDecisaoConflito(
                f"O grupo {grupo} está marcado como [DUPLICADA], mas não informa MANTER."
            )
        if valores["decisao"] == DECISAO_NAO_DUPLICADA:
            valores["manter"] = ""
    return decisoes


def ler_decisoes_possiveis(caminho: Path) -> dict[str, dict[str, str]]:
    if not caminho.exists():
        return {}
    texto = caminho.read_text(encoding="utf-8-sig")
    linhas = texto.splitlines()
    decisoes: dict[str, dict[str, str]] = {}
    possivel_id = None
    decisao = None
    manter = None

    def salvar_atual() -> None:
        nonlocal possivel_id, decisao, manter
        if possivel_id is None:
            return
        if decisao is None:
            raise ErroDecisaoConflito(
                f"O item {possivel_id} não possui uma linha 'DECISÃO: [...]'."
            )
        decisoes[possivel_id] = {"decisao": decisao, "manter": manter or ""}
        possivel_id = None
        decisao = None
        manter = None

    padrao_id = re.compile(r"^ID DA POSSÍVEL DUPLICATA:\s*(\S+)\s*$", re.IGNORECASE)
    padrao_decisao = re.compile(r"^DECISÃO:\s*\[([^\]]+)\]\s*$", re.IGNORECASE)
    padrao_manter = re.compile(r"^MANTER:\s*\[([^\]]*)\]\s*$", re.IGNORECASE)

    for linha in linhas:
        linha_limpa = linha.strip()
        m = padrao_id.match(linha_limpa)
        if m:
            salvar_atual()
            possivel_id = m.group(1).strip()
            continue
        m = padrao_decisao.match(linha_limpa)
        if m and possivel_id:
            decisao = m.group(1).strip().upper()
            continue
        m = padrao_manter.match(linha_limpa)
        if m and possivel_id:
            manter = m.group(1).strip().upper()
    salvar_atual()

    for grupo, valores in decisoes.items():
        if valores["decisao"] not in DECISOES_POSSIVEIS_VALIDAS:
            raise ErroDecisaoConflito(
                f"Decisão inválida para {grupo}: [{valores['decisao']}]. "
                "Use [REVISAR], [DUPLICADA] ou [NAO_DUPLICADA]."
            )
        if valores["decisao"] == DECISAO_DUPLICADA and valores["manter"] not in {"A", "B"}:
            raise ErroDecisaoConflito(
                f"O item {grupo} está como [DUPLICADA], mas MANTER deve ser [A] ou [B]."
            )
        if valores["decisao"] != DECISAO_DUPLICADA:
            valores["manter"] = ""
    return decisoes


def aplicar_decisoes_possiveis(
    banco: list[dict[str, Any]],
    candidatos: list[dict[str, Any]],
    decisoes: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    remocoes: set[int] = set()
    mantidas: set[int] = set()
    auditoria: list[dict[str, Any]] = []
    removidas: list[dict[str, Any]] = []

    candidatos_por_id = {
        id_possivel_por_par(c["a"], c["b"]): c for c in candidatos
    }

    for possivel_id, registro in decisoes.items():
        if possivel_id not in candidatos_por_id:
            raise ErroDecisaoConflito(
                f"O ID {possivel_id} não corresponde a nenhuma possível duplicata atual."
            )
        decisao = registro["decisao"]
        if decisao == DECISAO_REVISAR:
            continue
        candidato = candidatos_por_id[possivel_id]
        a, b = candidate = (candidato["a"], candidato["b"])
        if decisao == DECISAO_NAO_DUPLICADA:
            auditoria.append({"id": possivel_id, "decisao": decisao, "mantida": [a, b], "removidas": []})
            continue
        manter_pos = a if registro["manter"] == "A" else b
        remover_pos = b if manter_pos == a else a
        if remover_pos in mantidas:
            raise ErroDecisaoConflito(
                f"Conflito entre decisões: a questão na posição {remover_pos} foi marcada para ser mantida em outro item, "
                f"mas {possivel_id} manda removê-la."
            )
        if manter_pos in remocoes:
            raise ErroDecisaoConflito(
                f"Conflito entre decisões: a questão na posição {manter_pos} foi marcada para remoção em outro item, "
                f"mas {possivel_id} manda mantê-la."
            )
        mantidas.add(manter_pos)
        remocoes.add(remover_pos)
        auditoria.append({"id": possivel_id, "decisao": decisao, "mantida": [manter_pos], "removidas": [remover_pos]})

    for indice in sorted(remocoes):
        removidas.append({
            "indice_original": indice,
            "indice_mantida": next((r["mantida"][0] for r in auditoria if indice in r["removidas"]), None),
            "motivo": "Removida conforme decisão registrada em questoes_possiveis_duplicatas.txt.",
            "questao": banco[indice - 1],
        })

    novo_banco = [q for indice, q in enumerate(banco, start=1) if indice not in remocoes]
    return novo_banco, removidas, auditoria


def escrever_relatorio_possiveis_resolvidos(caminho: Path, auditoria: list[dict[str, Any]]) -> None:
    with caminho.open("w", encoding="utf-8") as arquivo:
        arquivo.write("RELATÓRIO DE DECISÕES APLICADAS — POSSÍVEIS DUPLICATAS\n")
        arquivo.write("=" * 90 + "\n")
        arquivo.write(f"Total de decisões aplicadas: {len(auditoria)}\n\n")
        if not auditoria:
            arquivo.write("Nenhuma decisão foi aplicada.\n")
            return
        for registro in auditoria:
            arquivo.write(f"ID: {registro['id']}\n")
            arquivo.write(f"Decisão: {registro['decisao']}\n")
            arquivo.write("Posições mantidas: " + ", ".join(map(str, registro["mantida"])) + "\n")
            arquivo.write("Posições removidas: " + (", ".join(map(str, registro["removidas"])) if registro["removidas"] else "nenhuma") + "\n")
            arquivo.write("-" * 90 + "\n")


def escrever_relatorio_conflitos(
    caminho: Path,
    conflitos: list[list[dict[str, Any]]],
    decisoes_existentes: dict[str, dict[str, str]],
    banco: list[dict[str, Any]],
    candidatos: list[dict[str, Any]],
) -> None:
    with caminho.open("w", encoding="utf-8") as arquivo:
        arquivo.write("ARQUIVO DE DECISÕES — QUESTÕES SUSPEITAS DE DUPLICIDADE\n")
        arquivo.write("=" * 100 + "\n")
        arquivo.write(
            "INSTRUÇÕES:\n"
            "1. Cada grupo contém questões com forte similaridade estrutural.\n"
            "2. Por padrão, o grupo é [DUPLICADA] e [A] é mantida.\n"
            "3. Se não forem duplicadas, altere para [NAO_DUPLICADA].\n"
            "4. Se outra ocorrência for a melhor, altere MANTER para [B], [C] etc.\n"
            "5. Não altere o ID DO GRUPO.\n"
            "6. Só aplique as decisões executando com --aplicar-conflitos.\n\n"
        )
        arquivo.write(f"Total de grupos: {len(conflitos)}\n")
        arquivo.write("=" * 100 + "\n\n")
        if not conflitos:
            arquivo.write("Nenhum grupo de forte similaridade encontrado.\n")
            return

        # Mapa de pares para detalhar a similaridade entre ocorrências do mesmo grupo.
        mapa_pares: dict[tuple[int, int], dict[str, Any]] = {}
        for candidato in candidatos:
            mapa_pares[(min(candidato["a"], candidato["b"]), max(candidato["a"], candidato["b"]))] = candidato

        for grupo in conflitos:
            grupo_id = id_grupo_conflito(grupo)
            valores = decisoes_existentes.get(
                grupo_id,
                {"decisao": DECISAO_DUPLICADA, "manter": "A"},
            )
            rotulos_validos = {rotulo_ocorrencia(i) for i in range(len(grupo))}
            decisao = valores.get("decisao", DECISAO_DUPLICADA)
            manter = valores.get("manter", "A")
            if decisao == DECISAO_DUPLICADA and manter not in rotulos_validos:
                raise ErroDecisaoConflito(
                    f"O grupo {grupo_id} possui MANTER=[{manter}], válidos: {', '.join(sorted(rotulos_validos))}."
                )

            arquivo.write("#" * 100 + "\n")
            arquivo.write("GRUPO DE CONFLITO\n")
            arquivo.write(f"ID DO GRUPO: {grupo_id}\n")
            arquivo.write(f"DECISÃO: [{decisao}]\n")
            arquivo.write(f"MANTER: [{manter}]\n")
            arquivo.write("POSIÇÕES NO BANCO: " + ", ".join(str(x["indice"]) for x in grupo) + "\n")
            arquivo.write("#" * 100 + "\n\n")

            melhor = None
            for i in range(len(grupo)):
                for j in range(i + 1, len(grupo)):
                    par = (grupo[i]["indice"], grupo[j]["indice"])
                    analise = mapa_pares.get(par)
                    if analise and (melhor is None or analise["geral"] > melhor["geral"]):
                        melhor = analise
            if melhor:
                arquivo.write(f"Classificação predominante: {melhor['classificacao']}\n")
                arquivo.write(f"Similaridade geral máxima: {melhor['geral']:.1%}\n")
                arquivo.write(f"Enunciado: {melhor['pergunta']:.1%}\n")
                arquivo.write(f"Alternativas: {melhor['opcoes']:.1%}\n")
                arquivo.write(f"Gabarito: {melhor['gabarito']:.1%}\n")
                arquivo.write(f"Temas: {melhor['temas']:.1%}\n")
                arquivo.write(f"Grande área: {melhor['area']:.1%}\n\n")

            for indice_local, item in enumerate(grupo):
                rotulo = rotulo_ocorrencia(indice_local)
                questao = item["questao"]
                arquivo.write(f"QUESTÃO {rotulo}\n")
                arquivo.write(f"Posição no banco: {item['indice']}\n")
                arquivo.write(f"Bloco: {formatar_valor(questao.get('bloco'))}\n")
                arquivo.write(f"Área: {formatar_valor(questao.get('grandeArea'))}\n")
                arquivo.write(f"Tipo: {formatar_valor(questao.get('tipo'))}\n")
                arquivo.write(f"Temas: {formatar_valor(questao.get('temas'))}\n")
                arquivo.write(f"Pergunta: {formatar_valor(questao.get('pergunta'))}\n")
                arquivo.write(f"Opções: {formatar_valor(questao.get('opcoes'))}\n")
                arquivo.write(f"Gabarito: {formatar_valor(questao.get('gabarito'))}\n")
                arquivo.write(f"Informações complementares:\n{formatar_valor(questao.get('informacoesComplementares'))}\n")
                arquivo.write("-" * 100 + "\n\n")


def validar_decisoes_e_obter_remocoes(
    conflitos: list[list[dict[str, Any]]],
    decisoes: dict[str, dict[str, str]],
) -> tuple[set[int], list[dict[str, Any]], list[str]]:
    remocoes: set[int] = set()
    auditoria: list[dict[str, Any]] = []
    grupos_sem_decisao: list[str] = []
    for grupo in conflitos:
        grupo_id = id_grupo_conflito(grupo)
        registro = decisoes.get(grupo_id)
        if registro is None:
            grupos_sem_decisao.append(grupo_id)
            continue
        decisao = registro["decisao"]
        manter = registro["manter"]
        if decisao == DECISAO_NAO_DUPLICADA:
            auditoria.append({"grupo_id": grupo_id, "decisao": decisao,
                              "mantida": [x["indice"] for x in grupo], "removidas": []})
            continue
        rotulos = {rotulo_ocorrencia(i): item for i, item in enumerate(grupo)}
        if manter not in rotulos:
            raise ErroDecisaoConflito(
                f"O grupo {grupo_id} informa MANTER=[{manter}], válidos: {', '.join(rotulos)}."
            )
        mantida = rotulos[manter]
        removidas_grupo = [item for rotulo, item in rotulos.items() if rotulo != manter]
        for item in removidas_grupo:
            remocoes.add(item["indice"])
        auditoria.append({"grupo_id": grupo_id, "decisao": decisao,
                          "mantida": [mantida["indice"]],
                          "removidas": [x["indice"] for x in removidas_grupo]})
    return remocoes, auditoria, grupos_sem_decisao


def aplicar_decisoes_conflitos(
    banco: list[dict[str, Any]],
    conflitos: list[list[dict[str, Any]]],
    decisoes: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    remocoes, auditoria, grupos_sem_decisao = validar_decisoes_e_obter_remocoes(conflitos, decisoes)
    if grupos_sem_decisao:
        raise ErroDecisaoConflito(
            "Existem grupos sem decisão no arquivo: " + ", ".join(grupos_sem_decisao)
        )
    removidas: list[dict[str, Any]] = []
    for indice, questao in enumerate(banco, start=1):
        if indice in remocoes:
            correspondente = next((r for r in auditoria if indice in r["removidas"]), None)
            removidas.append({
                "indice_original": indice,
                "indice_mantida": correspondente["mantida"][0] if correspondente else None,
                "motivo": "Removida conforme decisão registrada em questoes_conflitantes.txt.",
                "questao": questao,
            })
    novo_banco = [q for indice, q in enumerate(banco, start=1) if indice not in remocoes]
    return novo_banco, removidas, auditoria


def escrever_relatorio_conflitos_resolvidos(caminho: Path, auditoria: list[dict[str, Any]]) -> None:
    with caminho.open("w", encoding="utf-8") as arquivo:
        arquivo.write("RELATÓRIO DE DECISÕES APLICADAS AOS CONFLITOS\n")
        arquivo.write("=" * 90 + "\n")
        arquivo.write(f"Total de grupos processados: {len(auditoria)}\n\n")
        if not auditoria:
            arquivo.write("Nenhuma decisão de conflito foi aplicada.\n")
            return
        for registro in auditoria:
            arquivo.write(f"Grupo: {registro['grupo_id']}\n")
            arquivo.write(f"Decisão: {registro['decisao']}\n")
            arquivo.write("Posições mantidas: " + ", ".join(map(str, registro["mantida"])) + "\n")
            arquivo.write("Posições removidas: " + (", ".join(map(str, registro["removidas"])) if registro["removidas"] else "nenhuma") + "\n")
            arquivo.write("-" * 90 + "\n")


def escrever_relatorio_removidas(caminho: Path, removidas: list[dict[str, Any]]) -> None:
    with caminho.open("w", encoding="utf-8") as arquivo:
        arquivo.write("RELATÓRIO DE QUESTÕES REMOVIDAS (DUPLICADAS)\n")
        arquivo.write("=" * 90 + "\n")
        arquivo.write(f"Total de questões removidas: {len(removidas)}\n\n")
        if not removidas:
            arquivo.write("Nenhuma questão foi removida.\n")
            return
        for item in removidas:
            q = item["questao"]
            arquivo.write(f"--- QUESTÃO REMOVIDA {item['indice_original']} ---\n")
            arquivo.write(f"Origem da decisão: {item['motivo']}\n")
            arquivo.write(f"Manteve-se a questão na posição original: {item['indice_mantida']}\n")
            arquivo.write(f"Bloco: {formatar_valor(q.get('bloco'))}\n")
            arquivo.write(f"Área: {formatar_valor(q.get('grandeArea'))}\n")
            arquivo.write(f"Tipo: {formatar_valor(q.get('tipo'))}\n")
            arquivo.write(f"Temas: {formatar_valor(q.get('temas'))}\n")
            arquivo.write(f"Pergunta: {formatar_valor(q.get('pergunta'))}\n")
            arquivo.write(f"Gabarito: {formatar_valor(q.get('gabarito'))}\n")
            arquivo.write("-" * 90 + "\n\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Limpa e analisa duplicidade literal, estrutural e quase idêntica em um banco de questões JavaScript."
    )
    parser.add_argument("--entrada", default=ARQUIVO_ENTRADA_PADRAO)
    parser.add_argument("--saida-js", default=ARQUIVO_SAIDA_JS_PADRAO)
    parser.add_argument("--saida-txt", default=ARQUIVO_SAIDA_REMOVIDAS_PADRAO)
    parser.add_argument("--saida-conflitos", default=ARQUIVO_SAIDA_CONFLITOS_PADRAO)
    parser.add_argument("--saida-conflitos-resolvidos", default=ARQUIVO_SAIDA_CONFLITOS_RESOLVIDOS_PADRAO)
    parser.add_argument("--saida-possiveis", default=ARQUIVO_SAIDA_POSSIVEIS_PADRAO)
    parser.add_argument("--saida-possiveis-resolvidos", default=ARQUIVO_SAIDA_POSSIVEIS_RESOLVIDOS_PADRAO)
    parser.add_argument("--aplicar-conflitos", action="store_true")
    parser.add_argument("--aplicar-possiveis", action="store_true")
    args = parser.parse_args()

    pasta_script = Path(__file__).resolve().parent

    def resolver(caminho: str) -> Path:
        p = Path(caminho)
        return p if p.is_absolute() else pasta_script / p

    entrada = resolver(args.entrada)
    saida_js = resolver(args.saida_js)
    saida_txt = resolver(args.saida_txt)
    saida_conflitos = resolver(args.saida_conflitos)
    saida_resolvidos = resolver(args.saida_conflitos_resolvidos)
    saida_possiveis = resolver(args.saida_possiveis)
    saida_possiveis_resolvidos = resolver(args.saida_possiveis_resolvidos)

    print("=" * 90)
    print("QUESTION BANK CLEANER — ANÁLISE AVANÇADA")
    print("=" * 90)
    print(f"Arquivo de entrada: {entrada}")

    try:
        banco = extrair_lista_js(entrada.read_text(encoding="utf-8-sig"))
        print(f"Questões encontradas: {len(banco)}")
        print(f"RapidFuzz disponível: {'SIM' if RAPIDFUZZ_DISPONIVEL else 'NÃO'}")
        if not RAPIDFUZZ_DISPONIVEL:
            print("  O processamento continuará, mas será mais lento no modo de fallback.")
        print()

        print("Analisando duplicatas integrais...")
        banco_sem_integras, removidas_automaticas = limpar_automatico_integral(banco)
        print(f"  Duplicatas integrais removidas: {len(removidas_automaticas)}")

        print("Analisando duplicatas de alta confiança...")
        banco_sem_alta, removidas_alta, grupos_auto = limpar_automatico_alta_confianca(
            banco_sem_integras
        )
        print(f"  Duplicatas de alta confiança removidas: {len(removidas_alta)}")

        print("Procurando possíveis duplicatas para revisão...")
        conflitos, candidatos = construir_candidatos_similaridade(banco_sem_alta)
        decisoes_existentes = ler_decisoes_existentes(saida_conflitos)
        decisoes_possiveis_existentes = ler_decisoes_possiveis(saida_possiveis)

        escrever_relatorio_conflitos(
            saida_conflitos, conflitos, decisoes_existentes, banco_sem_alta, candidatos
        )
        escrever_relatorio_possiveis(
            saida_possiveis, candidatos, conflitos, banco_sem_alta, decisoes_possiveis_existentes
        )

        banco_final = banco_sem_alta
        removidas_conflitos: list[dict[str, Any]] = []
        auditoria: list[dict[str, Any]] = []
        auditoria_possiveis: list[dict[str, Any]] = []

        # Todas as decisões usam a mesma base (banco_sem_alta), evitando que
        # as posições do relatório de possíveis duplicatas mudem antes de sua
        # aplicação. Só depois unimos as remoções.
        indices_remover: set[int] = set()

        if args.aplicar_conflitos:
            _, removidas_conflitos, auditoria = aplicar_decisoes_conflitos(
                banco_sem_alta, conflitos, decisoes_existentes
            )
            indices_remover.update(item["indice_original"] for item in removidas_conflitos)
            escrever_relatorio_conflitos_resolvidos(saida_resolvidos, auditoria)

        if args.aplicar_possiveis:
            _, removidas_possiveis, auditoria_possiveis = aplicar_decisoes_possiveis(
                banco_sem_alta, candidatos, decisoes_possiveis_existentes
            )
            indices_remover.update(item["indice_original"] for item in removidas_possiveis)
            removidas_conflitos.extend(removidas_possiveis)
            escrever_relatorio_possiveis_resolvidos(saida_possiveis_resolvidos, auditoria_possiveis)

        if indices_remover:
            banco_final = [
                q for indice, q in enumerate(banco_sem_alta, start=1)
                if indice not in indices_remover
            ]
            # Verificação final de segurança após decisões humanas.
            banco_final, protecao = limpar_automatico_integral(banco_final)
            removidas_conflitos.extend(protecao)

        novo_json = json.dumps(banco_final, indent=4, ensure_ascii=False)
        saida_js.write_text("const bancoDeQuestoes = " + novo_json + ";\n", encoding="utf-8")
        escrever_relatorio_removidas(
            saida_txt,
            removidas_automaticas + removidas_alta + removidas_conflitos,
        )

        print("-" * 90)
        print("PROCESSAMENTO CONCLUÍDO")
        print("-" * 90)
        print(f"Questões originais                 : {len(banco)}")
        total_auto = len(removidas_automaticas) + len(removidas_alta)
        print(f"Duplicatas removidas automaticamente: {total_auto}")
        print(f"  - integrais                        : {len(removidas_automaticas)}")
        print(f"  - alta confiança                   : {len(removidas_alta)}")
        print(f"Grupos de forte similaridade      : {len(conflitos)}")
        print(f"Pares de possível duplicata       : {len(candidatos)}")
        if args.aplicar_conflitos or args.aplicar_possiveis:
            print(f"Removidas por decisões             : {len(removidas_conflitos)}")
            print(f"Total final de questões            : {len(banco_final)}")
            print(f"Decisões de conflitos aplicadas   : {len(auditoria)}")
            print(f"Decisões de possíveis aplicadas   : {len(auditoria_possiveis)}")
        else:
            print(f"Total na saída antes dos conflitos: {len(banco_final)}")
        print(f"Banco de saída                     : {saida_js}")
        print(f"Relatório de removidas             : {saida_txt}")
        print(f"Arquivo de decisões                : {saida_conflitos}")
        print(f"Possíveis duplicatas               : {saida_possiveis}")
        if args.aplicar_conflitos:
            print(f"Auditoria dos conflitos             : {saida_resolvidos}")
        if args.aplicar_possiveis:
            print(f"Auditoria das possíveis             : {saida_possiveis_resolvidos}")
        return 0

    except FileNotFoundError:
        print(f"Erro: arquivo de entrada não encontrado: {entrada}", file=sys.stderr)
        return 1
    except (ValueError, ErroDecisaoConflito) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 2
    except Exception as erro:
        print(f"Erro inesperado: {erro}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
