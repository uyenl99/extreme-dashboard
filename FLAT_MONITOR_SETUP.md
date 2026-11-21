# Private remote flat monitor

Prepared for https://www.extremetradinginc.com/flat-monitor.html.
The PC remains the only TradeStation client. It sends results outward over HTTPS;
no router port, inbound PC listener, or broker key is exposed to the internet.

## Activation

1. In Supabase SQL editor run `flat-monitor-setup.sql`. Its final read-only query
   verifies that `uyenl99@yahoo.com` is an existing confirmed account.
2. Set Vercel server environment variables (production only):
   - `FLAT_MONITOR_OWNER_EMAIL`: `uyenl99@yahoo.com`
   - `FLAT_MONITOR_DB_SECRET`: the existing Supabase project secret/server key.
     This is server-only, never a browser/public variable.
   - `FLAT_MONITOR_DEVICE_KEY`: a new random 32+ character secret shared only
     between this endpoint and the PC bridge.
   Existing `SUPABASE_URL` and `SUPABASE_ANON_KEY` are reused for login verification.
3. Deploy this isolated website change using the normal GitHub/Vercel workflow.
4. On the PC run `.venv/Scripts/python.exe remote_relay.py --configure` and enter
   the same device secret. It is encrypted with Windows DPAPI, outside the repo.
5. Start the existing local dashboard, then run
   `.venv/Scripts/python.exe remote_relay.py`. Keep both processes running.
6. Sign in through the site's normal members page and open `/flat-monitor.html`.
   Verify unauthenticated and other-member requests cannot read or control it.
   Verify offline PC / stale data show gray before using remote controls.

The website does not grant access based solely on the page URL or Stripe membership.
The API verifies the Supabase login and confirmed owner email on every request.
The relay table denies direct access to anonymous and authenticated browser clients.
The device can publish state and retrieve commands but does not receive the database
secret or website password. The local CSRF token never leaves the PC.

Remote changes use a latest-command mailbox with unique IDs and a 60-second expiry.
Only start/update watchlist and stop are accepted; no shell commands, file paths,
broker orders or arbitrary URLs can be sent. Results expire after 45 seconds without
a heartbeat, and each ticker's own timestamp is also checked. Remote UI polls every
5 seconds. Local filtering retains V6, Pacific displays and the 08:00 Pacific cutoff.

## Operational limits

PC must be on, awake and online. Both the local monitor and relay must run.
The relay currently starts manually; no startup task has been installed.
Supabase/Vercel quotas apply. Stop the relay to disable remote delivery; revoke
the device secret to revoke that PC. Removing the owner-email setting disables
browser access. Existing website and trading-monitor functionality are unchanged.
