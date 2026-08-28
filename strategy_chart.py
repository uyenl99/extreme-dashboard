import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_equity_drawdown_chart(
    dates,
    strategy_equity,
    spy_equity,
    strategy_name,
    div_id,
    start_date=None,
    rebase=False,
):
    """Render aligned strategy/SPY equity and drawdown panes."""
    chart = pd.DataFrame(
        {
            "date": pd.to_datetime(dates),
            "strategy": pd.to_numeric(strategy_equity, errors="coerce"),
            "spy": pd.to_numeric(spy_equity, errors="coerce"),
        }
    ).dropna(subset=["date", "strategy", "spy"])
    chart = chart.sort_values("date").drop_duplicates("date", keep="last")
    if start_date is not None:
        chart = chart.loc[chart["date"] >= pd.Timestamp(start_date)].copy()
    if chart.empty:
        raise ValueError(f"No aligned strategy/SPY chart data for {strategy_name}")

    if rebase:
        chart["strategy"] = chart["strategy"] / chart["strategy"].iloc[0] * 100_000.0
        chart["spy"] = chart["spy"] / chart["spy"].iloc[0] * 100_000.0

    chart["strategy_drawdown"] = chart["strategy"] / chart["strategy"].cummax() - 1.0
    chart["spy_drawdown"] = chart["spy"] / chart["spy"].cummax() - 1.0

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.68, 0.32],
        subplot_titles=("Equity Growth", "Drawdown"),
    )
    fig.add_trace(
        go.Scatter(
            x=chart["date"],
            y=chart["strategy"],
            mode="lines",
            name=strategy_name,
            line=dict(color="#60a5fa", width=3),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=chart["date"],
            y=chart["spy"],
            mode="lines",
            name="SPY",
            line=dict(color="#94a3b8", width=1.7),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=chart["date"],
            y=chart["strategy_drawdown"],
            mode="lines",
            name=f"{strategy_name} Drawdown",
            line=dict(color="#60a5fa", width=1.8),
            fill="tozeroy",
            fillcolor="rgba(96,165,250,0.18)",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=chart["date"],
            y=chart["spy_drawdown"],
            mode="lines",
            name="SPY Drawdown",
            line=dict(color="#f59e0b", width=1.5),
        ),
        row=2,
        col=1,
    )
    fig.update_layout(
        template="plotly_dark",
        height=720,
        margin=dict(l=60, r=25, t=55, b=45),
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=0),
    )
    fig.update_yaxes(
        title_text="Equity ($)",
        tickprefix="$",
        tickformat=",.0f",
        gridcolor="#273449",
        row=1,
        col=1,
    )
    fig.update_yaxes(
        title_text="Drawdown",
        tickformat=".0%",
        gridcolor="#273449",
        zeroline=True,
        zerolinecolor="#475569",
        row=2,
        col=1,
    )
    fig.update_xaxes(gridcolor="#273449")
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"responsive": True},
        div_id=div_id,
    )
