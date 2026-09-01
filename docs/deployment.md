# Deployment

## GitHub
Canonical repository: `millerjaytee-star/Jaytee-Shop-Black-Gold`. Changes use feature branches and pull requests. Do not force-push `main` and do not mix Concrete Motivation, MarketIQ or other projects.

## Netlify
Project: `stabilis-ops-group`. Production deploys from `main`; publish directory is repository root. Netlify Forms powers the `stabilis-lead` public consultation form. Public environment variables must never contain Supabase service-role or other privileged credentials.

## Backend
FastAPI remains a reference/orchestration service until a secure backend runtime is explicitly selected. The public static Netlify deployment must not pretend that Python files inside the repository are executing server-side.

## Supabase
Use a dedicated Stabilis project. Apply migrations in lexical order. Verify RLS/storage/auth/security advisor results before setting the financial-data release gate to PASSED. Only publish the Supabase URL and publishable key to a browser application; privileged keys remain server-side.
