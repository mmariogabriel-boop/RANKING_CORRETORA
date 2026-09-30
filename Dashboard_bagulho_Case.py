import os
import textwrap
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
    KeepTogether
)


# =========================================================
# CONFIGURAÇÃO
# =========================================================
st.set_page_config(
    page_title="Entradas x Saídas de Vidas",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Entradas x Saídas de Vidas")
st.caption(
    "Dashboard baseado no relatório consolidado por mês e corretora."
)


# =========================================================
# IDENTIDADE VISUAL
# =========================================================
VERDE_MEDIATORIE = "#84BD22"
VERDE_ESCURO = "#5E8618"
CINZA = "#737A76"
CINZA_CLARO = "#F3F5F2"
CINZA_TEXTO = "#4D4D4D"
VERMELHO_SAIDA = "#B45B5B"


# =========================================================
# FUNÇÕES BÁSICAS
# =========================================================
def percentual(numerador, denominador):
    if denominador == 0:
        return 0
    return (numerador / denominador) * 100


def formatar_inteiro(valor):
    return f"{int(round(valor)):,}".replace(",", ".")


def formatar_percentual(valor):
    return f"{valor:.1f}%".replace(".", ",")


def nome_curto(texto, limite=42):
    texto = str(texto)
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3] + "..."


def localizar_logo_mediatorie():
    """
    Procura a logo na pasta do script e, como segunda opção,
    no diretório atual.
    """
    pasta_script = os.path.dirname(os.path.abspath(__file__))

    nomes = [
        "logo_mediatorie.png",
        "mediatorie.png",
        "logo.png"
    ]

    for nome in nomes:
        candidatos = [
            os.path.join(pasta_script, nome),
            nome
        ]

        for caminho in candidatos:
            if os.path.exists(caminho):
                return caminho

    return None


# =========================================================
# CARREGAMENTO DA BASE
# =========================================================
def carregar_base():
    """
    Procura Relatoriov2.xlsx na mesma pasta do app.
    Caso não encontre, libera upload pelo menu lateral.
    """
    arquivo_padrao = "Relatoriov2.xlsx"

    if os.path.exists(arquivo_padrao):
        st.sidebar.success(
            f"Base carregada: {arquivo_padrao}"
        )
        return pd.read_excel(arquivo_padrao)

    arquivo = st.sidebar.file_uploader(
        "Selecione o relatório",
        type=["xlsx", "xls"]
    )

    if arquivo is None:
        st.info(
            "Coloque o arquivo Relatoriov2.xlsx na mesma pasta "
            "do aplicativo ou envie a planilha pelo menu lateral."
        )
        st.stop()

    return pd.read_excel(arquivo)


# =========================================================
# TOP 10
# =========================================================
def preparar_top10_corretoras(
    df,
    coluna_vida_nova,
    coluna_movimentacao,
    coluna_saida
):
    """
    Ranking consolidado por nome da corretora.

    Entradas = Vida Nova + Movimentação
    Saldo    = Entradas - Saídas
    """

    ranking = (
        df.groupby(
            "Corretora",
            as_index=False
        )[
            [
                coluna_vida_nova,
                coluna_movimentacao,
                coluna_saida
            ]
        ]
        .sum()
    )

    ranking = ranking.rename(
        columns={
            coluna_vida_nova: "Vida Nova",
            coluna_movimentacao: "Movimentação",
            coluna_saida: "Saídas"
        }
    )

    ranking["Entradas"] = (
        ranking["Vida Nova"]
        + ranking["Movimentação"]
    )

    ranking["Saldo"] = (
        ranking["Entradas"]
        - ranking["Saídas"]
    )

    ranking["% Evasão"] = ranking.apply(
        lambda linha: percentual(
            linha["Saídas"],
            linha["Entradas"]
        ),
        axis=1
    )

    colunas = [
        "Corretora",
        "Vida Nova",
        "Movimentação",
        "Entradas",
        "Saídas",
        "Saldo",
        "% Evasão"
    ]

    top_entradas = (
        ranking[colunas]
        .sort_values(
            ["Entradas", "Corretora"],
            ascending=[False, True]
        )
        .head(10)
        .reset_index(drop=True)
    )

    top_saidas = (
        ranking[colunas]
        .sort_values(
            ["Saídas", "Corretora"],
            ascending=[False, True]
        )
        .head(10)
        .reset_index(drop=True)
    )

    top_entradas.index = top_entradas.index + 1
    top_saidas.index = top_saidas.index + 1

    return top_entradas, top_saidas


# =========================================================
# GRÁFICO TOP 10 - STREAMLIT
# =========================================================
def grafico_top10_streamlit(
    ranking,
    coluna,
    titulo,
    cor
):
    """
    Gráfico horizontal por corretora.
    Ordena de modo que a maior corretora apareça no topo.
    """

    dados = (
        ranking
        .reset_index()
        .rename(columns={"index": "Posição"})
        .sort_values(coluna, ascending=True)
        .copy()
    )

    dados["Corretora Curta"] = dados["Corretora"].apply(
        lambda x: nome_curto(x, 38)
    )

    fig = go.Figure()

    fig.add_bar(
        x=dados[coluna],
        y=dados["Corretora Curta"],
        orientation="h",
        text=dados[coluna].apply(formatar_inteiro),
        textposition="outside",
        customdata=dados[
            [
                "Corretora",
                "Vida Nova",
                "Movimentação",
                "Entradas",
                "Saídas",
                "Saldo",
                "% Evasão"
            ]
        ],
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Vida Nova: %{customdata[1]:,.0f}<br>"
            "Movimentação: %{customdata[2]:,.0f}<br>"
            "Entradas: %{customdata[3]:,.0f}<br>"
            "Saídas: %{customdata[4]:,.0f}<br>"
            "Saldo: %{customdata[5]:,.0f}<br>"
            "Evasão: %{customdata[6]:.1f}%"
            "<extra></extra>"
        ),
        marker_color=cor,
        name=coluna
    )

    fig.update_layout(
        title={
            "text": titulo,
            "x": 0.01,
            "xanchor": "left"
        },
        height=520,
        xaxis_title="Quantidade de vidas",
        yaxis_title="",
        showlegend=False,
        margin=dict(
            l=20,
            r=85,
            t=60,
            b=40
        )
    )

    fig.update_xaxes(
        rangemode="tozero",
        gridcolor="#E6E6E6"
    )

    fig.update_yaxes(
        automargin=True
    )

    return fig


# =========================================================
# GRÁFICO TOP 10 - PDF
# =========================================================
def grafico_ranking_pdf(
    ranking,
    coluna,
    titulo,
    cor
):
    """
    Gera PNG do ranking em memória para incorporar ao PDF.
    """

    dados = ranking.sort_values(
        coluna,
        ascending=True
    ).copy()

    labels = [
        "\n".join(
            textwrap.wrap(
                str(nome),
                width=34
            )
        )
        for nome in dados["Corretora"]
    ]

    valores = dados[coluna].astype(float).tolist()

    fig, ax = plt.subplots(
        figsize=(9.3, 4.2)
    )

    barras = ax.barh(
        labels,
        valores,
        color=cor
    )

    maior = max(valores) if valores else 0
    folga = max(maior * 0.08, 1)

    for barra, valor in zip(
        barras,
        valores
    ):
        ax.text(
            barra.get_width() + folga * 0.10,
            barra.get_y() + barra.get_height() / 2,
            formatar_inteiro(valor),
            va="center",
            ha="left",
            fontsize=8,
            fontweight="bold"
        )

    ax.set_title(
        titulo,
        loc="left",
        fontsize=11,
        fontweight="bold"
    )

    ax.set_xlabel(
        "Quantidade de vidas",
        fontsize=8
    )

    ax.tick_params(
        axis="x",
        labelsize=8
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    ax.grid(
        axis="x",
        alpha=0.18
    )

    ax.set_axisbelow(True)

    if maior > 0:
        ax.set_xlim(
            0,
            maior + folga
        )

    for lado in [
        "top",
        "right",
        "left"
    ]:
        ax.spines[lado].set_visible(False)

    plt.tight_layout()

    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=180,
        bbox_inches="tight",
        transparent=False
    )

    plt.close(fig)

    buffer.seek(0)

    return buffer


# =========================================================
# PDF - CABEÇALHO E RODAPÉ
# =========================================================
def desenhar_cabecalho_rodape(canvas, doc):
    largura, altura = A4

    canvas.saveState()

    # Cabeçalho
    canvas.setFont(
        "Helvetica-Bold",
        7.5
    )

    canvas.setFillColor(
        colors.HexColor(VERDE_ESCURO)
    )

    canvas.drawString(
        1.25 * cm,
        altura - 0.9 * cm,
        "MEDIATORIE | DASHBOARD ENTRADAS X SAIDAS"
    )

    canvas.setStrokeColor(
        colors.HexColor(VERDE_MEDIATORIE)
    )

    canvas.setLineWidth(0.8)

    canvas.line(
        1.25 * cm,
        altura - 1.05 * cm,
        largura - 1.25 * cm,
        altura - 1.05 * cm
    )

    # Rodapé
    canvas.setFillColor(
        colors.HexColor("#777777")
    )

    canvas.setFont(
        "Helvetica",
        6.5
    )

    canvas.drawString(
        1.25 * cm,
        0.65 * cm,
        "Mediatorie Administradora de Beneficios"
    )

    canvas.drawRightString(
        largura - 1.25 * cm,
        0.65 * cm,
        f"Pagina {doc.page}"
    )

    canvas.restoreState()


# =========================================================
# PDF - ESTILOS
# =========================================================
def estilos_pdf():
    estilos = getSampleStyleSheet()

    titulo = ParagraphStyle(
        "TituloMediatorie",
        parent=estilos["Title"],
        fontName="Helvetica-Bold",
        fontSize=19,
        leading=23,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#343834"),
        spaceAfter=7
    )

    subtitulo = ParagraphStyle(
        "SubtituloMediatorie",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#777777"),
        spaceAfter=10
    )

    secao = ParagraphStyle(
        "SecaoMediatorie",
        parent=estilos["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        alignment=TA_LEFT,
        textColor=colors.HexColor(VERDE_ESCURO),
        spaceBefore=5,
        spaceAfter=8
    )

    texto = ParagraphStyle(
        "TextoMediatorie",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor(CINZA_TEXTO)
    )

    pequeno = ParagraphStyle(
        "PequenoMediatorie",
        parent=estilos["Normal"],
        fontName="Helvetica",
        fontSize=6.7,
        leading=8,
        textColor=colors.HexColor(CINZA_TEXTO)
    )

    return titulo, subtitulo, secao, texto, pequeno


# =========================================================
# PDF - TABELA DE FILTROS
# =========================================================
def tabela_filtros_pdf(
    ano_selecionado,
    corretora_selecionada
):
    dados = [
        ["Gerado em", datetime.now().strftime("%d/%m/%Y %H:%M")],
        ["Base", "Relatoriov2.xlsx"],
        ["Ano", str(ano_selecionado)],
        ["Corretora", str(corretora_selecionada)]
    ]

    tabela = Table(
        dados,
        colWidths=[
            4.2 * cm,
            11.0 * cm
        ]
    )

    tabela.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#EFF5E6")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (0, -1),
                    colors.HexColor(VERDE_ESCURO)
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold"
                ),
                (
                    "FONTNAME",
                    (1, 0),
                    (1, -1),
                    "Helvetica"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7.5
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor("#D7DDD2")
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                )
            ]
        )
    )

    return tabela


# =========================================================
# PDF - TABELA DE RANKING
# =========================================================
def tabela_ranking_pdf(
    ranking,
    destaque
):
    _, _, _, _, estilo_pequeno = estilos_pdf()

    cabecalho = [
        "Pos.",
        "Corretora",
        "Vida Nova",
        "Mov.",
        "Entradas",
        "Saidas",
        "Saldo",
        "% Evasao"
    ]

    dados = [cabecalho]

    for posicao, linha in ranking.iterrows():
        dados.append(
            [
                str(posicao),
                Paragraph(
                    str(linha["Corretora"]),
                    estilo_pequeno
                ),
                formatar_inteiro(
                    linha["Vida Nova"]
                ),
                formatar_inteiro(
                    linha["Movimentação"]
                ),
                formatar_inteiro(
                    linha["Entradas"]
                ),
                formatar_inteiro(
                    linha["Saídas"]
                ),
                formatar_inteiro(
                    linha["Saldo"]
                ),
                formatar_percentual(
                    linha["% Evasão"]
                )
            ]
        )

    tabela = Table(
        dados,
        colWidths=[
            0.8 * cm,
            7.2 * cm,
            1.55 * cm,
            1.35 * cm,
            1.55 * cm,
            1.45 * cm,
            1.35 * cm,
            1.55 * cm
        ],
        repeatRows=1
    )

    estilos = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor(VERDE_MEDIATORIE)
        ),
        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),
        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        ),
        (
            "FONTSIZE",
            (0, 0),
            (-1, 0),
            6.5
        ),
        (
            "FONTSIZE",
            (0, 1),
            (-1, -1),
            6.5
        ),
        (
            "ALIGN",
            (0, 0),
            (0, -1),
            "CENTER"
        ),
        (
            "ALIGN",
            (2, 1),
            (-1, -1),
            "RIGHT"
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE"
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.3,
            colors.HexColor("#D8DDD5")
        ),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor("#F5F7F4")
            ]
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            4
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            4
        )
    ]

    mapa_colunas = {
        "Entradas": 4,
        "Saídas": 5
    }

    coluna_destaque = mapa_colunas[destaque]

    estilos.append(
        (
            "FONTNAME",
            (coluna_destaque, 1),
            (coluna_destaque, -1),
            "Helvetica-Bold"
        )
    )

    tabela.setStyle(
        TableStyle(estilos)
    )

    return tabela


# =========================================================
# PDF - DETALHAMENTO POR CORRETORA
# =========================================================
def preparar_mensal_corretora_pdf(df_corretora, competencias):
    """
    Consolida uma corretora por competência.
    O período é reindexado para que meses sem movimento apareçam com zero.
    """

    colunas_base = [
        "Vida Nova Saúde",
        "Movimentação Saúde",
        "Saída Saúde",
        "Saldo Saúde",
        "Vida Nova Odonto",
        "Movimentação Odonto",
        "Saída Odonto",
        "Saldo Odonto",
        "Saldo Geral"
    ]

    mensal = (
        df_corretora
        .groupby("Mês")[colunas_base]
        .sum()
        .reindex(competencias, fill_value=0)
        .reset_index()
    )

    mensal["Entradas Saúde"] = (
        mensal["Vida Nova Saúde"]
        + mensal["Movimentação Saúde"]
    )

    mensal["Entradas Odonto"] = (
        mensal["Vida Nova Odonto"]
        + mensal["Movimentação Odonto"]
    )

    # Recalcula os saldos para garantir coerência visual no PDF.
    mensal["Saldo Saúde"] = (
        mensal["Entradas Saúde"]
        - mensal["Saída Saúde"]
    )

    mensal["Saldo Odonto"] = (
        mensal["Entradas Odonto"]
        - mensal["Saída Odonto"]
    )

    mensal["Saldo Geral"] = (
        mensal["Saldo Saúde"]
        + mensal["Saldo Odonto"]
    )

    return mensal


def resumo_corretora_pdf(df_corretora):
    """Retorna uma tabela-resumo de Saúde, Odonto e Total."""

    vida_nova_saude = df_corretora["Vida Nova Saúde"].sum()
    mov_saude = df_corretora["Movimentação Saúde"].sum()
    saida_saude = df_corretora["Saída Saúde"].sum()
    entrada_saude = vida_nova_saude + mov_saude
    saldo_saude = entrada_saude - saida_saude
    evasao_saude = percentual(saida_saude, entrada_saude)

    vida_nova_odonto = df_corretora["Vida Nova Odonto"].sum()
    mov_odonto = df_corretora["Movimentação Odonto"].sum()
    saida_odonto = df_corretora["Saída Odonto"].sum()
    entrada_odonto = vida_nova_odonto + mov_odonto
    saldo_odonto = entrada_odonto - saida_odonto
    evasao_odonto = percentual(saida_odonto, entrada_odonto)

    vida_nova_total = vida_nova_saude + vida_nova_odonto
    mov_total = mov_saude + mov_odonto
    entrada_total = entrada_saude + entrada_odonto
    saida_total = saida_saude + saida_odonto
    saldo_total = saldo_saude + saldo_odonto
    evasao_total = percentual(saida_total, entrada_total)

    dados = [
        [
            "Produto",
            "Vida Nova",
            "Movimentacao",
            "Entradas",
            "Saidas",
            "Saldo",
            "% Evasao"
        ],
        [
            "Saude",
            formatar_inteiro(vida_nova_saude),
            formatar_inteiro(mov_saude),
            formatar_inteiro(entrada_saude),
            formatar_inteiro(saida_saude),
            formatar_inteiro(saldo_saude),
            formatar_percentual(evasao_saude)
        ],
        [
            "Odonto",
            formatar_inteiro(vida_nova_odonto),
            formatar_inteiro(mov_odonto),
            formatar_inteiro(entrada_odonto),
            formatar_inteiro(saida_odonto),
            formatar_inteiro(saldo_odonto),
            formatar_percentual(evasao_odonto)
        ],
        [
            "Total",
            formatar_inteiro(vida_nova_total),
            formatar_inteiro(mov_total),
            formatar_inteiro(entrada_total),
            formatar_inteiro(saida_total),
            formatar_inteiro(saldo_total),
            formatar_percentual(evasao_total)
        ]
    ]

    tabela = Table(
        dados,
        colWidths=[
            2.25 * cm,
            2.25 * cm,
            2.45 * cm,
            2.25 * cm,
            2.15 * cm,
            2.15 * cm,
            2.15 * cm
        ]
    )

    tabela.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#EFF5E6")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(VERDE_ESCURO)
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "FONTNAME",
                    (0, -1),
                    (-1, -1),
                    "Helvetica-Bold"
                ),
                (
                    "ALIGN",
                    (1, 0),
                    (-1, -1),
                    "CENTER"
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#D7DDD2")
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F7F8F6")
                    ]
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7.0
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                )
            ]
        )
    )

    return tabela


def grafico_corretora_pdf(mensal, corretora):
    """
    Gráfico mensal de entradas x saídas para Saúde e Odonto.
    """

    if mensal.empty:
        return None

    labels = mensal["Mês"].dt.strftime("%m/%Y").tolist()
    x = np.arange(len(labels))
    largura = 0.20

    fig, ax = plt.subplots(figsize=(9.4, 3.5))

    series = [
        (
            mensal["Entradas Saúde"].astype(float).tolist(),
            -1.5 * largura,
            "Entradas Saude",
            VERDE_MEDIATORIE
        ),
        (
            mensal["Saída Saúde"].astype(float).tolist(),
            -0.5 * largura,
            "Saidas Saude",
            CINZA
        ),
        (
            mensal["Entradas Odonto"].astype(float).tolist(),
            0.5 * largura,
            "Entradas Odonto",
            VERDE_ESCURO
        ),
        (
            mensal["Saída Odonto"].astype(float).tolist(),
            1.5 * largura,
            "Saidas Odonto",
            "#A9ADAA"
        )
    ]

    maior = 0

    for valores, deslocamento, legenda, cor in series:
        barras = ax.bar(
            x + deslocamento,
            valores,
            width=largura,
            label=legenda,
            color=cor
        )

        if valores:
            maior = max(maior, max(valores))

        for barra, valor in zip(barras, valores):
            if valor > 0:
                ax.text(
                    barra.get_x() + barra.get_width() / 2,
                    barra.get_height() + max(maior * 0.012, 0.25),
                    formatar_inteiro(valor),
                    ha="center",
                    va="bottom",
                    fontsize=5.5,
                    rotation=0
                )

    ax.set_title(
        "Entradas x Saidas por competencia",
        loc="left",
        fontsize=10.5,
        fontweight="bold"
    )

    ax.set_xticks(x)
    ax.set_xticklabels(
        labels,
        rotation=35,
        ha="right",
        fontsize=7
    )

    ax.tick_params(
        axis="y",
        labelsize=7
    )

    ax.set_ylabel(
        "Quantidade de vidas",
        fontsize=7
    )

    ax.grid(
        axis="y",
        alpha=0.18
    )

    ax.set_axisbelow(True)

    ax.legend(
        fontsize=6.3,
        ncol=4,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.02),
        frameon=False
    )

    for lado in [
        "top",
        "right",
        "left"
    ]:
        ax.spines[lado].set_visible(False)

    if maior > 0:
        ax.set_ylim(
            0,
            maior * 1.20 + 1
        )

    plt.tight_layout()

    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=135,
        bbox_inches="tight",
        transparent=False
    )

    plt.close(fig)
    buffer.seek(0)

    return buffer


def tabela_mensal_corretora_pdf(mensal):
    """Tabela consolidada por competência para uma corretora."""

    _, _, _, _, estilo_pequeno = estilos_pdf()

    dados = [
        [
            "Competencia",
            "Entr. Saude",
            "Saida Saude",
            "Saldo Saude",
            "Entr. Odonto",
            "Saida Odonto",
            "Saldo Odonto",
            "Saldo Geral"
        ]
    ]

    for _, linha in mensal.iterrows():
        dados.append(
            [
                linha["Mês"].strftime("%m/%Y"),
                formatar_inteiro(linha["Entradas Saúde"]),
                formatar_inteiro(linha["Saída Saúde"]),
                formatar_inteiro(linha["Saldo Saúde"]),
                formatar_inteiro(linha["Entradas Odonto"]),
                formatar_inteiro(linha["Saída Odonto"]),
                formatar_inteiro(linha["Saldo Odonto"]),
                formatar_inteiro(linha["Saldo Geral"])
            ]
        )

    tabela = Table(
        dados,
        colWidths=[
            2.0 * cm,
            2.15 * cm,
            2.0 * cm,
            2.0 * cm,
            2.15 * cm,
            2.0 * cm,
            2.0 * cm,
            2.0 * cm
        ],
        repeatRows=1
    )

    tabela.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(VERDE_MEDIATORIE)
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    6.3
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#D8DDD5")
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F5F7F4")
                    ]
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3.5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3.5
                )
            ]
        )
    )

    return tabela


# =========================================================
# PDF COMPLETO - SAÚDE + ODONTO
# =========================================================
def gerar_pdf_top10_completo(
    ano_selecionado,
    corretora_selecionada,
    top_entradas_saude,
    top_saidas_saude,
    top_entradas_odonto,
    top_saidas_odonto,
    df_detalhe
):
    """
    Gera UM ÚNICO PDF:
    1 - Capa
    2 - Top 10 Entradas Saúde
    3 - Top 10 Saídas Saúde
    4 - Top 10 Entradas Odonto
    5 - Top 10 Saídas Odonto
    6 em diante - Uma página individual para cada corretora
    """

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.25 * cm,
        leftMargin=1.25 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.15 * cm
    )

    titulo, subtitulo, secao, texto, _ = estilos_pdf()

    story = []

    # -----------------------------------------------------
    # CAPA
    # -----------------------------------------------------
    logo_local = localizar_logo_mediatorie()

    story.append(
        Spacer(
            1,
            1.5 * cm
        )
    )

    if logo_local:
        story.append(
            RLImage(
                logo_local,
                width=5.5 * cm,
                height=2.2 * cm
            )
        )
        story[-1].hAlign = "CENTER"

        story.append(
            Spacer(
                1,
                0.35 * cm
            )
        )

    story.append(
        Paragraph(
            "Relatorio Gerencial - Entradas x Saidas",
            titulo
        )
    )

    story.append(
        Paragraph(
            "Top 10 e detalhamento individual por corretora - Saude e Odonto.",
            subtitulo
        )
    )

    story.append(
        Spacer(
            1,
            0.25 * cm
        )
    )

    story.append(
        tabela_filtros_pdf(
            ano_selecionado=ano_selecionado,
            corretora_selecionada=corretora_selecionada
        )
    )

    story.append(
        Spacer(
            1,
            0.35 * cm
        )
    )

    story.append(
        Paragraph(
            "O relatorio utiliza o mesmo recorte de filtros aplicado "
            "no dashboard no momento da geracao.",
            texto
        )
    )

    quantidade_corretoras_pdf = int(
        df_detalhe["Corretora"].nunique()
    )

    story.append(
        Spacer(1, 0.18 * cm)
    )

    story.append(
        Paragraph(
            f"O arquivo inclui {quantidade_corretoras_pdf} pagina(s) "
            "de detalhamento individual por corretora.",
            texto
        )
    )

    story.append(
        PageBreak()
    )

    # -----------------------------------------------------
    # FUNÇÃO INTERNA PARA PÁGINA DO RANKING
    # -----------------------------------------------------
    def adicionar_pagina_ranking(
        produto,
        tipo_ranking,
        ranking,
        coluna,
        cor
    ):
        story.append(
            Paragraph(
                f"{produto} - Top 10 Corretoras por {tipo_ranking}",
                secao
            )
        )

        total_ranking = ranking[coluna].sum()

        resumo_cards = Table(
            [
                [
                    f"Corretoras no ranking",
                    f"Total de {tipo_ranking.lower()}",
                    "Maior valor"
                ],
                [
                    str(len(ranking)),
                    formatar_inteiro(
                        total_ranking
                    ),
                    formatar_inteiro(
                        ranking[coluna].max()
                        if not ranking.empty
                        else 0
                    )
                ]
            ],
            colWidths=[
                5.1 * cm,
                5.1 * cm,
                5.1 * cm
            ]
        )

        resumo_cards.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#EFF5E6")
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(VERDE_ESCURO)
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "FONTNAME",
                        (0, 1),
                        (-1, 1),
                        "Helvetica-Bold"
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.HexColor("#D7DDD2")
                    ),
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        7.5
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    )
                ]
            )
        )

        story.append(
            resumo_cards
        )

        story.append(
            Spacer(
                1,
                0.3 * cm
            )
        )

        imagem_grafico = grafico_ranking_pdf(
            ranking=ranking,
            coluna=coluna,
            titulo=f"{produto} - Top 10 por {tipo_ranking}",
            cor=cor
        )

        story.append(
            RLImage(
                imagem_grafico,
                width=17.4 * cm,
                height=7.2 * cm
            )
        )

        story.append(
            Spacer(
                1,
                0.15 * cm
            )
        )

        story.append(
            tabela_ranking_pdf(
                ranking=ranking,
                destaque=coluna
            )
        )

        story.append(
            PageBreak()
        )

    # SAÚDE
    adicionar_pagina_ranking(
        produto="Saude",
        tipo_ranking="Entradas",
        ranking=top_entradas_saude,
        coluna="Entradas",
        cor=VERDE_MEDIATORIE
    )

    adicionar_pagina_ranking(
        produto="Saude",
        tipo_ranking="Saidas",
        ranking=top_saidas_saude,
        coluna="Saídas",
        cor=CINZA
    )

    # ODONTO
    adicionar_pagina_ranking(
        produto="Odonto",
        tipo_ranking="Entradas",
        ranking=top_entradas_odonto,
        coluna="Entradas",
        cor=VERDE_MEDIATORIE
    )

    # última página sem PageBreak extra ao final
    story.append(
        Paragraph(
            "Odonto - Top 10 Corretoras por Saidas",
            secao
        )
    )

    resumo_cards_odonto = Table(
        [
            [
                "Corretoras no ranking",
                "Total de saidas",
                "Maior valor"
            ],
            [
                str(len(top_saidas_odonto)),
                formatar_inteiro(
                    top_saidas_odonto["Saídas"].sum()
                ),
                formatar_inteiro(
                    top_saidas_odonto["Saídas"].max()
                    if not top_saidas_odonto.empty
                    else 0
                )
            ]
        ],
        colWidths=[
            5.1 * cm,
            5.1 * cm,
            5.1 * cm
        ]
    )

    resumo_cards_odonto.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#EFF5E6")
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(VERDE_ESCURO)
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, 1),
                    "Helvetica-Bold"
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#D7DDD2")
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7.5
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                )
            ]
        )
    )

    story.append(
        resumo_cards_odonto
    )

    story.append(
        Spacer(
            1,
            0.3 * cm
        )
    )

    grafico_odonto_saidas = grafico_ranking_pdf(
        ranking=top_saidas_odonto,
        coluna="Saídas",
        titulo="Odonto - Top 10 por Saidas",
        cor=CINZA
    )

    story.append(
        RLImage(
            grafico_odonto_saidas,
            width=17.4 * cm,
            height=7.2 * cm
        )
    )

    story.append(
        Spacer(
            1,
            0.15 * cm
        )
    )

    story.append(
        tabela_ranking_pdf(
            ranking=top_saidas_odonto,
            destaque="Saídas"
        )
    )

    # -----------------------------------------------------
    # DETALHAMENTO INDIVIDUAL POR CORRETORA
    # -----------------------------------------------------
    if not df_detalhe.empty:
        story.append(
            PageBreak()
        )

        competencias_pdf = sorted(
            pd.to_datetime(
                df_detalhe["Mês"],
                errors="coerce"
            )
            .dropna()
            .unique()
            .tolist()
        )

        corretoras_pdf = sorted(
            df_detalhe["Corretora"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        for indice_corretora, nome_corretora in enumerate(corretoras_pdf):
            df_corretora = df_detalhe[
                df_detalhe["Corretora"].astype(str)
                == nome_corretora
            ].copy()

            # Título + logo, seguindo o padrão visual do relatório.
            if logo_local:
                titulo_corretora = Table(
                    [
                        [
                            Paragraph(
                                nome_corretora,
                                secao
                            ),
                            RLImage(
                                logo_local,
                                width=2.35 * cm,
                                height=1.48 * cm
                            )
                        ]
                    ],
                    colWidths=[
                        13.8 * cm,
                        3.2 * cm
                    ]
                )

                titulo_corretora.setStyle(
                    TableStyle(
                        [
                            (
                                "VALIGN",
                                (0, 0),
                                (-1, -1),
                                "MIDDLE"
                            ),
                            (
                                "ALIGN",
                                (1, 0),
                                (1, 0),
                                "RIGHT"
                            ),
                            (
                                "LEFTPADDING",
                                (0, 0),
                                (-1, -1),
                                0
                            ),
                            (
                                "RIGHTPADDING",
                                (0, 0),
                                (-1, -1),
                                0
                            ),
                            (
                                "TOPPADDING",
                                (0, 0),
                                (-1, -1),
                                0
                            ),
                            (
                                "BOTTOMPADDING",
                                (0, 0),
                                (-1, -1),
                                0
                            )
                        ]
                    )
                )

                story.append(
                    titulo_corretora
                )
            else:
                story.append(
                    Paragraph(
                        nome_corretora,
                        secao
                    )
                )

            story.append(
                Spacer(1, 0.18 * cm)
            )

            story.append(
                resumo_corretora_pdf(df_corretora)
            )

            story.append(
                Spacer(1, 0.22 * cm)
            )

            mensal_corretora = preparar_mensal_corretora_pdf(
                df_corretora=df_corretora,
                competencias=competencias_pdf
            )

            grafico_corretora = grafico_corretora_pdf(
                mensal=mensal_corretora,
                corretora=nome_corretora
            )

            if grafico_corretora is not None:
                story.append(
                    RLImage(
                        grafico_corretora,
                        width=17.2 * cm,
                        height=6.15 * cm
                    )
                )

            story.append(
                Spacer(1, 0.12 * cm)
            )

            story.append(
                Paragraph(
                    "Consolidacao por competencia",
                    ParagraphStyle(
                        "SubsecaoCorretora",
                        parent=texto,
                        fontName="Helvetica-Bold",
                        fontSize=8.2,
                        leading=10,
                        textColor=colors.HexColor("#333333"),
                        spaceAfter=4
                    )
                )
            )

            story.append(
                tabela_mensal_corretora_pdf(
                    mensal_corretora
                )
            )

            if indice_corretora < len(corretoras_pdf) - 1:
                story.append(
                    PageBreak()
                )

    doc.build(
        story,
        onFirstPage=desenhar_cabecalho_rodape,
        onLaterPages=desenhar_cabecalho_rodape
    )

    buffer.seek(0)

    return buffer.getvalue()


# =========================================================
# LÂMINA DO DASHBOARD
# =========================================================
def montar_lamina(
    df,
    nome,
    icone,
    coluna_vida_nova,
    coluna_movimentacao,
    coluna_saida,
    coluna_saldo
):
    st.subheader(
        f"{icone} {nome}"
    )

    # =====================================================
    # RESUMO MENSAL
    # =====================================================
    resumo = (
        df.groupby(
            "Mês",
            as_index=False
        )[
            [
                coluna_vida_nova,
                coluna_movimentacao,
                coluna_saida,
                coluna_saldo
            ]
        ]
        .sum()
        .sort_values("Mês")
    )

    resumo["Total Entradas"] = (
        resumo[coluna_vida_nova]
        + resumo[coluna_movimentacao]
    )

    resumo["% Evasão s/ Venda"] = resumo.apply(
        lambda linha: percentual(
            linha[coluna_saida],
            linha[coluna_vida_nova]
        ),
        axis=1
    )

    resumo[
        "% Evasão s/ Venda + Movimentação"
    ] = resumo.apply(
        lambda linha: percentual(
            linha[coluna_saida],
            linha["Total Entradas"]
        ),
        axis=1
    )

    resumo["Competência"] = (
        resumo["Mês"]
        .dt.strftime("%m/%Y")
    )

    # =====================================================
    # TOTAIS
    # =====================================================
    total_vida_nova = int(
        resumo[coluna_vida_nova].sum()
    )

    total_movimentacao = int(
        resumo[coluna_movimentacao].sum()
    )

    total_entradas = (
        total_vida_nova
        + total_movimentacao
    )

    total_saidas = int(
        resumo[coluna_saida].sum()
    )

    total_saldo = int(
        resumo[coluna_saldo].sum()
    )

    total_evasao = percentual(
        total_saidas,
        total_entradas
    )

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    c1.metric(
        "Vida Nova",
        formatar_inteiro(total_vida_nova)
    )

    c2.metric(
        "Movimentação",
        formatar_inteiro(total_movimentacao)
    )

    c3.metric(
        "Entradas",
        formatar_inteiro(total_entradas)
    )

    c4.metric(
        "Saídas",
        formatar_inteiro(total_saidas)
    )

    c5.metric(
        "Saldo",
        formatar_inteiro(total_saldo)
    )

    c6.metric(
        "Evasão",
        f"{total_evasao:.1f}%"
    )

    # =====================================================
    # ENTRADAS X SAÍDAS POR COMPETÊNCIA
    # =====================================================
    st.divider()
    st.subheader(
        "Entradas x Saídas por Competência"
    )

    fig = go.Figure()

    fig.add_bar(
        name="Vida Nova",
        x=resumo["Competência"],
        y=resumo[coluna_vida_nova],
        text=resumo[coluna_vida_nova],
        textposition="outside",
        marker_color=VERDE_MEDIATORIE
    )

    fig.add_bar(
        name="Movimentação",
        x=resumo["Competência"],
        y=resumo[coluna_movimentacao],
        text=resumo[coluna_movimentacao],
        textposition="outside",
        marker_color=CINZA
    )

    fig.add_bar(
        name="Saídas",
        x=resumo["Competência"],
        y=-resumo[coluna_saida],
        text=resumo[coluna_saida],
        textposition="outside",
        marker_color=VERMELHO_SAIDA
    )

    fig.add_scatter(
        name="Saldo",
        x=resumo["Competência"],
        y=resumo[coluna_saldo],
        mode="lines+markers+text",
        text=resumo[coluna_saldo],
        textposition="top center"
    )

    fig.update_layout(
        barmode="group",
        xaxis_title="Competência",
        yaxis_title="Quantidade de vidas",
        legend_title="Indicador",
        height=520,
        uniformtext_minsize=9,
        uniformtext_mode="hide",
        margin=dict(
            t=40,
            b=40
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================================
    # RESUMO MENSAL
    # =====================================================
    st.subheader(
        "Resumo mensal"
    )

    tabela = resumo[
        [
            "Competência",
            coluna_vida_nova,
            coluna_movimentacao,
            "Total Entradas",
            coluna_saida,
            coluna_saldo,
            "% Evasão s/ Venda",
            "% Evasão s/ Venda + Movimentação"
        ]
    ].copy()

    tabela = tabela.rename(
        columns={
            coluna_vida_nova: "Vida Nova",
            coluna_movimentacao: "Movimentação",
            coluna_saida: "Saídas",
            coluna_saldo: "Saldo"
        }
    )

    st.dataframe(
        tabela,
        use_container_width=True,
        hide_index=True,
        column_config={
            "% Evasão s/ Venda":
                st.column_config.NumberColumn(
                    format="%.1f%%"
                ),
            "% Evasão s/ Venda + Movimentação":
                st.column_config.NumberColumn(
                    format="%.1f%%"
                )
        }
    )

    # =====================================================
    # TOP 10 CORRETORAS
    # =====================================================
    st.divider()
    st.subheader(
        "🏆 Top 10 Corretoras"
    )

    top_entradas, top_saidas = preparar_top10_corretoras(
        df=df,
        coluna_vida_nova=coluna_vida_nova,
        coluna_movimentacao=coluna_movimentacao,
        coluna_saida=coluna_saida
    )

    # -----------------------------------------------------
    # TOP 10 ENTRADAS
    # -----------------------------------------------------
    st.markdown(
        "### Top 10 corretoras por Entradas"
    )

    fig_top_entradas = grafico_top10_streamlit(
        ranking=top_entradas,
        coluna="Entradas",
        titulo=f"{nome} - Top 10 por Entradas",
        cor=VERDE_MEDIATORIE
    )

    st.plotly_chart(
        fig_top_entradas,
        use_container_width=True,
        key=f"grafico_top_entradas_{nome}"
    )

    tabela_top_entradas = (
        top_entradas
        .reset_index()
        .rename(
            columns={
                "index": "Posição"
            }
        )
    )

    st.dataframe(
        tabela_top_entradas,
        use_container_width=True,
        hide_index=True,
        column_config={
            "% Evasão":
                st.column_config.NumberColumn(
                    format="%.1f%%"
                )
        }
    )

    # -----------------------------------------------------
    # TOP 10 SAÍDAS
    # -----------------------------------------------------
    st.markdown(
        "### Top 10 corretoras por Saídas"
    )

    fig_top_saidas = grafico_top10_streamlit(
        ranking=top_saidas,
        coluna="Saídas",
        titulo=f"{nome} - Top 10 por Saídas",
        cor=CINZA
    )

    st.plotly_chart(
        fig_top_saidas,
        use_container_width=True,
        key=f"grafico_top_saidas_{nome}"
    )

    tabela_top_saidas = (
        top_saidas
        .reset_index()
        .rename(
            columns={
                "index": "Posição"
            }
        )
    )

    st.dataframe(
        tabela_top_saidas,
        use_container_width=True,
        hide_index=True,
        column_config={
            "% Evasão":
                st.column_config.NumberColumn(
                    format="%.1f%%"
                )
        }
    )

    # =====================================================
    # RESUMO POR CORRETORA
    # =====================================================
    st.divider()
    st.subheader(
        "Resumo por corretora"
    )

    corretoras = (
        df.groupby(
            "Corretora",
            as_index=False
        )[
            [
                coluna_vida_nova,
                coluna_movimentacao,
                coluna_saida,
                coluna_saldo
            ]
        ]
        .sum()
    )

    corretoras["Total Entradas"] = (
        corretoras[coluna_vida_nova]
        + corretoras[coluna_movimentacao]
    )

    corretoras["% Evasão"] = corretoras.apply(
        lambda linha: percentual(
            linha[coluna_saida],
            linha["Total Entradas"]
        ),
        axis=1
    )

    corretoras = corretoras.rename(
        columns={
            coluna_vida_nova: "Vida Nova",
            coluna_movimentacao: "Movimentação",
            coluna_saida: "Saídas",
            coluna_saldo: "Saldo"
        }
    )

    corretoras = corretoras[
        [
            "Corretora",
            "Vida Nova",
            "Movimentação",
            "Total Entradas",
            "Saídas",
            "Saldo",
            "% Evasão"
        ]
    ].sort_values(
        "Total Entradas",
        ascending=False
    )

    st.dataframe(
        corretoras,
        use_container_width=True,
        hide_index=True,
        column_config={
            "% Evasão":
                st.column_config.NumberColumn(
                    format="%.1f%%"
                )
        }
    )

    return top_entradas, top_saidas


# =========================================================
# CARREGA BASE
# =========================================================
df = carregar_base()


# =========================================================
# VALIDAÇÃO DE COLUNAS
# =========================================================
colunas_obrigatorias = [
    "Mês",
    "Corretora",
    "Vida Nova Saúde",
    "Movimentação Saúde",
    "Saída Saúde",
    "Saldo Saúde",
    "Vida Nova Odonto",
    "Movimentação Odonto",
    "Saída Odonto",
    "Saldo Odonto",
    "Saldo Geral"
]

faltantes = [
    coluna
    for coluna in colunas_obrigatorias
    if coluna not in df.columns
]

if faltantes:
    st.error(
        "A nova base não possui as seguintes colunas obrigatórias: "
        + ", ".join(faltantes)
    )

    st.write(
        "Colunas encontradas:"
    )

    st.write(
        list(df.columns)
    )

    st.stop()


# =========================================================
# TRATAMENTO
# =========================================================
df["Mês"] = pd.to_datetime(
    df["Mês"],
    errors="coerce"
)

df = df[
    df["Mês"].notna()
].copy()

df["Corretora"] = (
    df["Corretora"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.strip()
)

colunas_numericas = [
    "Vida Nova Saúde",
    "Movimentação Saúde",
    "Saída Saúde",
    "Saldo Saúde",
    "Vida Nova Odonto",
    "Movimentação Odonto",
    "Saída Odonto",
    "Saldo Odonto",
    "Saldo Geral"
]

for coluna in colunas_numericas:
    df[coluna] = pd.to_numeric(
        df[coluna],
        errors="coerce"
    ).fillna(0)


# =========================================================
# FILTROS
# =========================================================
st.sidebar.header(
    "Filtros"
)

anos = sorted(
    df["Mês"]
    .dt.year
    .dropna()
    .unique()
    .tolist(),
    reverse=True
)

ano_selecionado = st.sidebar.selectbox(
    "Ano",
    anos
)

df_filtrado = df[
    df["Mês"].dt.year
    == ano_selecionado
].copy()

corretoras = sorted(
    df_filtrado["Corretora"]
    .dropna()
    .unique()
    .tolist()
)

corretora_selecionada = st.sidebar.selectbox(
    "Corretora",
    ["TODAS"] + corretoras
)

if corretora_selecionada != "TODAS":
    df_filtrado = df_filtrado[
        df_filtrado["Corretora"]
        == corretora_selecionada
    ].copy()

if df_filtrado.empty:
    st.warning(
        "Não existem dados para os filtros selecionados."
    )
    st.stop()

competencia_min = (
    df_filtrado["Mês"].min()
)

competencia_max = (
    df_filtrado["Mês"].max()
)

st.sidebar.caption(
    f"Período disponível: "
    f"{competencia_min.strftime('%m/%Y')} "
    f"até {competencia_max.strftime('%m/%Y')}"
)


# =========================================================
# LÂMINAS
# =========================================================
tab_saude, tab_odonto = st.tabs(
    [
        "🩺 SAÚDE",
        "🦷 ODONTO"
    ]
)

with tab_saude:
    (
        top_entradas_saude,
        top_saidas_saude
    ) = montar_lamina(
        df=df_filtrado,
        nome="Saúde",
        icone="🩺",
        coluna_vida_nova="Vida Nova Saúde",
        coluna_movimentacao="Movimentação Saúde",
        coluna_saida="Saída Saúde",
        coluna_saldo="Saldo Saúde"
    )

with tab_odonto:
    (
        top_entradas_odonto,
        top_saidas_odonto
    ) = montar_lamina(
        df=df_filtrado,
        nome="Odonto",
        icone="🦷",
        coluna_vida_nova="Vida Nova Odonto",
        coluna_movimentacao="Movimentação Odonto",
        coluna_saida="Saída Odonto",
        coluna_saldo="Saldo Odonto"
    )


# =========================================================
# PDF COMPLETO
# =========================================================
st.divider()

st.subheader(
    "📄 Relatório Gerencial - Top 10 + Corretoras"
)

quantidade_corretoras_pdf = int(
    df_filtrado["Corretora"].nunique()
)

st.caption(
    "O PDF reúne Saúde e Odonto, os rankings Top 10 e também "
    f"uma página individual para cada corretora do filtro atual "
    f"({quantidade_corretoras_pdf} corretora(s))."
)

# O relatório com uma página por corretora pode ficar grande.
# Por isso ele só é montado quando o usuário clicar no botão.
assinatura_base = int(
    pd.util.hash_pandas_object(
        df_filtrado,
        index=True
    ).sum()
)

chave_pdf_atual = (
    int(ano_selecionado),
    str(corretora_selecionada),
    assinatura_base
)

if st.session_state.get("chave_pdf_corretoras") != chave_pdf_atual:
    st.session_state.pop("pdf_corretoras", None)

if st.button(
    "⚙️ Gerar PDF completo",
    use_container_width=True
):
    with st.spinner(
        "Gerando o relatório. Como existe uma página por corretora, "
        "esse processo pode levar alguns segundos..."
    ):
        pdf_completo = gerar_pdf_top10_completo(
            ano_selecionado=ano_selecionado,
            corretora_selecionada=corretora_selecionada,
            top_entradas_saude=top_entradas_saude,
            top_saidas_saude=top_saidas_saude,
            top_entradas_odonto=top_entradas_odonto,
            top_saidas_odonto=top_saidas_odonto,
            df_detalhe=df_filtrado
        )

        st.session_state["pdf_corretoras"] = pdf_completo
        st.session_state["chave_pdf_corretoras"] = chave_pdf_atual

if "pdf_corretoras" in st.session_state:
    st.success(
        "PDF gerado. O relatório já está pronto para download."
    )

    st.download_button(
        label="📄 Baixar PDF completo - Saúde + Odonto + Corretoras",
        data=st.session_state["pdf_corretoras"],
        file_name=(
            f"relatorio_corretoras_"
            f"{ano_selecionado}.pdf"
        ),
        mime="application/pdf",
        use_container_width=True
    )

