import XCTest

final class ZovaUITests: XCTestCase {
    override func setUp() { continueAfterFailure = false }
    func testNativeProductTabsAndNextMoveContainNoEmbeddedWebScreens() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        XCTAssertTrue(app.buttons["next-move"].waitForExistence(timeout: 12))
        capture(app, "Native Studio — empty")
        XCTAssertEqual(app.webViews.count, 0)
        app.buttons["next-move"].tap()
        XCTAssertTrue(app.staticTexts["AI recommendation"].waitForExistence(timeout: 8))
        capture(app, "Native Next Move — mobile parity")
        app.buttons["Next idea"].tap(); app.buttons["Next idea"].tap(); app.buttons["Next idea"].tap()
        XCTAssertTrue(app.staticTexts["Idea 4"].waitForExistence(timeout: 8))
        app.buttons["your-strategy"].tap()
        XCTAssertTrue(app.textFields["You and your audience"].exists || app.textViews["You and your audience"].exists)
        capture(app, "Native Strategy — two inputs")
        app.buttons["Close Your strategy"].tap()
        for tab in ["Schedule", "Performance", "Account"] {
            app.buttons["tab-" + tab].tap()
            XCTAssertTrue(app.staticTexts[tab].firstMatch.waitForExistence(timeout: 8))
            capture(app, "Native " + tab + " — mobile parity")
            XCTAssertEqual(app.webViews.count, 0)
        }
    }

    func testNativeComposerMovesSentIdeaIntoTranscriptAndKeepsEditableCaption() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        let composer = app.textFields["post-composer"]
        XCTAssertTrue(composer.waitForExistence(timeout: 12))
        composer.tap(); composer.typeText("A simple pottery tip")
        capture(app, "Native Studio — keyboard")
        XCTAssertTrue(app.keyboards.firstMatch.exists, "Background saving must keep the keyboard open")
        XCTAssertFalse(app.alerts.firstMatch.exists, "Typing must autosave without an alert: " + app.debugDescription)
        XCTAssertFalse(app.staticTexts["How can we grow your\nengagement today?"].exists)
        let send = app.buttons["Send idea"]
        let ready = expectation(for: NSPredicate(format: "enabled == true AND hittable == true"), evaluatedWith: send)
        wait(for: [ready], timeout: 10); send.tap()
        XCTAssertTrue(app.textFields["caption-0"].waitForExistence(timeout: 10), app.debugDescription)
        XCTAssertTrue(app.staticTexts["A simple pottery tip"].exists)
        XCTAssertFalse((composer.value as? String ?? "").contains("A simple pottery tip"))
        capture(app, "Native Studio — proposed caption")
        app.buttons["tab-Schedule"].tap(); app.buttons["tab-Studio"].tap()
        XCTAssertTrue(app.textFields["caption-0"].exists)
        XCTAssertEqual(app.webViews.count, 0)
    }
    func testStrategyEditsPersistAndIdeaOpensInNativeStudio() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        XCTAssertTrue(app.buttons["next-move"].waitForExistence(timeout: 12)); app.buttons["next-move"].tap()
        XCTAssertTrue(app.buttons["your-strategy"].waitForExistence(timeout: 8)); app.buttons["your-strategy"].tap()
        let direction = app.textFields["What would you like to post?"]
        XCTAssertTrue(direction.waitForExistence(timeout: 5)); direction.tap(); direction.typeText(" Include studio tours.")
        app.swipeUp()
        let update = app.buttons["Update my strategy ✦"]
        XCTAssertTrue(update.waitForExistence(timeout: 5)); update.tap()
        let save = app.buttons["Save strategy"]
        for _ in 0..<3 { if save.isHittable { break }; app.swipeUp() }
        XCTAssertTrue(save.waitForExistence(timeout: 8)); save.tap()
        XCTAssertTrue(app.staticTexts["Saved to your brand"].waitForExistence(timeout: 8))
        app.swipeDown(); app.swipeDown(); app.buttons["Close Your strategy"].tap()
        app.buttons["next-move"].tap()
        XCTAssertTrue(app.buttons["your-strategy"].waitForExistence(timeout: 8)); app.buttons["your-strategy"].tap()
        XCTAssertTrue((direction.value as? String ?? "").contains("Include studio tours."))
        app.buttons["Close Your strategy"].tap(); app.buttons["next-move"].tap()
        XCTAssertTrue(app.buttons["Draft post"].waitForExistence(timeout: 8)); app.buttons["Draft post"].tap()
        XCTAssertTrue(app.textFields["caption-0"].waitForExistence(timeout: 8))
        XCTAssertEqual(app.webViews.count, 0)
    }
    func testCaptionEditIsRetainedAndFinalReviewCanBeCancelledWithoutSending() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        XCTAssertTrue(app.buttons["next-move"].waitForExistence(timeout: 12)); app.buttons["next-move"].tap()
        XCTAssertTrue(app.buttons["Draft post"].waitForExistence(timeout: 8)); app.buttons["Draft post"].tap()
        let caption = app.textFields["caption-0"]
        XCTAssertTrue(caption.waitForExistence(timeout: 8)); caption.tap(); caption.typeText(" Come join us.")
        XCTAssertTrue(app.buttons["finish-editing"].waitForExistence(timeout: 5)); app.buttons["finish-editing"].tap()
        app.buttons["More caption options"].tap(); app.buttons["Preview"].tap()
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Come join us.")).firstMatch.waitForExistence(timeout: 5))
        XCTAssertEqual(app.webViews.count, 0); app.buttons["Close Preview"].tap()
        let review = app.buttons["review-draft"]
        for _ in 0..<3 { if review.isHittable { break }; app.swipeUp() }
        XCTAssertTrue(review.isHittable, app.debugDescription); review.tap()
        let finalReview = app.buttons["Review final post"]
        XCTAssertTrue(finalReview.waitForExistence(timeout: 8)); finalReview.tap()
        XCTAssertTrue(app.buttons["confirm-publication"].waitForExistence(timeout: 8))
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "Come join us.")).firstMatch.exists)
        capture(app, "Native immutable final review — no publication")
        app.buttons["Close Confirm publish"].tap()
        app.buttons["tab-Schedule"].tap()
        XCTAssertTrue(app.buttons["Saved posts"].waitForExistence(timeout: 8)); app.buttons["Saved posts"].tap()
        XCTAssertTrue(app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "pottery studio")).firstMatch.waitForExistence(timeout: 8))
        app.buttons["tab-Studio"].tap()
        XCTAssertTrue((caption.value as? String ?? "").contains("Come join us."))
        XCTAssertEqual(app.webViews.count, 0)
    }
    func testTikTokRequiresChosenPrivacyAndFreshCommercialConsent() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture", "--fixture-tiktok"]; app.launch()
        XCTAssertTrue(app.buttons["next-move"].waitForExistence(timeout: 12)); app.buttons["next-move"].tap()
        XCTAssertTrue(app.buttons["Draft post"].waitForExistence(timeout: 8)); app.buttons["Draft post"].tap()
        let review = app.buttons["review-draft"]
        XCTAssertTrue(review.waitForExistence(timeout: 8))
        for _ in 0..<3 { if review.isHittable { break }; app.swipeUp() }
        review.tap()
        let privacy = app.buttons["tiktok-privacy"], consent = app.switches["tiktok-consent"], finalReview = app.buttons["Review final post"]
        XCTAssertTrue(privacy.waitForExistence(timeout: 8))
        XCTAssertEqual(consent.value as? String, "0"); XCTAssertFalse(finalReview.isEnabled)
        privacy.tap(); app.buttons["Everyone"].tap()
        consent.tap(); XCTAssertTrue(finalReview.isEnabled)
        app.switches["Promotes a brand, product or service"].tap()
        XCTAssertEqual(consent.value as? String, "0"); XCTAssertFalse(finalReview.isEnabled)
        app.switches["Your brand"].tap()
        for _ in 0..<3 { if consent.isHittable { break }; app.swipeUp() }
        consent.tap(); XCTAssertTrue(finalReview.isEnabled)
        capture(app, "Native TikTok — explicit privacy and commercial consent")
        app.swipeDown(); privacy.tap(); app.buttons["Only me"].tap()
        XCTAssertEqual(consent.value as? String, "0"); XCTAssertFalse(finalReview.isEnabled)
        XCTAssertEqual(app.webViews.count, 0)
    }
    private func capture(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot()); attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    private func reveal(_ element: XCUIElement, in app: XCUIApplication, down: Bool = false) {
        for _ in 0..<12 {
            if element.isHittable { return }
            if down { app.swipeDown() } else { app.swipeUp() }
        }
        XCTAssertTrue(element.isHittable, app.debugDescription)
    }
    private func assertTarget(_ element: XCUIElement, app: XCUIApplication) {
        XCTAssertTrue(element.isHittable, app.debugDescription)
        XCTAssertGreaterThanOrEqual(element.frame.width, 43.5, element.identifier)
        XCTAssertGreaterThanOrEqual(element.frame.height, 43.5, element.identifier)
        XCTAssertGreaterThanOrEqual(element.frame.minX, app.frame.minX - 1)
        XCTAssertLessThanOrEqual(element.frame.maxX, app.frame.maxX + 1)
    }
    private func revealCalendarDay(_ day: XCUIElement, in app: XCUIApplication) {
        // A large-text month grid scrolls on two axes. Keep the target row in
        // view before panning horizontally; vertical swipes alone cannot find it.
        for _ in 0..<12 {
            let frame = day.frame
            if day.isHittable && frame.minX >= 0 && frame.maxX <= app.frame.maxX { return }
            if frame.minY < app.frame.minY + 85 { app.swipeDown(); continue }
            if frame.maxY > app.frame.maxY - 100 { app.swipeUp(); continue }
            let y = (frame.midY - app.frame.minY) / app.frame.height
            let left = app.coordinate(withNormalizedOffset: CGVector(dx: 0.16, dy: y))
            let right = app.coordinate(withNormalizedOffset: CGVector(dx: 0.84, dy: y))
            if frame.maxX > app.frame.maxX { right.press(forDuration: 0.05, thenDragTo: left) }
            else { left.press(forDuration: 0.05, thenDragTo: right) }
        }
        assertTarget(day, app: app)
    }
    func testThreadExplanationAndSecondaryTargets() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        XCTAssertTrue(app.buttons["brand-selector"].waitForExistence(timeout: 12))
        assertTarget(app.buttons["brand-selector"], app: app)
        assertTarget(app.buttons["Your posts"], app: app)
        let x = app.buttons["X"]
        if x.value as? String != "Selected" { x.tap() }
        XCTAssertTrue(app.staticTexts["One update, up to 280 characters."].waitForExistence(timeout: 5))
        app.buttons["x-format"].tap(); app.buttons["Thread · 3 posts"].tap()
        XCTAssertTrue(app.staticTexts["3 connected posts, read in order."].waitForExistence(timeout: 5))
        capture(app, "Native Studio — clear X formats and larger targets")
        app.buttons["tab-Schedule"].tap()
        XCTAssertTrue(app.buttons["Next month"].waitForExistence(timeout: 8))
        for name in ["Previous month", "Next month", "Refresh schedule", "Today"] { assertTarget(app.buttons[name], app: app) }
        assertTarget(app.buttons["calendar-day-1"], app: app)
    }
    func testAccessibilityLargestTextKeepsProductActionsReachable() {
        let app = XCUIApplication()
        // Exercise UIKit's size preference too, including newly presented sheets.
        app.launchArguments = ["--native-fixture", "-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityXXXL"]
        app.launch()
        XCTAssertTrue(app.buttons["next-move"].waitForExistence(timeout: 12))
        assertTarget(app.buttons["Your posts"], app: app)
        for tab in ["Studio", "Schedule", "Performance", "Account"] {
            assertTarget(app.buttons["tab-" + tab], app: app)
            XCTAssertLessThanOrEqual(app.buttons["tab-" + tab].frame.height, 80, "Navigation must leave room for content")
        }
        capture(app, "Native Studio — largest accessibility text")
        let composer = app.textFields["post-composer"]
        XCTAssertTrue(composer.isHittable, "An empty Studio must show where to type, without scrolling past its input: " + app.debugDescription)
        composer.tap(); composer.typeText("A large-text pottery idea")
        XCTAssertFalse(app.buttons["next-move"].exists, "Typing should make room above the keyboard")
        let send = app.buttons["Send idea"]; reveal(send, in: app); assertTarget(send, app: app)
        let ready = expectation(for: NSPredicate(format: "enabled == true"), evaluatedWith: send)
        wait(for: [ready], timeout: 10)
        capture(app, "Native Studio — largest text with keyboard and Send")
        send.tap(); XCTAssertTrue(app.textFields["caption-0"].waitForExistence(timeout: 10))
        app.buttons["next-move"].tap()
        XCTAssertTrue(app.staticTexts["next-move-title"].waitForExistence(timeout: 8))
        XCTAssertGreaterThan(app.staticTexts["next-move-title"].frame.height, 60, "The presented sheet must inherit the large text preference")
        capture(app, "Native Next Move — largest accessibility text")
        reveal(app.buttons["Draft post"], in: app)
        assertTarget(app.buttons["Draft post"], app: app)
        app.swipeDown(); app.swipeDown(); app.buttons["Close ✦ Next move"].tap()
        app.buttons["tab-Schedule"].tap()
        XCTAssertTrue(app.buttons["Next month"].waitForExistence(timeout: 8))
        reveal(app.buttons["Next month"], in: app); assertTarget(app.buttons["Next month"], app: app)
        let day = app.buttons["calendar-day-1"]
        revealCalendarDay(day, in: app); assertTarget(day, app: app); day.tap()
        XCTAssertTrue(app.buttons["Show month"].waitForExistence(timeout: 5))
        capture(app, "Native Schedule — scaled calendar")
        app.buttons["tab-Performance"].tap()
        XCTAssertTrue(app.staticTexts["Performance"].waitForExistence(timeout: 8))
        capture(app, "Native Performance — largest accessibility text")
        app.buttons["tab-Account"].tap()
        XCTAssertTrue(app.buttons["Your details"].waitForExistence(timeout: 8))
        capture(app, "Native Account — largest accessibility text")
        XCTAssertFalse(app.alerts.firstMatch.exists, app.debugDescription)
    }
    func testLandscapeComposerAndAllTabsRemainUsable() {
        let app = XCUIApplication()
        XCUIDevice.shared.orientation = .landscapeLeft
        defer { app.terminate(); XCUIDevice.shared.orientation = .portrait }
        app.launchArguments = ["--native-fixture"]; app.launch()
        let composer = app.textFields["post-composer"]
        XCTAssertTrue(composer.waitForExistence(timeout: 12)); reveal(composer, in: app)
        composer.tap(); composer.typeText("A landscape pottery idea")
        let send = app.buttons["Send idea"]; reveal(send, in: app)
        assertTarget(send, app: app); capture(app, "Native landscape — keyboard and Send")
        send.tap()
        XCTAssertTrue(app.textFields["caption-0"].waitForExistence(timeout: 10))
        for tab in ["Schedule", "Performance", "Account", "Studio"] {
            app.buttons["tab-" + tab].tap()
            switch tab {
            case "Schedule": XCTAssertTrue(app.buttons["calendar-day-1"].waitForExistence(timeout: 8))
            case "Performance": XCTAssertTrue(app.staticTexts["1,240"].waitForExistence(timeout: 8))
            case "Account": XCTAssertTrue(app.buttons["Your details"].waitForExistence(timeout: 8))
            default: XCTAssertTrue(app.textFields["caption-0"].waitForExistence(timeout: 8)); app.swipeDown()
            }
            capture(app, "Native landscape — " + tab)
        }
        XCTAssertTrue(app.textFields["caption-0"].exists)
        XCTAssertFalse(app.alerts.firstMatch.exists, app.debugDescription)
    }
    func testVoiceScanPopulatesFieldsAndSurvivesAccountNavigation() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        XCTAssertTrue(app.buttons["tab-Account"].waitForExistence(timeout: 12)); app.buttons["tab-Account"].tap()
        XCTAssertTrue(app.buttons["Your voice"].waitForExistence(timeout: 8)); app.buttons["Your voice"].tap()
        let scan = app.buttons["Scan recent posts"]; reveal(scan, in: app); scan.tap()
        XCTAssertTrue(app.staticTexts["Voice updated from recent captions."].waitForExistence(timeout: 8))
        XCTAssertEqual(app.textFields["Writing tone"].value as? String, "Warm, curious and conversational")
        app.buttons["tab-Studio"].tap(); app.buttons["tab-Account"].tap()
        XCTAssertEqual(app.textFields["Writing tone"].value as? String, "Warm, curious and conversational")
        reveal(app.textFields["Writing tone"], in: app, down: true)
        capture(app, "Native voice — saved scan fields")
        XCTAssertFalse(app.alerts.firstMatch.exists, app.debugDescription)
    }
    func testScheduledEditStopsDeliveryAndReturnsToSavedListWithoutRestart() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        XCTAssertTrue(app.buttons["tab-Schedule"].waitForExistence(timeout: 12)); app.buttons["tab-Schedule"].tap()
        let manage = app.buttons["Manage schedule →"]
        XCTAssertTrue(manage.waitForExistence(timeout: 8)); reveal(manage, in: app); manage.tap()
        app.buttons["Edit caption / media"].tap()
        app.buttons["Stop deliveries and edit"].tap()
        XCTAssertTrue(app.textFields["caption-0"].waitForExistence(timeout: 8))
        app.buttons["tab-Schedule"].tap(); app.buttons["Saved posts"].tap()
        let other = app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "Autumn class dates")).firstMatch
        XCTAssertTrue(other.waitForExistence(timeout: 8)); reveal(other, in: app); other.tap()
        XCTAssertTrue(app.textFields["caption-0"].waitForExistence(timeout: 8))
        XCTAssertEqual(app.textFields["caption-0"].value as? String, "Autumn classes are open for booking.")
        app.buttons["tab-Schedule"].tap(); app.buttons["Calendar"].tap()
        XCTAssertTrue(app.staticTexts["No posts scheduled this month."].waitForExistence(timeout: 8))
        XCTAssertFalse(app.alerts.firstMatch.exists, app.debugDescription)
    }
    func testDeletionRequiresPasswordAndConfirmationAndKeepsItsReceipt() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        XCTAssertTrue(app.buttons["tab-Account"].waitForExistence(timeout: 12)); app.buttons["tab-Account"].tap()
        let deletion = app.buttons["Delete account"]; reveal(deletion, in: app); deletion.tap()
        XCTAssertTrue(app.secureTextFields["Current password"].waitForExistence(timeout: 8))
        XCTAssertFalse(app.buttons["Delete my account"].isEnabled)
        XCTAssertTrue(app.textFields["Type DELETE to confirm"].exists)
        capture(app, "Native account deletion — explicit protected request")
        // Offline fixture only: this never contacts or deletes a real account.
        app.secureTextFields["Current password"].tap(); app.secureTextFields["Current password"].typeText("Synthetic-fixture-password")
        XCTAssertFalse(app.buttons["Delete my account"].isEnabled)
        app.textFields["Type DELETE to confirm"].tap(); app.textFields["Type DELETE to confirm"].typeText("DELETE")
        let submit = app.buttons["Delete my account"]; reveal(submit, in: app); submit.tap()
        XCTAssertTrue(app.buttons["deletion-receipt"].waitForExistence(timeout: 8), app.debugDescription)
        XCTAssertTrue(app.staticTexts["Your deletion request was received. Account access is closed; data erasure is still pending."].exists)
        XCTAssertFalse(app.secureTextFields["Current password"].exists)
        reveal(app.buttons["deletion-receipt"], in: app)
        assertTarget(app.buttons["deletion-receipt"], app: app)
        capture(app, "Native deletion — receipt available after sign-out")
        XCTAssertFalse(app.alerts.firstMatch.exists, app.debugDescription)
    }
    func testScheduleCanBeReviewedRescheduledAndCancelledExplicitly() {
        let app = XCUIApplication(); app.launchArguments = ["--native-fixture"]; app.launch()
        XCTAssertTrue(app.buttons["tab-Schedule"].waitForExistence(timeout: 12)); app.buttons["tab-Schedule"].tap()
        let manage = app.buttons["Manage schedule →"]
        XCTAssertTrue(manage.waitForExistence(timeout: 8))
        for _ in 0..<3 { if manage.isHittable { break }; app.swipeUp() }
        manage.tap()
        XCTAssertTrue(app.buttons["Save new time"].waitForExistence(timeout: 8))
        capture(app, "Native scheduled delivery — guarded editing")
        app.buttons["Save new time"].tap()
        XCTAssertTrue(manage.waitForExistence(timeout: 8)); manage.tap()
        XCTAssertTrue(app.buttons["Cancel scheduled post"].waitForExistence(timeout: 8)); app.buttons["Cancel scheduled post"].tap()
        XCTAssertTrue(app.buttons["Cancel delivery"].waitForExistence(timeout: 5)); app.buttons["Cancel delivery"].tap()
        XCTAssertTrue(app.staticTexts["No posts scheduled this month."].waitForExistence(timeout: 8))
        XCTAssertFalse(app.alerts.firstMatch.exists, app.debugDescription)
        XCTAssertEqual(app.webViews.count, 0)
    }
    func testFreshInstallHasClearSignInAndReadableBranding() {
        let app = XCUIApplication()
        app.launchArguments = ["--test-fresh-install"]
        app.launch()
        XCTAssertTrue(app.buttons["continue-zova"].waitForExistence(timeout: 12))
        XCTAssertTrue(app.staticTexts["Turn your ideas into captions and a content plan with Zova, your AI social media manager."].exists)
        XCTAssertTrue(app.buttons["Privacy"].exists)
        XCTAssertTrue(app.buttons["Terms"].exists)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Zova iPhone welcome"; screenshot.lifetime = .keepAlways
        add(screenshot)
        XCTAssertFalse(app.otherElements["zova-launch"].exists)
        XCUIDevice.shared.press(.home)
        app.activate()
        XCTAssertTrue(app.buttons["continue-zova"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.otherElements["zova-launch"].exists, "Resuming must not replay the launch sequence")
    }

    func testBrandedLaunchWaitsForDestinationThenRevealsIt() {
        let app = XCUIApplication()
        app.launchArguments = ["--test-launch-screen"]
        app.launch()
        XCTAssertTrue(app.otherElements["zova-launch"].waitForExistence(timeout: 2))
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Zova branded launch portrait"; screenshot.lifetime = .keepAlways
        add(screenshot)
        XCTAssertTrue(app.staticTexts["launch-completed"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.otherElements["zova-launch"].exists)
    }

    func testReducedMotionLaunchStillReachesDestination() {
        let app = XCUIApplication()
        app.launchArguments = ["--test-launch-screen", "--launch-reduce-motion"]
        app.launch()
        XCTAssertTrue(app.otherElements["zova-launch"].waitForExistence(timeout: 2))
        XCTAssertTrue(app.staticTexts["launch-completed"].waitForExistence(timeout: 10))
        XCTAssertFalse(app.otherElements["zova-launch"].exists)
    }

    func testSlowLaunchReleasesCoverWithoutHidingRecovery() {
        let app = XCUIApplication()
        app.launchArguments = ["--test-launch-screen", "--launch-never-ready"]
        XCUIDevice.shared.orientation = .landscapeLeft
        defer { XCUIDevice.shared.orientation = .portrait }
        app.launch()
        XCTAssertTrue(app.otherElements["zova-launch"].waitForExistence(timeout: 2))
        // Full framebuffer avoids XCTest's stale application crop after rotation.
        let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        screenshot.name = "Zova branded launch landscape"; screenshot.lifetime = .keepAlways
        add(screenshot)
        XCTAssertTrue(app.staticTexts["launch-completed"].waitForExistence(timeout: 12))
        XCTAssertFalse(app.otherElements["zova-launch"].exists)
    }
}
