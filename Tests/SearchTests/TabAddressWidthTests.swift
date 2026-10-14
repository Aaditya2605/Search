import XCTest
@testable import Search

/// The address field a tab grows into while its address is edited
/// (TabBar.swift): as wide as the address, within the tab and 340.
final class TabAddressWidthTests: XCTestCase {
    func testAShortAddressKeepsTheTabsWidth() {
        XCTAssertEqual(TabAddressField.width(for: "x.com", tab: 186, room: 1000), 186)
    }

    func testALinkGetsItsOwnWidth() {
        let width = TabAddressField.width(for: "github.com/gitroomhq/postiz-app", tab: 120, room: 1000)
        XCTAssertGreaterThan(width, 120)
        XCTAssertLessThan(width, 340)
        XCTAssertGreaterThan(TabAddressField.width(for: "github.com/gitroomhq/postiz-app/issues", tab: 120, room: 1000), width)
    }

    func testALongAddressStopsAt340OrTheRoom() {
        let long = String(repeating: "github.com/gitroomhq/", count: 10)
        XCTAssertEqual(TabAddressField.width(for: long, tab: 120, room: 1000), 340)
        XCTAssertEqual(TabAddressField.width(for: long, tab: 120, room: 250), 250)
    }
}
