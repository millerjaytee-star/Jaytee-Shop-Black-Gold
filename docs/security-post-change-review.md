# Security Post-Change Review Scope

Release validation must retest: organization A→A, A→B denial, cross-tenant write denial, assigned-location scope, customer denial from analyst workspaces, anonymous denial, private storage, report/forecast/action/verified-value/alert isolation, auth redirects, recovery, invitation/session refresh, service-role absence from browser assets, Supabase security advisors, and production security headers.

A high-severity unresolved security finding blocks controlled-pilot release.
