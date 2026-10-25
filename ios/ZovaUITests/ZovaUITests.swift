import XCTest

final class ZovaUITests: XCTestCase {
    func testFreshInstallHasClearSignInAndReadableBranding() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.buttons["continue-zova"].waitForExistence(timeout: 12))
        XCTAssertTrue(app.staticTexts["Your AI social manager."].exists)
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
