# Hacktoberfest 2026 event tracker

Static single-page tracker for the Hacktoberfest 2026 schedule: mark each event attended or missed.
Progress is cached in the browser and synced to Supabase when you are signed in.

## Structure

```
hacktoberfest-2026/
├── index.html          # the whole app (HTML, CSS, JS)
├── supabase/
│   └── setup.sql       # run once in Supabase SQL Editor
└── README.md
```

## Setup

1. Create a Supabase project and run `supabase/setup.sql` in the SQL Editor.
2. Open the app. On first visit, enter your Supabase project URL and **publishable key**
   (`sb_publishable_...`) or legacy anon key in the setup screen. The values are saved in
   this browser only; each contributor configures their own project.
3. Supabase > Authentication > URL Configuration: set Site URL and add the deployed URL
   under Redirect URLs.
4. Deploy: Vercel with Framework Preset "Other", no build command, output directory `.`
5. Sign in once with your email, then turn off "Allow new users to sign up" in
   Authentication > Sign In / Providers.

This is a static, buildless page, so the browser cannot read `.env` files. `.env.example`
documents the two settings, but cloud sync is configured in the first-run screen. Never
put a Supabase `sb_secret_` or `service_role` key in the page or browser. If a secret key
was previously exposed, revoke/rotate it in the Supabase dashboard.
