"""
Dashboard Eleitoral Brasil 2022 - versão Streamlit

Como executar localmente:
    streamlit run app.py

Arquivos esperados na mesma pasta:
    - zone_candidates.csv
    - state_summary.csv
"""

from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Eleitoral Brasil 2022",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Constantes ──────────────────────────────────────────────────────────────
BASE = os.path.dirname(__file__)

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

# ── Estilo visual ───────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        .stApp {
            background: #0d1117;
            color: #ffffff;
        }

        [data-testid="stHeader"] {
            background: rgba(13, 17, 23, 0.85);
        }

        .main-header {
            background: #161b22;
            border-bottom: 1px solid #21262d;
            padding: 1rem 1.25rem;
            border-radius: 0 0 14px 14px;
            margin-bottom: 0.8rem;
        }

        .main-title {
            font-size: 1.55rem;
            font-weight: 800;
            color: #ffffff;
        }

        .main-subtitle {
            color: #8b949e;
            font-size: 0.95rem;
            margin-left: 0.3rem;
        }

        .breadcrumb {
            color: #8b949e;
            font-size: 0.9rem;
            padding: 0.4rem 0 0.8rem 0;
        }

        .section-title {
            color: #f4a261;
            font-weight: 800;
            font-size: 1.05rem;
            margin: 0.3rem 0 0.65rem 0;
        }

        .muted {
            color: #8b949e;
        }

        .stat-card {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 14px;
            padding: 0.8rem 0.5rem;
            text-align: center;
            min-height: 86px;
        }

        .stat-number {
            font-size: 1.65rem;
            font-weight: 800;
        }

        .stat-label {
            color: #8b949e;
            font-size: 0.82rem;
        }

        .candidate-card {
            background: #161b22;
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 16px;
            padding: 0.95rem;
            margin-bottom: 0.65rem;
        }

        .candidate-name {
            font-weight: 800;
            font-size: 1rem;
            color: #ffffff;
            margin-bottom: 0.25rem;
        }

        .badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.18rem 0.55rem;
            font-size: 0.75rem;
            font-weight: 700;
            margin-right: 0.35rem;
            color: #fff;
        }

        .badge-secondary {
            background: #30363d;
        }

        .detail-card {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 14px;
            padding: 0.85rem;
            margin-bottom: 0.75rem;
        }

        .avatar {
            width: 64px;
            height: 64px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 1.35rem;
            color: #ffffff;
            margin-right: 0.8rem;
        }

        .welcome-box {
            min-height: 520px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: #8b949e;
            border: 1px dashed #30363d;
            border-radius: 18px;
            background: rgba(22, 27, 34, 0.35);
        }

        div[data-testid="stButton"] > button {
            border-radius: 999px;
            border: 1px solid #30363d;
            background: #161b22;
            color: #ffffff;
        }

        div[data-testid="stButton"] > button:hover {
            border-color: #2a9d8f;
            color: #2a9d8f;
        }

        hr {
            border-color: #21262d;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Carregamento de dados ──────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carrega os CSVs usados no dashboard."""
    zone_path = os.path.join(BASE, "zone_candidates.csv")
    state_path = os.path.join(BASE, "state_summary.csv")

    missing = [path for path in [zone_path, state_path] if not os.path.exists(path)]
    if missing:
        st.error(
            "Arquivos CSV não encontrados. Coloque `zone_candidates.csv` e "
            "`state_summary.csv` na mesma pasta do `app.py`."
        )
        st.stop()

    zone_cands = pd.read_csv(zone_path)
    state_summary = pd.read_csv(state_path)
    return zone_cands, state_summary


zone_cands, state_summary = load_data()


# ── Funções auxiliares ─────────────────────────────────────────────────────
def br_int(value: Any) -> str:
    """Formata inteiros com separador brasileiro."""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)


def initials_from_name(name: str) -> str:
    parts = [p for p in str(name).split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def make_brazil_map(selected_uf: Optional[str] = None) -> go.Figure:
    df = state_summary.copy()
    df["state_name"] = df["UF"].map(STATE_NAMES)
    df["iso"] = "BR-" + df["UF"].astype(str)

    fig = px.choropleth(
        df,
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
            "Zonas: %{customdata[3]}<br>"
            "<i>Clique para ver detalhes</i><extra></extra>"
        )
    )

    if selected_uf:
        fig.add_trace(
            go.Choropleth(
                locations=["BR-" + selected_uf],
                locationmode="ISO-3",
                z=[1],
                colorscale=[[0, "rgba(255,215,0,0.65)"], [1, "rgba(255,215,0,0.65)"]],
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
    )
    return fig


def extract_uf_from_plotly_selection(event: Any) -> Optional[str]:
    """Lê a UF selecionada no mapa do Plotly, quando o Streamlit suportar seleção."""
    if event is None:
        return None

    points: list[dict[str, Any]] = []
    try:
        points = list(event.selection.points)  # Streamlit >= versões com seleção em gráficos
    except Exception:
        try:
            points = event.get("selection", {}).get("points", [])
        except Exception:
            points = []

    if not points:
        return None

    point = points[0]
    location = point.get("location")
    if location and str(location).startswith("BR-"):
        return str(location).replace("BR-", "")

    customdata = point.get("customdata")
    if isinstance(customdata, (list, tuple)) and customdata:
        return str(customdata[0])

    return None


def make_cargo_chart(df: pd.DataFrame) -> go.Figure:
    cargo_df = df.groupby("Cargo")["Nome candidato"].nunique().reset_index()
    cargo_df.columns = ["Cargo", "Eleitos"]
    cargo_df["cor"] = cargo_df["Cargo"].map(CARGO_COLORS).fillna("#888888")

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
        margin=dict(l=0, r=40, t=10, b=0),
        height=230,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="white")),
        font=dict(color="white"),
    )
    return fig


def make_party_chart(df: pd.DataFrame) -> go.Figure:
    party_df = df.groupby("Partido")["Nome candidato"].nunique().reset_index()
    party_df.columns = ["Partido", "Eleitos"]
    party_df = party_df.sort_values("Eleitos", ascending=False).head(10)

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
        height=230,
        xaxis=dict(tickfont=dict(color="white")),
        yaxis=dict(showgrid=False, showticklabels=False),
        font=dict(color="white"),
    )
    return fig


def make_candidate_zone_chart(df: pd.DataFrame, cargo: str) -> go.Figure:
    color = CARGO_COLORS.get(cargo, "#888888")
    zone_votes = df[["Zona", "votos_nominais"]].sort_values("votos_nominais", ascending=False)

    fig = go.Figure(
        go.Bar(
            x=zone_votes["votos_nominais"],
            y=zone_votes["Zona"].astype(str),
            orientation="h",
            marker_color=color,
            text=zone_votes["votos_nominais"].apply(br_int),
            textposition="outside",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=70, t=10, b=20),
        height=max(220, min(len(zone_votes) * 24 + 70, 390)),
        xaxis=dict(showgrid=False, showticklabels=False, color="white"),
        yaxis=dict(tickfont=dict(color="white", size=10), title="Zona"),
        font=dict(color="white"),
    )
    return fig


def set_selected_uf(uf: Optional[str]) -> None:
    if st.session_state.get("selected_uf") != uf:
        st.session_state.selected_uf = uf
        st.session_state.selected_zone = None
        st.session_state.selected_candidate = None


# ── Estado da sessão ───────────────────────────────────────────────────────
if "selected_uf" not in st.session_state:
    st.session_state.selected_uf = None
if "selected_zone" not in st.session_state:
    st.session_state.selected_zone = None
if "selected_candidate" not in st.session_state:
    st.session_state.selected_candidate = None


# ── Cabeçalho ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
        <span style="color:#2a9d8f;font-size:1.45rem;">🗺️</span>
        <span class="main-title">Dashboard Eleitoral Brasil 2022</span>
        <span class="main-subtitle">· Eleições Gerais</span>
    </div>
    """,
    unsafe_allow_html=True,
)

breadcrumb = "<span style='color:#2a9d8f;'>Brasil</span>"
if st.session_state.selected_uf:
    breadcrumb += f" <span>›</span> <span>{STATE_NAMES.get(st.session_state.selected_uf, st.session_state.selected_uf)} ({st.session_state.selected_uf})</span>"
if st.session_state.selected_zone:
    breadcrumb += f" <span>›</span> <span>Zona {st.session_state.selected_zone}</span>"
st.markdown(f"<div class='breadcrumb'>{breadcrumb}</div>", unsafe_allow_html=True)

left_col, right_col = st.columns([0.42, 0.58], gap="large")


# ── Coluna esquerda: mapa e zonas ──────────────────────────────────────────
with left_col:
    st.markdown("<div class='section-title'>Clique em um estado para explorar</div>", unsafe_allow_html=True)

    selected_uf = st.session_state.selected_uf
    map_fig = make_brazil_map(selected_uf)

    try:
        event = st.plotly_chart(
            map_fig,
            use_container_width=True,
            config={"displayModeBar": False},
            key="brazil-map",
            on_select="rerun",
            selection_mode="points",
        )
        clicked_uf = extract_uf_from_plotly_selection(event)
        if clicked_uf and clicked_uf in STATE_NAMES and clicked_uf != st.session_state.selected_uf:
            set_selected_uf(clicked_uf)
            st.rerun()
    except TypeError:
        # Compatibilidade com versões antigas do Streamlit, sem seleção em gráficos.
        st.plotly_chart(map_fig, use_container_width=True, config={"displayModeBar": False})

    uf_options = [None] + sorted(state_summary["UF"].dropna().astype(str).unique().tolist())
    uf_labels = {None: "Selecione uma UF pelo menu", **{uf: f"{STATE_NAMES.get(uf, uf)} ({uf})" for uf in uf_options if uf}}
    current_index = uf_options.index(st.session_state.selected_uf) if st.session_state.selected_uf in uf_options else 0

    uf_choice = st.selectbox(
        "UF",
        uf_options,
        index=current_index,
        format_func=lambda x: uf_labels.get(x, str(x)),
        label_visibility="collapsed",
    )
    if uf_choice != st.session_state.selected_uf:
        set_selected_uf(uf_choice)
        st.rerun()

    if st.session_state.selected_uf:
        uf = st.session_state.selected_uf
        df_state = zone_cands[zone_cands["UF"] == uf]
        zones = sorted(df_state["Zona"].dropna().unique())
        state_name = STATE_NAMES.get(uf, uf)
        n_eleitos = df_state["Nome candidato"].nunique()
        n_zones = len(zones)
        n_cargos = df_state["Cargo"].nunique()

        st.markdown(f"<div class='section-title'>📍 {state_name}</div>", unsafe_allow_html=True)

        s1, s2, s3 = st.columns(3)
        with s1:
            st.markdown(
                f"<div class='stat-card'><div class='stat-number' style='color:#2a9d8f'>{n_eleitos}</div><div class='stat-label'>Eleitos</div></div>",
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"<div class='stat-card'><div class='stat-number' style='color:#f4a261'>{n_zones}</div><div class='stat-label'>Zonas</div></div>",
                unsafe_allow_html=True,
            )
        with s3:
            st.markdown(
                f"<div class='stat-card'><div class='stat-number' style='color:#e63946'>{n_cargos}</div><div class='stat-label'>Cargos</div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<p class='muted'>Selecione uma zona eleitoral:</p>", unsafe_allow_html=True)

        zone_options = [None] + zones
        zone_index = zone_options.index(st.session_state.selected_zone) if st.session_state.selected_zone in zone_options else 0
        zone_choice = st.selectbox(
            "Zona eleitoral",
            zone_options,
            index=zone_index,
            format_func=lambda z: "Visão geral do estado" if z is None else f"Zona {z}",
        )
        if zone_choice != st.session_state.selected_zone:
            st.session_state.selected_zone = zone_choice
            st.session_state.selected_candidate = None
            st.rerun()

        # Grade de botões, mantendo o estilo do app original.
        grid_cols = st.columns(3)
        for i, z in enumerate(zones):
            zone_df = df_state[df_state["Zona"] == z]
            n = zone_df["Nome candidato"].nunique()
            label = f"Zona {z}\n{n} eleito{'s' if n != 1 else ''}"
            if grid_cols[i % 3].button(label, key=f"zone-{uf}-{z}"):
                st.session_state.selected_zone = z
                st.session_state.selected_candidate = None
                st.rerun()


# ── Coluna direita: visão geral, candidatos e detalhes ─────────────────────
with right_col:
    uf = st.session_state.selected_uf
    zone = st.session_state.selected_zone

    if not uf:
        st.markdown(
            """
            <div class="welcome-box">
                <div style="font-size:4rem;color:#2a9d8f;opacity:0.65;">🗳️</div>
                <h2>Explore os Eleitos de 2022</h2>
                <p style="max-width:470px;">
                    Clique em qualquer estado no mapa ou escolha uma UF no menu para visualizar
                    candidatos eleitos, zonas eleitorais, cargos e detalhes de cada político.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        df_state = zone_cands[zone_cands["UF"] == uf]
        state_name = STATE_NAMES.get(uf, uf)

        if not zone:
            st.markdown(
                f"<h3>🚩 {state_name} <span class='muted'>({uf})</span></h3>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p class='muted'>Selecione uma zona eleitoral no painel à esquerda para ver os candidatos.</p>",
                unsafe_allow_html=True,
            )

            st.markdown("<div class='section-title'>Eleitos por Cargo</div>", unsafe_allow_html=True)
            st.plotly_chart(make_cargo_chart(df_state), use_container_width=True, config={"displayModeBar": False})

            st.markdown("<div class='section-title'>Top 10 Partidos</div>", unsafe_allow_html=True)
            st.plotly_chart(make_party_chart(df_state), use_container_width=True, config={"displayModeBar": False})

        else:
            df_zone = df_state[df_state["Zona"] == zone]
            candidates = df_zone.drop_duplicates("Nome candidato").sort_values("total_votos", ascending=False)

            st.markdown(
                f"<h3>📍 Zona {zone} · {state_name}</h3>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<p class='muted'>{len(candidates)} candidato{'s' if len(candidates) != 1 else ''} eleito{'s' if len(candidates) != 1 else ''}</p>",
                unsafe_allow_html=True,
            )

            # Detalhes do candidato selecionado, substituindo o modal do Dash.
            selected_candidate = st.session_state.selected_candidate
            if selected_candidate:
                df_candidate = df_state[df_state["Nome candidato"] == selected_candidate]
                if not df_candidate.empty:
                    row = df_candidate.iloc[0]
                    cargo = row["Cargo"]
                    partido = row["Partido"]
                    genero = row.get("Gênero", "-")
                    ocupacao = row.get("Ocupação", "-")
                    faixa = row.get("Faixa etária", "-")
                    total = df_candidate["total_votos"].iloc[0]
                    color = CARGO_COLORS.get(cargo, "#888888")
                    initials = initials_from_name(selected_candidate)
                    wiki_name = str(selected_candidate).title().replace(" ", "_")
                    wiki_url = f"https://pt.wikipedia.org/wiki/{wiki_name}"
                    photo_search = (
                        "https://commons.wikimedia.org/w/index.php?search="
                        f"{quote_plus(str(selected_candidate))}&title=Special:MediaSearch&go=Go&type=image"
                    )

                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="display:flex;align-items:center;margin-bottom:0.8rem;">
                                <div class="avatar" style="background:{color};">{initials}</div>
                                <div>
                                    <h3 style="margin:0;">{str(selected_candidate).title()}</h3>
                                    <span class="badge" style="background:{color};">{cargo}</span>
                                    <span class="badge badge-secondary">{partido}</span>
                                    <div style="margin-top:0.35rem;">
                                        <a href="{wiki_url}" target="_blank" style="color:#58a6ff;text-decoration:none;">Wikipedia</a>
                                        <span class="muted"> · </span>
                                        <a href="{photo_search}" target="_blank" style="color:#8b949e;text-decoration:none;">Buscar foto</a>
                                    </div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        d1, d2 = st.columns(2)
                        with d1:
                            st.markdown(
                                f"<div class='detail-card'>⚧ <span class='muted'>Gênero:</span> <b>{genero}</b></div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"<div class='detail-card'>💼 <span class='muted'>Ocupação:</span> <b>{ocupacao}</b></div>",
                                unsafe_allow_html=True,
                            )
                        with d2:
                            st.markdown(
                                f"<div class='detail-card'>🎂 <span class='muted'>Faixa Etária:</span> <b>{faixa}</b></div>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(
                                f"<div class='detail-card'>🗺️ <span class='muted'>Estado:</span> <b>{state_name} ({uf})</b></div>",
                                unsafe_allow_html=True,
                            )

                        st.markdown(
                            f"<p><span class='muted'>Total de Votos:</span> <b style='color:{color};font-size:1.35rem;'>{br_int(total)}</b></p>",
                            unsafe_allow_html=True,
                        )
                        st.markdown("<div class='section-title'>Votos por Zona Eleitoral</div>", unsafe_allow_html=True)
                        st.plotly_chart(
                            make_candidate_zone_chart(df_candidate, cargo),
                            use_container_width=True,
                            config={"displayModeBar": False},
                        )

                        if st.button("Fechar detalhes", key="close-candidate-details"):
                            st.session_state.selected_candidate = None
                            st.rerun()

                st.divider()

            # Lista de candidatos da zona selecionada.
            for _, row in candidates.iterrows():
                cargo = row["Cargo"]
                color = CARGO_COLORS.get(cargo, "#888888")
                name = row["Nome candidato"]
                votos_zona = row["votos_nominais"]
                total = row["total_votos"]
                initials = initials_from_name(name)

                card_left, card_right = st.columns([0.83, 0.17], vertical_alignment="center")
                with card_left:
                    st.markdown(
                        f"""
                        <div class="candidate-card" style="border-color:{color}55;">
                            <div style="display:flex;align-items:center;gap:0.8rem;">
                                <div class="avatar" style="background:{color};width:52px;height:52px;font-size:1rem;margin:0;">{initials}</div>
                                <div>
                                    <div class="candidate-name">{str(name).title()}</div>
                                    <span class="badge" style="background:{color};">{cargo}</span>
                                    <span class="badge badge-secondary">{row['Partido']}</span>
                                    <div class="muted" style="font-size:0.82rem;margin-top:0.35rem;">
                                        🗳 {br_int(total)} votos totais · Zona: {br_int(votos_zona)}
                                    </div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with card_right:
                    if st.button("Ver", key=f"candidate-{uf}-{zone}-{name}"):
                        st.session_state.selected_candidate = name
                        st.rerun()
