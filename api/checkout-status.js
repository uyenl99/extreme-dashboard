const { sendJson, stripeRequest } = require("./_auth");

const ACTIVE_SUBSCRIPTION_STATUSES = new Set(["active", "trialing"]);

module.exports = async function handler(req, res) {
  if (req.method !== "GET") return sendJson(res, 405, { error: "Method not allowed" });
  try {
    const sessionId = String(req.query?.session_id || "");
    if (!sessionId.startsWith("cs_")) return sendJson(res, 400, { error: "Invalid checkout session." });
    const session = await stripeRequest(`/checkout/sessions/${encodeURIComponent(sessionId)}?expand[]=subscription`);
    const email = session.customer_details?.email || session.customer_email || "";
    const status = session.subscription?.status;
    const paid = session.status === "complete" && ACTIVE_SUBSCRIPTION_STATUSES.has(status);
    if (!paid || !email) return sendJson(res, 403, { error: "An active subscription was not found." });
    return sendJson(res, 200, { email });
  } catch (error) {
    console.error(error);
    return sendJson(res, 400, { error: "Unable to verify this checkout." });
  }
};
