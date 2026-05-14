import dash
from dash import dcc, html, Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import os

# ── Load data ──────────────────────────────────────────────────────────────
BASE = os.path.dirname(__file__)
zone_cands = pd.read_csv(os.path.join(BASE, "zone_candidates.csv"))
state_summary = pd.read_csv(os.path.join(BASE, "state_summary.csv"))

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

# ── App setup ──────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.FONT_AWESOME],
    title="Dashboard Eleitoral Brasil 2022",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
server = app.server  # for gunicorn

# ── Brazil map (choropleth via ISO codes) ──────────────────────────────────
def make_brazil_map(selected_uf=None):
    df = state_summary.copy()
    df["state_name"] = df["UF"].map(STATE_NAMES)
    df["iso"] = "BR-" + df["UF"]
    df["selected"] = df["UF"] == selected_uf

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
    # Highlight selected state
    if selected_uf:
        sel = df[df["UF"] == selected_uf]
        fig.add_trace(
            go.Choropleth(
                locations=["BR-" + selected_uf],
                locationmode="ISO-3",
                z=[1],
                colorscale=[[0, "rgba(255,215,0,0.6)"], [1, "rgba(255,215,0,0.6)"]],
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


# ── Layout ─────────────────────────────────────────────────────────────────
app.layout = dbc.Container(
    fluid=True,
    className="p-0",
    style={"backgroundColor": "#0d1117", "minHeight": "100vh"},
    children=[
        # Header
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.I(className="fa fa-map-marked-alt me-2", style={"color": "#2a9d8f"}),
                        html.Span("Dashboard Eleitoral Brasil 2022", className="fw-bold fs-4"),
                        html.Span(
                            " · Eleições Gerais",
                            className="text-muted fs-6 ms-2",
                        ),
                    ],
                    className="d-flex align-items-center py-3 px-4",
                    style={"borderBottom": "1px solid #21262d", "backgroundColor": "#161b22"},
                )
            )
        ),

        # Breadcrumb / state header
        dbc.Row(
            dbc.Col(
                html.Div(id="breadcrumb", className="px-4 py-2 text-muted small"),
            )
        ),

        # Main content
        dbc.Row(
            [
                # LEFT: Map / Zones list
                dbc.Col(
                    [
                        # State map
                        html.Div(
                            id="map-panel",
                            children=[
                                html.H6(
                                    "Clique em um estado para explorar",
                                    className="text-muted px-3 pt-3 pb-1 small",
                                ),
                                dcc.Graph(
                                    id="brazil-map",
                                    figure=make_brazil_map(),
                                    config={"displayModeBar": False},
                                    style={"height": "520px"},
                                ),
                            ],
                        ),

                        # Zone selector (shown after state selected)
                        html.Div(id="zone-panel", className="px-3 pb-3"),
                    ],
                    md=5,
                    className="pe-0",
                    style={"borderRight": "1px solid #21262d"},
                ),

                # RIGHT: Candidates panel
                dbc.Col(
                    html.Div(id="candidates-panel", className="p-4"),
                    md=7,
                ),
            ],
            className="mx-0",
            style={"flex": "1"},
        ),

        # Candidate modal
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(id="modal-title"), close_button=True),
                dbc.ModalBody(id="modal-body"),
            ],
            id="candidate-modal",
            size="lg",
            centered=True,
            scrollable=True,
        ),

        # Hidden stores
        dcc.Store(id="selected-uf", data=None),
        dcc.Store(id="selected-zone", data=None),
    ],
)


# ── Callbacks ──────────────────────────────────────────────────────────────

@app.callback(
    Output("selected-uf", "data"),
    Input("brazil-map", "clickData"),
    State("selected-uf", "data"),
    prevent_initial_call=True,
)
def on_map_click(click_data, current_uf):
    if not click_data:
        return no_update
    iso = click_data["points"][0]["location"]  # e.g. "BR-SP"
    uf = iso.replace("BR-", "")
    # Toggle off if same state clicked
    if uf == current_uf:
        return None
    return uf


@app.callback(
    Output("selected-zone", "data"),
    Input("selected-uf", "data"),
    prevent_initial_call=False,
)
def reset_zone_on_state_change(uf):
    return None


@app.callback(
    Output("brazil-map", "figure"),
    Input("selected-uf", "data"),
)
def update_map(uf):
    return make_brazil_map(uf)


@app.callback(
    Output("breadcrumb", "children"),
    Input("selected-uf", "data"),
    Input("selected-zone", "data"),
)
def update_breadcrumb(uf, zone):
    parts = [
        html.Span(
            "Brasil",
            id="bc-brasil",
            style={"cursor": "pointer", "color": "#2a9d8f"},
        )
    ]
    if uf:
        parts += [html.Span(" › "), html.Span(f"{STATE_NAMES.get(uf, uf)} ({uf})")]
    if zone:
        parts += [html.Span(" › "), html.Span(f"Zona {zone}")]
    return parts


@app.callback(
    Output("zone-panel", "children"),
    Input("selected-uf", "data"),
)
def render_zone_panel(uf):
    if not uf:
        return []

    df = zone_cands[zone_cands["UF"] == uf]
    zones = sorted(df["Zona"].unique())
    state_name = STATE_NAMES.get(uf, uf)

    # Stats bar
    n_eleitos = df["Nome candidato"].nunique()
    n_zones = len(zones)
    cargo_counts = df.groupby("Cargo")["Nome candidato"].nunique()

    stats = dbc.Row(
        [
            dbc.Col(
                html.Div(
                    [
                        html.Div(str(n_eleitos), className="fs-4 fw-bold", style={"color": "#2a9d8f"}),
                        html.Div("Eleitos", className="text-muted small"),
                    ],
                    className="text-center p-2 rounded",
                    style={"backgroundColor": "#161b22"},
                ),
                xs=4,
            ),
            dbc.Col(
                html.Div(
                    [
                        html.Div(str(n_zones), className="fs-4 fw-bold", style={"color": "#f4a261"}),
                        html.Div("Zonas", className="text-muted small"),
                    ],
                    className="text-center p-2 rounded",
                    style={"backgroundColor": "#161b22"},
                ),
                xs=4,
            ),
            dbc.Col(
                html.Div(
                    [
                        html.Div(str(len(cargo_counts)), className="fs-4 fw-bold", style={"color": "#e63946"}),
                        html.Div("Cargos", className="text-muted small"),
                    ],
                    className="text-center p-2 rounded",
                    style={"backgroundColor": "#161b22"},
                ),
                xs=4,
            ),
        ],
        className="g-2 mb-3",
    )

    # Zone buttons in a scrollable grid
    btns = []
    for z in zones:
        zone_df = df[df["Zona"] == z]
        n = zone_df["Nome candidato"].nunique()
        btns.append(
            dbc.Button(
                [
                    html.Div(f"Zona {z}", className="fw-bold small"),
                    html.Div(f"{n} eleito{'s' if n != 1 else ''}", className="text-muted", style={"fontSize": "0.7rem"}),
                ],
                id={"type": "zone-btn", "index": z},
                color="secondary",
                outline=True,
                size="sm",
                className="me-1 mb-1 text-start",
                style={"minWidth": "90px"},
            )
        )

    return html.Div(
        [
            html.H6(
                [html.I(className="fa fa-map-pin me-1"), f"{state_name}"],
                className="fw-bold mb-2",
                style={"color": "#f4a261"},
            ),
            stats,
            html.P("Selecione uma zona eleitoral:", className="text-muted small mb-2"),
            html.Div(btns, style={"maxHeight": "200px", "overflowY": "auto"}),
        ]
    )


@app.callback(
    Output("selected-zone", "data"),
    Input({"type": "zone-btn", "index": dash.ALL}, "n_clicks"),
    State({"type": "zone-btn", "index": dash.ALL}, "id"),
    prevent_initial_call=True,
)
def on_zone_click(n_clicks_list, ids):
    ctx = callback_context
    if not ctx.triggered or all(n is None for n in n_clicks_list):
        return no_update
    triggered_id = ctx.triggered[0]["prop_id"]
    import json as _json
    idx = _json.loads(triggered_id.split(".")[0])["index"]
    return idx


@app.callback(
    Output("candidates-panel", "children"),
    Input("selected-uf", "data"),
    Input("selected-zone", "data"),
)
def render_candidates(uf, zone):
    if not uf:
        return render_welcome()

    df = zone_cands[zone_cands["UF"] == uf]

    if not zone:
        return render_state_overview(df, uf)

    df = df[df["Zona"] == zone]
    return render_zone_candidates(df, uf, zone)


def render_welcome():
    return html.Div(
        [
            html.Div(
                [
                    html.I(className="fa fa-vote-yea", style={"fontSize": "4rem", "color": "#2a9d8f", "opacity": "0.5"}),
                    html.H4("Explore os Eleitos de 2022", className="mt-3 text-muted"),
                    html.P(
                        "Clique em qualquer estado no mapa para visualizar os candidatos eleitos, "
                        "zonas eleitorais, cargos e detalhes de cada político.",
                        className="text-muted",
                        style={"maxWidth": "400px"},
                    ),
                ],
                className="text-center py-5",
            )
        ],
        style={"display": "flex", "alignItems": "center", "justifyContent": "center", "height": "100%"},
    )


def render_state_overview(df, uf):
    state_name = STATE_NAMES.get(uf, uf)

    # Cargo distribution chart
    cargo_df = df.groupby("Cargo")["Nome candidato"].nunique().reset_index()
    cargo_df.columns = ["Cargo", "Eleitos"]
    cargo_df["cor"] = cargo_df["Cargo"].map(CARGO_COLORS).fillna("#888")

    fig_bar = go.Figure(
        go.Bar(
            x=cargo_df["Eleitos"],
            y=cargo_df["Cargo"],
            orientation="h",
            marker_color=cargo_df["cor"].tolist(),
            text=cargo_df["Eleitos"],
            textposition="outside",
        )
    )
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=40, t=10, b=0),
        height=200,
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(tickfont=dict(color="white")),
        font=dict(color="white"),
    )

    # Party distribution
    party_df = df.groupby("Partido")["Nome candidato"].nunique().reset_index()
    party_df.columns = ["Partido", "Eleitos"]
    party_df = party_df.sort_values("Eleitos", ascending=False).head(10)

    fig_party = go.Figure(
        go.Bar(
            x=party_df["Partido"],
            y=party_df["Eleitos"],
            marker_color="#2a9d8f",
            text=party_df["Eleitos"],
            textposition="outside",
        )
    )
    fig_party.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=200,
        xaxis=dict(tickfont=dict(color="white")),
        yaxis=dict(showgrid=False, showticklabels=False),
        font=dict(color="white"),
    )

    return html.Div(
        [
            html.H5(
                [
                    html.I(className="fa fa-flag me-2", style={"color": "#f4a261"}),
                    state_name,
                    html.Span(f" ({uf})", className="text-muted fs-6"),
                ],
                className="mb-3",
            ),
            html.P(
                "Selecione uma zona eleitoral no painel à esquerda para ver os candidatos.",
                className="text-muted small",
            ),
            html.H6("Eleitos por Cargo", className="text-muted mt-3 mb-1 small text-uppercase"),
            dcc.Graph(figure=fig_bar, config={"displayModeBar": False}),
            html.H6("Top 10 Partidos", className="text-muted mt-3 mb-1 small text-uppercase"),
            dcc.Graph(figure=fig_party, config={"displayModeBar": False}),
        ]
    )


def render_zone_candidates(df, uf, zone):
    state_name = STATE_NAMES.get(uf, uf)
    candidates = df.drop_duplicates("Nome candidato").sort_values("total_votos", ascending=False)

    cards = []
    for _, row in candidates.iterrows():
        cargo = row["Cargo"]
        color = CARGO_COLORS.get(cargo, "#888")
        name = row["Nome candidato"]
        initials = "".join(w[0] for w in name.split()[:2]).upper()
        votos_zona = int(row["votos_nominais"])
        total = int(row["total_votos"])

        card = dbc.Card(
            dbc.CardBody(
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                initials,
                                style={
                                    "width": "48px",
                                    "height": "48px",
                                    "borderRadius": "50%",
                                    "backgroundColor": color,
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "fontWeight": "bold",
                                    "fontSize": "1.1rem",
                                    "color": "white",
                                    "flexShrink": "0",
                                },
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            [
                                html.Div(
                                    name.title(),
                                    className="fw-bold",
                                    style={"color": "white", "fontSize": "0.9rem"},
                                ),
                                html.Div(
                                    [
                                        dbc.Badge(cargo, style={"backgroundColor": color}, className="me-1 small"),
                                        dbc.Badge(row["Partido"], color="secondary", className="small"),
                                    ],
                                    className="mb-1",
                                ),
                                html.Div(
                                    [
                                        html.Span(
                                            f"🗳 {total:,} votos totais",
                                            className="text-muted small me-2",
                                        ),
                                        html.Span(
                                            f"Zona: {votos_zona:,}",
                                            className="text-muted small",
                                        ),
                                    ]
                                ),
                            ]
                        ),
                        dbc.Col(
                            dbc.Button(
                                [html.I(className="fa fa-user me-1"), "Ver"],
                                id={"type": "candidate-btn", "name": name, "uf": uf},
                                size="sm",
                                color="outline-light",
                                className="border-secondary",
                                style={"fontSize": "0.75rem"},
                            ),
                            width="auto",
                            className="d-flex align-items-center",
                        ),
                    ],
                    align="center",
                    className="g-2",
                )
            ),
            className="mb-2",
            style={"backgroundColor": "#161b22", "border": f"1px solid {color}33"},
        )
        cards.append(card)

    return html.Div(
        [
            html.H5(
                [
                    html.I(className="fa fa-map-marker-alt me-2", style={"color": "#2a9d8f"}),
                    f"Zona {zone} · {state_name}",
                ],
                className="mb-1",
            ),
            html.P(
                f"{len(candidates)} candidato{'s' if len(candidates) != 1 else ''} eleito{'s' if len(candidates) != 1 else ''}",
                className="text-muted small mb-3",
            ),
            html.Div(
                cards,
                style={"maxHeight": "calc(100vh - 200px)", "overflowY": "auto"},
            ),
        ]
    )


# ── Candidate modal ─────────────────────────────────────────────────────────

@app.callback(
    Output("candidate-modal", "is_open"),
    Output("modal-title", "children"),
    Output("modal-body", "children"),
    Input({"type": "candidate-btn", "name": dash.ALL, "uf": dash.ALL}, "n_clicks"),
    State({"type": "candidate-btn", "name": dash.ALL, "uf": dash.ALL}, "id"),
    prevent_initial_call=True,
)
def open_modal(n_clicks_list, ids):
    ctx = callback_context
    if not ctx.triggered or all(n is None for n in n_clicks_list):
        return False, "", ""

    triggered = ctx.triggered[0]["prop_id"]
    import json as _json
    id_part = triggered.split(".")[0]
    info = _json.loads(id_part)
    name = info["name"]
    uf = info["uf"]

    df = zone_cands[(zone_cands["Nome candidato"] == name) & (zone_cands["UF"] == uf)]
    if df.empty:
        return False, "", ""

    row = df.iloc[0]
    total = int(df["total_votos"].iloc[0])
    cargo = row["Cargo"]
    partido = row["Partido"]
    genero = row["Gênero"]
    ocupacao = row["Ocupação"]
    faixa = row["Faixa etária"]
    color = CARGO_COLORS.get(cargo, "#888")
    initials = "".join(w[0] for w in name.split()[:2]).upper()

    # Zone votes breakdown
    zone_votes = df[["Zona", "votos_nominais"]].sort_values("votos_nominais", ascending=False)
    fig_zones = go.Figure(
        go.Bar(
            x=zone_votes["votos_nominais"],
            y=zone_votes["Zona"].astype(str),
            orientation="h",
            marker_color=color,
            text=zone_votes["votos_nominais"].apply(lambda v: f"{v:,}"),
            textposition="outside",
        )
    )
    fig_zones.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=50, t=10, b=20),
        height=max(180, min(len(zone_votes) * 22 + 40, 350)),
        xaxis=dict(showgrid=False, showticklabels=False, color="white"),
        yaxis=dict(tickfont=dict(color="white", size=10), title="Zona"),
        font=dict(color="white"),
    )

    # Wikipedia photo search URL (links to Wikipedia for public figures)
    wiki_name = name.title().replace(" ", "_")
    wiki_url = f"https://pt.wikipedia.org/wiki/{wiki_name}"
    photo_search = f"https://commons.wikimedia.org/w/index.php?search={name.replace(' ', '+')}&title=Special:MediaSearch&go=Go&type=image"

    body = html.Div(
        [
            # Header with avatar
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            initials,
                            style={
                                "width": "80px",
                                "height": "80px",
                                "borderRadius": "50%",
                                "backgroundColor": color,
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                                "fontWeight": "bold",
                                "fontSize": "1.8rem",
                                "color": "white",
                                "margin": "auto",
                            },
                        ),
                        width="auto",
                        className="pe-3",
                    ),
                    dbc.Col(
                        [
                            html.H5(name.title(), className="mb-1"),
                            dbc.Badge(cargo, style={"backgroundColor": color}, className="me-1"),
                            dbc.Badge(partido, color="secondary"),
                            html.Div(
                                html.A(
                                    [html.I(className="fa fa-wikipedia-w me-1"), "Wikipedia"],
                                    href=wiki_url,
                                    target="_blank",
                                    className="text-info small",
                                ),
                                className="mt-2",
                            ),
                            html.Div(
                                html.A(
                                    [html.I(className="fa fa-image me-1"), "Buscar foto"],
                                    href=photo_search,
                                    target="_blank",
                                    className="text-muted small",
                                ),
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            ),

            # Info grid
            dbc.Row(
                [
                    dbc.Col(info_card("Gênero", genero, "fa-venus-mars"), md=6),
                    dbc.Col(info_card("Faixa Etária", faixa, "fa-birthday-cake"), md=6),
                ],
                className="mb-2",
            ),
            dbc.Row(
                [
                    dbc.Col(info_card("Ocupação", ocupacao, "fa-briefcase"), md=6),
                    dbc.Col(info_card("Estado", f"{STATE_NAMES.get(uf, uf)} ({uf})", "fa-map"), md=6),
                ],
                className="mb-3",
            ),

            # Total votes highlight
            html.Div(
                [
                    html.Span("Total de Votos: ", className="text-muted"),
                    html.Span(
                        f"{total:,}",
                        className="fw-bold fs-5",
                        style={"color": color},
                    ),
                ],
                className="mb-3",
            ),

            # Zone breakdown chart
            html.H6("Votos por Zona Eleitoral", className="text-muted small text-uppercase mb-2"),
            dcc.Graph(figure=fig_zones, config={"displayModeBar": False}),
        ]
    )

    return True, name.title(), body


def info_card(label, value, icon):
    return html.Div(
        [
            html.I(className=f"fa {icon} me-1 text-muted"),
            html.Span(label + ": ", className="text-muted small"),
            html.Span(value, className="small fw-bold"),
        ],
        className="p-2 rounded mb-2",
        style={"backgroundColor": "#161b22"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=8050)
