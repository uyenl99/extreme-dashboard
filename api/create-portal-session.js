const { getMembership, getUser, sendJson, stripeRequest } = require("./_auth");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") return sendJson(res, 405, { error: "Method not allowed" });
  try {
    const user = await getUser(req);
    if (!user?.email) return sendJson(res, 401, { error: "Please sign in first." });
    const membership = await getMembership(user.email);
    if (!membership) return sendJson(res, 403, { error: "No active subscription found." });
    const body = new URLSearchParams({ customer: membership.customer.id, return_url: `https://${req.headers.host}/members.html` });
    const session = await stripeRequest("/billing_portal/sessions", { method: "POST", body });
    return sendJson(res, 200, { url: session.url });
  } catch (error) {
    console.error(error);
    return sendJson(res, 500, { error: "Unable to open billing settings." });
  }
};
