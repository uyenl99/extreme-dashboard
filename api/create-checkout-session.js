const { sendJson, stripeRequest } = require("./_auth");

module.exports = async function handler(req, res) {
  if (req.method !== "POST") return sendJson(res, 405, { error: "Method not allowed" });
  try {
    let requestBody = req.body || {};
    if (typeof requestBody === "string") {
      try { requestBody = JSON.parse(requestBody); } catch { requestBody = {}; }
    }
    if (requestBody.acceptedTerms !== true) {
      return sendJson(res, 400, { error: "You must accept the membership terms and risk disclosures before checkout." });
    }
    const priceId = process.env.STRIPE_PRICE_ID;
    if (!priceId) return sendJson(res, 503, { error: "The membership plan is not configured." });
    const origin = `https://${req.headers.host}`;
    const body = new URLSearchParams({
      mode: "subscription",
      "line_items[0][price]": priceId, "line_items[0][quantity]": "1",
      success_url: `${origin}/members.html?checkout=success&session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/subscribe.html?checkout=cancelled`,
      allow_promotion_codes: "true",
      "metadata[terms_version]": "2026-08-23",
      "metadata[terms_accepted]": "true",
      "metadata[terms_accepted_at]": new Date().toISOString(),
      "subscription_data[metadata][terms_version]": "2026-08-23",
      "subscription_data[metadata][terms_accepted]": "true",
    });
    const session = await stripeRequest("/checkout/sessions", { method: "POST", body });
    return sendJson(res, 200, { url: session.url });
  } catch (error) {
    console.error(error);
    return sendJson(res, 500, { error: "Unable to start checkout." });
  }
};
