const fs = require("fs");
const path = require("path");
const { getMembership, getUser } = require("./_auth");

const PAGES = { "extreme-os": "extreme-os.html", momentum: "momentum.html", momentum2: "momentum2.html", "momentum-stocks": "momentum-stocks.html", "mean-reversion": "mean-reversion.html" };
const MEMBER_DIRECTORY_URL = "members.html?view=strategies&nav=12";
const NAV_BUTTON_STYLE = "margin-left:20px;padding:0;border:0;background:none;color:white;font:inherit;cursor:pointer";
const MEMBER_NAV = `<nav class="site-nav"><strong class="brand">Extreme Trading Inc.</strong><div class="navlinks"><a href="${MEMBER_DIRECTORY_URL}">Home</a><a href="${MEMBER_DIRECTORY_URL}">Strategies</a><a href="subscribe.html">Subscribe</a><a href="about.html">About</a><a href="contact.html">Contact</a><button id="detail-billing-button" type="button" style="${NAV_BUTTON_STYLE}">Manage billing</button><button id="detail-signout-button" type="button" style="${NAV_BUTTON_STYLE}">Sign out</button></div></nav>`;
const MEMBER_NAV_SCRIPT = `<script>
document.getElementById("detail-billing-button")?.addEventListener("click", async () => {
  let session = null;
  try { session = JSON.parse(localStorage.getItem("eti_member_session")); } catch {}
  if (!session?.access_token) { location.href = "members.html"; return; }
  const response = await fetch("/api/create-portal-session", {
    method: "POST",
    headers: { "content-type": "application/json", authorization: "Bearer " + session.access_token },
    body: "{}"
  });
  const payload = await response.json();
  if (payload.url) location.href = payload.url;
  else alert(payload.error || "Unable to open billing.");
});
document.getElementById("detail-signout-button")?.addEventListener("click", () => {
  localStorage.removeItem("eti_member_session");
  location.href = "members.html";
});
</script>`;

function decorateMemberPage(html) {
  return html
    .replace(/<nav\b[^>]*>[\s\S]*?<\/nav>/i, MEMBER_NAV)
    .replace("</body>", `${MEMBER_NAV_SCRIPT}</body>`);
}

async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).send("Method not allowed");
  try {
    const user = await getUser(req);
    if (!user?.email) return res.status(401).send("Please sign in first.");
    if (!await getMembership(user.email)) return res.status(403).send("An active subscription is required.");
    const filename = PAGES[String(req.query.strategy || "")];
    if (!filename) return res.status(404).send("Strategy not found.");
    const html = decorateMemberPage(
      fs.readFileSync(path.join(__dirname, "_member-content", filename), "utf8")
    );
    res.setHeader("Cache-Control", "private, no-store");
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res.status(200).send(html);
  } catch (error) {
    console.error(error);
    return res.status(500).send("Member strategy page is temporarily unavailable.");
  }
}

module.exports = handler;
module.exports.decorateMemberPage = decorateMemberPage;
