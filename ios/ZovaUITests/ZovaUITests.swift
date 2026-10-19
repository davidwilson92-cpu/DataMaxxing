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
    }
}
