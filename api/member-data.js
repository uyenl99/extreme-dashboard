const { getMembership, getUser, required, sendJson } = require("./_auth");

function symbol(item) {
  return item?.C2Symbol?.FullSymbol || item?.C2Symbol?.Underlying || item?.Symbol || "";
}

async function collective2(endpoint, params) {
  const url = new URL(`https://api4-general.collective2.com/Strategies/${endpoint}`);
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
  const response = await fetch(url, {
    headers: { authorization: `Bearer ${required("C2_API_KEY")}` },
  });
  if (!response.ok) throw new Error(`Collective2 ${endpoint} failed`);
  const payload = await response.json();
  return payload.Results || [];
}

module.exports = async function handler(req, res) {
  if (req.method !== "GET") return sendJson(res, 405, { error: "Method not allowed" });
  try {
    const user = await getUser(req);
    if (!user?.email) return sendJson(res, 401, { error: "Please sign in first." });
    if (!await getMembership(user.email)) return sendJson(res, 403, { error: "An active subscription is required." });

    const strategyId = process.env.C2_STRATEGY_ID || "13202557";
    const today = new Date().toISOString().slice(0, 10);
    const [positions, orders, trades] = await Promise.all([
      collective2("GetStrategyOpenPositions", { StrategyIds: strategyId }),
      collective2("GetStrategyHistoricalOrders", { StrategyId: strategyId, StartDate: today, EndDate: today }),
      collective2("GetStrategyHistoricalClosedTrades", { StrategyId: strategyId, CommissionPlan: "0" }),
    ]);

    return sendJson(res, 200, {
      updatedAt: new Date().toISOString(),
      positions: positions.map((item) => ({
        openedAt: item.OpenedDate, symbol: symbol(item), quantity: item.Quantity, averagePrice: item.AvgPx,
      })),
      alerts: orders.map((item) => ({
        time: item.PostedDate || item.TradedDate || item.CreatedDate, symbol: symbol(item),
        action: item.Action || item.OrderType || item.Side, quantity: item.Quantity, status: item.Status,
      })),
      trades: trades.sort((a, b) => new Date(b.CloseDate) - new Date(a.CloseDate)).map((item) => ({
        openedAt: item.OpenDate, closedAt: item.CloseDate, symbol: symbol(item), side: item.OpenSide,
        quantity: item.OpenedQuantity, openPrice: item.AvgOpenFillPrice,
        closePrice: item.AvgCloseFillPrice, profitLoss: item.ProfitLoss,
      })),
    });
  } catch (error) {
    console.error(error);
    return sendJson(res, 500, { error: "Member data is temporarily unavailable." });
  }
};
