const fs = require("fs");
const path = require("path");
const { getMembership, getUser } = require("./_auth");

const PAGES = { momentum: "momentum.html", momentum2: "momentum2.html", "momentum-stocks": "momentum-stocks.html", "mean-reversion": "mean-reversion.html" };
const MEMBER_NAV = `<nav><div><strong>Extreme Trading Inc.</strong></div><div><a href="members.html">Home</a><a href="subscribe.html">Subscribe</a><a href="about.html">About</a><a href="contact.html">Contact</a><button type="button" onclick="localStorage.removeItem('eti_member_session');location.href='members.html'" style="margin-left:20px;padding:0;border:0;background:none;color:white;font:inherit;cursor:pointer">Sign out</button></div></nav>`;

module.exports = async function handler(req, res) {
  if (req.method !== "GET") return res.status(405).send("Method not allowed");
  try {
    const user = await getUser(req);
    if (!user?.email) return res.status(401).send("Please sign in first.");
    if (!await getMembership(user.email)) return res.status(403).send("An active subscription is required.");
    const filename = PAGES[String(req.query.strategy || "")];
    if (!filename) return res.status(404).send("Strategy not found.");
    const html = fs.readFileSync(path.join(__dirname, "_member-content", filename), "utf8")
      .replace(/<nav>[\s\S]*?<\/nav>/i, MEMBER_NAV);
    res.setHeader("Cache-Control", "private, no-store");
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    return res.status(200).send(html);
  } catch (error) {
    console.error(error);
    return res.status(500).send("Member strategy page is temporarily unavailable.");
  }
};
