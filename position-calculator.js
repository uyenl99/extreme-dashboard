(() => {
  const panels = Array.from(document.querySelectorAll("section.panel"));
  const panel = panels.find((item) => ["Latest Alert", "Latest MOO Orders"].includes(item.querySelector("h2")?.textContent.trim()));
  if (!panel || panel.querySelector(".position-calculator")) return;
  const source = panel.querySelector("table");
  if (!source) return;
  const headers = Array.from(source.querySelectorAll("thead th")).map((cell) => cell.textContent.trim());
  let positions = [];
  const holdingLabel = headers.includes("Holdings") ? "Holdings" : headers.includes("Holding") ? "Holding" : "";
  if (holdingLabel) {
    const index = headers.indexOf(holdingLabel);
    const cell = source.querySelector(`tbody tr td:nth-child(${index + 1})`);
    const tickers = (cell?.textContent || "").split(",").map((ticker) => ticker.trim()).filter(Boolean);
    positions = tickers.map((ticker) => ({ ticker, weight: 1 / tickers.length }));
  } else if (headers.includes("Action") && headers.includes("Position Value")) {
    const indexes = Object.fromEntries(["Action", "Ticker", "Direction", "Position Value"].map((label) => [label, headers.indexOf(label)]));
    const entries = Array.from(source.querySelectorAll("tbody tr")).map((row) => {
      const cells = row.querySelectorAll("td");
      return {
        action: cells[indexes.Action]?.textContent.trim() || "",
        ticker: cells[indexes.Ticker]?.textContent.trim() || "",
        direction: cells[indexes.Direction]?.textContent.trim() || "",
        value: Number((cells[indexes["Position Value"]]?.textContent || "").replace(/[^0-9.-]/g, "")),
      };
    }).filter((item) => item.action === "Buy" || item.action === "Sell Short");
    const gross = entries.reduce((sum, item) => sum + Math.abs(item.value), 0);
    positions = entries.map((item) => ({ ...item, weight: gross ? Math.abs(item.value) / gross : 0 }));
  }
  if (!positions.length) return;
  const style = document.createElement("style");
  style.textContent = ".position-calculator-actions{margin-top:16px}.position-calculator-toggle{border:0;border-radius:7px;background:#2563eb;color:#fff;padding:10px 15px;font:inherit;font-weight:700;cursor:pointer}.position-calculator{margin-top:18px;padding-top:18px;border-top:1px solid #374151}.position-calculator label{display:block;margin-bottom:7px;color:#cbd5e1;font-size:13px}.position-calculator input{width:min(100%,320px);border:1px solid #4b5563;border-radius:7px;background:#0f172a;color:#e5e7eb;padding:10px 12px;font:inherit}.position-calculator-error{min-height:20px;margin:7px 0;color:#f87171;font-size:13px}";
  document.head.appendChild(style);
  const root = document.createElement("div");
  const tradeColumns = positions[0].action ? "<th>Action</th><th>Ticker</th><th>Direction</th>" : "<th>Ticker</th>";
  root.innerHTML = `<div class="position-calculator-actions"><button type="button" class="position-calculator-toggle" aria-expanded="false">Calculate Position Size</button></div><div class="position-calculator" hidden><label>Account equity</label><input type="number" min="0.01" step="1000" inputmode="decimal" placeholder="100,000"><p class="position-calculator-error" role="alert"></p><div class="table-wrap"><table><thead><tr>${tradeColumns}<th>Target Weight</th><th>Your Position Size</th></tr></thead><tbody></tbody></table></div><p class="subtle">Dollar targets preserve the model allocation. They do not calculate share quantity or account for fills, slippage, commissions, or broker requirements.</p></div>`;
  panel.appendChild(root);
  const box = root.querySelector(".position-calculator"), button = root.querySelector("button"), input = root.querySelector("input"), error = root.querySelector(".position-calculator-error"), tbody = root.querySelector("tbody");
  positions.forEach((item) => {
    const row = document.createElement("tr");
    row.dataset.weight = item.weight;
    row.innerHTML = item.action ? `<td>${item.action}</td><td>${item.ticker}</td><td>${item.direction}</td><td>${(item.weight * 100).toFixed(2)}%</td><td class="calculated-size">—</td>` : `<td>${item.ticker}</td><td>${(item.weight * 100).toFixed(2)}%</td><td class="calculated-size">—</td>`;
    tbody.appendChild(row);
  });
  const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
  function calculate() {
    const equity = Number(input.value), valid = Number.isFinite(equity) && equity > 0;
    error.textContent = valid || !input.value ? "" : "Enter an account equity greater than zero.";
    tbody.querySelectorAll("tr").forEach((row) => row.querySelector(".calculated-size").textContent = valid ? money.format(equity * Number(row.dataset.weight)) : "—");
  }
  button.addEventListener("click", () => {
    const opening = box.hidden;
    box.hidden = !opening;
    button.setAttribute("aria-expanded", String(opening));
    button.textContent = opening ? "Hide Position Calculator" : "Calculate Position Size";
    if (opening) input.focus();
  });
  input.addEventListener("input", calculate);
})();
