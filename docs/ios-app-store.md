# Stabilis for iOS release handoff

Apple requirements checked November 20, 2026. This release candidate is for restaurant group staff with a Stabilis invitation. The separate fictional Juniper Café review lets anyone try the workflow on-device. Use synthetic workspaces for beta testing and App Review. The founder chooses the distribution method and approves release.

## Distribution

| Path | Where it fits |
| --- | --- |
| **Internal TestFlight** | First signed build for the Stabilis team. Apple supports up to 100 eligible App Store Connect users. Use a named internal group and a monitored feedback inbox. [TestFlight](https://developer.apple.com/testflight/) |
| **External TestFlight** | A subsequent invitation-only beta for independent restaurant operators, after founder approval. Use email invitations and isolated synthetic accounts. Apple requires beta information and review of the first external build. [TestFlight](https://developer.apple.com/testflight/) |
| **Unlisted App Store** | Recommended for invited staff across restaurant groups using personal and company iPhones. Apple reviews the final app and separately approves the Unlisted request. Anyone with the link can install it. Stabilis sign-in and organization/location grants control workspace access. [Unlisted distribution](https://developer.apple.com/support/unlisted-app-distribution/) |
| **Custom App through Apple Business** | Use when customers have Apple Business accounts, want managed distribution and can supply their organization IDs. Choose Private when creating the distribution configuration. A change between private and public distribution after approval requires a new app record and review. [Distribution methods](https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/set-distribution-methods/) |
| **Public App Store** | Consider if the founder wants discovery and has verified the support and onboarding path for people who arrive through search. [Distribution methods](https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/set-distribution-methods/) |

For Unlisted, set up public availability in App Store Connect, choose manual release, state the intended Unlisted distribution in the review notes and file Apple's request after the final app is submitted for review. Wait for Unlisted approval and founder authorization before release. TestFlight covers the beta phase. [Unlisted request](https://developer.apple.com/support/unlisted-app-distribution/) · [Manual release](https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/select-an-app-store-version-release-option/)

## Product and policy review

| Apple requirement | Stabilis review evidence and remaining work |
| --- | --- |
| **2.1 Completeness** | Provide a working synthetic account with a seeded location, a released review and an assigned action. Provide a second synthetic role if review acceptance or verification is role-dependent. Keep the isolated backend reachable during review and test each login on a fresh install. The offline walkthrough complements authenticated review. Apple requires prior approval to substitute a complete demo for login access when legal or security obligations prevent providing an account. [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/#app-completeness) · [Complete review](https://developer.apple.com/help/app-review/before-submitting-for-review/complete-review/) |
| **4.2 Minimum functionality** | The review should demonstrate native screens for the variance explanation, action response, evidence entry and results. Exercise offline fictional use, resuming the assigned task, accessible controls and the native export or share flow that actually ships. Show the restaurant-specific decision from the sales, approved schedule and payroll records through a comparable week. Include a short capture if a state transition is difficult to discover. [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/#minimum-functionality) |
| **4.8 Sign-in** | Use Stabilis-issued organization accounts with email and password. The current design uses Supabase as the backend for Stabilis account credentials and relies on the company-account exception. If a social provider is added for the primary account, reevaluate the equivalent privacy-preserving login requirement. [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/#login-services) |
| **5.1.1(v) Account deletion** | Verify that the invitation flow gives access to a pre-provisioned account. If an invite, external link or automatic flow creates an account, let the user initiate deletion from an easy-to-find account screen. If completion occurs on the web, link directly to the deletion flow. Account deactivation, sign-out, and a general support form alone are insufficient where this requirement applies. Verify account removal, session revocation, removal of associated personal data and disclosure of legally retained records. Keep organization-level audit and contract obligations distinct from the individual's account. [Apple account deletion guidance](https://developer.apple.com/support/offering-account-deletion-in-your-app/) |
| **3.1.3(c) Enterprise services** | The app is free to install. Invited staff use an organization workspace provided through the group's Stabilis relationship. The app has no checkout, prices, purchase links or consumer subscriptions. Explain the group-only relationship in the review notes. Review any future digital unlock or consumer plan separately under Apple's purchase rules. [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/#other-purchase-methods) |
| **5.1.1 Privacy and support** | Place the privacy policy and support in app settings and App Store Connect. Confirm actual support contact information, the support form's delivery and replies, and the policy's data handling and retention terms before App Review. Remove account credentials and customer records from all screenshots and notes outside the designated private reviewer fields. [App Review](https://developer.apple.com/app-store/review/) · [Metadata](https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information/) |

## App Store Connect draft

| Field | Proposed entry |
| --- | --- |
| Name | Stabilis Operator Intelligence |
| Subtitle | Weekly labor for managers |
| Seller and copyright | Stabilis Ops Group, LLC. Confirm legal enrollment name. Copyright `2026 Stabilis Ops Group, LLC`. |
| Category and language | Business. English (U.S.). Start with the U.S. storefront if the founder selects it. |
| Keywords | restaurant,labor,payroll,schedule,variance,manager,operations |
| Marketing URL | `https://stabilis-ops-group.netlify.app/` |
| Support URL | `https://stabilis-ops-group.netlify.app/support` after the approved release and contact verification. |
| Privacy Policy URL | `https://stabilis-ops-group.netlify.app/privacy` after the updated policy is deployed and verified. |
| Release option | Manual. |

The full product name uses 30 characters. Keep the trademark symbol in appropriate brand copy. Complete the age rating questionnaire, content rights, pricing/availability and encryption information in Connect against the final signed build. Choose the list of supported accessibility features only after testing them on the corresponding devices. [App information](https://developer.apple.com/help/app-store-connect/reference/app-information/app-information/) · [Accessibility labels](https://developer.apple.com/help/app-store-connect/manage-app-accessibility/overview-of-accessibility-nutrition-labels/)

**Description draft**

When labor misses plan, see how much came from the sales forecast, the approved schedule and paid labor. Stabilis Operator Intelligence helps restaurant owners and managers review the numbers, follow an assigned action and compare the next week.

Invited staff sign in to work with the locations their organization has assigned to them. Try the fictional Juniper Café review to see the workflow before signing in.

**Review notes draft**

Use after verifying it against the submitted build and selecting a distribution path. Enter the review contact and synthetic account access only in App Store Connect's designated review fields.

> The app is distributed to invited staff of restaurant organizations using Stabilis. Operators use it to understand weekly labor variance and act on the finding. The app contains no purchase or subscription offer.
>
> Open the fictional Juniper Café review to see the baseline with $450 over target. It breaks down to $0 from the schedule against target, $250 from sales below forecast and $200 from actual payroll above schedule. The comparison week shows $125 over target. The $325 observed improvement and $0 client-verified impact are distinct measures.
>
> For the authenticated workflow, use the supplied synthetic organization credentials. Open the assigned weekly action, accept it, submit evidence, and view the follow-up. The reviewer account has access to a synthetic location. Support and privacy links appear on the welcome screen and in the workspace.

For an Unlisted request, add that the audience is invited restaurant managers and operators across separate organizations, including staff on personally owned devices. Supply an exact build-specific route through the screens, any second-role test credentials, relevant sample input and the availability window. [App Review information](https://developer.apple.com/help/app-review/before-submitting-for-review/complete-review/)

## Privacy disclosures and screenshots

- Verify App Privacy answers against the archive and actual backend. Likely categories to assess include account contact information and user ID, uploaded evidence or notes under User Content, and any retained product interaction, diagnostic or support data. Include actual collection by integrated providers. Confirm linkage and purpose for each category, distinguishing in-app account data from business operating records and purely on-device fictional activity. Review file types actually accepted by the app. Confirm tracking status with the shipping dependency and telemetry inventory. [App Privacy Details](https://developer.apple.com/app-store/app-privacy-details/)
- Inspect the archived `PrivacyInfo.xcprivacy` and Xcode privacy report. Account for required-reason APIs and applicable third-party SDK manifests and signatures. For example, if the app uses `UserDefaults` solely for its own settings, confirm the matching approved reason against the implementation. Verify use of standard OS HTTPS and any library crypto before answering export compliance or signing off `ITSAppUsesNonExemptEncryption`. [Required reason APIs](https://developer.apple.com/documentation/bundleresources/describing-use-of-required-reason-api) · [SDK requirements](https://developer.apple.com/support/third-party-SDK-requirements/) · [Export compliance](https://developer.apple.com/help/app-store-connect/manage-app-information/overview-of-export-compliance/)
- Capture actual app screens showing the variance breakdown, action with named owner and date, evidence entry and the following-week result. Use the synthetic tenant and fictional device data. Apple currently requires at least one Dynamic Island medium-display iPhone screenshot, such as 1179 × 2556 or 1206 × 2622 portrait, and a 13-inch iPad screenshot if the target supports iPadOS. Capture up to 10 per size as opaque PNG or JPEG. For iPad use 2064 × 2752 or 2048 × 2732 portrait. Confirm the active upload slots when uploading. Include the 1024 × 1024 app icon in Xcode's asset catalog. [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/) · [Xcode app icon](https://developer.apple.com/documentation/xcode/configuring-your-app-icon)

## Archive and TestFlight

1. Confirm the Stabilis organization membership and authorized App Store Connect role. If enrollment is still needed, the Account Holder confirms legal entity identity, authority to bind it, organization website and D‑U‑N‑S number. The developer program has a US$99 annual fee. Enrollment and paid services require separate authorization. [Enrollment](https://developer.apple.com/help/account/membership/program-enrollment/) · [Roles](https://developer.apple.com/help/app-store-connect/manage-your-team/overview-of-accounts-and-roles/)
2. On a Mac with supported Xcode, select the Stabilis team in Signing & Capabilities, confirm availability of the proposed bundle ID `com.stabilisops.operatorintelligence`, and create a matching App Store Connect record with a unique SKU. Use the existing record if the target is already registered, and verify the version and increment the build number. Current Apple minimum is Xcode 26 with iOS 26 SDK or later. Apple lists an iOS 27 SDK minimum starting April 2027. The current project targets iPhone with iOS 17 or later. [Upcoming requirements](https://developer.apple.com/news/upcoming-requirements/) · [Add a new app](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app/)
3. Build for an iOS device and test on a real iPhone. Check fresh install, demo in airplane mode, account sign-in, stale sessions, switching users and locations, one permitted action write, evidence, revoked access, sign-out and the state after reopening. Check VoiceOver, Larger Text, large touch targets, portrait layout and printing or sharing as supported. Verify hosted calls with synthetic accounts against the isolated backend and confirm the beta points to that backend. [Preparing for distribution](https://developer.apple.com/documentation/xcode/preparing-your-app-for-distribution)
4. Select a generic iOS device, use Product → Archive, then validate the archive in Organizer. Use Distribute App → App Store Connect to upload an authorized signed build. Use the internal-only upload option for a build intended exclusively for the Stabilis team, or prepare a distribution-capable archive when external beta or App Review is planned. After processing, complete export compliance, enter the beta test instructions and assign the build to the authorized internal group. [Upload builds](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/) · [Distribute from Xcode](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases)
5. In the beta instructions ask testers to open the demo, inspect the $450 breakdown, accept the assigned action, enter evidence, view the next week and reopen the app to check persistence. Ask them to flag confusing measures, inaccessible controls and failed transitions. Use the monitored feedback email. Get separate approval for external beta invitations, App Review submission or public release. [TestFlight](https://developer.apple.com/testflight/) · [Submit an app](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-app/)

Before verifying link handoff on-device, enable Associated Domains for the signed App ID. Serve `/.well-known/apple-app-site-association` at the authorized host over HTTPS with the actual application identifier prefix and bundle ID, the review path and an HTTP 200 without a redirect. Test a review link from Messages or Notes with the app installed and validate the browser fallback with the app removed. Confirm both destinations still require authorized access to client records. [Associated domains](https://developer.apple.com/documentation/xcode/supporting-associated-domains) · [Universal link diagnostics](https://developer.apple.com/documentation/technotes/tn3155-debugging-universal-links)

## Reproduce the simulator and archive checks

On a Mac, run `xcrun simctl list devices available` and set `STABILIS_SIMULATOR_ID` to an available iPhone simulator's UUID. Run the same project and scheme used in CI from the repository root.

```bash
swift test --package-path ios
stabilis_results=$(mktemp -d)
xcodebuild -project ios/Stabilis.xcodeproj -scheme Stabilis \
  -destination "platform=iOS Simulator,id=$STABILIS_SIMULATOR_ID" \
  -derivedDataPath "$stabilis_results/derived" \
  -resultBundlePath "$stabilis_results/Stabilis.xcresult" \
  -parallel-testing-enabled NO test
xcrun xcresulttool export attachments --path "$stabilis_results/Stabilis.xcresult" \
  --output-path "$stabilis_results/screenshots"
xcodebuild -project ios/Stabilis.xcodeproj -scheme Stabilis -configuration Release \
  -destination 'generic/platform=iOS' -archivePath "$stabilis_results/Stabilis.xcarchive" \
  CODE_SIGNING_ALLOWED=NO archive
```

The UI suite captures the welcome screen, historical variance, GM assignment, evidence entry and comparison result using fictional records. The compact and large iPhone CI jobs retain the screenshots, unsigned simulator builds and result bundles. The compact job also attempts an unsigned device archive. A signed distribution archive and TestFlight upload use the Apple team steps above.

The interactive workspace runs Linux. GitHub Actions provides the macOS simulator and unsigned archive checks. The workspace has no connected App Store Connect integration. GitHub's integration returned HTTP 403 on a read-only signing configuration check. Apple team membership, bundle ID availability, signing and upload require a verified Apple account and Mac or authorized macOS runner. Signed archive, actual screenshots, hosted reviewer sign-in, support routing and a TestFlight build need direct verification before claiming release readiness.
