# Individual member account setup

Each member creates an account with their own email and password. Supabase
handles authentication and password resets. Stripe controls subscription
access, and Collective2 supplies the protected live trading data.

## Supabase

1. Create a Supabase project.
2. In **Authentication > Sign In / Providers > Email**, enable Email and
   Password sign-in, enable email confirmation, and leave anonymous sign-ins
   disabled. The site does not use magic-link or OTP sign-in.
3. In **Authentication > URL Configuration**, set the Site URL to
   `https://YOUR_DOMAIN` and add these Redirect URLs:
   - `https://YOUR_DOMAIN/members.html`
   - `http://localhost:3000/members.html` for local testing only
4. In **Project Settings > API Keys**, copy the project URL and the public
   publishable key (a legacy `anon` key also works with this implementation).
5. Configure a custom SMTP provider before production. Password sign-in does
   not send mail, but account confirmation and password recovery do.

## Stripe

1. Create recurring Starter and Professional prices.
2. Enable the Stripe customer portal.
3. Copy the secret key and both `price_...` IDs.

## Vercel

Add every value from `.env.example` as a Production environment variable and
redeploy. Test with Stripe test-mode keys before switching to live mode.

## Verify access

1. Each person can register with a unique email and password.
2. Password-reset emails return to `/members.html` and allow a new password.
3. An account without an active Stripe subscription cannot load member data.
4. Checkout under the same email unlocks the member dashboard.
5. Cancelling the subscription removes access after Stripe marks it inactive.
6. Public trades remain delayed by 96 hours and current positions are absent.
7. `/data/extreme_os.csv` is unavailable from the Vercel deployment.

If the Git repository is public, tracked CSVs and their history remain readable
through the Git host. Make the repository private or purge that history before
treating the data as confidential.
