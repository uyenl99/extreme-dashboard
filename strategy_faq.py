"""Shared strategy FAQ content and HTML rendering."""

from html import escape


FAQS = {
    "extreme-os": {
        "public": [
            ("What is Extreme OS?", "Extreme OS is a rules-based trading strategy whose published history is sourced from Collective2. The public page focuses on published closed trades and historical performance."),
            ("Are the public results the member feed?", "No. The public page shows published historical results. Current orders and positions are reserved for active members."),
            ("What do the performance figures represent?", "They summarize the strategy record shown on the page. They are not a promise of future returns and may differ from an individual account."),
            ("What do members receive?", "Members can view current orders, open positions, alerts, and the complete available trade history."),
        ],
        "member": [
            ("Where should I look first?", "Check Today's Orders first, then Current Open Positions. Historical trades provide context but are not current instructions."),
            ("When is the page updated?", "The site refreshes from the latest published Collective2 data. Always check the displayed update time before acting."),
            ("Why can my fill differ?", "Broker timing, spreads, liquidity, order handling, account size, and missed alerts can make personal results differ from the model."),
            ("Are alerts personalized advice?", "No. Alerts report model activity. Members remain responsible for execution, sizing, taxes, and risk decisions."),
        ],
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
            ("How should positions be sized?", "The model uses equal weighting across selected ETFs. Personal sizing and risk limits remain the member's responsibility."),
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
            ("What does XLP / IEF mean?", "It represents a blended defensive allocation rather than a single ETF holding."),
            ("How often is Momentum ETF2 updated?", "It is refreshed on weekdays, but allocations are monthly. The page may not materially change when no new completed data is available."),
            ("What do the recent allocations show?", "They show completed effective holding months and model returns, newest first. Monthly returns compound rather than simply add."),
            ("Why can my account differ?", "Timing, spreads, fills, fees, taxes, fractional shares, cash drag, and delayed rebalancing can create differences."),
            ("Are the exact model rules disclosed?", "No. The page explains the service at a useful level without publishing proprietary calculations, parameters, or source code."),
        ],
    },
    "momentum-stocks": {
        "public": [
            ("What is Momentum Stocks?", "It is a monthly model that selects ten strong stocks from a point-in-time Russell 1000 universe and can move to defensive assets when its risk filter is active."),
            ("Why use a point-in-time universe?", "It reduces survivorship bias by avoiding a universe made only from today's successful companies."),
            ("What are the main risks?", "A concentrated stock portfolio can experience sharp losses, turnover, gaps, and liquidity or execution differences."),
            ("What is available to members?", "Members see current holdings, the preliminary next-month alert, its execution date, and recent monthly allocations."),
        ],
        "member": [
            ("Are the latest alert stocks already held?", "Not necessarily. Current holdings are listed separately. The alert is for the stated future execution date and can change before the signal period closes."),
            ("How is the portfolio weighted?", "The displayed model uses equal weights across ten selected stocks when risk-on. Personal sizing remains your responsibility."),
            ("What happens in risk-off conditions?", "The model moves away from the stock basket into the defensive allocation shown on the page."),
            ("Why can my results differ?", "Stocks can gap and have different spreads or fills. Taxes, fees, account size, fractional shares, and execution timing also matter."),
        ],
    },
    "mean-reversion": {
        "public": [
            ("What is Mean Reversion?", "It is a systematic long/short equity strategy designed to trade short-term price dislocations and subsequent reversals."),
            ("When are signals executed in the backtest?", "Signals use completed daily bars and simulated entries and exits fill at the next market open."),
            ("Why might there be no order on a trading day?", "No position may have met an exit rule and available portfolio slots may already be full. A new data date does not require a new trade."),
            ("What are the main risks?", "Long and short positions can both lose money. Opening gaps, borrow constraints, liquidity, and real fills can differ materially from a backtest."),
        ],
        "member": [
            ("What should I check first?", "Review Latest MOO Orders, then Open Positions. An empty order table means the model currently has no new order to execute."),
            ("What does MOO mean?", "Market-on-open: the model assumes execution at the next regular market open after a completed-bar signal."),
            ("Why can the results date advance without a new order?", "Open positions are still marked to the latest close even when no entry or exit condition is triggered."),
            ("Can I copy the backtest exactly?", "Not necessarily. Opening prices, slippage, short availability, borrow costs, fees, and order timing can produce different results."),
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
