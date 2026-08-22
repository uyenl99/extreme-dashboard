const { getMembership, getUser, sendJson } = require("./_auth");

module.exports = async function handler(req, res) {
  if (req.method !== "GET") return sendJson(res, 405, { error: "Method not allowed" });
  try {
    const user = await getUser(req);
    if (!user?.email) return sendJson(res, 401, { error: "Please sign in first." });
    if (!await getMembership(user.email)) {
      return sendJson(res, 403, { error: "An active subscription is required." });
    }
    return sendJson(res, 200, { active: true });
  } catch (error) {
    console.error(error);
    return sendJson(res, 500, { error: "Member access is temporarily unavailable." });
  }
};
