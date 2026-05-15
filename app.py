import streamlit as st
import pandas as pd
import os
import re
from io import BytesIO
import plotly.express as px
from datetime import datetime

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Dvolv — Distribuição de Comissões",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR     = "."
HISTORY_FILE = os.path.join(DATA_DIR, "history_projects.csv")

# ─────────────────────────────────────────
# PALETA DVOLV
# ─────────────────────────────────────────
C_GREEN      = "#00693E"
C_GREEN_DARK = "#004D2C"
C_GREEN_LITE = "#E6F4EE"
C_NAVY       = "#0B1F3A"
C_NAVY_LITE  = "#1C3354"
C_WHITE      = "#FFFFFF"
C_BORDER     = "#D0D7E2"
C_AMBER      = "#B8860B"
C_AMBER_LITE = "#FDF5DC"
C_RED        = "#C0392B"
C_RED_LITE   = "#FEECEC"
C_BLUE       = "#1565C0"
C_BLUE_LITE  = "#EBF0F8"

# ─────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────
FIXED_FUNCOES = [
    ("taxa_reserva",    "Taxa de Reserva",  10.0),
    ("comercial",       "Comercial",        10 / 3),
    ("contrato",        "Contrato",         10 / 3),
    ("analise_inicial", "Análise Inicial",  10 / 3),
    ("coordenacao",     "Coordenação",      10.0),
]

DIRECIONADOR = {
    1: [70.0,  0.0,  0.0, 0.0, 0.0],
    2: [50.0, 20.0,  0.0, 0.0, 0.0],
    3: [45.0, 15.0, 10.0, 0.0, 0.0],
    4: [40.0, 15.0, 10.0, 5.0, 0.0],
    5: [35.0, 15.0, 10.0, 5.0, 5.0],
}

# ─────────────────────────────────────────
# CSS — TOTALMENTE ADAPTATIVO (light + dark)
# ─────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  html, body, [class*="css"] {{
      font-family: 'Inter', sans-serif;
  }}

  /* ── Botões principais ── */
  .stButton > button {{
      background-color: {C_GREEN} !important;
      color: {C_WHITE} !important;
      border: none !important;
      border-radius: 4px !important;
      font-weight: 600 !important;
      font-size: 0.85rem !important;
      padding: 0.55rem 1.25rem !important;
      letter-spacing: 0.03em !important;
      transition: background-color 0.2s !important;
  }}
  .stButton > button:hover {{
      background-color: {C_GREEN_DARK} !important;
  }}
  .stDownloadButton > button {{
      background-color: {C_NAVY} !important;
      color: {C_WHITE} !important;
      border: none !important;
      border-radius: 4px !important;
      font-weight: 600 !important;
      font-size: 0.85rem !important;
      width: 100% !important;
  }}
  .stDownloadButton > button:hover {{
      background-color: {C_NAVY_LITE} !important;
  }}

  /* ── Labels ── */
  .stTextInput label, .stNumberInput label, .stDateInput label {{
      font-size: 0.75rem !important;
      font-weight: 700 !important;
      text-transform: uppercase !important;
      letter-spacing: 0.07em !important;
      opacity: 0.65;
  }}
  .stCheckbox label {{
      font-size: 0.875rem !important;
      font-weight: 500 !important;
  }}

  /* ── Inputs ── */
  .stTextInput > div > div > input {{
      border-radius: 4px !important;
  }}
  .stTextInput > div > div > input:focus,
  .stNumberInput > div > div > input:focus {{
      border-color: {C_GREEN} !important;
      box-shadow: 0 0 0 2px {C_GREEN_LITE} !important;
  }}

  /* ── Campo desabilitado (faturamento calculado) ── */
  .stTextInput > div > div > input:disabled {{
      opacity: 0.85 !important;
      font-weight: 600 !important;
  }}

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {{
      background-color: {C_NAVY};
  }}
  [data-testid="stSidebar"] * {{
      color: #CBD5E1 !important;
  }}
  [data-testid="stSidebar"] hr {{
      border-color: {C_NAVY_LITE};
  }}
  [data-testid="stSidebar"] .stButton > button {{
      background-color: transparent !important;
      border: 1px solid #4A6080 !important;
      color: #CBD5E1 !important;
      width: 100%;
  }}
  [data-testid="stSidebar"] .stButton > button:hover {{
      border-color: {C_GREEN} !important;
      color: {C_WHITE} !important;
  }}

  /* ── Métricas adaptativas ── */
  [data-testid="metric-container"] {{
      background-color: var(--secondary-background-color);
      border: 1px solid rgba(0,0,0,0.08);
      border-radius: 6px;
      padding: 0.9rem 1.1rem;
  }}
  [data-testid="metric-container"] label {{
      font-size: 0.7rem !important;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      opacity: 0.55;
      font-weight: 700 !important;
  }}
  [data-testid="metric-container"] [data-testid="stMetricValue"] {{
      font-size: 1.25rem !important;
      font-weight: 700 !important;
  }}

  /* ── Dataframe ── */
  [data-testid="stDataFrame"] {{
      border-radius: 6px;
      overflow: hidden;
  }}

  .block-container {{
      padding-top: 1.5rem;
      padding-bottom: 3rem;
  }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# HELPERS — FORMATAÇÃO pt-BR
# ─────────────────────────────────────────
def fmt_ptbr(x, decimals=2):
    try:
        x = float(x or 0)
    except Exception:
        x = 0.0
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def fmt_brl(x):
    return f"R$ {fmt_ptbr(x, 2)}"

def parse_ptbr(s):
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

# ─────────────────────────────────────────
# HELPERS — MÁSCARAS
# ─────────────────────────────────────────
def mask_cnpj(value: str) -> str:
    d = re.sub(r'\D', '', str(value))[:14]
    if len(d) <= 2:   return d
    if len(d) <= 5:   return f"{d[:2]}.{d[2:]}"
    if len(d) <= 8:   return f"{d[:2]}.{d[2:5]}.{d[5:]}"
    if len(d) <= 12:  return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:]}"
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"

def mask_brl_input(value: str) -> str:
    digits = re.sub(r'\D', '', str(value))
    if not digits or int(digits) == 0:
        return "0,00"
    number = int(digits) / 100
    return fmt_ptbr(number, 2)

# ─────────────────────────────────────────
# HELPERS — HISTÓRICO
# ─────────────────────────────────────────
def append_history(record: dict):
    df = pd.DataFrame([record])
    if os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df.to_csv(HISTORY_FILE, index=False, encoding="utf-8")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            return pd.read_csv(HISTORY_FILE, encoding="utf-8")
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

# ─────────────────────────────────────────
# HELPERS — EXCEL COM FÓRMULAS
# ─────────────────────────────────────────
def _fmt_xl_date(date_str: str) -> str:
    """Converte AAAA-MM-DD para DD/MM/AAAA."""
    try:
        return datetime.strptime(str(date_str), "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return str(date_str)

def to_excel_bytes(df_result: pd.DataFrame, meta: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.cell.cell import MergedCell

    wb = Workbook()
    ws = wb.active
    ws.title = "RESULTADO"

    # Estilos
    green_fill = PatternFill("solid", fgColor="00693E")
    navy_fill  = PatternFill("solid", fgColor="0B1F3A")
    lite_green = PatternFill("solid", fgColor="E6F4EE")
    lite_blue  = PatternFill("solid", fgColor="EBF0F8")
    grey_fill  = PatternFill("solid", fgColor="F4F6F9")
    red_fill   = PatternFill("solid", fgColor="FEECEC")
    amb_fill   = PatternFill("solid", fgColor="FDF5DC")
    thin  = Side(style="thin",   color="D0D7E2")
    thick = Side(style="medium", color="00693E")
    tb = Border(left=thin,  right=thin,  top=thin,  bottom=thin)
    gb = Border(left=thick, right=thick, top=thick, bottom=thick)
    FMT_BRL = '#,##0.00'
    FMT_PCT = '0.00'
    FMT_P4  = '0.0000'

    wht  = lambda sz=10, bold=True:  Font(name="Calibri", size=sz, bold=bold, color="FFFFFF")
    blk  = lambda sz=10, bold=False: Font(name="Calibri", size=sz, bold=bold)
    grey_font = Font(name="Calibri", size=9, italic=True, color="888888")

    def S(row, col, val, font=None, fill=None, border=None,
          align=None, nfmt=None):
        c = ws.cell(row=row, column=col, value=val)
        if font:   c.font           = font
        if fill:   c.fill           = fill
        if border: c.border         = border
        if align:  c.alignment      = align
        if nfmt:   c.number_format  = nfmt
        return c

    ctr = Alignment(horizontal="center", vertical="center")
    rgt = Alignment(horizontal="right")

    # ── Título (sem merge para evitar conflito de células) ──
    S(1,1,"DVOLV INTELIGÊNCIA TRIBUTÁRIA — DISTRIBUIÇÃO DE COMISSÕES",
      font=wht(14), fill=navy_fill, align=ctr)
    # Preenche colunas mescladas com fill para visual consistente
    for _ci in range(2, 8):
        c = ws.cell(row=1, column=_ci)
        c.fill  = navy_fill
        c.border = tb
    ws.merge_cells("A1:G1")
    ws.row_dimensions[1].height = 32
    ws.append([])

    # ── Dados do projeto ──
    for label, value in [
        ("Projeto",            meta.get("project_name","")),
        ("Data de Geração",    datetime.now().strftime("%d/%m/%Y %H:%M")),
        ("Cliente",            meta.get("cliente","")),
        ("CNPJ",               meta.get("cnpj","")),
        ("Serviço",            meta.get("servico","")),
        ("Data Faturamento",   _fmt_xl_date(meta.get("data_faturamento",""))),
        ("Forma de Pagamento", meta.get("forma_pagamento","")),
    ]:
        r = ws.max_row + 1
        S(r,1,label, font=blk(10,True),  fill=grey_fill, border=tb)
        S(r,2,value, font=blk(10,False), fill=grey_fill, border=tb)

    ws.append([])

    # ── Bloco financeiro com fórmulas (sem coluna de anotações) ──
    r = ws.max_row + 1
    R_BENEF = r
    S(r,1,"Benefício Econômico para o Cliente (R$)", font=blk(10,True), border=tb)
    S(r,2, meta.get("beneficio_cliente", 0),        font=blk(10),       border=tb, nfmt=FMT_BRL)

    r = ws.max_row + 1
    R_PCT_EXITO = r
    S(r,1,"% Honorários Êxito", font=blk(10,True), border=tb)
    S(r,2, meta.get("pct_exito", 0),               font=blk(10),  border=tb, nfmt=FMT_PCT)

    r = ws.max_row + 1
    R_FAT = r
    S(r,1,"Faturamento Bruto (R$)", font=blk(10,True), fill=grey_fill, border=tb)
    S(r,2,f"=B{R_BENEF}*B{R_PCT_EXITO}/100",
      font=blk(10,True), fill=grey_fill, border=tb, nfmt=FMT_BRL)

    r = ws.max_row + 1
    R_PCT_IMP = r
    S(r,1,"% Impostos", font=blk(10,True), border=tb)
    S(r,2, meta.get("pct_impostos", 0), font=blk(10), border=tb, nfmt=FMT_PCT)

    r = ws.max_row + 1
    R_VAL_IMP = r
    S(r,1,"Valor Impostos (R$)", font=blk(10,True), fill=red_fill, border=tb)
    S(r,2,f"=B{R_FAT}*B{R_PCT_IMP}/100",
      font=blk(10), fill=red_fill, border=tb, nfmt=FMT_BRL)

    r = ws.max_row + 1
    R_APOS_IMP = r
    S(r,1,"Após Impostos (R$)", font=blk(10,True), fill=grey_fill, border=tb)
    S(r,2,f"=B{R_FAT}-B{R_VAL_IMP}",
      font=blk(10,True), fill=grey_fill, border=tb, nfmt=FMT_BRL)

    r = ws.max_row + 1
    R_PCT_TERC = r
    S(r,1,"% Comissão Terceiro", font=blk(10,True), border=tb)
    S(r,2, meta.get("pct_terceiro", 0), font=blk(10), border=tb, nfmt=FMT_PCT)

    r = ws.max_row + 1
    R_VAL_TERC = r
    S(r,1,"Valor Comissão Terceiro (R$)", font=blk(10,True), fill=amb_fill, border=tb)
    S(r,2,f"=B{R_APOS_IMP}*B{R_PCT_TERC}/100",
      font=blk(10), fill=amb_fill, border=tb, nfmt=FMT_BRL)

    r = ws.max_row + 1
    R_LIQ = r
    S(r,1,"BASE DE CÁLCULO — LÍQUIDO (R$)", font=wht(11), fill=green_fill, border=gb)
    S(r,2,f"=B{R_APOS_IMP}-B{R_VAL_TERC}", font=wht(11), fill=green_fill, border=gb, nfmt=FMT_BRL)

    r = ws.max_row + 1
    S(r,1,"Direcionador Aplicado", font=blk(10,True), fill=grey_fill, border=tb)
    S(r,2, meta.get("direcionador",""),              font=blk(10),    fill=grey_fill, border=tb)

    ws.append([])

    # ── Cabeçalho tabela (sem coluna de referência) ──
    HEADERS = ["Participante", "Função", "Tipo", "% Distribuição", "Valor (R$)"]
    R_HEAD = ws.max_row + 1
    for ci, h in enumerate(HEADERS, 1):
        S(R_HEAD, ci, h, font=wht(10), fill=green_fill, border=tb, align=ctr)
    ws.row_dimensions[R_HEAD].height = 20

    # ── Dados com fórmulas ──
    R_D0 = R_HEAD + 1
    for idx, (_, row) in enumerate(df_result.iterrows()):
        dr   = R_D0 + idx
        fill = lite_green if row.get("Tipo") == "Fixo (30%)" else lite_blue
        pct  = row.get("% Distribuição", 0)
        S(dr,1, row.get("Participante",""), font=blk(10), fill=fill, border=tb)
        S(dr,2, row.get("Função",""),       font=blk(10), fill=fill, border=tb)
        S(dr,3, row.get("Tipo",""),         font=blk(10), fill=fill, border=tb)
        S(dr,4, pct,                        font=blk(10), fill=fill, border=tb, nfmt=FMT_P4, align=rgt)
        S(dr,5, f"=$B${R_LIQ}*D{dr}/100",  font=blk(10), fill=fill, border=tb, nfmt=FMT_BRL, align=rgt)

    R_DE = R_D0 + len(df_result) - 1

    # ── Totais ──
    tr = R_DE + 1
    S(tr,1,"",       font=wht(10), fill=green_fill, border=tb)
    S(tr,2,"TOTAL",  font=wht(10), fill=green_fill, border=tb)
    S(tr,3,"",       font=wht(10), fill=green_fill, border=tb)
    S(tr,4,f"=SUM(D{R_D0}:D{R_DE})", font=wht(10), fill=green_fill, border=tb, nfmt=FMT_P4, align=rgt)
    S(tr,5,f"=SUM(E{R_D0}:E{R_DE})", font=wht(10), fill=green_fill, border=tb, nfmt=FMT_BRL, align=rgt)

    # ── Remover linhas de grade ──
    ws.sheet_view.showGridLines = False

    # ── Largura colunas ──
    from openpyxl.utils import get_column_letter
    for i, w in enumerate([32, 22, 18, 16, 20], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.read()

# ─────────────────────────────────────────
# COMPONENTES VISUAIS ADAPTATIVOS
# ─────────────────────────────────────────
def section_header(title: str, subtitle: str = ""):
    sub = (f"<p style='margin:2px 0 0;font-size:0.78rem;opacity:0.5'>{subtitle}</p>") if subtitle else ""
    st.markdown(f"""
    <div style='border-left:3px solid {C_GREEN};padding:6px 14px;
                margin:1.75rem 0 1rem;
                background:var(--secondary-background-color);
                border-radius:0 4px 4px 0;
                box-shadow:0 1px 4px rgba(0,0,0,0.07)'>
      <p style='margin:0;font-size:0.75rem;font-weight:800;text-transform:uppercase;
                letter-spacing:0.1em'>{title}</p>
      {sub}
    </div>
    """, unsafe_allow_html=True)

def info_card(label: str, value: str, accent: str = C_GREEN):
    st.markdown(f"""
    <div style='background:var(--secondary-background-color);
                border:1px solid rgba(0,0,0,0.07);border-radius:6px;
                padding:0.85rem 1rem;border-top:3px solid {accent}'>
      <p style='margin:0;font-size:0.67rem;font-weight:800;text-transform:uppercase;
                letter-spacing:0.09em;opacity:0.45'>{label}</p>
      <p style='margin:4px 0 0;font-size:1.2rem;font-weight:700'>{value}</p>
    </div>
    """, unsafe_allow_html=True)

def calc_display(label: str, value: str, formula: str,
                 accent: str = C_GREEN, inverted: bool = False):
    txt_color = C_WHITE if inverted else "var(--text-color)"
    bg = f"linear-gradient(135deg,{accent} 0%,{C_GREEN_DARK} 100%)" if inverted else f"var(--secondary-background-color)"
    border_css = "" if inverted else f"border:1px solid rgba(0,0,0,0.07);border-top:3px solid {accent};"
    opacity_formula = "0.65" if inverted else "0.45"
    st.markdown(f"""
    <div style='background:{bg};{border_css}border-radius:6px;padding:0.85rem 1rem'>
      <p style='margin:0;font-size:0.67rem;font-weight:800;text-transform:uppercase;
                letter-spacing:0.09em;color:{txt_color};opacity:{opacity_formula}'>{label}</p>
      <p style='margin:3px 0 2px;font-size:1.25rem;font-weight:800;color:{txt_color}'>{value}</p>
      <p style='margin:0;font-size:0.68rem;color:{txt_color};opacity:{opacity_formula}'>{formula}</p>
    </div>
    """, unsafe_allow_html=True)

def alert_box(msg: str, kind: str = "info"):
    cfg = {
        "info":    (C_GREEN_LITE, C_GREEN,  C_GREEN_DARK),
        "warning": (C_AMBER_LITE, C_AMBER,  "#7A5700"),
        "error":   (C_RED_LITE,   C_RED,    "#8B0000"),
    }
    bg, border, text = cfg.get(kind, cfg["info"])
    st.markdown(f"""
    <div style='background:{bg};border:1px solid {border};border-radius:4px;
                padding:0.65rem 1rem;font-size:0.85rem;color:{text};margin:0.5rem 0'>
      {msg}
    </div>
    """, unsafe_allow_html=True)

def group_label(title: str, subtitle: str, bg: str, border: str, text: str):
    st.markdown(f"""
    <div style='background:{bg};border:1px solid {border};border-radius:4px;
                padding:8px 14px;margin-bottom:10px'>
      <p style='margin:0;font-size:0.72rem;font-weight:800;text-transform:uppercase;
                letter-spacing:0.08em;color:{text}'>{title}</p>
      <p style='margin:2px 0 0;font-size:0.78rem;color:{text};opacity:0.75'>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# SESSION STATE — máscaras
# ─────────────────────────────────────────
for k, v in {"cnpj_raw": "", "beneficio_raw": "0,00"}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def _on_cnpj():
    st.session_state.cnpj_raw = mask_cnpj(st.session_state.cnpj_raw)

def _on_beneficio():
    st.session_state.beneficio_raw = mask_brl_input(st.session_state.beneficio_raw)

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
st.sidebar.markdown(f"""
<div style='text-align:center;padding:1.5rem 0.5rem 1rem;
            border-bottom:1px solid {C_NAVY_LITE};margin-bottom:1rem'>
  <p style='font-size:1.2rem;font-weight:900;color:{C_WHITE};margin:0;letter-spacing:0.07em'>DVOLV</p>
  <p style='font-size:0.65rem;color:#94A3B8;margin:3px 0 0;
            letter-spacing:0.12em;text-transform:uppercase'>Inteligência Tributária</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(
    f"<p style='font-size:0.65rem;font-weight:800;text-transform:uppercase;"
    f"letter-spacing:0.1em;color:#94A3B8;margin-bottom:6px'>Funções Fixas — 30%</p>",
    unsafe_allow_html=True
)
for _, label, pct in FIXED_FUNCOES:
    st.sidebar.markdown(
        f"<p style='font-size:0.82rem;margin:3px 0;color:#CBD5E1'>{label}"
        f"<span style='float:right;font-weight:700;color:{C_WHITE}'>{pct:.2f}%</span></p>",
        unsafe_allow_html=True
    )
st.sidebar.markdown("<hr>", unsafe_allow_html=True)
st.sidebar.markdown(
    f"<p style='font-size:0.65rem;font-weight:800;text-transform:uppercase;"
    f"letter-spacing:0.1em;color:#94A3B8;margin-bottom:6px'>Direcionadores — 70%</p>",
    unsafe_allow_html=True
)
for qtd, pcts in DIRECIONADOR.items():
    linhas = " · ".join([f"Ex{i+1}: {p:.0f}%" for i, p in enumerate(pcts) if p > 0])
    st.sidebar.markdown(
        f"<p style='font-size:0.8rem;margin:4px 0;color:#CBD5E1'>"
        f"<span style='color:{C_WHITE};font-weight:700'>Dir. {qtd}</span>  {linhas}</p>",
        unsafe_allow_html=True
    )
st.sidebar.markdown("<hr>", unsafe_allow_html=True)
if st.sidebar.button("Limpar Histórico"):
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
        st.sidebar.success("Histórico removido.")
    else:
        st.sidebar.info("Nenhum histórico encontrado.")

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown(f"""
<div style='background:linear-gradient(135deg,{C_NAVY} 0%,{C_NAVY_LITE} 100%);
            border-radius:8px;padding:1.4rem 2rem;margin-bottom:1rem'>
  <p style='margin:0;font-size:0.65rem;font-weight:800;text-transform:uppercase;
            letter-spacing:0.14em;color:#64748B'>Dvolv Inteligência Tributária</p>
  <p style='margin:4px 0 0;font-size:1.5rem;font-weight:800;color:{C_WHITE};letter-spacing:0.02em'>
    Distribuição de Comissões
  </p>
  <p style='margin:4px 0 0;font-size:0.78rem;color:#475569'>
    {datetime.now().strftime("%d de %B de %Y")} &nbsp;·&nbsp; Uso Interno
  </p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SEÇÃO 1 — PROJETO
# ─────────────────────────────────────────
section_header("Informações do Projeto", "Identificação do projeto e dados do cliente")
colA, colB = st.columns(2)
project_name     = colA.text_input("Nome do Projeto",     placeholder="Ex: Revisão PIS/COFINS — Empresa XYZ")
data_faturamento = colA.date_input("Data do Faturamento", value=datetime.today(), format="DD/MM/YYYY")
cliente          = colA.text_input("Cliente",             placeholder="Razão social")
colB.text_input("CNPJ", key="cnpj_raw", on_change=_on_cnpj, placeholder="00.000.000/0000-00")
cnpj            = st.session_state.cnpj_raw
servico         = colB.text_input("Serviço",             placeholder="Ex: Recuperação ICMS-ST")
forma_pagamento = colB.text_input("Forma de Pagamento",  placeholder="Ex: À vista / 30 dias")

# ─────────────────────────────────────────
# SEÇÃO 2 — FINANCEIRO
# ─────────────────────────────────────────
section_header("Informações Financeiras",
               "Benefício econômico → Faturamento Bruto → Impostos → Terceiro → Líquido")

# ── Bloco de inputs: lado a lado, alinhados ──
inp_left, inp_right = st.columns([3, 2])

with inp_left:
    st.markdown(f"""
    <div style='background:var(--secondary-background-color);border:1px solid rgba(0,0,0,0.08);
                border-radius:6px;padding:1rem 1.25rem 0.5rem'>
      <p style='margin:0 0 0.75rem;font-size:0.72rem;font-weight:800;text-transform:uppercase;
                letter-spacing:0.09em;opacity:0.45'>Origem do Faturamento</p>
    """, unsafe_allow_html=True)
    ia, ib = st.columns([3, 2])
    ia.text_input(
        "Benefício Econômico ao Cliente (R$)",
        key="beneficio_raw", on_change=_on_beneficio,
        placeholder="0,00",
        help="Valor total da economia gerada ao cliente"
    )
    beneficio_cliente = parse_ptbr(st.session_state.beneficio_raw)
    pct_exito = ib.number_input(
        "% Honorários Êxito", min_value=0.0, max_value=100.0,
        step=0.1, value=0.0, format="%.2f",
        help="Percentual de êxito sobre o benefício"
    )
    st.markdown("</div>", unsafe_allow_html=True)

with inp_right:
    st.markdown(f"""
    <div style='background:var(--secondary-background-color);border:1px solid rgba(0,0,0,0.08);
                border-radius:6px;padding:1rem 1.25rem 0.5rem'>
      <p style='margin:0 0 0.75rem;font-size:0.72rem;font-weight:800;text-transform:uppercase;
                letter-spacing:0.09em;opacity:0.45'>Deduções</p>
    """, unsafe_allow_html=True)
    dc1, dc2 = st.columns(2)
    tem_impostos = dc1.checkbox("Incide Impostos?", value=False)
    pct_impostos = 0.0
    if tem_impostos:
        pct_impostos = dc1.number_input(
            "% Impostos", min_value=0.0, max_value=100.0,
            step=0.1, value=0.0, format="%.2f"
        )
    tem_terceiro = dc2.checkbox("Comissão Terceiro?", value=False)
    pct_terceiro = 0.0
    if tem_terceiro:
        pct_terceiro = dc2.number_input(
            "% Terceiro", min_value=0.0, max_value=100.0,
            step=0.1, value=0.0, format="%.2f"
        )
    st.markdown("</div>", unsafe_allow_html=True)

# ── Cálculos ──
faturamento_bruto = beneficio_cliente * (pct_exito / 100.0)
val_impostos      = faturamento_bruto * (pct_impostos / 100.0)
apos_impostos     = faturamento_bruto - val_impostos
val_terceiro      = apos_impostos * (pct_terceiro / 100.0)
liquido           = apos_impostos - val_terceiro

# ── Cascata de resultados: 5 cards com setas ──
st.markdown("<div style='margin-top:0.9rem'></div>", unsafe_allow_html=True)

def arrow_sep():
    st.markdown(
        f"<div style='display:flex;align-items:center;justify-content:center;"
        f"height:100%;padding-top:1.4rem;font-size:1.2rem;opacity:0.3;font-weight:300'>→</div>",
        unsafe_allow_html=True
    )

cascade_cols = st.columns([3, 0.4, 2, 0.4, 2, 0.4, 2, 0.4, 3])

with cascade_cols[0]:
    calc_display("Faturamento Bruto",
                 fmt_brl(faturamento_bruto),
                 f"Benefício × {pct_exito:.2f}%",
                 accent=C_NAVY)

with cascade_cols[1]: arrow_sep()

with cascade_cols[2]:
    calc_display(
        f"(−) Impostos{f'  {pct_impostos:.2f}%' if tem_impostos else ''}",
        fmt_brl(val_impostos) if tem_impostos else "—",
        f"Fat. Bruto × {pct_impostos:.2f}%" if tem_impostos else "Não aplicável",
        accent=C_RED
    )

with cascade_cols[3]: arrow_sep()

with cascade_cols[4]:
    calc_display("Após Impostos",
                 fmt_brl(apos_impostos),
                 "Bruto − Impostos",
                 accent=C_NAVY_LITE)

with cascade_cols[5]: arrow_sep()

with cascade_cols[6]:
    calc_display(
        f"(−) Terceiro{f'  {pct_terceiro:.2f}%' if tem_terceiro else ''}",
        fmt_brl(val_terceiro) if tem_terceiro else "—",
        f"Após Impostos × {pct_terceiro:.2f}%" if tem_terceiro else "Não aplicável",
        accent=C_AMBER
    )

with cascade_cols[7]: arrow_sep()

with cascade_cols[8]:
    calc_display("BASE DE CÁLCULO — LÍQUIDO",
                 fmt_brl(liquido),
                 "Após Impostos − Terceiro",
                 accent=C_GREEN,
                 inverted=True)

# ─────────────────────────────────────────
# SEÇÃO 3 — EQUIPE
# ─────────────────────────────────────────
section_header("Composição da Equipe", "Atribua participantes a cada função")

group_label(
    "Funções Fixas — 30% do Líquido",
    "Taxa de Reserva 10%  ·  Comercial 3,33%  ·  Contrato 3,33%  ·  Análise Inicial 3,33%  ·  Coordenação 10%",
    bg=C_GREEN_LITE, border="#B2D8C4", text=C_GREEN_DARK
)
fixed_cols  = st.columns(5)
fixed_names = {}
for col_ui, (key, label, pct) in zip(fixed_cols, FIXED_FUNCOES):
    if key == "taxa_reserva":
        # Campo travado — sempre Dvolv
        col_ui.text_input(
            f"{label} ({pct:.2f}%)",
            value="Dvolv",
            disabled=True,
            key=f"fixed_{key}"
        )
        fixed_names[key] = "Dvolv"
    else:
        fixed_names[key] = col_ui.text_input(
            f"{label} ({pct:.2f}%)", key=f"fixed_{key}", placeholder="Nome"
        )

group_label(
    "Executores — 70% do Líquido",
    "Preencha em ordem sequencial. Direcionador definido automaticamente pelo número de executores.",
    bg=C_BLUE_LITE, border="#B8C8E0", text=C_NAVY
)
exec_cols  = st.columns(5)
exec_names = []
for i, col_ui in enumerate(exec_cols):
    exec_names.append(
        col_ui.text_input(f"Executor {i+1}", key=f"exec_{i}", placeholder="Nome").strip()
    )

# Validação de ordem
ordem_invalida = False
for i in range(1, 5):
    if exec_names[i] and not exec_names[i - 1]:
        ordem_invalida = True
        alert_box(
            f"Executor {i+1} preenchido sem o Executor {i}. "
            "Preencha em sequência, sem pular posições.",
            "error"
        )
        break

qtd_executores   = sum(1 for n in exec_names if n) if not ordem_invalida else 0
direcionador_num = qtd_executores if qtd_executores >= 1 else 0

if direcionador_num > 0:
    ref = DIRECIONADOR[direcionador_num]
    det = " &nbsp;·&nbsp; ".join([f"Ex{i+1}: {p:.0f}%" for i, p in enumerate(ref) if p > 0])
    alert_box(
        f"<strong>Direcionador {direcionador_num}</strong> &nbsp;—&nbsp; "
        f"{qtd_executores} executor{'es' if qtd_executores > 1 else ''} &nbsp;·&nbsp; {det}",
        "info"
    )
elif not ordem_invalida:
    alert_box("Preencha ao menos o Executor 1 para calcular a distribuição dos 70%.", "warning")

# ─────────────────────────────────────────
# CÁLCULO
# ─────────────────────────────────────────
resultados = []
for key, label, pct in FIXED_FUNCOES:
    resultados.append({
        "Participante":   fixed_names.get(key, ""),
        "Função":         label,
        "Tipo":           "Fixo (30%)",
        "% Distribuição": round(pct, 4),
        "Valor (R$)":     round(liquido * pct / 100, 2),
    })
if direcionador_num >= 1:
    for i, pct in enumerate(DIRECIONADOR[direcionador_num]):
        if pct > 0:
            resultados.append({
                "Participante":   exec_names[i],
                "Função":         f"Executor {i+1}",
                "Tipo":           "Executor (70%)",
                "% Distribuição": float(pct),
                "Valor (R$)":     round(liquido * pct / 100, 2),
            })
df_result = pd.DataFrame(resultados)

# ─────────────────────────────────────────
# SEÇÃO 4 — RESULTADOS
# ─────────────────────────────────────────
st.markdown("<hr style='border-color:rgba(0,0,0,0.08);margin:1.5rem 0'>", unsafe_allow_html=True)
section_header("Resultado da Distribuição", "Valores calculados sobre a base líquida")

# Métricas em cascata
m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1: info_card("Benefício ao Cliente",   fmt_brl(beneficio_cliente), C_NAVY)
with m2: info_card(f"Fat. Bruto ({pct_exito:.1f}% êxito)", fmt_brl(faturamento_bruto), C_NAVY_LITE)
with m3: info_card(f"Impostos ({pct_impostos:.1f}%)" if tem_impostos else "Impostos",
                   fmt_brl(val_impostos) if tem_impostos else "—", C_RED)
with m4: info_card(f"Terceiro ({pct_terceiro:.1f}%)" if tem_terceiro else "Terceiro",
                   fmt_brl(val_terceiro) if tem_terceiro else "—", C_AMBER)
with m5: info_card("Base Líquida",            fmt_brl(liquido),           C_GREEN)
with m6: info_card("Direcionador",            str(direcionador_num) if direcionador_num else "—", C_NAVY)

st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

if not df_result.empty:
    total_pct = df_result["% Distribuição"].sum()
    total_val = df_result["Valor (R$)"].sum()

    st.markdown(f"""
    <div style='background:var(--secondary-background-color);
                border:1px solid rgba(0,0,0,0.07);
                border-radius:4px;padding:0.6rem 1rem;margin-bottom:0.75rem;
                display:flex;gap:2rem;align-items:center'>
      <span style='font-size:0.82rem;opacity:0.7'>
        Total distribuído: <strong style='opacity:1'>{total_pct:.4f}%</strong>
      </span>
      <span style='opacity:0.25'>|</span>
      <span style='font-size:0.82rem;opacity:0.7'>
        Total em R$: <strong style='color:{C_GREEN}'>{fmt_brl(total_val)}</strong>
      </span>
    </div>
    """, unsafe_allow_html=True)

    # Tabela HTML totalmente adaptativa (light + dark mode)
    rows_html = ""
    for _, row in df_result.iterrows():
        is_fixed  = row["Tipo"] == "Fixo (30%)"
        tag_bg    = "rgba(0,105,62,0.15)"    if is_fixed else "rgba(21,101,192,0.15)"
        tag_color = C_GREEN                   if is_fixed else C_BLUE
        nome      = row["Participante"] or "<span style='opacity:0.3;font-style:italic'>—</span>"
        rows_html += f"""
        <tr class='dvolv-row'>
          <td class='dvolv-td'>{nome}</td>
          <td class='dvolv-td'><strong>{row['Função']}</strong></td>
          <td class='dvolv-td'>
            <span style='background:{tag_bg};color:{tag_color};
                         border:1px solid {tag_color}55;border-radius:3px;
                         padding:2px 8px;font-size:0.7rem;font-weight:700;
                         white-space:nowrap;letter-spacing:0.04em'>{row['Tipo']}</span>
          </td>
          <td class='dvolv-td dvolv-num'>{row['% Distribuição']:.4f}%</td>
          <td class='dvolv-td dvolv-num' style='font-weight:700;color:{C_GREEN}'>{fmt_brl(row['Valor (R$)'])}</td>
        </tr>"""

    st.markdown(f"""
    <style>
      .dvolv-table {{ width:100%;border-collapse:collapse;font-size:0.84rem }}
      .dvolv-table thead tr {{ background:{C_NAVY} }}
      .dvolv-table thead th {{
        padding:10px 14px;text-align:left;color:{C_WHITE};font-size:0.68rem;
        font-weight:700;text-transform:uppercase;letter-spacing:0.09em;
        border-right:1px solid rgba(255,255,255,0.07)
      }}
      .dvolv-table thead th:last-child {{ text-align:right;border-right:none }}
      .dvolv-table thead th:nth-child(4) {{ text-align:right }}
      .dvolv-row {{ border-bottom:1px solid rgba(128,128,128,0.12);transition:background 0.15s }}
      .dvolv-row:last-child {{ border-bottom:none }}
      .dvolv-row:hover {{ background:rgba(0,105,62,0.07) }}
      .dvolv-td {{ padding:9px 14px;color:var(--text-color);
                   border-right:1px solid rgba(128,128,128,0.07) }}
      .dvolv-td:last-child {{ border-right:none }}
      .dvolv-num {{ text-align:right;font-variant-numeric:tabular-nums }}
    </style>
    <div style='border:1px solid rgba(128,128,128,0.18);border-radius:6px;
                overflow:hidden;margin-top:0.5rem'>
      <table class='dvolv-table'>
        <thead>
          <tr>
            <th>Participante</th>
            <th>Função</th>
            <th>Tipo</th>
            <th>% Distribuição</th>
            <th>Valor (R$)</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:0.75rem'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    cmap = {"Fixo (30%)": C_GREEN, "Executor (70%)": C_NAVY}
    base_layout = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter"), legend=dict(bgcolor="rgba(0,0,0,0)"),
        legend_title_text="Categoria", margin=dict(t=40, b=30, l=10, r=10),
        title_font=dict(size=13),
    )

    fig_pie = px.pie(df_result, names="Função", values="% Distribuição",
                     title="Composição Percentual", color="Tipo",
                     color_discrete_map=cmap, hole=0.42)
    fig_pie.update_traces(textinfo="percent+label", textfont_size=11,
                          marker=dict(line=dict(color="rgba(255,255,255,0.8)", width=1.5)))
    fig_pie.update_layout(**base_layout)
    c1.plotly_chart(fig_pie, use_container_width=True)

    df_bar = df_result.copy()
    df_bar["Rótulo"] = df_bar.apply(
        lambda r: r["Participante"] if r["Participante"] else r["Função"], axis=1
    )
    fig_bar = px.bar(df_bar.sort_values("Valor (R$)", ascending=False),
                     x="Rótulo", y="Valor (R$)", color="Tipo",
                     color_discrete_map=cmap, text="Valor (R$)",
                     title="Valor R$ por Participante / Função")
    fig_bar.update_traces(texttemplate="%{y:,.2f}", textposition="outside", marker_line_width=0)
    fig_bar.update_layout(**base_layout, xaxis_tickangle=-30, xaxis_title="",
                          yaxis_title="R$", separators=",.",
                          yaxis=dict(gridcolor="rgba(0,0,0,0.06)", gridwidth=0.5))
    c2.plotly_chart(fig_bar, use_container_width=True)

# ─────────────────────────────────────────
# SEÇÃO 5 — EXPORTAR / SALVAR
# ─────────────────────────────────────────
st.markdown("<hr style='border-color:rgba(0,0,0,0.08);margin:1.5rem 0'>", unsafe_allow_html=True)
section_header("Exportar e Registrar")

colx1, colx2 = st.columns(2)
with colx1:
    if st.button("Exportar para Excel", use_container_width=True):
        if df_result.empty:
            alert_box("Preencha ao menos um executor antes de exportar.", "warning")
        else:
            meta = dict(
                project_name=project_name, date=datetime.now().isoformat(),
                cliente=cliente, cnpj=cnpj, servico=servico,
                data_faturamento=data_faturamento.isoformat(),
                forma_pagamento=forma_pagamento,
                beneficio_cliente=beneficio_cliente,
                pct_exito=pct_exito,
                faturamento_bruto=faturamento_bruto,
                tem_impostos=tem_impostos, pct_impostos=pct_impostos, val_impostos=val_impostos,
                tem_terceiro=tem_terceiro, pct_terceiro=pct_terceiro, val_terceiro=val_terceiro,
                liquido=liquido, direcionador=direcionador_num,
            )
            excel_bytes = to_excel_bytes(df_result, meta)
            st.download_button(
                label="Baixar Planilha (.xlsx)",
                data=excel_bytes,
                file_name=f"dvolv_comissoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

with colx2:
    if st.button("Registrar no Histórico", use_container_width=True):
        if df_result.empty:
            alert_box("Nenhum dado para registrar.", "warning")
        else:
            record = dict(
                timestamp=datetime.now().isoformat(),
                project_name=project_name, cliente=cliente, cnpj=cnpj,
                servico=servico, data_faturamento=data_faturamento.isoformat(),
                beneficio_cliente=beneficio_cliente, pct_exito=pct_exito,
                faturamento_bruto=faturamento_bruto,
                pct_impostos=pct_impostos, val_impostos=val_impostos,
                pct_terceiro=pct_terceiro, val_terceiro=val_terceiro,
                liquido=liquido, direcionador=direcionador_num,
            )
            for _, row in df_result.iterrows():
                safe = row["Função"].replace(" ", "_").lower()
                record[f"{safe}_participante"] = row["Participante"]
                record[f"{safe}_pct"]          = row["% Distribuição"]
                record[f"{safe}_val"]          = row["Valor (R$)"]
            append_history(record)
            st.success("Projeto registrado no histórico.")

# ─────────────────────────────────────────
# SEÇÃO 6 — HISTÓRICO
# ─────────────────────────────────────────
st.markdown("<hr style='border-color:rgba(0,0,0,0.08);margin:1.5rem 0'>", unsafe_allow_html=True)
section_header("Histórico de Projetos", "Últimos registros salvos")

hist = load_history()
if hist.empty:
    alert_box("Nenhum projeto registrado ainda. Use 'Registrar no Histórico' para começar.", "info")
else:
    st.markdown(
        f"<p style='font-size:0.82rem;opacity:0.6'>Total de projetos: "
        f"<strong style='opacity:1'>{len(hist)}</strong></p>",
        unsafe_allow_html=True
    )
    base_cols = ["timestamp","project_name","cliente","faturamento_bruto",
                 "val_impostos","val_terceiro","liquido","direcionador"]
    show_cols = [c for c in base_cols if c in hist.columns]
    df_h = hist[show_cols].tail(10).copy()
    for col in ["faturamento_bruto","val_impostos","val_terceiro","liquido"]:
        if col in df_h.columns:
            df_h[col] = df_h[col].apply(lambda v: fmt_brl(v) if pd.notna(v) else "—")
    df_h.rename(columns={
        "timestamp":"Data/Hora","project_name":"Projeto","cliente":"Cliente",
        "faturamento_bruto":"Fat. Bruto","val_impostos":"Impostos",
        "val_terceiro":"Terceiro","liquido":"Líquido","direcionador":"Dir."
    }, inplace=True)
    st.dataframe(df_h, use_container_width=True, hide_index=True)

    person_vals = {}
    for _, row in hist.iterrows():
        for c in hist.columns:
            if c.endswith("_participante"):
                name = str(row[c]).strip() if pd.notna(row[c]) else ""
                val_col = c.replace("_participante", "_val")
                if name and val_col in hist.columns:
                    try:    v = float(row[val_col])
                    except: v = 0.0
                    person_vals[name] = person_vals.get(name, 0.0) + v

    if person_vals:
        st.markdown("<div style='margin-top:1.25rem'></div>", unsafe_allow_html=True)
        section_header("Ranking Acumulado", "Total recebido por participante em todos os projetos")
        df_rank = (
            pd.DataFrame.from_dict(person_vals, orient="index", columns=["Total (R$)"])
            .reset_index().rename(columns={"index": "Participante"})
            .sort_values("Total (R$)", ascending=False)
        )
        df_rd = df_rank.copy()
        df_rd["Total (R$)"] = df_rd["Total (R$)"].apply(fmt_brl)
        st.dataframe(df_rd, use_container_width=True, hide_index=True)

        fig_rank = px.bar(df_rank.head(10), x="Participante", y="Total (R$)",
                          title="Top 10 — Acumulado Histórico", text="Total (R$)",
                          color_discrete_sequence=[C_GREEN])
        fig_rank.update_traces(texttemplate="%{y:,.2f}", textposition="outside", marker_line_width=0)
        fig_rank.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter"), xaxis_tickangle=-30,
            xaxis_title="", yaxis_title="R$", separators=",.",
            margin=dict(t=40, b=40),
            yaxis=dict(gridcolor="rgba(0,0,0,0.06)", gridwidth=0.5)
        )
        st.plotly_chart(fig_rank, use_container_width=True)

# ─────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────
st.markdown(f"""
<div style='background:{C_NAVY};border-radius:6px;padding:1rem 1.5rem;margin-top:2rem;
            display:flex;justify-content:space-between;align-items:center'>
  <div>
    <p style='margin:0;font-size:0.82rem;font-weight:900;color:{C_WHITE};letter-spacing:0.07em'>DVOLV</p>
    <p style='margin:0;font-size:0.68rem;color:#475569'>Inteligência Tributária — Uso Interno</p>
  </div>
  <p style='margin:0;font-size:0.68rem;color:#334155'>
    Dados armazenados localmente · history_projects.csv
  </p>
</div>
""", unsafe_allow_html=True)
