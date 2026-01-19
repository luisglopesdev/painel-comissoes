import streamlit as st
import pandas as pd
import numpy as np
import json
import os
from io import BytesIO
import plotly.express as px
from datetime import datetime

# ---------------------------
# CONFIG / CONSTANTS
# ---------------------------
st.set_page_config(page_title="Comissões - Painel Financeiro",
                   layout="wide", initial_sidebar_state="expanded")

DATA_DIR = "."
PRESETS_FILE = os.path.join(DATA_DIR, "presets.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history_projects.csv")

DEFAULT_FUNCOES = [
    {"Função": "Vendedor", "Grupo": "COM", "Existe": 1, "Peso": 1},
    {"Função": "Coordenador", "Grupo": "COM", "Existe": 1, "Peso": 1},
    {"Função": "Executor 1", "Grupo": "EXEC", "Existe": 1, "Peso": 5},
    {"Função": "Executor 2", "Grupo": "EXEC", "Existe": 0, "Peso": 2},
    {"Função": "Executor 3", "Grupo": "EXEC", "Existe": 0, "Peso": 1},
    {"Função": "Retificador 1", "Grupo": "RET", "Existe": 1, "Peso": 3},
    {"Função": "Retificador 2", "Grupo": "RET", "Existe": 0, "Peso": 1},
]

DEFAULT_PRESETS = {
    # Vendedor, Coordenador, Executor 1, Executor 2, Executor 3, Retificador 1, Retificador 2
    "A - Simples":         [10, 10, 70, 0, 0, 10, 0],
    "B - 2 Exec + 1 Ret":  [10, 10, 50, 20, 0, 10, 0],
    "C - 3 Exec + 1 Ret":  [10, 10, 40, 20, 10, 10, 0],
    "D - 2 Exec + 2 Ret":  [10, 10, 45, 20, 0, 10, 5],
    "E - Completo":        [10, 10, 45, 20, 10, 12, 3],  # deixei como estava, já que você não mandou novo modelo
    "Auto (Dinâmico)":     None
}


DEFAULT_POOLS = {"COM": 20.0, "EXEC": 60.0, "RET": 20.0}

# ---------------------------
# HELPERS: pt-BR formatting
# ---------------------------
def fmt_ptbr_number(x, decimals=2):
    try:
        x = 0.0 if x is None else float(x)
    except Exception:
        x = 0.0
    s = f"{x:,.{decimals}f}"  # 10,000.00
    return s.replace(",", "X").replace(".", ",").replace("X", ".")  # 10.000,00

def fmt_brl(x):
    return f"R$ {fmt_ptbr_number(x, 2)}"

def parse_ptbr_number(s):
    if s is None:
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).strip()
    if not s:
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def recalc_faturamento():
    beneficio = parse_ptbr_number(st.session_state.get("beneficio_cliente_str", "0"))
    exito = float(st.session_state.get("percent_exito", 0.0) or 0.0)
    fat = beneficio * (exito / 100.0)
    st.session_state.beneficio_cliente = beneficio
    st.session_state.faturamento = fat
    st.session_state.faturamento_str = fmt_ptbr_number(fat, 2)

# ---------------------------
# HELPERS: load/save presets & history
# ---------------------------
def load_presets():
    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE, "r", encoding="utf-8") as f:
                presets = json.load(f)
            for k, v in DEFAULT_PRESETS.items():
                if k not in presets:
                    presets[k] = v
            return presets
        except Exception:
            return DEFAULT_PRESETS.copy()
    else:
        return DEFAULT_PRESETS.copy()

def save_presets(presets):
    with open(PRESETS_FILE, "w", encoding="utf-8") as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)

def append_history(record: dict):
    df = pd.DataFrame([record])
    if os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df.to_csv(HISTORY_FILE, index=False, encoding="utf-8")

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE, encoding="utf-8")
    else:
        return pd.DataFrame()

def to_excel_bytes(df_result, df_input, preset_name, meta):
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "RESULTADO"
    ws1.append([f"Projeto: {meta.get('project_name','')}"])
    ws1.append([f"Data: {meta.get('date', '')}"])
    ws1.append([f"Faturamento: {fmt_brl(meta.get('faturamento', 0))}"])
    ws1.append([f"Comissão total (%): {meta.get('comissao_pct',0)}"])
    ws1.append([f"Preset: {preset_name}"])
    ws1.append([f"Data Faturamento: {meta.get('data_faturamento','')}"])
    ws1.append([f"Cliente: {meta.get('cliente','')}"])
    ws1.append([f"CNPJ: {meta.get('cnpj','')}"])
    ws1.append([f"Serviço: {meta.get('servico','')}"])
    ws1.append([f"Forma Pagamento: {meta.get('forma_pagamento','')}"])
    ws1.append([f"Benefício Cliente: {fmt_brl(meta.get('beneficio_cliente', 0))}"])
    ws1.append([f"% Êxito: {meta.get('percent_exito',0):.2f}"])
    ws1.append([])
    for r in dataframe_to_rows(df_result, index=False, header=True):
        ws1.append(r)
    ws2 = wb.create_sheet("INPUT")
    for r in dataframe_to_rows(df_input, index=False, header=True):
        ws2.append(r)
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.read()

# ---------------------------
# CALC: distribution logic
# ---------------------------
def distribuir_auto(df_funcoes, pools):
    df = df_funcoes.copy()
    df["Existe"] = df["Existe"].astype(int)
    soma = df[df["Existe"] == 1].groupby("Grupo")["Peso"].sum().to_dict()
    for g in ["COM", "EXEC", "RET"]:
        soma.setdefault(g, 0.0)
    pct_final = []
    for _, row in df.iterrows():
        if row["Existe"] == 0:
            pct_final.append(0.0)
            continue
        g = row["Grupo"]
        if soma[g] == 0:
            pct_final.append(0.0)
        else:
            val = (row["Peso"] / soma[g]) * pools.get(g, 0.0)
            pct_final.append(float(val))
    return pd.Series(pct_final, index=df.index)

# ---------------------------
# SESSION STATE DEFAULTS
# ---------------------------
if "beneficio_cliente_str" not in st.session_state:
    st.session_state.beneficio_cliente_str = fmt_ptbr_number(0.0, 2)
if "percent_exito" not in st.session_state:
    st.session_state.percent_exito = 100.0
if "faturamento_str" not in st.session_state:
    st.session_state.faturamento_str = fmt_ptbr_number(0.0, 2)
if "beneficio_cliente" not in st.session_state:
    st.session_state.beneficio_cliente = 0.0
if "faturamento" not in st.session_state:
    st.session_state.faturamento = 0.0

recalc_faturamento()

# ---------------------------
# UI: Sidebar - settings, presets
# ---------------------------
st.sidebar.header("Configurações")
presets = load_presets()
preset_names = list(presets.keys())
preset_choice = st.sidebar.selectbox(
    "Escolher Preset",
    preset_names,
    index=preset_names.index("A - Simples") if "A - Simples" in preset_names else 0
)

st.sidebar.markdown("**Pools (Total 100%)** — alterar se quiser")
col1, col2, col3 = st.sidebar.columns(3)
pool_COM = col1.number_input("COM (%)", value=DEFAULT_POOLS["COM"], min_value=0.0, max_value=100.0, step=1.0)
pool_EXEC = col2.number_input("EXEC (%)", value=DEFAULT_POOLS["EXEC"], min_value=0.0, max_value=100.0, step=1.0)
pool_RET = col3.number_input("RET (%)", value=DEFAULT_POOLS["RET"], min_value=0.0, max_value=100.0, step=1.0)

if abs((pool_COM + pool_EXEC + pool_RET) - 100.0) > 0.001:
    st.sidebar.warning("Os pools não somam 100%. Ajuste para totalizar 100% se desejar.")

st.sidebar.markdown("---")
st.sidebar.subheader("Gerenciar Presets")
with st.sidebar.expander("Criar / Atualizar preset"):
    new_name = st.text_input("Nome do preset", value="Meu Preset")
    base_len = len(DEFAULT_FUNCOES)
    default_weights = [
        DEFAULT_PRESETS.get("A - Simples", [])[i]
        if i < len(DEFAULT_PRESETS.get("A - Simples", [])) else 0
        for i in range(base_len)
    ]
    weights = []
    cols = st.columns([3, 1])
    for i, f in enumerate([x["Função"] for x in DEFAULT_FUNCOES]):
        w = cols[0].number_input(
            f"{f} (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(default_weights[i] if default_weights else 0.0),
            key=f"preset_w_{i}"
        )
        weights.append(w)
    save_preset_btn = st.button("Salvar preset", key="save_preset")
    if save_preset_btn:
        presets[new_name] = weights
        save_presets(presets)
        st.success(f"Preset '{new_name}' salvo.")
        preset_names = list(presets.keys())

st.sidebar.markdown("---")
if st.sidebar.button("Limpar histórico"):
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
        st.sidebar.success("Histórico apagado.")
    else:
        st.sidebar.info("Não havia histórico.")

# ---------------------------
# MAIN: Header
# ---------------------------
st.markdown("<h1 style='color:#2b6f2b;'>📊 Painel de Distribuição de Comissões</h1>", unsafe_allow_html=True)
st.markdown(f"<div style='color:#6b7280'>Servidor: local — {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>", unsafe_allow_html=True)

# ---------------------------
# INPUTS: project info + cliente + financials (auto faturamento)
# ---------------------------
st.markdown("### 📝 Informações do Projeto / Cliente")
colA, colB = st.columns(2)
data_faturamento = colA.date_input("Data do Faturamento", value=datetime.today(), format="DD/MM/YYYY")
cliente = colA.text_input("Cliente", value="")
cnpj = colB.text_input("CNPJ", value="")
servico = colA.text_input("Serviço", value="")

colB.text_input(
    "Benefício gerado p/ cliente (R$)",
    key="beneficio_cliente_str",
    on_change=recalc_faturamento
)

forma_pagamento = colB.date_input("Forma de Pagamento", value=datetime.today(), format="DD/MM/YYYY")

st.markdown("### 💰 Informações Financeiras")
col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
project_name = col1.text_input("Nome do Projeto", value="")

col2.number_input(
    "% Êxito",
    min_value=0.0,
    max_value=100.0,
    step=0.1,
    format="%.2f",
    key="percent_exito",
    on_change=recalc_faturamento
)

col3.text_input(
    "Faturamento do Projeto (R$)",
    key="faturamento_str",
    disabled=True
)

comissao_pct = col4.number_input("Comissão total (%)", min_value=0.0, value=5.0, step=0.1)

beneficio_cliente = st.session_state.beneficio_cliente
percent_exito = float(st.session_state.percent_exito or 0.0)
faturamento = st.session_state.faturamento

# ---------------------------
# FUNCTIONS TABLE (editable with Nome participante)
# ---------------------------
if "df_funcoes" not in st.session_state:
    st.session_state.df_funcoes = pd.DataFrame(DEFAULT_FUNCOES)

if "Nome participante" not in st.session_state.df_funcoes.columns:
    st.session_state.df_funcoes.insert(0, "Nome participante", "")

st.markdown("### 👥 Composição da equipe (edite livremente)")
edited = st.data_editor(st.session_state.df_funcoes, num_rows="dynamic", key="editor")

df_funcoes = edited.copy()
for c in ["Nome participante", "Função", "Grupo", "Existe", "Peso"]:
    if c not in df_funcoes.columns:
        df_funcoes[c] = 1 if c in ["Existe", "Peso"] else ""
df_funcoes["Grupo"] = df_funcoes["Grupo"].astype(str).str.upper().replace({"EXECUTOR": "EXEC"})
df_funcoes["Grupo"] = df_funcoes["Grupo"].replace({"EXEC": "EXEC", "RET": "RET", "COM": "COM", "COMERCIAL": "COM"})
df_funcoes["Existe"] = df_funcoes["Existe"].astype(int).clip(0, 1)
df_funcoes["Peso"] = pd.to_numeric(df_funcoes["Peso"], errors="coerce").fillna(0).astype(float)
st.session_state.df_funcoes = df_funcoes

# ---------------------------
# CALCULATION: apply preset or auto
# ---------------------------
n = len(df_funcoes)
if preset_choice not in presets:
    st.error("Preset não encontrado. Escolha outro.")
    pct_series = pd.Series([0.0] * n, index=df_funcoes.index)
else:
    preset_val = presets[preset_choice]
    if preset_choice == "Auto (Dinâmico)" or preset_val is None:
        pct_series = distribuir_auto(df_funcoes, {"COM": pool_COM, "EXEC": pool_EXEC, "RET": pool_RET})
    else:
        v = preset_val + [0.0] * (n - len(preset_val)) if len(preset_val) < n else preset_val[:n]
        pct_series = pd.Series(v, index=df_funcoes.index).astype(float)

comissao_total_val = faturamento * (comissao_pct / 100.0)
valores = (faturamento * (pct_series / 100.0)).round(2)

df_result = df_funcoes.copy()
df_result["% Final"] = pct_series.fillna(0.0).round(4)
df_result["Valor (R$)"] = valores
group_sum_pct = df_result.groupby("Grupo")["% Final"].transform(lambda s: s.where(df_result["Existe"] == 1, 0).sum())
df_result["% no Grupo"] = df_result.apply(
    lambda r: (r["% Final"] / group_sum_pct[r.name] * 100) if group_sum_pct[r.name] and r["Existe"] == 1 else 0.0,
    axis=1
).round(2)
df_result = df_result[["Nome participante", "Função", "Grupo", "Existe", "Peso", "% Final", "% no Grupo", "Valor (R$)"]]

# ---------------------------
# DISPLAY RESULTS
# ---------------------------
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Faturamento", fmt_brl(faturamento))
col2.metric("Comissão total (%)", f"{comissao_pct:.2f}%")
col3.metric("Valor comissão (R$)", fmt_brl(comissao_total_val))

st.write(
    f"**Preset:** {preset_choice}    •    "
    f"**Total % distribuído:** {df_result['% Final'].sum():.4f}%    •    "
    f"**Total R$ distribuído:** {fmt_brl(df_result['Valor (R$)'].sum())}"
)

st.dataframe(
    df_result.style.format({
        "% Final": "{:.4f}",
        "% no Grupo": "{:.2f}",
        "Valor (R$)": lambda v: fmt_brl(v)
    }),
    use_container_width=True
)

# ---------------------------
# VISUALS: pie + bar
# ---------------------------
fig_pie = px.pie(df_result[df_result["Existe"] == 1], names="Nome participante", values="% Final",
                 title="Distribuição % por Participante", hole=0.35)
fig_pie.update_traces(textinfo="percent+label")
fig_pie.update_layout(separators=",.")

fig_bar = px.bar(df_result[df_result["Existe"] == 1].sort_values("Valor (R$)", ascending=False),
                 x="Nome participante", y="Valor (R$)", title="Valor R$ por Participante", text="Valor (R$)")
fig_bar.update_layout(xaxis_tickangle=-45, separators=",.")

c1, c2 = st.columns([1, 1])
c1.plotly_chart(fig_pie, use_container_width=True)
c2.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------
# EXPORT / SAVE / HISTORY
# ---------------------------
st.markdown("---")
colx1, colx2, colx3 = st.columns([1, 1, 1])

with colx1:
    if st.button("📥 Exportar Excel (Resultado + Input)"):
        meta = {
            "project_name": project_name,
            "date": datetime.now().isoformat(),
            "faturamento": faturamento,
            "comissao_pct": comissao_pct,
            "data_faturamento": data_faturamento.isoformat(),
            "cliente": cliente,
            "cnpj": cnpj,
            "servico": servico,
            "forma_pagamento": forma_pagamento.isoformat(),
            "beneficio_cliente": beneficio_cliente,
            "percent_exito": percent_exito
        }
        excel_bytes = to_excel_bytes(df_result, df_funcoes, preset_choice, meta)
        st.download_button(
            "Baixar Excel",
            data=excel_bytes,
            file_name=f"comissoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

with colx2:
    if st.button("💾 Salvar Projeto no Histórico"):
        record = {
            "timestamp": datetime.now().isoformat(),
            "project_name": project_name,
            "faturamento": faturamento,
            "comissao_pct": comissao_pct,
            "preset": preset_choice,
            "data_faturamento": data_faturamento.isoformat(),
            "cliente": cliente,
            "cnpj": cnpj,
            "servico": servico,
            "forma_pagamento": forma_pagamento.isoformat(),
            "beneficio_cliente": beneficio_cliente,
            "percent_exito": percent_exito
        }
        for i, row in df_result.reset_index().iterrows():
            record[f"fun_{i}_participant"] = row["Nome participante"]
            record[f"fun_{i}_name"] = row["Função"]
            record[f"fun_{i}_pct"] = row["% Final"]
            record[f"fun_{i}_val"] = row["Valor (R$)"]
        append_history(record)
        st.success("Projeto salvo no histórico.")

with colx3:
    if st.button("🔁 Resetar tabela para padrão"):
        st.session_state.df_funcoes = pd.DataFrame(DEFAULT_FUNCOES)
        st.experimental_rerun()

# ---------------------------
# HISTORY & RANKING
# ---------------------------
st.markdown("## 📚 Histórico de Projetos")
hist = load_history()
if hist.empty:
    st.info("Nenhum projeto salvo ainda. Use 'Salvar Projeto no Histórico' para começar.")
else:
    st.write(f"Total projetos salvos: {len(hist)}")
    st.dataframe(hist.tail(10).drop(columns=[c for c in hist.columns if c.startswith("fun_")][:0]), use_container_width=True)

    person_vals = {}
    for _, row in hist.iterrows():
        for c in hist.columns:
            if c.endswith("_participant"):
                idx = c.split("_")[1]
                name = row[c]
                val_col = f"fun_{idx}_val"
                if pd.notna(name) and val_col in hist.columns:
                    v = row.get(val_col, 0.0)
                    try:
                        v = float(v)
                    except Exception:
                        v = 0.0
                    person_vals[name] = person_vals.get(name, 0.0) + v

    if person_vals:
        df_rank = pd.DataFrame.from_dict(person_vals, orient="index", columns=["Total R$"]).reset_index().rename(columns={"index": "Participante"})
        df_rank = df_rank.sort_values("Total R$", ascending=False)
        st.markdown("### 🏆 Ranking acumulado (por participante)")
        st.dataframe(df_rank.style.format({"Total R$": lambda v: fmt_brl(v)}), use_container_width=True)

        fig_rank = px.bar(df_rank.head(10), x="Participante", y="Total R$", title="Top 10 - Acumulado", text="Total R$")
        fig_rank.update_layout(separators=",.")
        st.plotly_chart(fig_rank, use_container_width=True)

# ---------------------------
# EXPORTAR EXCEL A PARTIR DO HISTÓRICO
# ---------------------------

st.markdown("## 📦 Exportar Excel de projeto salvo do histórico")

hist_export = load_history()
if hist_export.empty:
    st.info("Nenhum projeto salvo no histórico para exportar.")
else:
    # montar labels para escolha do projeto
    labels = []
    idx_map = {}
    for idx, row in hist_export.iterrows():
        ts = str(row.get("timestamp", ""))[:19]
        nome = str(row.get("project_name", "") or "")
        cli = str(row.get("cliente", "") or "")
        label = f"{idx} - {ts} - {nome} - {cli}"
        labels.append(label)
        idx_map[label] = idx

    selected_label = st.selectbox(
        "Selecione o projeto do histórico para gerar o Excel",
        options=[""] + labels,
        index=0
    )

    if selected_label:
        selected_idx = idx_map[selected_label]
        row = hist_export.loc[selected_idx]

        # monta meta para o relatório
        meta_hist = {
            "project_name": row.get("project_name", ""),
            "date": row.get("timestamp", ""),
            "faturamento": row.get("faturamento", 0.0),
            "comissao_pct": row.get("comissao_pct", 0.0),
            "data_faturamento": row.get("data_faturamento", ""),
            "cliente": row.get("cliente", ""),
            "cnpj": row.get("cnpj", ""),
            "servico": row.get("servico", ""),
            "forma_pagamento": row.get("forma_pagamento", ""),
            "beneficio_cliente": row.get("beneficio_cliente", 0.0),
            "percent_exito": row.get("percent_exito", 0.0),
        }

        # reconstrói df_result a partir das colunas fun_* gravadas no histórico
        participantes = []
        for col in hist_export.columns:
            if col.startswith("fun_") and col.endswith("_participant"):
                idx_fun = col.split("_")[1]   # ex: fun_0_participant -> "0"
                nome_part = row.get(f"fun_{idx_fun}_participant", "")
                funcao = row.get(f"fun_{idx_fun}_name", "")
                pct = row.get(f"fun_{idx_fun}_pct", 0.0)
                val = row.get(f"fun_{idx_fun}_val", 0.0)

                # ignora linhas vazias
                if (pd.isna(nome_part) or str(nome_part).strip() == "") and \
                   (pd.isna(funcao) or str(funcao).strip() == ""):
                    continue

                participantes.append({
                    "Nome participante": str(nome_part or ""),
                    "Função": str(funcao or ""),
                    "Grupo": "",
                    "Existe": 1,
                    "Peso": 0.0,
                    "% Final": float(pct or 0.0),
                    "% no Grupo": 0.0,
                    "Valor (R$)": float(val or 0.0)
                })

        if participantes:
            df_result_hist = pd.DataFrame(participantes)
            # input mínimo para a aba INPUT do Excel
            df_input_hist = df_result_hist[["Nome participante", "Função", "Grupo", "Existe", "Peso"]].copy()

            excel_hist_bytes = to_excel_bytes(
                df_result_hist,
                df_input_hist,
                row.get("preset", ""),
                meta_hist
            )

            st.download_button(
                "Baixar Excel do projeto selecionado",
                data=excel_hist_bytes,
                file_name=f"comissoes_hist_{selected_idx}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Este registro de histórico não possui dados de participantes para gerar o Excel.")

st.markdown("---")
st.caption("App local — arquivos gerados na pasta do app (presets.json e history_projects.csv).")



