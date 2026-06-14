import os
import pandas as pd
import resend

CSV_FILE = "data/extreme_os.csv"
ALERT_FILE = "data/alerts_sent.csv"

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
ALERT_EMAIL = os.environ["ALERT_EMAIL"]

resend.api_key = RESEND_API_KEY

def load_sent_alerts():
    if os.path.exists(ALERT_FILE):
        df = pd.read_csv(ALERT_FILE)
    
        if "Trade ID" in df.columns:
            return set(df["Trade ID"].astype(str))
    
    return set()
    

def save_sent_alerts(sent_ids):
    pd.DataFrame(
        {"Trade ID": sorted(sent_ids)}
    ).to_csv(
        ALERT_FILE,
        index=False
    )

def send_entry_alert(row):
    symbol = row["Symbol"]
    side = row["Side"]
    trade_id = str(row["Trade ID"])
    
    entry_price = row["Avg Price Open"]
    
    open_time = row["Open Time ET"]
    
    subject = (
        f"Extreme OS Alert - {symbol}"
    )
    
    html = f"""
    <h2>Extreme OS Entry Alert</h2>
    
    <p><b>Symbol:</b> {symbol}</p>
    
    <p><b>Side:</b> {side}</p>
    
    <p><b>Entry Price:</b> {entry_price}</p>
    
    <p><b>Open Time:</b> {open_time}</p>
    
    <p><b>Trade ID:</b> {trade_id}</p>
    """
    
    resend.Emails.send({
        "from":
            "alerts@extremetradinginc.com",
    
        "to":
            [ALERT_EMAIL],
    
        "subject":
            subject,
    
        "html":
            html
    })
    
    print(
        f"Alert sent for "
        f"{symbol} ({trade_id})"
    )

def main():
    df = pd.read_csv(CSV_FILE)
    
    open_positions = df[
        df["Closed Time ET"].isna()
    ]
    
    sent_ids = load_sent_alerts()
    
    updated_ids = set(sent_ids)
    
    new_alerts = 0
    
    for _, row in open_positions.iterrows():
    
        trade_id = str(
            row["Trade ID"]
        )
    
        if trade_id in sent_ids:
            continue
    
        send_entry_alert(row)
    
        updated_ids.add(
            trade_id
        )
    
        new_alerts += 1
    
    save_sent_alerts(
        updated_ids
    )
    
    print(
        f"Finished. "
        f"{new_alerts} new alerts."
    )

if **name** == "**main**":
main()
