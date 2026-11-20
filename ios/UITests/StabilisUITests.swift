import XCTest

final class StabilisUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["-AppleLanguages", "(en-US)", "-AppleLocale", "en_US"]
        app.launch()
    }

    func testWelcomeKeepsFictionalReviewAndClientSignInSeparate() {
        XCTAssertTrue(control("demo.open").waitForExistence(timeout: 8))
        XCTAssertTrue(control("signin.open").exists)
        capture("01 Welcome and fictional review entry")
        if control("signin.open").isEnabled {
            tap("signin.open")
            XCTAssertTrue(app.textFields["Work email"].waitForExistence(timeout: 4))
            XCTAssertTrue(app.secureTextFields["Password"].exists)
            app.buttons["Close"].tap()
        } else {
            requireText("This build has no client workspace connection.")
        }

        tap("demo.open")
        XCTAssertTrue(control("demo.role").waitForExistence(timeout: 6))
        XCTAssertFalse(control("signin.open").exists)
        requireText("Juniper Café")
    }

    func testFictionalBaselineExplainsThe450DollarVariance() {
        openFreshFictionalReview()

        requireText("$450")
        requireText("30%")
        requireText("$250")
        requireText("$200")
        requireText("Historical variance")
        capture("02 Fictional labor variance")
    }

    func testFictionalActionAndComparisonPersistAfterRelaunch() {
        openFreshFictionalReview()

        tap("review.assign")
        tap("review.saveAssignment")
        XCTAssertFalse(control("review.accept").exists)

        selectDemoRole("General manager")
        let accept = control("review.accept")
        reveal(accept)
        XCTAssertTrue(accept.isHittable)
        capture("03 Fictional manager assignment")
        accept.tap()
        tap("review.evidence")
        let evidence = control("review.evidenceNote")
        reveal(evidence)
        XCTAssertTrue(evidence.isHittable)
        capture("04 Fictional completion evidence")
        evidence.tap()
        evidence.typeText("Reviewed seven closing shifts against schedule.")
        tap("review.submitEvidence")

        selectDemoRole("Owner")
        tap("review.compare")
        let comparable = app.buttons["Comparable"].firstMatch
        if !comparable.exists { tap("review.comparability") }
        reveal(comparable)
        XCTAssertTrue(comparable.isHittable)
        comparable.tap()
        tap("review.saveComparison")
        requireText("$125")
        requireObservedChange()
        capture("05 Fictional following-week results")

        app.terminate()
        app.launch()
        tap("demo.open")
        tap("demo.review")
        requireObservedChange()
    }

    private func openFreshFictionalReview() {
        tap("demo.open")
        tap("demo.reset")
        let confirmation = control("demo.confirmReset")
        if confirmation.waitForExistence(timeout: 2) {
            confirmation.tap()
        } else {
            let sheetButton = app.sheets.buttons["Reset fictional review"].firstMatch
            XCTAssertTrue(sheetButton.waitForExistence(timeout: 3))
            sheetButton.tap()
        }
        tap("demo.review")
    }

    private func requireText(_ text: String, file: StaticString = #filePath, line: UInt = #line) {
        let pattern = NSPredicate(format: "label CONTAINS[c] %@ OR value CONTAINS[c] %@", text, text)
        let element = app.descendants(matching: .any).matching(pattern).firstMatch
        if !element.waitForExistence(timeout: 3) { reveal(element) }
        XCTAssertTrue(element.exists, "Expected to find \(text)", file: file, line: line)
    }

    private func requireObservedChange() {
        let observation = control("review.observedChange")
        reveal(observation)
        XCTAssertTrue(observation.exists)
        XCTAssertEqual(observation.label, "Observed change")
        XCTAssertEqual(observation.value as? String, "$325")
    }

    private func capture(_ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func selectDemoRole(_ role: String) {
        tap("demo.detailRole")
        let option = app.buttons[role].firstMatch
        XCTAssertTrue(option.waitForExistence(timeout: 4))
        option.tap()
    }

    private func control(_ identifier: String) -> XCUIElement {
        app.descendants(matching: .any).matching(identifier: identifier).firstMatch
    }

    private func tap(_ identifier: String, file: StaticString = #filePath, line: UInt = #line) {
        let element = control(identifier)
        reveal(element)
        XCTAssertTrue(element.isHittable, "Cannot tap \(identifier)", file: file, line: line)
        element.tap()
    }

    private func reveal(_ element: XCUIElement) {
        if element.waitForExistence(timeout: 3), element.isHittable { return }
        for _ in 0..<6 {
            app.swipeUp()
            if element.isHittable { return }
        }
        for _ in 0..<6 {
            app.swipeDown()
            if element.isHittable { return }
        }
    }
}
