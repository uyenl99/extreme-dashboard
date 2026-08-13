const { getUser, sendJson, stripeRequest } = require("./_auth");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") return sendJson(res, 405, { error: "Method not allowed" });
  try {
    const user = await getUser(req);
    if (!user?.email) return sendJson(res, 401, { error: "Please sign in first." });
    const priceKey = req.body?.price === "starter" ? "STRIPE_STARTER_PRICE_ID" : "STRIPE_PRO_PRICE_ID";
    const priceId = process.env[priceKey];
    if (!priceId) return sendJson(res, 503, { error: "This plan is not configured." });
    const origin = `https://${req.headers.host}`;
    const body = new URLSearchParams({
      mode: "subscription", customer_email: user.email,
      "line_items[0][price]": priceId, "line_items[0][quantity]": "1",
      success_url: `${origin}/members.html?checkout=success`, cancel_url: `${origin}/subscribe.html?checkout=cancelled`,
      allow_promotion_codes: "true",
    });
    const session = await stripeRequest("/checkout/sessions", { method: "POST", body });
    return sendJson(res, 200, { url: session.url });
  } catch (error) {
    console.error(error);
    return sendJson(res, 500, { error: "Unable to start checkout." });
  }
};
