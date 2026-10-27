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
    private func capture(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot()); attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
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
