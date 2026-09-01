# Unified Platform Release Checklist

Before merge:
- deterministic Harbor & Hearth fixtures regenerate;
- financial regression remains `$392,570.56`;
- HHR-07 overtime is supporting evidence only;
- Python tests, compile, lint and type checks pass;
- public/app static contracts pass;
- JavaScript syntax passes;
- Netlify and Vercel previews succeed;
- Supabase security advisor has no unresolved security lints;
- controlled-pilot RLS/adversarial tests pass.

After merge:
- production Netlify deploy is READY;
- `/`, `/operator-intelligence`, `/operator-intelligence-report`, `/login`, `/app`, `/security`, `/privacy`, `/terms` and shared assets return 200;
- production headers include HSTS, CSP, nosniff, frame denial and no-store/noindex for customer auth routes;
- authentication, recovery, refresh, tenant context and logout remain operational;
- Notion master build and knowledge vault record only verified completion.
