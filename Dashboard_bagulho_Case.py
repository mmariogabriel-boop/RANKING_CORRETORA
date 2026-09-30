import os
import textwrap
from io import BytesIO
from datetime import datetime

import streamlit as st
import pandas as pd
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
    "Dashboard baseado no relatório consolidado por mês, corretora e CNPJ."
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
    corretora_selecionada,
    cnpj_selecionado
):
    dados = [
        ["Gerado em", datetime.now().strftime("%d/%m/%Y %H:%M")],
        ["Base", "Relatoriov2.xlsx"],
        ["Ano", str(ano_selecionado)],
        ["Corretora", str(corretora_selecionada)],
        ["CNPJ", str(cnpj_selecionado)]
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
# PDF COMPLETO - SAÚDE + ODONTO
# =========================================================
def gerar_pdf_top10_completo(
    ano_selecionado,
    corretora_selecionada,
    cnpj_selecionado,
    top_entradas_saude,
    top_saidas_saude,
    top_entradas_odonto,
    top_saidas_odonto
):
    """
    Gera UM ÚNICO PDF:
    1 - Capa
    2 - Top 10 Entradas Saúde
    3 - Top 10 Saídas Saúde
    4 - Top 10 Entradas Odonto
    5 - Top 10 Saídas Odonto
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
    logo_local = None

    for possivel_logo in [
        "logo_mediatorie.png",
        "mediatorie.png",
        "logo.png"
    ]:
        if os.path.exists(possivel_logo):
            logo_local = possivel_logo
            break

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
            "Top 10 corretoras por entradas e saidas - Saude e Odonto.",
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
            corretora_selecionada=corretora_selecionada,
            cnpj_selecionado=cnpj_selecionado
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
            [
                "CNPJ",
                "Corretora"
            ],
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
            "CNPJ",
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
    "CNPJ",
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

df["CNPJ"] = (
    df["CNPJ"]
    .fillna("NÃO INFORMADO")
    .astype(str)
    .str.strip()
)

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

cnpjs = sorted(
    df_filtrado["CNPJ"]
    .dropna()
    .unique()
    .tolist()
)

cnpj_selecionado = st.sidebar.selectbox(
    "CNPJ",
    ["TODOS"] + cnpjs
)

if cnpj_selecionado != "TODOS":
    df_filtrado = df_filtrado[
        df_filtrado["CNPJ"]
        == cnpj_selecionado
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
    "📄 Relatório Gerencial - Top 10 Corretoras"
)

st.caption(
    "O PDF abaixo reúne Saúde e Odonto no mesmo arquivo, "
    "com gráfico e tabela para Top 10 Entradas e Top 10 Saídas."
)

pdf_completo = gerar_pdf_top10_completo(
    ano_selecionado=ano_selecionado,
    corretora_selecionada=corretora_selecionada,
    cnpj_selecionado=cnpj_selecionado,
    top_entradas_saude=top_entradas_saude,
    top_saidas_saude=top_saidas_saude,
    top_entradas_odonto=top_entradas_odonto,
    top_saidas_odonto=top_saidas_odonto
)

st.download_button(
    label="📄 Baixar PDF completo - Saúde + Odonto",
    data=pdf_completo,
    file_name=(
        f"relatorio_top10_corretoras_"
        f"{ano_selecionado}.pdf"
    ),
    mime="application/pdf",
    use_container_width=True
)
