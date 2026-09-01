# Deployment

## Production web
- GitHub: `millerjaytee-star/Jaytee-Shop-Black-Gold`
- Netlify site: `stabilis-ops-group`
- Production URL: `https://stabilis-ops-group.netlify.app`
- Publish directory: repository root (`.`)
- Production branch: `main`

## Supabase
- Dedicated project: `Stabilis Operator Intelligence`
- Project ref: `vpunfmwklwjefvchvmpn`
- Region: `us-east-2`
- API URL: `https://vpunfmwklwjefvchvmpn.supabase.co`
- Browser code uses only the publishable key. Never expose a service-role key.
- Private buckets: `stabilis-raw`, `stabilis-reports`, `stabilis-evidence`.

## Environment separation
Local/dev/preview/production configuration must be explicit. Development must not point at production customer financial data. Until a separate Stabilis development branch/project is justified, use fictional Harbor & Hearth data for non-production testing.

## Netlify routes
- `/` public site
- `/operator-intelligence` fictional demo
- `/operator-intelligence-report` fictional sample report
- `/login` Supabase Auth login/reset surface
- `/app` protected customer shell

## Release sequence
Feature branch -> tests/lint/type checks -> pull request -> Netlify deploy preview -> review -> squash merge -> production deploy -> production smoke test -> Notion release record.
