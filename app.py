from pathlib import Path
import math
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# Configuração geral
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Eleitoral Brasil 2022",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"

STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}

CARGO_COLORS = {
    "Governador": "#e63946",
    "Senador": "#f4a261",
    "Deputado Federal": "#2a9d8f",
    "Deputado Estadual": "#457b9d",
    "Deputado Distrital": "#6a4c93",
    "Presidente": "#e9c46a",
}

REQUIRED_COLUMNS = [
    "UF", "Zona", "Nome candidato", "Cargo", "Partido", "Gênero",
    "Ocupação", "Faixa etária", "Turno", "votos_nominais", "total_votos",
]

# ─────────────────────────────────────────────────────────────────────────────
# Estilo visual
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .stApp { background-color: #0d1117; color: #f0f6fc; }
    [data-testid="stSidebar"] { background-color: #161b22; }
    .block-container { padding-top: 1.3rem; padding-bottom: 2rem; }
    .small-muted { color: #8b949e; font-size: 0.87rem; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 14px 16px;
        text-align: center;
    }
    .candidate-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .candidate-name { font-weight: 700; color: #ffffff; font-size: 0.98rem; }
    .badge {
        display: inline-block;
        border-radius: 999px;
        padding: 3px 8px;
        font-size: 0.75rem;
        font-weight: 700;
        color: white;
        margin-right: 6px;
        margin-top: 4px;
    }
    .badge-secondary { background: #6c757d; }
    a { color: #58a6ff !important; }
    hr { border-color: #30363d; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Funções de dados
# ─────────────────────────────────────────────────────────────────────────────
def format_int(value) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except Exception:
        return "0"


def sort_zones(zones):
    def key(z):
        try:
            return (0, int(float(z)))
        except Exception:
            return (1, str(z))
    return sorted(zones, key=key)


def find_prepared_files():
    """Procura o arquivo reduzido do dashboard.

    O app aceita:
    - data/eleitos_zona.csv.gz
    - eleitos_zona.csv.gz
    - data/eleitos_zona_part001.csv.gz, data/eleitos_zona_part002.csv.gz, ...
    """
    part_files = sorted(DATA_DIR.glob("eleitos_zona_part*.csv.gz"))
    if part_files:
        return part_files

    candidates = [DATA_DIR / "eleitos_zona.csv.gz", BASE / "eleitos_zona.csv.gz"]
    return [p for p in candidates if p.exists()]


@st.cache_data(show_spinner="Carregando dados preparados...")
def load_prepared_data() -> pd.DataFrame:
    files = find_prepared_files()
    if not files:
        st.error(
            "Não encontrei o arquivo preparado `eleitos_zona.csv.gz`. "
            "Rode primeiro: `python preparar_dados.py`."
        )
        st.stop()

    frames = []
    for file in files:
        frames.append(pd.read_csv(file, compression="gzip"))

    df = pd.concat(frames, ignore_index=True)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"O arquivo preparado está sem estas colunas: {missing}")
        st.stop()

    df["UF"] = df["UF"].astype(str).str.upper().str.strip()
    df["Zona"] = df["Zona"].astype(str).str.strip()
    df["votos_nominais"] = pd.to_numeric(df["votos_nominais"], errors="coerce").fillna(0).astype(int)
    df["total_votos"] = pd.to_numeric(df["total_votos"], errors="coerce").fillna(0).astype(int)

    return df


@st.cache_data(show_spinner=False)
def make_state_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        df.groupby("UF")
        .agg(
            num_eleitos=("Nome candidato", "nunique"),
            num_zonas=("Zona", "nunique"),
        )
        .reset_index()
    )
    summary["state_name"] = summary["UF"].map(STATE_NAMES).fillna(summary["UF"])
    summary["iso"] = "BR-" + summary["UF"]
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Gráficos
# ─────────────────────────────────────────────────────────────────────────────
def make_brazil_map(summary: pd.DataFrame, selected_uf=None):
    plot_df = summary.copy()

    fig = px.choropleth(
        plot_df,
        locations="iso",
        locationmode="ISO-3",
        color="num_eleitos",
        color_continuous_scale="Blues",
        scope="south america",
        custom_data=["UF", "state_name", "num_eleitos", "num_zonas"],
        labels={"num_eleitos": "Eleitos"},
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[1]}</b><br>"
            "Eleitos: %{customdata[2]}<br>"
            "Zonas: %{customdata[3]}<extra></extra>"
        )
    )

    if selected_uf:
        fig.add_trace(
            go.Choropleth(
                locations=["BR-" + selected_uf],
                locationmode="ISO-3",
                z=[1],
                colorscale=[[0, "rgba(255,215,0,0.60)"], [1, "rgba(255,215,0,0.60)"]],
                showscale=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(
            title=dict(text="Eleitos", font=dict(color="white")),
            tickfont=dict(color="white"),
        ),
        geo=dict(
            bgcolor="rgba(0,0,0,0)",
            lakecolor="rgba(0,0,0,0)",
            landcolor="rgba(40,40,60,1)",
            showlakes=True,
            showland=True,
            showcoastlines=True,
            coastlinecolor="rgba(100,100,120,0.5)",
            showframe=False,
            projection_type="mercator",
            center=dict(lat=-14, lon=-52),
            lataxis_range=[-35, 6],
            lonaxis_range=[-75, -34],
        ),
        height=520,
        font=dict(color="white"),
    )
    return fig


def make_cargo_chart(df_state: pd.DataFrame):
    cargo_df = (
        df_state.groupby("Cargo")["Nome candidato"]
        .nunique()
        .reset_index(name="Eleitos")
        .sort_values("Eleitos")
    )
    cargo_df["cor"] = cargo_df["Cargo"].map(CARGO_COLORS).fillna("#888")

    fig = go.Figure(
        go.Bar(
            x=cargo_df["Eleitos"],
            y=cargo_df["Cargo"],
            orientation="h",
            marker_color=cargo_df["cor"].tolist(),
            text=cargo_df["Eleitos"],
            textposition="outside",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=45, t=10, b=0),
        height=240,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="white")),
        font=dict(color="white"),
    )
    return fig


def make_party_chart(df_state: pd.DataFrame):
    party_df = (
        df_state.groupby("Partido")["Nome candidato"]
        .nunique()
        .reset_index(name="Eleitos")
        .sort_values("Eleitos", ascending=False)
        .head(10)
    )
    fig = go.Figure(
        go.Bar(
            x=party_df["Partido"],
            y=party_df["Eleitos"],
            marker_color="#2a9d8f",
            text=party_df["Eleitos"],
            textposition="outside",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=260,
        xaxis=dict(tickfont=dict(color="white")),
        yaxis=dict(showgrid=False, showticklabels=False),
        font=dict(color="white"),
    )
    return fig


def make_candidate_zone_chart(df_candidate: pd.DataFrame, cargo: str):
    color = CARGO_COLORS.get(cargo, "#888")
    zone_votes = (
        df_candidate[["Zona", "votos_nominais"]]
        .groupby("Zona", as_index=False)["votos_nominais"]
        .sum()
        .sort_values("votos_nominais", ascending=True)
    )
    fig = go.Figure(
        go.Bar(
            x=zone_votes["votos_nominais"],
            y=zone_votes["Zona"].astype(str),
            orientation="h",
            marker_color=color,
            text=zone_votes["votos_nominais"].apply(format_int),
            textposition="outside",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=70, t=10, b=20),
        height=max(220, min(len(zone_votes) * 24 + 70, 470)),
        xaxis=dict(showgrid=False, showticklabels=False, color="white"),
        yaxis=dict(tickfont=dict(color="white", size=10), title="Zona"),
        font=dict(color="white"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Componentes de tela
# ─────────────────────────────────────────────────────────────────────────────
def metric_card(label, value, color):
    st.markdown(
        f"""
        <div class="metric-card">
            <div style="font-size:1.65rem;font-weight:800;color:{color};">{value}</div>
            <div class="small-muted">{label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def candidate_card(row, selected_zone):
    cargo = row["Cargo"]
    color = CARGO_COLORS.get(cargo, "#888")
    name = str(row["Nome candidato"]).title()
    total = format_int(row["total_votos"])
    votos_zona = format_int(row["votos_nominais"])

    st.markdown(
        f"""
        <div class="candidate-card" style="border-color:{color}66;">
            <div class="candidate-name">{name}</div>
            <span class="badge" style="background:{color};">{cargo}</span>
            <span class="badge badge-secondary">{row['Partido']}</span>
            <div class="small-muted" style="margin-top:8px;">
                🗳 {total} votos totais &nbsp; | &nbsp; Zona {selected_zone}: {votos_zona}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_candidate_details(df: pd.DataFrame, uf: str, candidate_name: str):
    df_candidate = df[(df["UF"] == uf) & (df["Nome candidato"] == candidate_name)]
    if df_candidate.empty:
        return

    row = df_candidate.iloc[0]
    cargo = row["Cargo"]
    color = CARGO_COLORS.get(cargo, "#888")
    state_name = STATE_NAMES.get(uf, uf)
    total = format_int(df_candidate["total_votos"].max())
    wiki_name = str(candidate_name).title().replace(" ", "_")
    wiki_url = f"https://pt.wikipedia.org/wiki/{wiki_name}"
    photo_search = (
        "https://commons.wikimedia.org/w/index.php?search="
        + str(candidate_name).replace(" ", "+")
        + "&title=Special:MediaSearch&go=Go&type=image"
    )

    st.markdown("---")
    st.subheader(str(candidate_name).title())
    st.markdown(
        f"<span class='badge' style='background:{color};'>{cargo}</span>"
        f"<span class='badge badge-secondary'>{row['Partido']}</span>",
        unsafe_allow_html=True,
    )
    st.caption(f"[{wiki_url.replace('https://', '')}]({wiki_url}) · [Buscar foto no Wikimedia Commons]({photo_search})")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total de votos", total, color)
    with c2:
        metric_card("Estado", f"{state_name} ({uf})", "#f4a261")
    with c3:
        metric_card("Gênero", row.get("Gênero", "-"), "#2a9d8f")
    with c4:
        metric_card("Faixa etária", row.get("Faixa etária", "-"), "#e63946")

    st.markdown(f"**Ocupação:** {row.get('Ocupação', '-')}")
    st.markdown("#### Votos por Zona Eleitoral")
    st.plotly_chart(make_candidate_zone_chart(df_candidate, cargo), use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────
df = load_prepared_data()
state_summary = make_state_summary(df)

st.title("Dashboard Eleitoral Brasil 2022")
st.caption("Eleições Gerais · candidatos eleitos por UF e zona eleitoral")

if "selected_uf" not in st.session_state:
    st.session_state.selected_uf = None
if "selected_zone" not in st.session_state:
    st.session_state.selected_zone = None
if "selected_candidate" not in st.session_state:
    st.session_state.selected_candidate = None

ufs = sort_zones(df["UF"].dropna().unique())
uf_options = ["Brasil"] + ufs
current_uf = st.session_state.selected_uf or "Brasil"

with st.sidebar:
    st.header("Filtros")
    selected_label = st.selectbox(
        "Selecione a UF",
        uf_options,
        index=uf_options.index(current_uf) if current_uf in uf_options else 0,
    )

    new_uf = None if selected_label == "Brasil" else selected_label
    if new_uf != st.session_state.selected_uf:
        st.session_state.selected_uf = new_uf
        st.session_state.selected_zone = None
        st.session_state.selected_candidate = None

    if st.session_state.selected_uf:
        uf = st.session_state.selected_uf
        zones = sort_zones(df[df["UF"] == uf]["Zona"].dropna().unique())
        zone_options = ["Visão geral"] + zones
        current_zone = st.session_state.selected_zone or "Visão geral"
        selected_zone = st.selectbox(
            "Selecione a zona eleitoral",
            zone_options,
            index=zone_options.index(current_zone) if current_zone in zone_options else 0,
        )
        new_zone = None if selected_zone == "Visão geral" else selected_zone
        if new_zone != st.session_state.selected_zone:
            st.session_state.selected_zone = new_zone
            st.session_state.selected_candidate = None

    st.markdown("---")
    st.caption("Dica: o arquivo original grande não precisa ir para o GitHub. Use apenas o CSV preparado pelo script.")

left, right = st.columns([1.05, 1.35], gap="large")

with left:
    st.markdown("#### Mapa do Brasil")
    fig_map = make_brazil_map(state_summary, st.session_state.selected_uf)

    # Em versões recentes do Streamlit, o clique no Plotly pode funcionar.
    # O selectbox lateral permanece como alternativa estável.
    try:
        map_event = st.plotly_chart(
            fig_map,
            use_container_width=True,
            config={"displayModeBar": False},
            on_select="rerun",
            selection_mode="points",
            key="mapa_brasil",
        )
        points = map_event.get("selection", {}).get("points", []) if isinstance(map_event, dict) else []
        if points:
            loc = points[0].get("location", "")
            if isinstance(loc, str) and loc.startswith("BR-"):
                clicked_uf = loc.replace("BR-", "")
                if clicked_uf in ufs and clicked_uf != st.session_state.selected_uf:
                    st.session_state.selected_uf = clicked_uf
                    st.session_state.selected_zone = None
                    st.session_state.selected_candidate = None
                    st.rerun()
    except TypeError:
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

    if st.session_state.selected_uf:
        uf = st.session_state.selected_uf
        df_state = df[df["UF"] == uf]
        zones = sort_zones(df_state["Zona"].dropna().unique())
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Eleitos", df_state["Nome candidato"].nunique(), "#2a9d8f")
        with c2:
            metric_card("Zonas", len(zones), "#f4a261")
        with c3:
            metric_card("Cargos", df_state["Cargo"].nunique(), "#e63946")

with right:
    uf = st.session_state.selected_uf
    zone = st.session_state.selected_zone

    if not uf:
        st.markdown("### Explore os Eleitos de 2022")
        st.write(
            "Selecione uma UF no menu lateral ou clique em um estado no mapa para visualizar "
            "os candidatos eleitos, zonas eleitorais, cargos, partidos e detalhes de votação."
        )
        st.markdown("#### Resumo nacional")
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("UFs", df["UF"].nunique(), "#2a9d8f")
        with c2:
            metric_card("Eleitos", df["Nome candidato"].nunique(), "#f4a261")
        with c3:
            metric_card("Zonas", df["Zona"].nunique(), "#e63946")

    elif not zone:
        df_state = df[df["UF"] == uf]
        state_name = STATE_NAMES.get(uf, uf)
        st.markdown(f"### {state_name} ({uf})")
        st.caption("Selecione uma zona eleitoral no menu lateral para ver os candidatos.")
        st.markdown("#### Eleitos por Cargo")
        st.plotly_chart(make_cargo_chart(df_state), use_container_width=True, config={"displayModeBar": False})
        st.markdown("#### Top 10 Partidos")
        st.plotly_chart(make_party_chart(df_state), use_container_width=True, config={"displayModeBar": False})

    else:
        df_zone = df[(df["UF"] == uf) & (df["Zona"] == zone)].copy()
        state_name = STATE_NAMES.get(uf, uf)
        candidates = (
            df_zone.drop_duplicates("Nome candidato")
            .sort_values("total_votos", ascending=False)
        )

        st.markdown(f"### Zona {zone} · {state_name}")
        st.caption(f"{len(candidates)} candidato(s) eleito(s)")

        candidate_names = candidates["Nome candidato"].tolist()
        selected_candidate = st.selectbox(
            "Ver detalhes do candidato",
            ["Selecione"] + candidate_names,
            format_func=lambda x: "Selecione" if x == "Selecione" else str(x).title(),
        )
        if selected_candidate != "Selecione":
            st.session_state.selected_candidate = selected_candidate

        for _, row in candidates.iterrows():
            candidate_card(row, zone)
            if st.button("Ver detalhes", key=f"btn_{uf}_{zone}_{row['Nome candidato']}"):
                st.session_state.selected_candidate = row["Nome candidato"]

        if st.session_state.selected_candidate:
            show_candidate_details(df, uf, st.session_state.selected_candidate)
