import pandas as pd


def yearly_returns_by_year(dates, values):
    """Return fractional calendar-year performance from a daily wealth series."""
    frame = pd.DataFrame({
        "date": pd.to_datetime(dates, errors="coerce"),
        "value": pd.to_numeric(values, errors="coerce"),
    }).dropna().sort_values("date")
    if frame.empty:
        return pd.Series(dtype="float64")

    frame["year"] = frame["date"].dt.year
    year_end = frame.groupby("year")["value"].last()
    returns = year_end.pct_change()
    first_year = int(frame["year"].iloc[0])
    first_values = frame.loc[frame["year"].eq(first_year), "value"]
    returns.loc[first_year] = first_values.iloc[-1] / first_values.iloc[0] - 1
    return returns
