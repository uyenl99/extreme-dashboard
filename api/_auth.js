const ACTIVE_SUBSCRIPTION_STATUSES = new Set(["active", "trialing"]);

function required(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing ${name}`);
  return value;
}

async function getUser(req) {
  const authorization = req.headers.authorization || "";
  if (!authorization.startsWith("Bearer ")) return null;
  const response = await fetch(`${required("SUPABASE_URL")}/auth/v1/user`, {
    headers: { apikey: required("SUPABASE_ANON_KEY"), authorization },
  });
  return response.ok ? response.json() : null;
}

async function stripeRequest(path, options = {}) {
  const response = await fetch(`https://api.stripe.com/v1${path}`, {
    ...options,
    headers: {
      authorization: `Bearer ${required("STRIPE_SECRET_KEY")}`,
      "content-type": "application/x-www-form-urlencoded",
      ...(options.headers || {}),
    },
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || "Stripe request failed");
  return payload;
}

async function getMembership(email) {
  const customers = await stripeRequest(`/customers?${new URLSearchParams({ email, limit: "100" })}`);
  for (const customer of customers.data || []) {
    const subscriptions = await stripeRequest(`/subscriptions?${new URLSearchParams({ customer: customer.id, status: "all", limit: "100" })}`);
    const subscription = (subscriptions.data || []).find((item) => ACTIVE_SUBSCRIPTION_STATUSES.has(item.status));
    if (subscription) return { customer, subscription };
  }
  return null;
}

function sendJson(res, status, body) {
  res.setHeader("Cache-Control", "private, no-store");
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  return res.status(status).json(body);
}

module.exports = { getMembership, getUser, required, sendJson, stripeRequest };
