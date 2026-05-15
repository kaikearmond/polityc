from pathlib import Path
import math
import os
import urllib.parse
import urllib.request
import json

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
        display: flex;
        gap: 14px;
        align-items: flex-start;
    }
    .candidate-card-photo {
        width: 64px;
        height: 64px;
        border-radius: 50%;
        object-fit: cover;
        flex-shrink: 0;
        border: 2px solid #30363d;
        background: #21262d;
    }
    .candidate-card-photo-placeholder {
        width: 64px;
        height: 64px;
        border-radius: 50%;
        flex-shrink: 0;
        border: 2px solid #30363d;
        background: #21262d;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
    }
    .candidate-card-body { flex: 1; min-width: 0; }
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

    /* Flashcard de detalhes do candidato */
    .detail-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 18px;
        padding: 24px;
        margin-top: 18px;
    }
    .detail-card-header {
        display: flex;
        gap: 20px;
        align-items: flex-start;
        margin-bottom: 18px;
    }
    .detail-card-photo {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #30363d;
        background: #21262d;
        flex-shrink: 0;
    }
    .detail-card-photo-placeholder {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        border: 3px solid #30363d;
        background: #21262d;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.8rem;
        flex-shrink: 0;
    }
    .detail-card-info { flex: 1; }
    .detail-card-name {
        font-size: 1.35rem;
        font-weight: 800;
        color: #ffffff;
        margin-bottom: 6px;
    }
    .detail-card-desc {
        color: #c9d1d9;
        font-size: 0.92rem;
        line-height: 1.55;
        margin-top: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Funções utilitárias
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
    part_files = sorted(DATA_DIR.glob("eleitos_zona_part*.csv.gz"))
    if part_files:
        return part_files
    candidates = [DATA_DIR / "eleitos_zona.csv.gz", BASE / "eleitos_zona.csv.gz"]
    return [p for p in candidates if p.exists()]


# ─────────────────────────────────────────────────────────────────────────────
# Wikipedia helpers (urllib puro — sem dependência de 'requests')
# ─────────────────────────────────────────────────────────────────────────────

def _wiki_api(params: dict, timeout: int = 5) -> dict:
    """Chama a API do Wikipedia pt e retorna o JSON. Lança em caso de erro."""
    params["format"] = "json"
    url = "https://pt.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "DashboardEleitoral/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _find_wiki_page_title(raw_name: str) -> str | None:
    """
    Usa list=search para encontrar o título exato da página no Wikipedia pt.
    Necessário porque os nomes no CSV estão em maiúsculas e o .title() pode
    gerar 'Lula Da Silva' em vez de 'Lula da Silva'.
    """
    try:
        data = _wiki_api({
            "action": "query",
            "list": "search",
            "srsearch": str(raw_name).title(),
            "srlimit": 1,
            "srnamespace": 0,
        })
        results = data.get("query", {}).get("search", [])
        if results:
            return results[0]["title"]
    except Exception:
        pass
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_wikimedia_photo(name: str) -> str | None:
    """
    Busca foto do candidato no Wikipedia pt.
    Estratégia:
      1. Usa list=search para achar o título exato da página.
      2. Busca a thumbnail da página encontrada.
    Retorna URL da imagem ou None.
    """
    try:
        page_title = _find_wiki_page_title(name)
        if not page_title:
            return None

        data = _wiki_api({
            "action": "query",
            "titles": page_title,
            "prop": "pageimages",
            "pithumbsize": 220,
            "redirects": 1,
        })
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                return thumb
    except Exception:
        pass
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_candidate_description(name: str, cargo: str, uf: str, partido: str) -> str:
    """
    Busca introdução do artigo do Wikipedia pt para o candidato.
    Estratégia:
      1. list=search para achar o título exato.
      2. prop=extracts para pegar o texto de introdução.
    Se não achar nada, retorna descrição gerada com dados disponíveis.
    """
    try:
        page_title = _find_wiki_page_title(name)
        if page_title:
            data = _wiki_api({
                "action": "query",
                "titles": page_title,
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "exsentences": 3,
                "redirects": 1,
            })
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    continue
                extract = page.get("extract", "").strip()
                if extract and len(extract) > 40:
                    if len(extract) > 320:
                        extract = extract[:320].rsplit(" ", 1)[0] + "…"
                    return extract
    except Exception:
        pass

    # Fallback: texto gerado com os dados do CSV
    state_name = STATE_NAMES.get(uf, uf)
    genero = ""  # será preenchido externamente se disponível
    return (
        f"{str(name).title()} foi eleito(a) {cargo} pelo estado de {state_name} "
        f"nas eleições gerais de 2022, representando o partido {partido}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Carregamento de dados
# ─────────────────────────────────────────────────────────────────────────────
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
    """Mapa coroplético apenas do Brasil, fixo, sem outros países."""
    plot_df = summary.copy()

    # Trace principal – todos os estados com gradiente de azul
    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            locations=plot_df["iso"],
            locationmode="ISO-3",
            z=plot_df["num_eleitos"],
            colorscale="Blues",
            customdata=plot_df[["UF", "state_name", "num_eleitos", "num_zonas"]].values,
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                "Eleitos: %{customdata[2]}<br>"
                "Zonas: %{customdata[3]}<extra></extra>"
            ),
            colorbar=dict(
                title=dict(text="Eleitos", font=dict(color="white")),
                tickfont=dict(color="white"),
            ),
            marker_line_color="rgba(100,100,120,0.6)",
            marker_line_width=0.8,
        )
    )

    # Destaque amarelo sobre o estado selecionado
    if selected_uf:
        sel_row = plot_df[plot_df["UF"] == selected_uf]
        if not sel_row.empty:
            fig.add_trace(
                go.Choropleth(
                    locations=["BR-" + selected_uf],
                    locationmode="ISO-3",
                    z=[1],
                    colorscale=[[0, "rgba(255,215,0,0.70)"], [1, "rgba(255,215,0,0.70)"]],
                    showscale=False,
                    hoverinfo="skip",
                    marker_line_color="rgba(255,215,0,1)",
                    marker_line_width=2.5,
                )
            )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        # Mapa 100% fixo no Brasil — sem scroll, sem zoom, sem pan
        geo=dict(
            bgcolor="rgba(13,17,23,1)",        # fundo = cor do app
            lakecolor="rgba(13,17,23,1)",
            landcolor="rgba(40,40,60,1)",
            showlakes=True,
            showland=True,
            showcoastlines=False,              # sem litoral de outros países
            showframe=False,
            showocean=True,
            oceancolor="rgba(13,17,23,1)",
            showcountries=False,               # sem fronteiras de outros países
            showsubunits=False,
            resolution=50,
            projection_type="mercator",
            # Centraliza e trava o enquadramento exato no Brasil
            center=dict(lat=-14, lon=-52),
            lataxis=dict(range=[-34, 6], showgrid=False),
            lonaxis=dict(range=[-74, -28], showgrid=False),
        ),
        height=520,
        font=dict(color="white"),
        # Desativa completamente interações de zoom/pan
        dragmode=False,
    )
    return fig


def make_cargo_chart_deputies(df_state: pd.DataFrame):
    """Gráfico mostrando apenas Deputados Estaduais e Federais eleitos."""
    deputy_cargos = ["Deputado Estadual", "Deputado Federal", "Deputado Distrital"]
    cargo_df = (
        df_state[df_state["Cargo"].isin(deputy_cargos)]
        .groupby("Cargo")["Nome candidato"]
        .nunique()
        .reset_index(name="Eleitos")
        .sort_values("Eleitos")
    )

    if cargo_df.empty:
        return None

    cargo_df["cor"] = cargo_df["Cargo"].map(CARGO_COLORS).fillna("#888")

    fig = go.Figure(
        go.Bar(
            x=cargo_df["Eleitos"],
            y=cargo_df["Cargo"],
            orientation="h",
            marker_color=cargo_df["cor"].tolist(),
            text=cargo_df["Eleitos"],
            textposition="outside",
            textfont=dict(color="white", size=14, weight=700),
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=55, t=10, b=0),
        height=180,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="white", size=13)),
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
    """Card compacto com foto, cargo e votos."""
    cargo = row["Cargo"]
    color = CARGO_COLORS.get(cargo, "#888")
    name = str(row["Nome candidato"]).title()
    total = format_int(row["total_votos"])
    votos_zona = format_int(row["votos_nominais"])

    photo_url = get_wikimedia_photo(row["Nome candidato"])

    if photo_url:
        photo_html = f'<img class="candidate-card-photo" src="{photo_url}" alt="{name}">'
    else:
        photo_html = '<div class="candidate-card-photo-placeholder">👤</div>'

    st.markdown(
        f"""
        <div class="candidate-card" style="border-color:{color}66;">
            {photo_html}
            <div class="candidate-card-body">
                <div class="candidate-name">{name}</div>
                <span class="badge" style="background:{color};">{cargo}</span>
                <span class="badge badge-secondary">{row['Partido']}</span>
                <div class="small-muted" style="margin-top:8px;">
                    🗳 {total} votos totais &nbsp;|&nbsp; Zona {selected_zone}: {votos_zona}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_candidate_details(df: pd.DataFrame, uf: str, candidate_name: str):
    """Flashcard completo com foto, descricao e grafico de votos por zona."""
    df_candidate = df[(df["UF"] == uf) & (df["Nome candidato"] == candidate_name)]
    if df_candidate.empty:
        st.warning("Candidato nao encontrado nos dados.")
        return

    row = df_candidate.iloc[0]
    cargo = str(row.get("Cargo", ""))
    partido = str(row.get("Partido", ""))
    genero = str(row.get("Genero", row.get("Gênero", "")))
    faixa = str(row.get("Faixa etaria", row.get("Faixa etária", "-")))
    ocupacao = str(row.get("Ocupacao", row.get("Ocupação", "-"))).title()

    color = CARGO_COLORS.get(cargo, "#888")
    state_name = STATE_NAMES.get(uf, uf)
    total = format_int(df_candidate["total_votos"].max())
    name_title = str(candidate_name).title()

    # Determina pronome para o fallback
    pronome = "eleita" if "FEMININO" in genero.upper() else "eleito(a)"

    with st.spinner(f"Buscando informacoes sobre {name_title}..."):
        photo_url = get_wikimedia_photo(candidate_name)
        description = get_candidate_description(candidate_name, cargo, uf, partido)

    if "eleito(a)" in description and pronome != "eleito(a)":
        description = description.replace("eleito(a)", pronome)

    if photo_url:
        photo_html = (
            f'<img class="detail-card-photo" src="{photo_url}" alt="{name_title}" '
            f'onerror="this.style.display=\'none\'">'
        )
    else:
        photo_html = '<div class="detail-card-photo-placeholder">👤</div>'

    wiki_search = urllib.parse.quote(name_title)
    wiki_url = f"https://pt.wikipedia.org/w/index.php?search={wiki_search}"

    st.markdown("---")
    st.markdown(
        f"""
        <div class="detail-card" style="border-color:{color}55;">
            <div class="detail-card-header">
                {photo_html}
                <div class="detail-card-info">
                    <div class="detail-card-name">{name_title}</div>
                    <span class="badge" style="background:{color};">{cargo}</span>
                    <span class="badge badge-secondary">{row['Partido']}</span>
                    <span class="badge badge-secondary">{state_name} ({uf})</span>
                    <div class="detail-card-desc">{description}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Métricas abaixo do card
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total de votos", total, color)
    with c2:
        metric_card("Gênero", genero.title() if genero else "-", "#2a9d8f")
    with c3:
        metric_card("Faixa etária", faixa, "#e63946")
    with c4:
        metric_card("Ocupação", ocupacao, "#f4a261")

    st.caption(f"[Ver no Wikipedia]({wiki_url})")
    st.markdown("#### Votos por Zona Eleitoral")
    st.plotly_chart(
        make_candidate_zone_chart(df_candidate, cargo),
        use_container_width=True,
        config={"displayModeBar": False},
    )


# ─────────────────────────────────────────────────────────────────────────────
# App principal
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

# ── Sidebar ──────────────────────────────────────────────────────────────────
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

# ── Layout principal ──────────────────────────────────────────────────────────
left, right = st.columns([1.05, 1.35], gap="large")

with left:
    st.markdown("#### Mapa do Brasil")

    fig_map = make_brazil_map(state_summary, st.session_state.selected_uf)

    try:
        map_event = st.plotly_chart(
            fig_map,
            use_container_width=True,
            config={
                "displayModeBar": False,
                "scrollZoom": False,         # sem zoom por scroll
                "doubleClick": False,        # sem reset por duplo clique
                "showTips": False,
            },
            on_select="rerun",
            selection_mode="points",
            key="mapa_brasil",
        )
        points = (
            map_event.get("selection", {}).get("points", [])
            if isinstance(map_event, dict)
            else []
        )
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
        st.plotly_chart(
            fig_map,
            use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False},
        )

    # Métricas do estado selecionado (abaixo do mapa)
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

# ── Painel direito ────────────────────────────────────────────────────────────
with right:
    uf = st.session_state.selected_uf
    zone = st.session_state.selected_zone

    # ── Tela inicial (nenhum estado selecionado) ──────────────────────────────
    if not uf:
        st.markdown("### Explore os Eleitos de 2022")
        st.write(
            "Selecione uma UF no menu lateral ou clique em um estado no mapa para visualizar "
            "os candidatos eleitos, zonas eleitorais, cargos, partidos e detalhes de votação."
        )

    # ── Visão geral do estado ─────────────────────────────────────────────────
    elif not zone:
        df_state = df[df["UF"] == uf]
        state_name = STATE_NAMES.get(uf, uf)
        st.markdown(f"### {state_name} ({uf})")
        st.caption("Selecione uma zona eleitoral no menu lateral para ver os candidatos.")

        st.markdown("#### Deputados eleitos por cargo")
        fig_dep = make_cargo_chart_deputies(df_state)
        if fig_dep is not None:
            st.plotly_chart(fig_dep, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhum deputado eleito encontrado para este estado.")

        st.markdown("#### Top 10 Partidos")
        st.plotly_chart(make_party_chart(df_state), use_container_width=True, config={"displayModeBar": False})

    # ── Zona eleitoral selecionada ────────────────────────────────────────────
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
