# Stabilis Custom Domain Readiness

Current verified production host: `https://stabilis-ops-group.netlify.app/`.

No branded Stabilis domain is assumed connected by this release. The Netlify subdomain remains the verified production origin until DNS ownership and configuration are completed.

Cutover sequence:
1. Add the Stabilis-owned domain to the existing Netlify `stabilis-ops-group` project.
2. Apply Netlify-provided DNS records at the authoritative DNS provider.
3. Wait for TLS issuance and verify HTTPS.
4. Add the branded origin to Supabase Auth Site URL / allowed redirect URLs for `/login` and `/app`.
5. Re-run login, recovery, invitation, session-refresh, form, protected-route and security-header smoke tests.
6. Only then make the branded domain canonical.

Do not remove the Netlify production origin until the branded domain passes the same controlled-pilot release gate.
