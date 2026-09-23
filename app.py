from __future__ import annotations

"""
Question Bank Cleaner

Aplicação desktop utilitária desenvolvida de forma independente por Pablo Phillipe Cândido dos Santos,
destinada à análise e deduplicação assistida de bancos de questões estruturados em JavaScript/JSON.

O desenvolvimento contou com ferramentas de inteligência artificial generativa como recurso auxiliar,
mantendo-se sob responsabilidade do autor a concepção, implementação, integração e verificação do projeto.

Currículo Lattes: http://lattes.cnpq.br/9500873674712528
"""

import contextlib
import io
import json
import os
import queue
import subprocess
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import cleaner_core as core


APP_NAME = "Question Bank Cleaner"
APP_VERSION = "1.1.0"

THEMES = {
    "dark": {
        "bg": "#0F172A",
        "surface": "#172033",
        "surface_alt": "#1E293B",
        "text": "#F1F5F9",
        "muted": "#94A3B8",
        "border": "#334155",
        "accent": "#3B82F6",
        "accent_hover": "#2563EB",
        "accent_pressed": "#1D4ED8",
        "success": "#22C55E",
        "warning": "#F59E0B",
        "danger": "#EF4444",
        "entry": "#111827",
        "selection": "#2563EB",
        "log_bg": "#0B1220",
        "log_fg": "#D8E2F0",
    },
    "light": {
        "bg": "#F3F6FA",
        "surface": "#FFFFFF",
        "surface_alt": "#EEF3F8",
        "text": "#172033",
        "muted": "#64748B",
        "border": "#D6DEE8",
        "accent": "#2563EB",
        "accent_hover": "#1D4ED8",
        "accent_pressed": "#1E40AF",
        "success": "#16A34A",
        "warning": "#D97706",
        "danger": "#DC2626",
        "entry": "#FFFFFF",
        "selection": "#BFDBFE",
        "log_bg": "#F8FAFC",
        "log_fg": "#1E293B",
    },
}


def caminho_recurso(relativo: str) -> Path:
    """Resolve recursos tanto no código-fonte quanto no executável PyInstaller."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relativo


def caminho_configuracao() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home()))
        return base / "QuestionBankCleaner" / "settings.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "QuestionBankCleaner" / "settings.json"
    return Path.home() / ".config" / "question-bank-cleaner" / "settings.json"


def carregar_tema_preferido() -> str:
    caminho = caminho_configuracao()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        tema = dados.get("theme")
        if tema in THEMES:
            return tema
    except Exception:
        pass
    return "dark"


def salvar_tema_preferido(tema: str) -> None:
    try:
        caminho = caminho_configuracao()
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json.dumps({"theme": tema}, indent=2), encoding="utf-8")
    except Exception:
        # A preferência visual não deve impedir o funcionamento do programa.
        pass


def aplicar_icone(janela: tk.Misc) -> None:
    """Aplica o ícone quando o usuário adicionar os recursos em assets/."""
    ico = caminho_recurso("assets/question_bank_cleaner.ico")
    png = caminho_recurso("assets/question_bank_cleaner.png")
    try:
        if sys.platform.startswith("win") and ico.exists():
            janela.wm_iconbitmap(str(ico))
            return
    except Exception:
        pass
    try:
        if png.exists():
            foto = tk.PhotoImage(file=str(png))
            janela.wm_iconphoto(True, foto)
            setattr(janela, "_qbc_icon_photo", foto)
    except Exception:
        pass


@dataclass
class ResultadoAnalise:
    entrada: Path
    pasta_saida: Path
    saida_js: Path
    saida_removidas: Path
    saida_conflitos: Path
    saida_conflitos_resolvidos: Path
    saida_possiveis: Path
    saida_possiveis_resolvidos: Path
    banco_original: list[dict[str, Any]]
    banco_base_revisao: list[dict[str, Any]]
    banco_final: list[dict[str, Any]]
    removidas_integras: list[dict[str, Any]]
    removidas_alta: list[dict[str, Any]]
    removidas_decisoes: list[dict[str, Any]]
    conflitos: list[list[dict[str, Any]]]
    candidatos: list[dict[str, Any]]
    decisoes_conflitos: dict[str, dict[str, str]]
    decisoes_possiveis: dict[str, dict[str, str]]


class QueueWriter(io.TextIOBase):
    def __init__(self, fila: queue.Queue[str]) -> None:
        self.fila = fila
        self._buffer = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buffer += s
        while "\n" in self._buffer:
            linha, self._buffer = self._buffer.split("\n", 1)
            if "\r" in linha:
                linha = linha.split("\r")[-1]
            if linha.strip():
                self.fila.put(linha + "\n")
        if "\r" in self._buffer:
            trecho = self._buffer.split("\r")[-1]
            if trecho.strip():
                self.fila.put(trecho)
            self._buffer = ""
        return len(s)

    def flush(self) -> None:
        if self._buffer.strip():
            self.fila.put(self._buffer)
        self._buffer = ""


def abrir_no_sistema(caminho: Path) -> None:
    caminho = caminho.resolve()
    if sys.platform.startswith("win"):
        os.startfile(str(caminho))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(caminho)])
    else:
        subprocess.Popen(["xdg-open", str(caminho)])


def caminhos_saida(pasta: Path) -> dict[str, Path]:
    return {
        "js": pasta / core.ARQUIVO_SAIDA_JS_PADRAO,
        "removidas": pasta / core.ARQUIVO_SAIDA_REMOVIDAS_PADRAO,
        "conflitos": pasta / core.ARQUIVO_SAIDA_CONFLITOS_PADRAO,
        "conflitos_resolvidos": pasta / core.ARQUIVO_SAIDA_CONFLITOS_RESOLVIDOS_PADRAO,
        "possiveis": pasta / core.ARQUIVO_SAIDA_POSSIVEIS_PADRAO,
        "possiveis_resolvidos": pasta / core.ARQUIVO_SAIDA_POSSIVEIS_RESOLVIDOS_PADRAO,
    }


def analisar_banco(entrada: Path, pasta_saida: Path) -> ResultadoAnalise:
    pasta_saida.mkdir(parents=True, exist_ok=True)
    paths = caminhos_saida(pasta_saida)

    print("=" * 88)
    print(f"{APP_NAME} — ANÁLISE")
    print("=" * 88)
    print(f"Entrada: {entrada}")
    print(f"Saída  : {pasta_saida}")
    print()

    banco = core.extrair_lista_js(entrada.read_text(encoding="utf-8-sig"))
    print(f"Questões encontradas: {len(banco)}")
    print(f"RapidFuzz disponível: {'SIM' if core.RAPIDFUZZ_DISPONIVEL else 'NÃO'}")
    if not core.RAPIDFUZZ_DISPONIVEL:
        print("Aviso: sem RapidFuzz o processamento usa o fallback e pode ser mais lento.")
    print()

    print("1/3 — Removendo duplicatas integralmente idênticas...")
    banco_sem_integras, removidas_integras = core.limpar_automatico_integral(banco)
    print(f"Duplicatas integrais removidas: {len(removidas_integras)}")

    print("2/3 — Procurando duplicatas de alta confiança...")
    banco_sem_alta, removidas_alta, _ = core.limpar_automatico_alta_confianca(banco_sem_integras)
    print(f"Duplicatas de alta confiança removidas: {len(removidas_alta)}")

    print("3/3 — Procurando itens que precisam de revisão humana...")
    conflitos, candidatos = core.construir_candidatos_similaridade(banco_sem_alta)

    decisoes_conflitos = core.ler_decisoes_existentes(paths["conflitos"]) if paths["conflitos"].exists() else {}
    decisoes_possiveis = core.ler_decisoes_possiveis(paths["possiveis"]) if paths["possiveis"].exists() else {}

    # Na GUI, novos conflitos começam no estado conservador "NÃO DUPLICADA".
    # Isso evita remoção humana acidental antes de uma revisão explícita.
    for grupo in conflitos:
        gid = core.id_grupo_conflito(grupo)
        decisoes_conflitos.setdefault(
            gid,
            {"decisao": core.DECISAO_NAO_DUPLICADA, "manter": ""},
        )

    core.escrever_relatorio_conflitos(
        paths["conflitos"], conflitos, decisoes_conflitos, banco_sem_alta, candidatos
    )
    core.escrever_relatorio_possiveis(
        paths["possiveis"], candidatos, conflitos, banco_sem_alta, decisoes_possiveis
    )

    banco_final = banco_sem_alta
    novo_json = json.dumps(banco_final, indent=4, ensure_ascii=False)
    paths["js"].write_text("const bancoDeQuestoes = " + novo_json + ";\n", encoding="utf-8")
    core.escrever_relatorio_removidas(
        paths["removidas"], removidas_integras + removidas_alta
    )

    print("-" * 88)
    print("ANÁLISE CONCLUÍDA")
    print(f"Originais                         : {len(banco)}")
    print(f"Removidas automaticamente         : {len(removidas_integras) + len(removidas_alta)}")
    print(f"Grupos de forte similaridade      : {len(conflitos)}")
    print(f"Pares de possível duplicata       : {len(candidatos)}")
    print(f"Questões na saída automática      : {len(banco_final)}")
    print("-" * 88)

    return ResultadoAnalise(
        entrada=entrada,
        pasta_saida=pasta_saida,
        saida_js=paths["js"],
        saida_removidas=paths["removidas"],
        saida_conflitos=paths["conflitos"],
        saida_conflitos_resolvidos=paths["conflitos_resolvidos"],
        saida_possiveis=paths["possiveis"],
        saida_possiveis_resolvidos=paths["possiveis_resolvidos"],
        banco_original=banco,
        banco_base_revisao=banco_sem_alta,
        banco_final=banco_final,
        removidas_integras=removidas_integras,
        removidas_alta=removidas_alta,
        removidas_decisoes=[],
        conflitos=conflitos,
        candidatos=candidatos,
        decisoes_conflitos=decisoes_conflitos,
        decisoes_possiveis=decisoes_possiveis,
    )


def aplicar_decisoes(resultado: ResultadoAnalise) -> ResultadoAnalise:
    print("=" * 88)
    print(f"{APP_NAME} — APLICAÇÃO DAS DECISÕES")
    print("=" * 88)

    # Releitura dos arquivos: permite editar externamente e retornar à GUI.
    decisoes_conflitos = core.ler_decisoes_existentes(resultado.saida_conflitos)
    decisoes_possiveis = core.ler_decisoes_possiveis(resultado.saida_possiveis)

    indices_remover: set[int] = set()
    removidas_decisoes: list[dict[str, Any]] = []

    _, removidas_conflitos, auditoria_conflitos = core.aplicar_decisoes_conflitos(
        resultado.banco_base_revisao,
        resultado.conflitos,
        decisoes_conflitos,
    )
    indices_remover.update(item["indice_original"] for item in removidas_conflitos)
    removidas_decisoes.extend(removidas_conflitos)
    core.escrever_relatorio_conflitos_resolvidos(
        resultado.saida_conflitos_resolvidos,
        auditoria_conflitos,
    )

    _, removidas_possiveis, auditoria_possiveis = core.aplicar_decisoes_possiveis(
        resultado.banco_base_revisao,
        resultado.candidatos,
        decisoes_possiveis,
    )
    indices_remover.update(item["indice_original"] for item in removidas_possiveis)
    removidas_decisoes.extend(removidas_possiveis)
    core.escrever_relatorio_possiveis_resolvidos(
        resultado.saida_possiveis_resolvidos,
        auditoria_possiveis,
    )

    banco_final = [
        q
        for indice, q in enumerate(resultado.banco_base_revisao, start=1)
        if indice not in indices_remover
    ]
    banco_final, protecao = core.limpar_automatico_integral(banco_final)
    removidas_decisoes.extend(protecao)

    novo_json = json.dumps(banco_final, indent=4, ensure_ascii=False)
    resultado.saida_js.write_text(
        "const bancoDeQuestoes = " + novo_json + ";\n",
        encoding="utf-8",
    )
    core.escrever_relatorio_removidas(
        resultado.saida_removidas,
        resultado.removidas_integras
        + resultado.removidas_alta
        + removidas_decisoes,
    )

    resultado.banco_final = banco_final
    resultado.removidas_decisoes = removidas_decisoes
    resultado.decisoes_conflitos = decisoes_conflitos
    resultado.decisoes_possiveis = decisoes_possiveis

    print(f"Decisões de conflitos aplicadas : {len(auditoria_conflitos)}")
    print(f"Decisões de possíveis aplicadas : {len(auditoria_possiveis)}")
    print(f"Removidas por decisões          : {len(removidas_decisoes)}")
    print(f"Total final                     : {len(banco_final)}")
    print(f"Banco final                     : {resultado.saida_js}")
    print("=" * 88)

    return resultado


def formatar_questao(questao: dict[str, Any], rotulo: str, posicao: int) -> str:
    opcoes = questao.get("opcoes")
    if isinstance(opcoes, list):
        opcoes_txt = "\n".join(f"  {chr(65+i)}) {v}" for i, v in enumerate(opcoes))
    else:
        opcoes_txt = str(opcoes or "N/A")

    temas = questao.get("temas")
    if isinstance(temas, list):
        temas_txt = ", ".join(map(str, temas))
    else:
        temas_txt = str(temas or "N/A")

    return (
        f"QUESTÃO {rotulo} — posição {posicao}\n"
        f"{'─' * 72}\n"
        f"Área: {questao.get('grandeArea', 'N/A')}\n"
        f"Temas: {temas_txt}\n"
        f"Tipo: {questao.get('tipo', 'N/A')}\n\n"
        f"PERGUNTA\n{questao.get('pergunta', '')}\n\n"
        f"OPÇÕES\n{opcoes_txt}\n\n"
        f"GABARITO\n{questao.get('gabarito', 'N/A')}\n\n"
        f"INFORMAÇÕES COMPLEMENTARES\n{questao.get('informacoesComplementares', 'N/A')}\n"
    )


class JanelaRevisaoConflitos(tk.Toplevel):
    def __init__(self, master: "App", resultado: ResultadoAnalise) -> None:
        super().__init__(master)
        self.master_app = master
        self.resultado = resultado
        self.grupos = resultado.conflitos
        self.indice = 0
        self.title("Revisar grupos de forte similaridade")
        self.geometry("980x720")
        self.minsize(760, 560)

        self.decisao = tk.StringVar()
        self.manter = tk.StringVar()

        topo = ttk.Frame(self, padding=12)
        topo.pack(fill="x")
        self.lbl_pos = ttk.Label(topo, font=("Segoe UI", 11, "bold"))
        self.lbl_pos.pack(side="left")
        ttk.Label(
            topo,
            text="Revise cada grupo antes de marcar como duplicado.",
            style="Subtitle.TLabel",
        ).pack(side="right")

        controles = ttk.LabelFrame(self, text="Decisão", padding=10)
        controles.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Radiobutton(
            controles,
            text="Não são duplicadas",
            variable=self.decisao,
            value=core.DECISAO_NAO_DUPLICADA,
            command=self._atualizar_estado_manter,
        ).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(
            controles,
            text="São duplicadas",
            variable=self.decisao,
            value=core.DECISAO_DUPLICADA,
            command=self._atualizar_estado_manter,
        ).pack(side="left")

        ttk.Label(controles, text="Manter:").pack(side="left", padx=(20, 6))
        self.combo_manter = ttk.Combobox(controles, textvariable=self.manter, width=8, state="readonly")
        self.combo_manter.pack(side="left")

        self.texto = ScrolledText(self, wrap="word", font=("Cascadia Mono", 10), relief="flat", borderwidth=0)
        self.texto.pack(fill="both", expand=True, padx=16, pady=10)
        self.master_app.registrar_janela_secundaria(self, self.texto)

        rodape = ttk.Frame(self, padding=(16, 8, 16, 16), style="Window.TFrame")
        rodape.pack(fill="x")
        ttk.Button(rodape, text="← Anterior", command=self.anterior).pack(side="left")
        ttk.Button(rodape, text="Salvar decisão", command=self.salvar_atual).pack(side="left", padx=8)
        ttk.Button(rodape, text="Próxima →", command=self.proximo).pack(side="left")
        ttk.Button(rodape, text="Concluir revisão", command=self.concluir).pack(side="right")

        if not self.grupos:
            messagebox.showinfo("Revisão", "Nenhum grupo de forte similaridade foi encontrado.", parent=self)
            self.after(100, self.destroy)
        else:
            self.carregar()

    def carregar(self) -> None:
        grupo = self.grupos[self.indice]
        gid = core.id_grupo_conflito(grupo)
        registro = self.resultado.decisoes_conflitos.get(
            gid, {"decisao": core.DECISAO_NAO_DUPLICADA, "manter": ""}
        )
        letras = [core.rotulo_ocorrencia(i) for i in range(len(grupo))]
        self.combo_manter["values"] = letras
        self.decisao.set(registro.get("decisao", core.DECISAO_NAO_DUPLICADA))
        self.manter.set(registro.get("manter", "") or letras[0])
        self.lbl_pos.config(text=f"Grupo {self.indice + 1} de {len(self.grupos)} • {gid}")
        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        for i, item in enumerate(grupo):
            rotulo = core.rotulo_ocorrencia(i)
            self.texto.insert("end", formatar_questao(item["questao"], rotulo, item["indice"]))
            self.texto.insert("end", "\n" + "=" * 78 + "\n\n")
        self.texto.config(state="disabled")
        self._atualizar_estado_manter()

    def _atualizar_estado_manter(self) -> None:
        if self.decisao.get() == core.DECISAO_DUPLICADA:
            self.combo_manter.configure(state="readonly")
        else:
            self.combo_manter.configure(state="disabled")

    def salvar_atual(self) -> None:
        grupo = self.grupos[self.indice]
        gid = core.id_grupo_conflito(grupo)
        decisao = self.decisao.get()
        manter = self.manter.get() if decisao == core.DECISAO_DUPLICADA else ""
        self.resultado.decisoes_conflitos[gid] = {"decisao": decisao, "manter": manter}
        core.escrever_relatorio_conflitos(
            self.resultado.saida_conflitos,
            self.resultado.conflitos,
            self.resultado.decisoes_conflitos,
            self.resultado.banco_base_revisao,
            self.resultado.candidatos,
        )

    def anterior(self) -> None:
        self.salvar_atual()
        if self.indice > 0:
            self.indice -= 1
            self.carregar()

    def proximo(self) -> None:
        self.salvar_atual()
        if self.indice < len(self.grupos) - 1:
            self.indice += 1
            self.carregar()

    def concluir(self) -> None:
        self.salvar_atual()
        messagebox.showinfo(
            "Revisão salva",
            "As decisões foram salvas no arquivo de conflitos.",
            parent=self,
        )
        self.destroy()


class JanelaRevisaoPossiveis(tk.Toplevel):
    def __init__(self, master: "App", resultado: ResultadoAnalise) -> None:
        super().__init__(master)
        self.master_app = master
        self.resultado = resultado

        pares_fortes: set[tuple[int, int]] = set()
        for grupo in resultado.conflitos:
            posicoes = [item["indice"] for item in grupo]
            for i in range(len(posicoes)):
                for j in range(i + 1, len(posicoes)):
                    pares_fortes.add((posicoes[i], posicoes[j]))

        self.itens = [
            c for c in resultado.candidatos
            if (min(c["a"], c["b"]), max(c["a"], c["b"])) not in pares_fortes
        ]
        self.indice = 0
        self.title("Revisar possíveis duplicatas")
        self.geometry("980x740")
        self.minsize(760, 560)

        self.decisao = tk.StringVar()
        self.manter = tk.StringVar()

        topo = ttk.Frame(self, padding=12)
        topo.pack(fill="x")
        self.lbl_pos = ttk.Label(topo, font=("Segoe UI", 11, "bold"))
        self.lbl_pos.pack(side="left")

        controles = ttk.LabelFrame(self, text="Decisão", padding=10)
        controles.pack(fill="x", padx=12, pady=(0, 8))
        for texto, valor in [
            ("Revisar depois", core.DECISAO_REVISAR),
            ("Não são duplicadas", core.DECISAO_NAO_DUPLICADA),
            ("São duplicadas", core.DECISAO_DUPLICADA),
        ]:
            ttk.Radiobutton(
                controles,
                text=texto,
                variable=self.decisao,
                value=valor,
                command=self._atualizar_estado_manter,
            ).pack(side="left", padx=(0, 12))
        ttk.Label(controles, text="Manter:").pack(side="left", padx=(12, 6))
        self.combo_manter = ttk.Combobox(
            controles, textvariable=self.manter, values=("A", "B"), width=8, state="readonly"
        )
        self.combo_manter.pack(side="left")

        self.lbl_score = ttk.Label(self, padding=(12, 0))
        self.lbl_score.pack(fill="x")

        self.texto = ScrolledText(self, wrap="word", font=("Cascadia Mono", 10), relief="flat", borderwidth=0)
        self.texto.pack(fill="both", expand=True, padx=16, pady=10)
        self.master_app.registrar_janela_secundaria(self, self.texto)

        rodape = ttk.Frame(self, padding=(16, 8, 16, 16), style="Window.TFrame")
        rodape.pack(fill="x")
        ttk.Button(rodape, text="← Anterior", command=self.anterior).pack(side="left")
        ttk.Button(rodape, text="Salvar decisão", command=self.salvar_atual).pack(side="left", padx=8)
        ttk.Button(rodape, text="Próxima →", command=self.proximo).pack(side="left")
        ttk.Button(rodape, text="Concluir revisão", command=self.concluir).pack(side="right")

        if not self.itens:
            messagebox.showinfo("Revisão", "Nenhuma possível duplicata adicional foi encontrada.", parent=self)
            self.after(100, self.destroy)
        else:
            self.carregar()

    def carregar(self) -> None:
        item = self.itens[self.indice]
        pid = core.id_possivel_por_par(item["a"], item["b"])
        registro = self.resultado.decisoes_possiveis.get(
            pid, {"decisao": core.DECISAO_REVISAR, "manter": ""}
        )
        self.decisao.set(registro.get("decisao", core.DECISAO_REVISAR))
        self.manter.set(registro.get("manter", "") or "A")
        self.lbl_pos.config(text=f"Par {self.indice + 1} de {len(self.itens)} • {pid}")
        self.lbl_score.config(
            text=(
                f"Similaridade geral: {float(item['geral']):.1%}  |  "
                f"Enunciado: {float(item['pergunta']):.1%}  |  "
                f"Alternativas: {float(item['opcoes']):.1%}  |  "
                f"Gabarito: {float(item['gabarito']):.1%}"
            )
        )
        qa = self.resultado.banco_base_revisao[item["a"] - 1]
        qb = self.resultado.banco_base_revisao[item["b"] - 1]
        self.texto.config(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("end", formatar_questao(qa, "A", item["a"]))
        self.texto.insert("end", "\n" + "=" * 78 + "\n\n")
        self.texto.insert("end", formatar_questao(qb, "B", item["b"]))
        self.texto.config(state="disabled")
        self._atualizar_estado_manter()

    def _atualizar_estado_manter(self) -> None:
        if self.decisao.get() == core.DECISAO_DUPLICADA:
            self.combo_manter.configure(state="readonly")
        else:
            self.combo_manter.configure(state="disabled")

    def salvar_atual(self, mostrar_confirmacao: bool = True) -> None:
        item = self.itens[self.indice]
        pid = core.id_possivel_por_par(item["a"], item["b"])
        decisao = self.decisao.get()
        manter = self.manter.get() if decisao == core.DECISAO_DUPLICADA else ""
        self.resultado.decisoes_possiveis[pid] = {"decisao": decisao, "manter": manter}
        core.escrever_relatorio_possiveis(
            self.resultado.saida_possiveis,
            self.resultado.candidatos,
            self.resultado.conflitos,
            self.resultado.banco_base_revisao,
            self.resultado.decisoes_possiveis,
        )
        if mostrar_confirmacao:
            messagebox.showinfo(
                "Decisão salva",
                "A decisão desta possível duplicata foi salva.",
                parent=self,
            )

    def anterior(self) -> None:
        if len(self.itens) == 1:
            messagebox.showinfo(
                "Apenas uma revisão",
                "Há apenas uma revisão a ser feita nesta lista.",
                parent=self,
            )
            return
        self.salvar_atual(False)
        if self.indice > 0:
            self.indice -= 1
            self.carregar()

    def proximo(self) -> None:
        if len(self.itens) == 1:
            messagebox.showinfo(
                "Apenas uma revisão",
                "Há apenas uma revisão a ser feita nesta lista.",
                parent=self,
            )
            return
        self.salvar_atual(False)
        if self.indice < len(self.itens) - 1:
            self.indice += 1
            self.carregar()

    def concluir(self) -> None:
        self.salvar_atual(False)
        messagebox.showinfo(
            "Revisão salva",
            "As decisões foram salvas no arquivo de possíveis duplicatas.",
            parent=self,
        )
        self.destroy()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1040x780")
        self.minsize(840, 650)

        self.fila_log: queue.Queue[str] = queue.Queue()
        self.em_execucao = False
        self.resultado: ResultadoAnalise | None = None
        self.janelas_secundarias: list[tuple[tk.Misc, ScrolledText | None]] = []

        self.var_entrada = tk.StringVar()
        self.var_saida = tk.StringVar()
        self.tema_atual = carregar_tema_preferido()
        self.var_tema = tk.StringVar(value=self.tema_atual)

        aplicar_icone(self)
        self._configurar_estilo()
        self._montar_menu()
        self._montar_interface()
        self._aplicar_tema()
        self.after(100, self._consumir_fila)

    @property
    def cores(self) -> dict[str, str]:
        return THEMES[self.tema_atual]

    def _configurar_estilo(self) -> None:
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

    def _montar_menu(self) -> None:
        self.menu_principal = tk.Menu(self, tearoff=False)
        menu_config = tk.Menu(self.menu_principal, tearoff=False)
        menu_aparencia = tk.Menu(menu_config, tearoff=False)

        menu_aparencia.add_radiobutton(
            label="Modo escuro",
            variable=self.var_tema,
            value="dark",
            command=lambda: self._alterar_tema("dark"),
        )
        menu_aparencia.add_radiobutton(
            label="Modo claro",
            variable=self.var_tema,
            value="light",
            command=lambda: self._alterar_tema("light"),
        )
        menu_config.add_cascade(label="Aparência", menu=menu_aparencia)
        self.menu_principal.add_cascade(label="Configurações", menu=menu_config)

        menu_ajuda = tk.Menu(self.menu_principal, tearoff=False)
        menu_ajuda.add_command(label="Sobre", command=self._sobre)
        self.menu_principal.add_cascade(label="Ajuda", menu=menu_ajuda)

        self.config(menu=self.menu_principal)
        self._menus = [self.menu_principal, menu_config, menu_aparencia, menu_ajuda]

    def _alterar_tema(self, tema: str) -> None:
        if tema not in THEMES:
            return
        self.tema_atual = tema
        self.var_tema.set(tema)
        salvar_tema_preferido(tema)
        self._aplicar_tema()

    def _aplicar_tema(self) -> None:
        c = self.cores
        self.configure(bg=c["bg"])

        # Tipografia e superfícies.
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("Window.TFrame", background=c["bg"])
        self.style.configure("Card.TFrame", background=c["surface"])
        self.style.configure(
            "TLabelframe",
            background=c["bg"],
            bordercolor=c["border"],
            relief="solid",
        )
        self.style.configure(
            "TLabelframe.Label",
            background=c["bg"],
            foreground=c["text"],
            font=("Segoe UI", 10, "bold"),
        )
        self.style.configure(
            "TLabel",
            background=c["bg"],
            foreground=c["text"],
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Card.TLabel",
            background=c["surface"],
            foreground=c["text"],
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Title.TLabel",
            background=c["bg"],
            foreground=c["text"],
            font=("Segoe UI Variable Display", 24, "bold"),
        )
        self.style.configure(
            "Subtitle.TLabel",
            background=c["bg"],
            foreground=c["muted"],
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "SectionTitle.TLabel",
            background=c["surface"],
            foreground=c["text"],
            font=("Segoe UI", 11, "bold"),
        )
        self.style.configure(
            "CardMuted.TLabel",
            background=c["surface"],
            foreground=c["muted"],
            font=("Segoe UI", 9),
        )
        self.style.configure(
            "Badge.TLabel",
            background=c["surface_alt"],
            foreground=c["accent"],
            font=("Segoe UI", 9, "bold"),
            padding=(8, 3),
        )

        # Entradas e caixas.
        self.style.configure(
            "Modern.TEntry",
            fieldbackground=c["entry"],
            foreground=c["text"],
            insertcolor=c["text"],
            bordercolor=c["border"],
            lightcolor=c["border"],
            darkcolor=c["border"],
            padding=8,
        )
        self.style.map(
            "Modern.TEntry",
            bordercolor=[("focus", c["accent"])],
            lightcolor=[("focus", c["accent"])],
            darkcolor=[("focus", c["accent"])],
        )
        self.style.configure(
            "Card.TLabelframe",
            background=c["surface"],
            bordercolor=c["border"],
            relief="solid",
        )
        self.style.configure(
            "Card.TLabelframe.Label",
            background=c["surface"],
            foreground=c["text"],
            font=("Segoe UI", 10, "bold"),
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=c["entry"],
            background=c["surface_alt"],
            foreground=c["text"],
            arrowcolor=c["text"],
            bordercolor=c["border"],
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", c["entry"])],
            foreground=[("readonly", c["text"])],
            selectbackground=[("readonly", c["entry"])],
            selectforeground=[("readonly", c["text"])],
        )
        self.style.configure(
            "TRadiobutton",
            background=c["surface"],
            foreground=c["text"],
            font=("Segoe UI", 10),
        )
        self.style.map("TRadiobutton", background=[("active", c["surface"])])

        # Botões modernos e planos.
        self._config_button_style("TButton", c["surface_alt"], c["text"], c["border"])
        self._config_button_style("Modern.TButton", c["surface_alt"], c["text"], c["border"])
        self._config_button_style("Primary.TButton", c["accent"], "#FFFFFF", c["accent"])
        self._config_button_style("Success.TButton", c["success"], "#FFFFFF", c["success"])

        self.style.configure(
            "Modern.Horizontal.TProgressbar",
            troughcolor=c["surface_alt"],
            background=c["accent"],
            bordercolor=c["surface_alt"],
            lightcolor=c["accent"],
            darkcolor=c["accent"],
            thickness=7,
        )

        # Menu clássico precisa de configuração direta.
        for menu in getattr(self, "_menus", []):
            try:
                menu.configure(
                    bg=c["surface"],
                    fg=c["text"],
                    activebackground=c["accent"],
                    activeforeground="#FFFFFF",
                    bd=0,
                    relief="flat",
                )
            except tk.TclError:
                pass

        if hasattr(self, "log"):
            self._estilizar_texto(self.log)

        # Atualiza Toplevels abertos e caixas de comparação.
        vivos: list[tuple[tk.Misc, ScrolledText | None]] = []
        for janela, texto in self.janelas_secundarias:
            try:
                if janela.winfo_exists():
                    janela.configure(bg=c["bg"])
                    if texto is not None:
                        self._estilizar_texto(texto)
                    vivos.append((janela, texto))
            except tk.TclError:
                pass
        self.janelas_secundarias = vivos

    def _config_button_style(self, nome: str, fundo: str, texto: str, borda: str) -> None:
        c = self.cores
        self.style.configure(
            nome,
            background=fundo,
            foreground=texto,
            bordercolor=borda,
            lightcolor=borda,
            darkcolor=borda,
            relief="flat",
            padding=(13, 8),
            font=("Segoe UI", 9, "bold"),
        )
        self.style.map(
            nome,
            background=[
                ("disabled", c["surface_alt"]),
                ("pressed", c["accent_pressed"]),
                ("active", c["accent_hover"]),
            ],
            foreground=[("disabled", c["muted"])],
        )

    def _estilizar_texto(self, widget: ScrolledText) -> None:
        c = self.cores
        widget.configure(
            bg=c["log_bg"],
            fg=c["log_fg"],
            insertbackground=c["text"],
            selectbackground=c["selection"],
            selectforeground=c["text"],
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=c["border"],
            highlightcolor=c["accent"],
        )

    def registrar_janela_secundaria(
        self, janela: tk.Misc, texto: ScrolledText | None = None
    ) -> None:
        aplicar_icone(janela)
        janela.configure(bg=self.cores["bg"])
        self.janelas_secundarias.append((janela, texto))
        if texto is not None:
            self._estilizar_texto(texto)

    def _card(self, parent: tk.Misc) -> ttk.Frame:
        return ttk.Frame(parent, style="Card.TFrame", padding=16)

    def _montar_interface(self) -> None:
        raiz = ttk.Frame(self, style="Window.TFrame", padding=(24, 22))
        raiz.pack(fill="both", expand=True)

        header = ttk.Frame(raiz, style="Window.TFrame")
        header.pack(fill="x", pady=(0, 18))
        titulo_linha = ttk.Frame(header, style="Window.TFrame")
        titulo_linha.pack(fill="x")
        ttk.Label(titulo_linha, text=APP_NAME, style="Title.TLabel").pack(side="left")
        ttk.Label(titulo_linha, text=f"v{APP_VERSION}", style="Badge.TLabel").pack(
            side="left", padx=(12, 0), pady=(4, 0)
        )
        ttk.Label(
            header,
            text="Análise e deduplicação assistida de bancos de questões",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        entrada_card = self._card(raiz)
        entrada_card.pack(fill="x", pady=(0, 12))
        ttk.Label(entrada_card, text="1 · Banco de entrada", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            entrada_card,
            text="Selecione o arquivo JavaScript ou JSON que contém o banco de questões.",
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(3, 10))
        entrada_linha = ttk.Frame(entrada_card, style="Card.TFrame")
        entrada_linha.pack(fill="x")
        ttk.Entry(entrada_linha, textvariable=self.var_entrada, style="Modern.TEntry").pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            entrada_linha, text="Selecionar arquivo", style="Modern.TButton", command=self._selecionar_entrada
        ).pack(side="left", padx=(10, 0))

        saida_card = self._card(raiz)
        saida_card.pack(fill="x", pady=(0, 12))
        ttk.Label(saida_card, text="2 · Pasta de saída", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            saida_card,
            text="Os arquivos gerados serão gravados em uma pasta separada; o original não é sobrescrito.",
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(3, 10))
        saida_linha = ttk.Frame(saida_card, style="Card.TFrame")
        saida_linha.pack(fill="x")
        ttk.Entry(saida_linha, textvariable=self.var_saida, style="Modern.TEntry").pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            saida_linha, text="Selecionar pasta", style="Modern.TButton", command=self._selecionar_saida
        ).pack(side="left", padx=(10, 0))

        acoes_card = self._card(raiz)
        acoes_card.pack(fill="x", pady=(0, 12))
        ttk.Label(acoes_card, text="3 · Analisar e revisar", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            acoes_card,
            text=(
                "A limpeza automática fica restrita a duplicatas integrais ou de alta confiança. "
                "Casos ambíguos permanecem disponíveis para revisão humana."
            ),
            style="CardMuted.TLabel",
            wraplength=900,
        ).pack(anchor="w", pady=(3, 12))

        linha1 = ttk.Frame(acoes_card, style="Card.TFrame")
        linha1.pack(fill="x")
        self.btn_analisar = ttk.Button(
            linha1, text="▶  Analisar banco", style="Primary.TButton", command=self._iniciar_analise
        )
        self.btn_analisar.pack(side="left")
        self.btn_revisar_conflitos = ttk.Button(
            linha1,
            text="Revisar grupos fortes",
            style="Modern.TButton",
            command=self._revisar_conflitos,
            state="disabled",
        )
        self.btn_revisar_conflitos.pack(side="left", padx=(8, 0))
        self.btn_revisar_possiveis = ttk.Button(
            linha1,
            text="Revisar possíveis duplicatas",
            style="Modern.TButton",
            command=self._revisar_possiveis,
            state="disabled",
        )
        self.btn_revisar_possiveis.pack(side="left", padx=(8, 0))

        linha2 = ttk.Frame(acoes_card, style="Card.TFrame")
        linha2.pack(fill="x", pady=(8, 0))
        self.btn_aplicar = ttk.Button(
            linha2,
            text="✓  Aplicar decisões e gerar banco final",
            style="Success.TButton",
            command=self._iniciar_aplicacao,
            state="disabled",
        )
        self.btn_aplicar.pack(side="left")
        self.btn_abrir_pasta = ttk.Button(
            linha2,
            text="Abrir pasta de saída",
            style="Modern.TButton",
            command=self._abrir_saida,
            state="disabled",
        )
        self.btn_abrir_pasta.pack(side="left", padx=(8, 0))
        self.btn_abrir_banco = ttk.Button(
            linha2,
            text="Abrir banco gerado",
            style="Modern.TButton",
            command=self._abrir_banco,
            state="disabled",
        )
        self.btn_abrir_banco.pack(side="left", padx=(8, 0))

        status_card = self._card(raiz)
        status_card.pack(fill="both", expand=True)
        status_top = ttk.Frame(status_card, style="Card.TFrame")
        status_top.pack(fill="x", pady=(0, 10))
        ttk.Label(status_top, text="Progresso e mensagens", style="SectionTitle.TLabel").pack(side="left")
        ttk.Label(
            status_top,
            text=f"RapidFuzz: {'ativo' if core.RAPIDFUZZ_DISPONIVEL else 'fallback'}",
            style="CardMuted.TLabel",
        ).pack(side="right")

        self.progress = ttk.Progressbar(
            status_card, mode="indeterminate", style="Modern.Horizontal.TProgressbar"
        )
        self.progress.pack(fill="x", pady=(0, 10))
        self.log = ScrolledText(
            status_card,
            height=13,
            wrap="word",
            font=("Cascadia Mono", 9),
            relief="flat",
            borderwidth=0,
        )
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        rodape = ttk.Frame(raiz, style="Window.TFrame")
        rodape.pack(fill="x", pady=(12, 0))
        ttk.Label(
            rodape,
            text="Configurações → Aparência permite alternar entre os modos escuro e claro.",
            style="Subtitle.TLabel",
        ).pack(side="left")
        ttk.Button(rodape, text="Sobre", style="Modern.TButton", command=self._sobre).pack(side="right")

    def _selecionar_entrada(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecione o banco de questões",
            filetypes=[
                ("Banco JavaScript", "*.js"),
                ("Arquivos JSON", "*.json"),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if caminho:
            self.var_entrada.set(caminho)
            if not self.var_saida.get():
                self.var_saida.set(str(Path(caminho).parent / "saida_question_bank_cleaner"))

    def _selecionar_saida(self) -> None:
        caminho = filedialog.askdirectory(title="Selecione a pasta de saída")
        if caminho:
            self.var_saida.set(caminho)

    def _validar_caminhos(self) -> tuple[Path, Path] | None:
        entrada = Path(self.var_entrada.get().strip())
        saida_texto = self.var_saida.get().strip()
        if not entrada.is_file():
            messagebox.showerror("Arquivo inválido", "Selecione um arquivo de banco de questões existente.")
            return None
        if not saida_texto:
            messagebox.showerror("Pasta de saída", "Selecione uma pasta de saída.")
            return None
        return entrada, Path(saida_texto)

    def _set_execucao(self, ativo: bool) -> None:
        self.em_execucao = ativo
        self.btn_analisar.configure(state="disabled" if ativo else "normal")
        if ativo:
            self.progress.start(10)
        else:
            self.progress.stop()

    def _iniciar_analise(self) -> None:
        if self.em_execucao:
            return
        validado = self._validar_caminhos()
        if not validado:
            return
        entrada, saida = validado
        self._set_execucao(True)
        self._log_limpar()

        def tarefa() -> None:
            escritor = QueueWriter(self.fila_log)
            try:
                with contextlib.redirect_stdout(escritor), contextlib.redirect_stderr(escritor):
                    resultado = analisar_banco(entrada, saida)
                self.after(0, lambda: self._analise_concluida(resultado))
            except Exception:
                detalhe = traceback.format_exc()
                self.fila_log.put(detalhe + "\n")
                self.after(0, lambda: self._falha("Não foi possível concluir a análise. Consulte o log."))
            finally:
                escritor.flush()

        threading.Thread(target=tarefa, daemon=True).start()

    def _analise_concluida(self, resultado: ResultadoAnalise) -> None:
        self.resultado = resultado
        self._set_execucao(False)
        self.btn_revisar_conflitos.configure(state="normal")
        self.btn_revisar_possiveis.configure(state="normal")
        self.btn_aplicar.configure(state="normal")
        self.btn_abrir_pasta.configure(state="normal")
        self.btn_abrir_banco.configure(state="normal")
        messagebox.showinfo(
            "Análise concluída",
            (
                f"Questões originais: {len(resultado.banco_original)}\n"
                f"Removidas automaticamente: {len(resultado.removidas_integras) + len(resultado.removidas_alta)}\n"
                f"Grupos fortes para revisão: {len(resultado.conflitos)}\n\n"
                "Revise os itens ambíguos antes de aplicar decisões."
            ),
        )

    def _revisar_conflitos(self) -> None:
        if self.resultado:
            JanelaRevisaoConflitos(self, self.resultado)

    def _revisar_possiveis(self) -> None:
        if self.resultado:
            JanelaRevisaoPossiveis(self, self.resultado)

    def _iniciar_aplicacao(self) -> None:
        if self.em_execucao or not self.resultado:
            return
        if not messagebox.askyesno(
            "Aplicar decisões",
            (
                "As decisões registradas nos relatórios serão aplicadas ao banco.\n\n"
                "Itens ainda marcados como REVISAR não serão removidos. "
                "Deseja continuar?"
            ),
        ):
            return
        self._set_execucao(True)

        def tarefa() -> None:
            escritor = QueueWriter(self.fila_log)
            try:
                with contextlib.redirect_stdout(escritor), contextlib.redirect_stderr(escritor):
                    resultado = aplicar_decisoes(self.resultado)
                self.after(0, lambda: self._aplicacao_concluida(resultado))
            except Exception:
                self.fila_log.put(traceback.format_exc() + "\n")
                self.after(0, lambda: self._falha("Não foi possível aplicar as decisões. Consulte o log."))
            finally:
                escritor.flush()

        threading.Thread(target=tarefa, daemon=True).start()

    def _aplicacao_concluida(self, resultado: ResultadoAnalise) -> None:
        self.resultado = resultado
        self._set_execucao(False)
        messagebox.showinfo(
            "Banco final gerado",
            (
                f"Total final: {len(resultado.banco_final)} questões.\n"
                f"Removidas por decisões: {len(resultado.removidas_decisoes)}\n\n"
                f"Arquivo:\n{resultado.saida_js}"
            ),
        )

    def _falha(self, mensagem: str) -> None:
        self._set_execucao(False)
        messagebox.showerror("Erro", mensagem)

    def _abrir_saida(self) -> None:
        if self.resultado:
            try:
                abrir_no_sistema(self.resultado.pasta_saida)
            except Exception as erro:
                messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{erro}")

    def _abrir_banco(self) -> None:
        if self.resultado and self.resultado.saida_js.exists():
            try:
                abrir_no_sistema(self.resultado.saida_js)
            except Exception as erro:
                messagebox.showerror("Erro", f"Não foi possível abrir o arquivo:\n{erro}")

    def _log_limpar(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _consumir_fila(self) -> None:
        try:
            while True:
                msg = self.fila_log.get_nowait()
                self.log.configure(state="normal")
                self.log.insert("end", msg)
                self.log.see("end")
                self.log.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._consumir_fila)

    def _sobre(self) -> None:
        messagebox.showinfo(
            f"Sobre o {APP_NAME}",
            (
                f"{APP_NAME} {APP_VERSION}\n\n"
                "Aplicação desktop para análise e deduplicação assistida de bancos de questões.\n\n"
                "Desenvolvido de forma independente por Pablo Phillipe Cândido dos Santos.\n"
                "Ferramentas de IA generativa foram utilizadas como recurso auxiliar no desenvolvimento.\n\n"
                "Currículo Lattes:\nhttp://lattes.cnpq.br/9500873674712528"
            ),
        )


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
