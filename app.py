"""Throws Analysis — Aspire Academy Dash app (Simi trajectory reports)."""

import dash
from dash import Dash

from aspire_dash import STYLESHEETS, setup_app
from aspire_dash.components import header, sidebar
from aspire_dash.layouts import page_layout

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=STYLESHEETS,
    suppress_callback_exceptions=True,
    title="Throws Analysis",
)
server = app.server  # for Posit Connect / gunicorn

setup_app(app)

nav = [
    {"label": "Trial Report", "href": "/", "icon": "fa-solid fa-bullseye", "section": "Analysis"},
    {"label": "Session Compare", "href": "/compare", "icon": "fa-solid fa-code-compare"},
    {"label": "Athlete Trend", "href": "/trend", "icon": "fa-solid fa-chart-line"},
    {"label": "Upload Data", "href": "/upload", "icon": "fa-solid fa-file-arrow-up", "section": "Data"},
]

app.layout = page_layout(
    sidebar_el=sidebar(
        title="Throws",
        subtitle="Aspire Academy",
        nav_items=nav,
        logo_src=dash.get_relative_path("/assets/aspire-logo.png"),
    ),
    header_el=header(title="Throws Analysis", subtitle="Implement trajectory · Simi Motion"),
    use_pages=True,
)

if __name__ == "__main__":
    app.run(debug=True, port=8060)
