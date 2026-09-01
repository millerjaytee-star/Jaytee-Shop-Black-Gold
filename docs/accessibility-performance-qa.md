# Front-End Release QA

The shared Operator Intelligence design system is responsive at desktop, laptop/tablet and mobile breakpoints. Dense data tables use horizontal overflow rather than clipping; KPI grids collapse from six columns to three, two and one; the authenticated sidebar collapses on smaller screens.

Accessibility contract:
- skip links on major product surfaces;
- visible focus treatment;
- semantic headings and tables;
- labels on forms/selectors;
- live status regions for authenticated loading/toasts;
- no color-only financial-state contract in copy;
- no authenticated application indexing.

Performance contract:
- no public framework bundle;
- shared CSS and small route scripts;
- no third-party fonts or stock imagery required for the product hero;
- authenticated dashboard uses one compact tenant-scoped workspace RPC rather than dozens of browser metric queries;
- assets cache briefly with revalidation, while login/app/config are no-store.
