# Stabilis fit-call and support release rehearsal

Checked November 20, 2026 against draft PR #15 at `79a3ba2` and the published site.

On November 20, Jaytee approved `stabilisopsgroup@gmail.com` for public support and controlled replies. The release branch adds the address on `/support`. The connected Gmail account is a different mailbox. A direct inbox or hosted Netlify notification test still requires verified access and routing.

| Surface | Observed behavior |
| --- | --- |
| PR #15 fit-call form | Hosted home and receipt return HTTP 200. The form posts `stabilis-pilot` to `/thanks`. The receipt identifies Jaytee and a 20-minute fit-call request. [Preview](https://deploy-preview-15--stabilis-ops-group.netlify.app/#diagnostic) · [Receipt](https://deploy-preview-15--stabilis-ops-group.netlify.app/thanks) |
| PR #15 app support | `/support`, `/support-received` and `/privacy` return HTTP 200. The support form uses `stabilis-support` and includes the account deletion topic. [Support](https://deploy-preview-15--stabilis-ops-group.netlify.app/support) · [Deletion requests](https://deploy-preview-15--stabilis-ops-group.netlify.app/support#account-deletion) · [Privacy](https://deploy-preview-15--stabilis-ops-group.netlify.app/privacy) |
| Netlify Forms | The project registers both forms with the expected field names and honeypots. Netlify lists one historical fit-call submission and zero support submissions. The notification settings require dashboard sign-in. [Project Forms](https://app.netlify.com/projects/stabilis-ops-group/forms) |
| Production | The published homepage still posts to `/?submitted=1#diagnostic` and presents the old call schedule. The published `/support` and `/support-received` return HTTP 404. `/privacy` still serves the previous policy. [Published site](https://stabilis-ops-group.netlify.app/) |

## Controlled inbox results

Both forms passed a Chromium rehearsal at phone width with JavaScript disabled. The native forms generated the intended payload and went to the corresponding receipt. The harness intercepted the POST, delivered a notification over SMTP to an in-memory staff inbox, checked its Reply-To, then sent a response to a synthetic operator inbox on the same loopback server. Only `example.test` test addresses were used. The support case asked to delete a fictional invited account and the reply explained identity verification. Netlify submissions, hosted notification delivery, account deletion and customer communication were outside the local rehearsal.

Run the rehearsal from the repository root with Python 3.11 or later:

```sh
python3 -m venv /tmp/stabilis-forms-rehearsal
/tmp/stabilis-forms-rehearsal/bin/python -m pip install './operator-intelligence[test]' aiosmtpd==1.4.6
/tmp/stabilis-forms-rehearsal/bin/python -m playwright install chromium
/tmp/stabilis-forms-rehearsal/bin/python operator-intelligence/scripts/rehearse_public_forms.py
```

For an existing Chromium installation, set `STABILIS_CHROMIUM_PATH` to its executable. The script allocates its own loopback HTTP and SMTP ports and discards the inbox contents on exit.

## Hosted delivery and support readiness

1. Verify the approved address appears and opens as a mail link on the hosted `/support` page. App Store Connect requires the Support URL to provide actual contact information. Confirm the staff coverage for the approved inbox. [Apple metadata reference](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/)
2. Verify Netlify notification destinations for both forms in the signed-in project dashboard. For a hosted rehearsal, use an authorized isolated project or another proved synthetic-only route. Review all email recipients, webhooks and integrations before posting. The existing PR preview uses the same project and form registrations as production. [Netlify form notifications](https://docs.netlify.com/manage/forms/notifications/)
3. Once the rehearsal delivery is verified to target only the approved inbox, submit one labeled inquiry and one labeled support request from a controlled test address. Check the form receipt, the resulting Netlify entry, notification delivery and the reply received at the controlled address. Record the test timestamps and message or submission references in the private release log. No test in this run reached hosted notifications.

## Account deletion handling

The iPhone and web sign-in screens are for pre-provisioned, invited work accounts. Confirm the actual invitation mode on hosted staging before App Review. If Stabilis introduces account creation within the app or through a linked flow, implement an account deletion initiation path that meets Apple's requirements. The current support page accepts a deletion request, with identity verification and confirmation before processing. [Apple account deletion guidance](https://developer.apple.com/support/offering-account-deletion-in-your-app/)

An authorized support operator should verify the requester through the work address already associated with the account, confirm the scope, and log the request in the private support queue. An authorized account administrator should verify revocation of sessions and access grants, removal of the account and associated personal data, and the records retained under legal or pilot obligations. Keep shared financial evidence and organizational audit records subject to the pilot agreement. Communicate the result and any retention to the requester. The website receipt confirms that a request was received. Completion requires a handled request and a verified backend.
