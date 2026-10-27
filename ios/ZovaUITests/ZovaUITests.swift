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
        app.buttons["Send idea"].tap()
        XCTAssertTrue(app.textFields["caption-0"].waitForExistence(timeout: 10))
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
        let attachment = XCTAttachment(screenshot: app.screenshot()); attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
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
