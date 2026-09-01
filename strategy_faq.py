"""Shared strategy FAQ content and HTML rendering."""

from html import escape


EXTREME_OS_FAQ = [
    ("What is Extreme OS?", "Extreme OS is an intraday discretionary stock trading system. It is not a rules-based or backtested model; its signals are submitted and tracked go-forward through Collective2."),
    ("When do trades take place?", "There is no fixed intraday schedule. Discretionary entries and exits can occur at unpredictable times throughout the regular trading day."),
    ("How many positions can the system hold, and how are they sized?", "The system can hold as many as 15 positions and has rarely used margin. Its recent positioning has generally been more conservative. This service does not prescribe subscriber-specific position sizes; each subscriber independently decides whether to trade and how much risk to take. More aggressive sizing increases loss and margin risk."),
    ("How is a subscription here different from Collective2?", "A Collective2 subscription provides Collective2's full Extreme OS signal delivery and optional AutoTrade; the Extreme OS content here is a summary. A subscription here does not provide AutoTrade, but it includes access to the other backtested systems. Direct email alerts for members who do not use Collective2 are planned but are not yet an active delivery channel."),
    ("Where should I look first?", "On the member page, check Today's Trades first, then Open Positions. Historical trades provide context but are not current instructions."),
    ("When is the page updated?", "The site refreshes from the latest published Collective2 data. Always check the displayed update time before acting."),
    ("Why can my fill differ?", "Broker timing, spreads, liquidity, order handling, account size, and missed alerts can make personal results differ from the model."),
    ("Are alerts personalized advice?", "No. Alerts report model activity. Members remain responsible for execution, sizing, taxes, and risk decisions."),
]


FAQS = {
    "extreme-os": {
        "public": EXTREME_OS_FAQ,
        "member": EXTREME_OS_FAQ,
    },
    "momentum": {
        "public": [
            ("What is MoMoEtf1?", "MoMoEtf1 is a systematic ETF allocation model. It adjusts monthly across major market exposures using proprietary trend and risk-management signals."),
            ("How often can holdings change?", "The model is designed around a monthly update process. It is not an intraday trading system, and an allocation can remain unchanged for multiple months."),
            ("Are the charts live account results?", "No. They are simulated backtest results and may omit real-world costs, taxes, slippage, and execution differences."),
            ("What is available to members?", "Members receive current model allocation details, model alerts, and subscriber-only updates."),
        ],
        "member": [
            ("What is the difference between current holdings and the latest alert?", "Current holdings are the allocation already in effect. The latest alert is the preliminary next-month allocation and can change until the signal period closes."),
            ("When is a monthly signal executed?", "The page states the intended execution month. Do not treat a signal dated in the current month as already held unless it appears under current holdings."),
            ("Why might the alert not change?", "The same ETFs can continue to rank highest or the risk filter can remain in the same state."),
            ("How should positions be sized?", "The model uses equal weighting across selected ETFs when risk-on. When risk-off, the full model portfolio is allocated to SHY. Personal sizing and risk limits remain the member's responsibility."),
            ("How are monthly entries and exits placed?", "The model assumes market-on-open (MOO) exit and entry orders on the first trading day of each month."),
        ],
    },
    "momentum2": {
        "public": [
            ("What is MoMoEtf2?", "MoMoEtf2 is a tactical ETF allocation model. It adjusts monthly across major market exposures using proprietary market-environment and risk-management signals."),
            ("How often can holdings change?", "The model is designed around a monthly update process. It is not an intraday trading system, and an allocation can remain unchanged for multiple months."),
            ("Are the charts live account results?", "No. They are simulated backtest results and may omit real-world costs, taxes, slippage, and execution differences."),
            ("What is available to members?", "Members receive current model allocation details, model alerts, and subscriber-only updates."),
        ],
        "member": [
            ("What does current allocation mean?", "It is the model holding for the effective month displayed on the page."),
            ("What does next holding mean?", "It is the proposed allocation from the latest preliminary signal. It is intended for the execution month shown and may change before month end."),
            ("What does XLP / IEF mean?", "It means buying XLP with 50% of the model portfolio and IEF with the other 50%."),
            ("How are monthly entries and exits placed?", "The model assumes market-on-open (MOO) exit and entry orders on the first trading day of each month."),
            ("How often is Momentum ETF2 updated?", "It is refreshed on weekdays, but allocations are monthly. The page may not materially change when no new completed data is available."),
            ("Why can my account differ?", "Timing, spreads, fills, fees, taxes, fractional shares, cash drag, and delayed rebalancing can create differences."),
        ],
    },
    "momentum-stocks": {
        "public": [
            ("What is MoMo Stocks?", "MoMo Stocks is a systematic stock allocation model. It adjusts monthly across selected equity opportunities using proprietary trend, quality, and risk-management signals."),
            ("How often can holdings change?", "The model is designed around a monthly update process. It is not an intraday trading system, and an allocation can remain unchanged for multiple months."),
            ("What are the main risks?", "A stock allocation model can experience sharp losses, turnover, price gaps, and liquidity or execution differences."),
            ("What is available to members?", "Members receive current model allocation details, model alerts, and subscriber-only updates."),
        ],
        "member": [
            ("Are the latest alert stocks already held?", "Not necessarily. Current holdings are listed separately. The alert is for the stated future execution date and can change before the signal period closes."),
            ("How is the portfolio weighted?", "When risk-on, the model holds ten selected stocks at 10% of the model portfolio each. When risk-off, 100% of the model portfolio is allocated to the selected defensive stock. Personal sizing remains your responsibility."),
            ("When are entries and exits placed?", "The model assumes market-on-open (MOO) exit and entry orders on the first trading day of each month."),
            ("Why can my results differ?", "Stocks can gap and have different spreads or fills. Taxes, fees, account size, fractional shares, and execution timing also matter."),
        ],
    },
    "mean-reversion": {
        "public": [
            ("What is Mean Reversion?", "It is a systematic equity strategy designed to trade temporary price dislocations and subsequent reversals."),
            ("When are signals executed in the backtest?", "Signals use completed daily bars and simulated entries and exits fill at the next market open."),
            ("How is the model portfolio constructed?", "The model can hold up to five positions. It uses equal target sizing of approximately 20% of strategy equity per position and does not use correlation clustering."),
            ("Why might there be no order on a trading day?", "No position may have met an exit rule and available portfolio slots may already be full. A new data date does not require a new trade."),
            ("What are the main risks?", "Long positions can lose money, and a five-position portfolio can be concentrated. Opening gaps, liquidity, and real fills can differ materially from a backtest."),
        ],
        "member": [
            ("What should I check first?", "Review Latest MOO Orders, then Open Positions. An empty order table means the model currently has no new order to execute."),
            ("What does MOO mean?", "Market-on-open: the model assumes execution at the next regular market open after a completed-bar signal."),
            ("How are positions sized?", "The strategy is fully invested when all five slots are filled. Each new position targets approximately 20% of current strategy equity. Actual weights can differ as prices and total equity change after entry."),
            ("Does the strategy use correlation clusters?", "No. This selected version does not restrict candidates using correlation clusters."),
            ("Why can the results date advance without a new order?", "Open positions are still marked to the latest close even when no entry or exit condition is triggered."),
            ("Can I copy the backtest exactly?", "Not necessarily. Opening prices, slippage, fees, liquidity, account size, and order timing can produce different results."),
        ],
    },
}


FAQ_CSS = """
.faq-wrap{margin:14px 0 0}.faq-wrap>summary{display:inline-flex;align-items:center;gap:8px;cursor:pointer;list-style:none;background:#2563eb;color:#fff;border:1px solid #60a5fa;border-radius:8px;padding:10px 16px;font-weight:700}.faq-wrap>summary::-webkit-details-marker{display:none}.faq-wrap>summary:after{content:'+';font-size:18px}.faq-wrap[open]>summary:after{content:'−'}.faq-content{margin-top:14px;padding:4px 18px;background:#0f172a;border:1px solid #374151;border-radius:10px}.faq-content details{padding:14px 0;border-bottom:1px solid #273449}.faq-content details:last-child{border-bottom:0}.faq-content details summary{cursor:pointer;font-weight:700;color:#e5e7eb}.faq-content details p{color:#cbd5e1;line-height:1.6;margin:10px 0 2px}.faq-note{color:#94a3b8;font-size:13px;margin:14px 0}
"""


def render_faq(strategy, audience):
    items = FAQS[strategy][audience]
    questions = "".join(
        f"<details><summary>{escape(question)}</summary><p>{escape(answer)}</p></details>"
        for question, answer in items
    )
    label = "Member FAQ" if audience == "member" else "Strategy FAQ"
    note = "Member guide for reading alerts and results." if audience == "member" else "Public overview. Current signals and positions are not shown here."
    return (
        f'<details class="faq-wrap"><summary aria-label="Open {label}">{label}</summary>'
        f'<div class="faq-content"><p class="faq-note">{note}</p>{questions}</div></details>'
    )
