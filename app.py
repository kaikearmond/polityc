from pathlib import Path
import urllib.parse
import urllib.request
import json

import pandas as pd
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

# GeoJSON com os estados do Brasil (propriedade sigla = UF, ex: "AC", "SP")
BRAZIL_GEOJSON_URL = (
    "https://raw.githubusercontent.com/giuliano-macedo/"
    "geodata-br-states/main/geojson/br_states.geojson"
)

STATE_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapa",
    "BA": "Bahia", "CE": "Ceara", "DF": "Distrito Federal", "ES": "Espirito Santo",
    "GO": "Goias", "MA": "Maranhao", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Para", "PB": "Paraiba", "PE": "Pernambuco",
    "PI": "Piaui", "PR": "Parana", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondonia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "Sao Paulo", "TO": "Tocantins",
}

# Display names with accents (for HTML only)
STATE_NAMES_DISPLAY = {
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
        background: #161b22; border: 1px solid #30363d;
        border-radius: 14px; padding: 14px 16px; text-align: center;
    }

    .candidate-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 14px; padding: 14px 16px; margin-bottom: 10px;
        display: flex; gap: 14px; align-items: flex-start;
    }
    .ccard-photo {
        width: 64px; height: 64px; border-radius: 50%;
        object-fit: cover; flex-shrink: 0;
        border: 2px solid #30363d; background: #21262d;
    }
    .ccard-nophoto {
        width: 64px; height: 64px; border-radius: 50%; flex-shrink: 0;
        border: 2px solid #30363d; background: #21262d;
        display: flex; align-items: center; justify-content: center; font-size: 1.7rem;
    }
    .ccard-body { flex: 1; min-width: 0; }
    .ccard-name { font-weight: 700; color: #ffffff; font-size: 0.98rem; }

    .detail-card {
        background: #161b22; border: 1px solid #30363d;
        border-radius: 18px; padding: 24px; margin-top: 18px;
    }
    .detail-header { display: flex; gap: 20px; align-items: flex-start; margin-bottom: 18px; }
    .detail-photo {
        width: 100px; height: 100px; border-radius: 50%;
        object-fit: cover; border: 3px solid #30363d;
        background: #21262d; flex-shrink: 0;
    }
    .detail-nophoto {
        width: 100px; height: 100px; border-radius: 50%;
        border: 3px solid #30363d; background: #21262d;
        display: flex; align-items: center; justify-content: center;
        font-size: 2.8rem; flex-shrink: 0;
    }
    .detail-info { flex: 1; }
    .detail-name { font-size: 1.35rem; font-weight: 800; color: #ffffff; margin-bottom: 6px; }
    .detail-desc { color: #c9d1d9; font-size: 0.92rem; line-height: 1.55; margin-top: 10px; }

    .gov-card {
        border-radius: 18px; padding: 20px 22px; margin-bottom: 22px;
        display: flex; gap: 20px; align-items: center;
        background: #161b22;
    }
    .gov-photo {
        width: 86px; height: 86px; border-radius: 50%;
        object-fit: cover; flex-shrink: 0;
    }
    .gov-nophoto {
        width: 86px; height: 86px; border-radius: 50%; flex-shrink: 0;
        background: #21262d;
        display: flex; align-items: center; justify-content: center; font-size: 2.2rem;
    }
    .gov-body { flex: 1; }
    .gov-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: #8b949e; margin-bottom: 4px; }
    .gov-name { font-size: 1.25rem; font-weight: 800; color: #ffffff; margin-bottom: 6px; }

    .badge {
        display: inline-block; border-radius: 999px; padding: 3px 8px;
        font-size: 0.75rem; font-weight: 700; color: white;
        margin-right: 6px; margin-top: 4px;
    }
    .badge-sec { background: #6c757d; }
    a { color: #58a6ff !important; }
    hr { border-color: #30363d; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
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
    return [p for p in [DATA_DIR / "eleitos_zona.csv.gz", BASE / "eleitos_zona.csv.gz"] if p.exists()]


def _http_get(url: str, timeout: int = 8) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "DashboardEleitoral/2.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# GeoJSON do Brasil
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=86400)
def load_brazil_geojson():
    try:
        return _http_get(BRAZIL_GEOJSON_URL, timeout=15)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Fotos — múltiplas fontes
# ─────────────────────────────────────────────────────────────────────────────
def _wiki_search_title(query: str) -> str | None:
    try:
        url = ("https://pt.wikipedia.org/w/api.php?" +
               urllib.parse.urlencode({
                   "action": "query", "list": "search",
                   "srsearch": query, "srlimit": 1,
                   "srnamespace": 0, "format": "json",
               }))
        data = _http_get(url, timeout=5)
        results = data.get("query", {}).get("search", [])
        if results:
            return results[0]["title"]
    except Exception:
        pass
    return None


def _wiki_photo(title: str) -> str | None:
    try:
        url = ("https://pt.wikipedia.org/w/api.php?" +
               urllib.parse.urlencode({
                   "action": "query", "titles": title,
                   "prop": "pageimages", "pithumbsize": 240,
                   "redirects": 1, "format": "json",
               }))
        data = _http_get(url, timeout=5)
        for page in data.get("query", {}).get("pages", {}).values():
            t = page.get("thumbnail", {}).get("source")
            if t:
                return t
    except Exception:
        pass
    return None


def _wiki_extract(title: str) -> str | None:
    try:
        url = ("https://pt.wikipedia.org/w/api.php?" +
               urllib.parse.urlencode({
                   "action": "query", "titles": title,
                   "prop": "extracts", "exintro": True,
                   "explaintext": True, "exsentences": 3,
                   "redirects": 1, "format": "json",
               }))
        data = _http_get(url, timeout=6)
        for pid, page in data.get("query", {}).get("pages", {}).items():
            if pid == "-1":
                continue
            ext = page.get("extract", "").strip()
            if ext and len(ext) > 40:
                return (ext[:340].rsplit(" ", 1)[0] + "…") if len(ext) > 340 else ext
    except Exception:
        pass
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def _camara_photo(name: str, uf: str) -> str | None:
    """Busca foto na API da Câmara dos Deputados (legislatura 57 = eleitos 2022)."""
    try:
        words = str(name).title().split()
        search = " ".join(words[:3])
        # Tenta primeiro com filtro de UF
        for params in [
            {"nome": search, "siglaUf": uf, "legislatura": 57, "ordem": "ASC", "ordenarPor": "nome"},
            {"nome": search, "legislatura": 57, "ordem": "ASC", "ordenarPor": "nome"},
        ]:
            url = ("https://dadosabertos.camara.leg.br/api/v2/deputados?" +
                   urllib.parse.urlencode(params))
            data = _http_get(url, timeout=6)
            deps = data.get("dados", [])
            if deps and deps[0].get("urlFoto"):
                return deps[0]["urlFoto"]
    except Exception:
        pass
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_photo(name: str, cargo: str, uf: str = "") -> str | None:
    """
    Estratégia multi-fonte:
      1. API da Câmara dos Deputados  →  apenas Deputados Federais
      2. Wikipedia pt com 4 variantes →  todos
    """
    if cargo == "Deputado Federal":
        p = _camara_photo(name, uf)
        if p:
            return p

    name_t = str(name).title()
    state = STATE_NAMES_DISPLAY.get(uf, "")
    for query in [
        name_t,
        f"{name_t} político",
        f"{name_t} {cargo.lower()}",
        f"{name_t} {state}",
    ]:
        title = _wiki_search_title(query)
        if title:
            p = _wiki_photo(title)
            if p:
                return p
    return None


@st.cache_data(show_spinner=False, ttl=3600)
def get_description(name: str, cargo: str, uf: str, partido: str, genero: str = "") -> str:
    name_t = str(name).title()
    for q in [name_t, f"{name_t} político"]:
        title = _wiki_search_title(q)
        if title:
            ext = _wiki_extract(title)
            if ext:
                return ext
    pronome = "eleita" if "FEMININO" in genero.upper() else "eleito"
    state = STATE_NAMES_DISPLAY.get(uf, uf)
    return (
        f"{name_t} foi {pronome} {cargo} pelo estado de {state} "
        f"nas eleições gerais de 2022, representando o partido {partido}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Dados
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Carregando dados preparados...")
def load_prepared_data() -> pd.DataFrame:
    files = find_prepared_files()
    if not files:
        st.error("Não encontrei `eleitos_zona.csv.gz`. Rode: `python preparar_dados.py`.")
        st.stop()
    df = pd.concat([pd.read_csv(f, compression="gzip") for f in files], ignore_index=True)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Colunas ausentes: {missing}")
        st.stop()
    df["UF"] = df["UF"].astype(str).str.upper().str.strip()
    df["Zona"] = df["Zona"].astype(str).str.strip()
    df["votos_nominais"] = pd.to_numeric(df["votos_nominais"], errors="coerce").fillna(0).astype(int)
    df["total_votos"] = pd.to_numeric(df["total_votos"], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(show_spinner=False)
def make_state_summary(df: pd.DataFrame) -> pd.DataFrame:
    s = (df.groupby("UF")
         .agg(num_eleitos=("Nome candidato", "nunique"), num_zonas=("Zona", "nunique"))
         .reset_index())
    s["state_name"] = s["UF"].map(STATE_NAMES_DISPLAY).fillna(s["UF"])
    return s


# ─────────────────────────────────────────────────────────────────────────────
# Mapa — GeoJSON: somente Brasil, nenhum país vizinho
# ─────────────────────────────────────────────────────────────────────────────
def make_brazil_map(summary: pd.DataFrame, selected_uf: str | None = None):
    """
    Cria um mapa APENAS com os estados do Brasil.

    O ponto principal aqui é NÃO usar a camada geográfica padrão do Plotly
    como fundo do mapa, porque ela pode exibir países vizinhos. Por isso,
    usamos geo.visible=False e desenhamos somente os polígonos do GeoJSON
    brasileiro.
    """
    geojson = load_brazil_geojson()
    fig = go.Figure()

    # Garante que o mapa sempre desenhe os 27 estados, mesmo que algum UF
    # não apareça no CSV carregado.
    all_states = pd.DataFrame({
        "UF": list(STATE_NAMES_DISPLAY.keys()),
        "state_name": list(STATE_NAMES_DISPLAY.values()),
    })
    map_summary = all_states.merge(
        summary[["UF", "num_eleitos", "num_zonas"]],
        on="UF",
        how="left",
    )
    map_summary["num_eleitos"] = map_summary["num_eleitos"].fillna(0).astype(int)
    map_summary["num_zonas"] = map_summary["num_zonas"].fillna(0).astype(int)

    if geojson:
        # Trace principal: todos os estados brasileiros.
        fig.add_trace(go.Choropleth(
            geojson=geojson,
            featureidkey="properties.sigla",
            locations=map_summary["UF"],
            z=map_summary["num_eleitos"],
            colorscale=[
                [0.00, "#1b263b"],
                [0.25, "#274c77"],
                [0.50, "#468faf"],
                [0.75, "#61a5c2"],
                [1.00, "#89c2d9"],
            ],
            customdata=map_summary[["UF", "state_name", "num_eleitos", "num_zonas"]].values,
            hovertemplate=(
                "<b>%{customdata[1]} (%{customdata[0]})</b><br>"
                "Eleitos: %{customdata[2]}<br>"
                "Zonas: %{customdata[3]}<extra></extra>"
            ),
            colorbar=dict(
                title=dict(text="Eleitos", font=dict(color="white")),
                tickfont=dict(color="white"),
                bgcolor="rgba(13,17,23,0.92)",
                bordercolor="rgba(255,255,255,0.15)",
                borderwidth=1,
            ),
            marker_line_color="rgba(255,255,255,0.35)",
            marker_line_width=0.7,
            showscale=True,
        ))

        # Trace de destaque: mantém o mapa inteiro do Brasil e pinta somente
        # o estado filtrado com preenchimento forte e borda grossa.
        if selected_uf:
            selected_name = STATE_NAMES_DISPLAY.get(selected_uf, selected_uf)
            fig.add_trace(go.Choropleth(
                geojson=geojson,
                featureidkey="properties.sigla",
                locations=[selected_uf],
                z=[1],
                colorscale=[[0, "#ffd60a"], [1, "#ffd60a"]],
                customdata=[[selected_uf, selected_name]],
                hovertemplate="<b>%{customdata[1]} (%{customdata[0]})</b><br>Estado selecionado<extra></extra>",
                showscale=False,
                marker_line_color="#ffffff",
                marker_line_width=3.8,
                opacity=0.92,
            ))

        # Esta configuração é o que impede aparecer Argentina, Bolívia,
        # Paraguai, oceano, fronteiras ou qualquer outro país.
        geo = dict(
            visible=False,             # remove o mapa-múndi de fundo do Plotly
            fitbounds="locations",     # enquadra nos polígonos desenhados: Brasil
            projection_type="mercator",
            bgcolor="rgba(13,17,23,1)",
        )

    else:
        # Sem GeoJSON não é possível desenhar corretamente os estados.
        # Em vez de mostrar mapa-múndi ou países vizinhos, exibimos um aviso limpo.
        fig.add_annotation(
            text="Não foi possível carregar o mapa dos estados do Brasil.",
            x=0.5,
            y=0.56,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color="white", size=15),
        )
        fig.add_annotation(
            text="Verifique sua conexão ou baixe o GeoJSON para a pasta do projeto.",
            x=0.5,
            y=0.48,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color="#8b949e", size=12),
        )
        geo = dict(visible=False, bgcolor="rgba(13,17,23,1)")

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        geo=geo,
        height=520,
        font=dict(color="white"),
        dragmode=False,
    )

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Gráficos auxiliares
# ─────────────────────────────────────────────────────────────────────────────
def make_cargo_chart_deputies(df_state: pd.DataFrame):
    deputy_cargos = ["Deputado Estadual", "Deputado Federal", "Deputado Distrital"]
    cargo_df = (
        df_state[df_state["Cargo"].isin(deputy_cargos)]
        .groupby("Cargo")["Nome candidato"].nunique()
        .reset_index(name="Eleitos").sort_values("Eleitos")
    )
    if cargo_df.empty:
        return None
    cargo_df["cor"] = cargo_df["Cargo"].map(CARGO_COLORS).fillna("#888")
    fig = go.Figure(go.Bar(
        x=cargo_df["Eleitos"], y=cargo_df["Cargo"], orientation="h",
        marker_color=cargo_df["cor"].tolist(),
        text=cargo_df["Eleitos"], textposition="outside",
        textfont=dict(color="white", size=14),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=55, t=10, b=0), height=180,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="white", size=13)),
        font=dict(color="white"),
    )
    return fig


def make_party_chart(df_state: pd.DataFrame):
    party_df = (
        df_state.groupby("Partido")["Nome candidato"].nunique()
        .reset_index(name="Eleitos")
        .sort_values("Eleitos", ascending=False).head(10)
    )
    fig = go.Figure(go.Bar(
        x=party_df["Partido"], y=party_df["Eleitos"],
        marker_color="#2a9d8f", text=party_df["Eleitos"], textposition="outside",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0), height=260,
        xaxis=dict(tickfont=dict(color="white")),
        yaxis=dict(showgrid=False, showticklabels=False),
        font=dict(color="white"),
    )
    return fig


def make_zone_chart(df_candidate: pd.DataFrame, cargo: str):
    color = CARGO_COLORS.get(cargo, "#888")
    zone_votes = (
        df_candidate[["Zona", "votos_nominais"]]
        .groupby("Zona", as_index=False)["votos_nominais"].sum()
        .sort_values("votos_nominais", ascending=True)
    )
    fig = go.Figure(go.Bar(
        x=zone_votes["votos_nominais"], y=zone_votes["Zona"].astype(str),
        orientation="h", marker_color=color,
        text=zone_votes["votos_nominais"].apply(format_int), textposition="outside",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=70, t=10, b=20),
        height=max(220, min(len(zone_votes) * 24 + 70, 470)),
        xaxis=dict(showgrid=False, showticklabels=False, color="white"),
        yaxis=dict(tickfont=dict(color="white", size=10), title="Zona"),
        font=dict(color="white"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Componentes de UI
# ─────────────────────────────────────────────────────────────────────────────
def metric_card(label, value, color):
    st.markdown(
        f'<div class="metric-card">'
        f'<div style="font-size:1.65rem;font-weight:800;color:{color};">{value}</div>'
        f'<div class="small-muted">{label}</div></div>',
        unsafe_allow_html=True,
    )


def _photo_img(url, css_class, name, fallback_class, fallback_style=""):
    """Gera HTML de foto com fallback automático via onerror."""
    if url:
        return (
            f'<img class="{css_class}" src="{url}" alt="{name}" '
            f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
            f'<div class="{fallback_class}" style="display:none;{fallback_style}">👤</div>'
        )
    return f'<div class="{fallback_class}" style="{fallback_style}">👤</div>'


def governor_card(df: pd.DataFrame, uf: str):
    """Card em destaque com o governador eleito do estado."""
    gov_df = df[(df["UF"] == uf) & (df["Cargo"] == "Governador")]
    if gov_df.empty:
        return
    gov = (gov_df.drop_duplicates("Nome candidato")
           .sort_values("total_votos", ascending=False).iloc[0])
    name = str(gov["Nome candidato"]).title()
    partido = str(gov.get("Partido", ""))
    total = format_int(gov["total_votos"])
    color = CARGO_COLORS["Governador"]

    with st.spinner(f"Carregando foto de {name}..."):
        photo_url = get_photo(gov["Nome candidato"], "Governador", uf)

    photo_html = _photo_img(
        photo_url,
        f'gov-photo" style="border:3px solid {color};',
        name,
        "gov-nophoto",
        f"border:3px solid {color};",
    )
    # Fix the malformed class from the trick above
    if photo_url:
        photo_html = (
            f'<img class="gov-photo" src="{photo_url}" alt="{name}" '
            f'style="border:3px solid {color};" '
            f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
            f'<div class="gov-nophoto" style="display:none;border:3px solid {color};">👤</div>'
        )
    else:
        photo_html = f'<div class="gov-nophoto" style="border:3px solid {color};">👤</div>'

    st.markdown(
        f'<div class="gov-card" style="border:2px solid {color}44;">'
        f'{photo_html}'
        f'<div class="gov-body">'
        f'<div class="gov-label">Governador Eleito</div>'
        f'<div class="gov-name">{name}</div>'
        f'<span class="badge" style="background:{color};">Governador</span>'
        f'<span class="badge badge-sec">{partido}</span>'
        f'<div class="small-muted" style="margin-top:8px;">🗳 {total} votos totais</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def candidate_card(row, zone: str, uf: str):
    """Card compacto da lista de candidatos com foto."""
    cargo = str(row["Cargo"])
    color = CARGO_COLORS.get(cargo, "#888")
    name = str(row["Nome candidato"]).title()

    photo_url = get_photo(row["Nome candidato"], cargo, uf)
    if photo_url:
        photo_html = (
            f'<img class="ccard-photo" src="{photo_url}" alt="{name}" '
            f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
            f'<div class="ccard-nophoto" style="display:none;">👤</div>'
        )
    else:
        photo_html = '<div class="ccard-nophoto">👤</div>'

    total = format_int(row["total_votos"])
    votos_zona = format_int(row["votos_nominais"])

    st.markdown(
        f'<div class="candidate-card" style="border-color:{color}66;">'
        f'{photo_html}'
        f'<div class="ccard-body">'
        f'<div class="ccard-name">{name}</div>'
        f'<span class="badge" style="background:{color};">{cargo}</span>'
        f'<span class="badge badge-sec">{row["Partido"]}</span>'
        f'<div class="small-muted" style="margin-top:8px;">'
        f'🗳 {total} votos totais &nbsp;|&nbsp; Zona {zone}: {votos_zona}'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )


def show_candidate_details(df: pd.DataFrame, uf: str, candidate_name: str):
    """Flashcard completo com foto, descrição e gráfico por zona."""
    df_cand = df[(df["UF"] == uf) & (df["Nome candidato"] == candidate_name)]
    if df_cand.empty:
        st.warning("Candidato não encontrado nos dados.")
        return

    row = df_cand.iloc[0]
    cargo = str(row.get("Cargo", ""))
    partido = str(row.get("Partido", ""))
    genero = str(row.get("Gênero", row.get("Genero", "")))
    faixa = str(row.get("Faixa etária", row.get("Faixa etaria", "-")))
    ocupacao = str(row.get("Ocupação", row.get("Ocupacao", "-"))).title()
    color = CARGO_COLORS.get(cargo, "#888")
    state_name = STATE_NAMES_DISPLAY.get(uf, uf)
    total = format_int(df_cand["total_votos"].max())
    name_t = str(candidate_name).title()

    with st.spinner(f"Buscando informações sobre {name_t}..."):
        photo_url = get_photo(candidate_name, cargo, uf)
        description = get_description(candidate_name, cargo, uf, partido, genero)

    if photo_url:
        photo_html = (
            f'<img class="detail-photo" src="{photo_url}" alt="{name_t}" '
            f'style="border-color:{color};" '
            f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
            f'<div class="detail-nophoto" style="display:none;border-color:{color};">👤</div>'
        )
    else:
        photo_html = f'<div class="detail-nophoto" style="border-color:{color};">👤</div>'

    wiki_q = urllib.parse.quote(name_t)
    wiki_url = f"https://pt.wikipedia.org/w/index.php?search={wiki_q}"

    st.markdown("---")
    st.markdown(
        f'<div class="detail-card" style="border-color:{color}55;">'
        f'<div class="detail-header">'
        f'{photo_html}'
        f'<div class="detail-info">'
        f'<div class="detail-name">{name_t}</div>'
        f'<span class="badge" style="background:{color};">{cargo}</span>'
        f'<span class="badge badge-sec">{partido}</span>'
        f'<span class="badge badge-sec">{state_name} ({uf})</span>'
        f'<div class="detail-desc">{description}</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

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
    st.plotly_chart(make_zone_chart(df_cand, cargo), use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────────────
# App principal
# ─────────────────────────────────────────────────────────────────────────────
df = load_prepared_data()
state_summary = make_state_summary(df)

st.title("Dashboard Eleitoral Brasil 2022")
st.caption("Eleições Gerais · candidatos eleitos por UF e zona eleitoral")

for k in ("selected_uf", "selected_zone", "selected_candidate"):
    if k not in st.session_state:
        st.session_state[k] = None

ufs = sort_zones(df["UF"].dropna().unique())
uf_options = ["Brasil"] + ufs
current_uf = st.session_state.selected_uf or "Brasil"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")
    sel_label = st.selectbox(
        "Selecione a UF", uf_options,
        index=uf_options.index(current_uf) if current_uf in uf_options else 0,
    )
    new_uf = None if sel_label == "Brasil" else sel_label
    if new_uf != st.session_state.selected_uf:
        st.session_state.selected_uf = new_uf
        st.session_state.selected_zone = None
        st.session_state.selected_candidate = None

    if st.session_state.selected_uf:
        uf_sb = st.session_state.selected_uf
        zones = sort_zones(df[df["UF"] == uf_sb]["Zona"].dropna().unique())
        zone_options = ["Visão geral"] + zones
        cur_zone = st.session_state.selected_zone or "Visão geral"
        sel_zone = st.selectbox(
            "Zona eleitoral", zone_options,
            index=zone_options.index(cur_zone) if cur_zone in zone_options else 0,
        )
        new_zone = None if sel_zone == "Visão geral" else sel_zone
        if new_zone != st.session_state.selected_zone:
            st.session_state.selected_zone = new_zone
            st.session_state.selected_candidate = None

    st.markdown("---")
    st.caption("Use apenas o CSV preparado pelo script — não é necessário subir o arquivo original ao GitHub.")

# ── Layout ────────────────────────────────────────────────────────────────────
left, right = st.columns([1.05, 1.35], gap="large")

with left:
    st.markdown("#### Mapa do Brasil")
    fig_map = make_brazil_map(state_summary, st.session_state.selected_uf)

    try:
        map_event = st.plotly_chart(
            fig_map, use_container_width=True,
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
            on_select="rerun", selection_mode="points", key="mapa_brasil",
        )
        points = (map_event.get("selection", {}).get("points", [])
                  if isinstance(map_event, dict) else [])
        if points:
            loc = str(points[0].get("location", "")).replace("BR-", "").upper()
            if loc in ufs and loc != st.session_state.selected_uf:
                st.session_state.selected_uf = loc
                st.session_state.selected_zone = None
                st.session_state.selected_candidate = None
                st.rerun()
    except TypeError:
        st.plotly_chart(fig_map, use_container_width=True,
                        config={"displayModeBar": False, "scrollZoom": False})

    if st.session_state.selected_uf:
        uf_m = st.session_state.selected_uf
        df_sm = df[df["UF"] == uf_m]
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Eleitos", df_sm["Nome candidato"].nunique(), "#2a9d8f")
        with c2:
            metric_card("Zonas", df_sm["Zona"].nunique(), "#f4a261")
        with c3:
            metric_card("Cargos", df_sm["Cargo"].nunique(), "#e63946")

# ── Painel direito ─────────────────────────────────────────────────────────────
with right:
    uf = st.session_state.selected_uf
    zone = st.session_state.selected_zone

    if not uf:
        st.markdown("### Explore os Eleitos de 2022")
        st.write(
            "Selecione uma UF no menu lateral ou clique em um estado no mapa para "
            "visualizar os candidatos eleitos, zonas eleitorais, cargos, partidos e "
            "detalhes de votação."
        )

    elif not zone:
        df_state = df[df["UF"] == uf]
        state_name = STATE_NAMES_DISPLAY.get(uf, uf)
        st.markdown(f"### {state_name} ({uf})")
        st.caption("Selecione uma zona eleitoral no menu lateral para ver os candidatos.")

        # ── Governador em destaque ────────────────────────────────────────────
        governor_card(df, uf)

        st.markdown("#### Deputados eleitos por cargo")
        fig_dep = make_cargo_chart_deputies(df_state)
        if fig_dep:
            st.plotly_chart(fig_dep, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhum deputado eleito encontrado para este estado.")

        st.markdown("#### Top 10 Partidos")
        st.plotly_chart(make_party_chart(df_state), use_container_width=True, config={"displayModeBar": False})

    else:
        df_zone = df[(df["UF"] == uf) & (df["Zona"] == zone)].copy()
        state_name = STATE_NAMES_DISPLAY.get(uf, uf)
        candidates = (df_zone.drop_duplicates("Nome candidato")
                      .sort_values("total_votos", ascending=False))

        st.markdown(f"### Zona {zone} · {state_name}")
        st.caption(f"{len(candidates)} candidato(s) eleito(s)")

        cand_names = candidates["Nome candidato"].tolist()
        sel_cand = st.selectbox(
            "Ver detalhes do candidato",
            ["Selecione"] + cand_names,
            format_func=lambda x: "Selecione" if x == "Selecione" else str(x).title(),
        )
        if sel_cand != "Selecione":
            st.session_state.selected_candidate = sel_cand

        for _, row in candidates.iterrows():
            candidate_card(row, zone, uf)
            if st.button("Ver detalhes", key=f"btn_{uf}_{zone}_{row['Nome candidato']}"):
                st.session_state.selected_candidate = row["Nome candidato"]

        if st.session_state.selected_candidate:
            show_candidate_details(df, uf, st.session_state.selected_candidate)
