import pandas as pd
from pathlib import Path

PUBLIC_DELAY_HOURS = 96
PUBLIC_TRADE_LIMIT = 100

def load_trades(csv_file):
df = pd.read_csv(csv_file)

```
df["Closed Time ET"] = pd.to_datetime(
    df["Closed Time ET"],
    errors="coerce"
)

return df
```

def build_public_table(df):

```
cutoff = (
    pd.Timestamp.now()
    - pd.Timedelta(hours=PUBLIC_DELAY_HOURS)
)

df = df[
    df["Closed Time ET"].notna()
]

df = df[
    df["Closed Time ET"] < cutoff
]

df = df.sort_values(
    "Closed Time ET",
    ascending=False
).head(PUBLIC_TRADE_LIMIT)

cols = [
    "Open Time ET",
    "Symbol",
    "Descrip",
    "Side",
    "Qty Open",
    "Avg Price Open",
    "Closed Time ET",
    "Trade P/L"
]

display_df = df[cols].copy()

display_df.columns = [
    "Open Time",
    "Symbol",
    "Description",
    "Side",
    "Qty",
    "Entry",
    "Close Time",
    "P/L"
]

return (
    display_df.style
    .format({
        "Entry": "{:.2f}",
        "P/L": "{:.2f}"
    })
    .map(
        lambda v:
        "color:#22c55e;font-weight:bold"
        if isinstance(v, (int, float)) and v > 0
        else (
            "color:#ef4444;font-weight:bold"
            if isinstance(v, (int, float)) and v < 0
            else ""
        ),
        subset=["P/L"]
    )
    .hide(axis="index")
    .to_html()
)
```

def build_member_table(df):

```
cols = [
    "Open Time ET",
    "Symbol",
    "Descrip",
    "Side",
    "Qty Open",
    "Avg Price Open",
    "Closed Time ET",
    "Trade P/L"
]

display_df = df[cols].copy()

display_df.columns = [
    "Open Time",
    "Symbol",
    "Description",
    "Side",
    "Qty",
    "Entry",
    "Close Time",
    "P/L"
]

return (
    display_df.tail(250)
    .style
    .format({
        "Entry": "{:.2f}",
        "P/L": "{:.2f}"
    })
    .hide(axis="index")
    .to_html()
)
```

def page_template(title, table_html):

```
return f"""
```

<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8">

<title>{title}</title>

<style>

body {{
    background:#0f172a;
    color:#e5e7eb;
    font-family:Arial,Helvetica,sans-serif;
    margin:0;
}}

nav {{
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:18px 30px;
    background:#111827;
}}

nav a {{
    color:white;
    text-decoration:none;
    margin-left:20px;
}}

.container {{
    width:95%;
    max-width:1400px;
    margin:auto;
    padding:20px;
}}

.card {{
    background:#111827;
    border:1px solid #374151;
    border-radius:10px;
    padding:20px;
}}

table {{
    width:100%;
    border-collapse:collapse;
}}

th {{
    background:#1f2937;
}}

th, td {{
    padding:4px 6px;
    border:1px solid #374151;
    font-size:12px;
}}

h1 {{
    margin-top:0;
}}

</style>

</head>

<body>

<nav>

<div>
<strong>Extreme Trading Inc.</strong>
</div>

<div>
<a href="index.html">Home</a>
<a href="performance.html">Performance</a>
<a href="strategies.html">Strategies</a>
<a href="members.html">Members</a>
<a href="subscribe.html">Subscribe</a>
<a href="contact.html">Contact</a>
</div>

</nav>

<div class="container">

<div class="card">

<h1>{title}</h1>

{table_html}

</div>

</div>

</body>

</html>
"""

def generate_strategy_page(
csv_file,
output_file,
title
):

```
df = load_trades(csv_file)

table_html = build_public_table(df)

html = page_template(
    title,
    table_html
)

Path(output_file).write_text(
    html,
    encoding="utf-8"
)

print(
    f"Generated {output_file}"
)
```

def generate_members_page():

```
os_df = load_trades(
    "data/extreme_os.csv"
)

mom_df = load_trades(
    "data/momentum.csv"
)

html = page_template(
    "Members Dashboard",
    f"""
```

<h2>Extreme OS</h2>

{build_member_table(os_df)}

<hr>

<h2>Momentum</h2>

{build_member_table(mom_df)}
"""
)

```
Path("members.html").write_text(
    html,
    encoding="utf-8"
)

print(
    "Generated members.html"
)
```

generate_strategy_page(
"data/extreme_os.csv",
"extreme-os.html",
"Extreme OS Historical Trades"
)

generate_strategy_page(
"data/momentum.csv",
"momentum.html",
"Momentum Historical Trades"
)

generate_members_page()
