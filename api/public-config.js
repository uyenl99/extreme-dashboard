const { sendJson } = require("./_auth");

module.exports = async function handler(req, res) {
  if (req.method !== "GET") return sendJson(res, 405, { error: "Method not allowed" });
  return sendJson(res, 200, { supabaseUrl: process.env.SUPABASE_URL || "", supabaseAnonKey: process.env.SUPABASE_ANON_KEY || "" });
};
