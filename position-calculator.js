(() => {
  const panels = Array.from(document.querySelectorAll("section.panel"));
  const panel = panels.find((item) => ["Latest Alert", "Latest MOO Orders"].includes(item.querySelector("h2")?.textContent.trim()));
  if (!panel || panel.querySelector(".position-calculator")) return;
  const source = panel.querySelector("table");
  if (!source) return;
  const headers = Array.from(source.querySelectorAll("thead th")).map((cell) => cell.textContent.trim());
  let positions = [];
  const holdingLabel = headers.includes("Holdings") ? "Holdings" : headers.includes("Holding") ? "Holding" : "";
  if (source.dataset.modelWeights) {
    // Models such as HAA can combine several defensive slots in one ETF.
    try {
      const weights = JSON.parse(source.dataset.modelWeights);
      const entries = Object.entries(weights);
      const total = entries.reduce((sum, [, weight]) => sum + Number(weight), 0);
      if (!entries.length || Math.abs(total - 1) > 1e-6 || entries.some(([ticker, weight]) => !/^[A-Z0-9.-]+$/.test(ticker) || !Number.isFinite(weight) || weight <= 0)) return;
      positions = entries.map(([ticker, weight]) => ({ ticker, weight }));
    } catch { return; }
  } else if (holdingLabel) {
    const index = headers.indexOf(holdingLabel);
    const cell = source.querySelector(`tbody tr td:nth-child(${index + 1})`);
    const tickers = (cell?.textContent || "").split(",").map((ticker) => ticker.trim()).filter(Boolean);
    positions = tickers.map((ticker) => ({ ticker, weight: 1 / tickers.length }));
  } else if (headers.includes("Action") && headers.includes("Position Value")) {
    const indexes = Object.fromEntries(["Action", "Ticker", "Direction", "Position Value", "MOO Fill Price"].map((label) => [label, headers.indexOf(label)]));
    const entries = Array.from(source.querySelectorAll("tbody tr")).map((row) => {
      const cells = row.querySelectorAll("td");
      return {
        action: cells[indexes.Action]?.textContent.trim() || "",
        ticker: cells[indexes.Ticker]?.textContent.trim() || "",
        direction: cells[indexes.Direction]?.textContent.trim() || "",
        value: Number((cells[indexes["Position Value"]]?.textContent || "").replace(/[^0-9.-]/g, "")),
        price: Number((cells[indexes["MOO Fill Price"]]?.textContent || "").replace(/[^0-9.-]/g, "")),
      };
    }).filter((item) => item.action === "Buy" || item.action === "Sell Short");
    const gross = entries.reduce((sum, item) => sum + Math.abs(item.value), 0);
    positions = entries.map((item) => ({ ...item, weight: gross ? Math.abs(item.value) / gross : 0 }));
  }
  if (!positions.length) return;
  const style = document.createElement("style");
  style.textContent = ".position-calculator-actions{margin-top:16px}.position-calculator-toggle{border:0;border-radius:7px;background:#2563eb;color:#fff;padding:10px 15px;font:inherit;font-weight:700;cursor:pointer}.position-calculator{margin-top:18px;padding-top:18px;border-top:1px solid #374151}.position-calculator label{display:block;margin-bottom:7px;color:#cbd5e1;font-size:13px}.position-calculator input{width:min(100%,320px);border:1px solid #4b5563;border-radius:7px;background:#0f172a;color:#e5e7eb;padding:10px 12px;font:inherit}.position-calculator .trade-price{width:110px;padding:7px 8px;font-size:13px}.position-calculator-error{min-height:20px;margin:7px 0;color:#f87171;font-size:13px}";
  document.head.appendChild(style);
  const root = document.createElement("div");
  const tradeColumns = positions[0].action ? "<th>Action</th><th>Ticker</th><th>Direction</th>" : "<th>Ticker</th>";
  root.innerHTML = `<div class="position-calculator-actions"><button type="button" class="position-calculator-toggle" aria-expanded="false">Calculate Position Size</button></div><div class="position-calculator" hidden><label>Account equity</label><input type="number" min="0.01" step="1000" inputmode="decimal" placeholder="100,000"><p class="position-calculator-error" role="alert"></p><div class="table-wrap"><table><thead><tr>${tradeColumns}<th>Target Weight</th><th>Your Position Size</th><th>Execution Price</th><th>Shares</th></tr></thead><tbody></tbody></table></div><p class="subtle">Enter an expected execution price for each ticker. Share quantities allow two decimal places and do not account for fills, slippage, commissions, or broker requirements.</p></div>`;
  panel.appendChild(root);
  const box = root.querySelector(".position-calculator"), button = root.querySelector("button"), input = root.querySelector("input"), error = root.querySelector(".position-calculator-error"), tbody = root.querySelector("tbody");
  positions.forEach((item) => {
    const row = document.createElement("tr");
    row.dataset.weight = item.weight;
    const price = Number.isFinite(item.price) && item.price > 0 ? item.price : "";
    const sizingCells = `<td>${(item.weight * 100).toFixed(2)}%</td><td class="calculated-size">—</td><td><input class="trade-price" type="number" min="0.01" step="0.01" inputmode="decimal" value="${price}" aria-label="${item.ticker} execution price"></td><td class="calculated-shares">—</td>`;
    row.innerHTML = item.action ? `<td>${item.action}</td><td>${item.ticker}</td><td>${item.direction}</td>${sizingCells}` : `<td>${item.ticker}</td>${sizingCells}`;
    tbody.appendChild(row);
  });
  const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
  function calculate() {
    const equity = Number(input.value), valid = Number.isFinite(equity) && equity > 0;
    error.textContent = valid || !input.value ? "" : "Enter an account equity greater than zero.";
    tbody.querySelectorAll("tr").forEach((row) => {
      const dollars = valid ? equity * Number(row.dataset.weight) : 0;
      const price = Number(row.querySelector(".trade-price").value);
      row.querySelector(".calculated-size").textContent = valid ? money.format(dollars) : "—";
      row.querySelector(".calculated-shares").textContent = valid && Number.isFinite(price) && price > 0 ? (dollars / price).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
    });
  }
  button.addEventListener("click", () => {
    const opening = box.hidden;
    box.hidden = !opening;
    button.setAttribute("aria-expanded", String(opening));
    button.textContent = opening ? "Hide Position Calculator" : "Calculate Position Size";
    if (opening) input.focus();
  });
  input.addEventListener("input", calculate);
  tbody.addEventListener("input", calculate);
})();
