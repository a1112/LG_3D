import QtQuick
import QtQuick.Window
import "../../Base"

Item {
    id: root

    property string adaptive_name: ""
    property int designWidth: 1920
    property int designHeight: 1080
    property int screenWidth: Math.max(1, Screen.desktopAvailableWidth > 0 ? Screen.desktopAvailableWidth : Screen.width)
    property int screenHeight: Math.max(1, Screen.desktopAvailableHeight > 0 ? Screen.desktopAvailableHeight : Screen.height)
    property real minScale: 0.78
    property real maxScale: 1.15
    property real minFontScale: 0.86
    property real maxFontScale: 1.12

    readonly property real widthScale: screenWidth / designWidth
    readonly property real heightScale: screenHeight / designHeight
    readonly property real scale: clamp(Math.min(widthScale, heightScale), minScale, maxScale)
    readonly property real fontScale: clamp(scale, minFontScale, maxFontScale)
    readonly property bool isSmallScreen: screenWidth < 1600 || screenHeight < 900
    readonly property bool isLargeScreen: screenWidth >= 2400 && screenHeight >= 1300

    property int windowMarginBase: 50
    property int mainSpacingBase: 10
    property int headerSpacingBase: 10
    property int headerSideGapBase: 20
    property int headerLargeGapBase: 50
    property int headerTabHeightBase: 35
    property int headerOffsetBase: -5
    property int leftPanelBaseWidth: 450
    property int leftPanelMinimumBaseWidth: 330
    property int leftPanelMaximumBaseWidth: 550
    property int maskToolBaseWidth: 220

    readonly property int windowMargin: scaleMetric(windowMarginBase, 20, 72)
    readonly property int minimumWindowWidth: scaleMetric(1280, 1024, 1600)
    readonly property int minimumWindowHeight: scaleMetric(720, 640, 960)
    readonly property int mainSpacing: scaleMetric(mainSpacingBase, 6, 16)
    readonly property int headerSpacing: scaleMetric(headerSpacingBase, 6, 18)
    readonly property int headerSideGap: scaleMetric(headerSideGapBase, 8, 28)
    readonly property int headerLargeGap: scaleMetric(headerLargeGapBase, 18, 72)
    readonly property int headerTabHeight: scaleMetric(headerTabHeightBase, 30, 48)
    readonly property int headerOffset: Math.round(headerOffsetBase * scale)
    readonly property int leftPanelMinimumWidth: scaleMetric(leftPanelMinimumBaseWidth, 300, 420)
    readonly property int leftPanelMaximumWidth: scaleMetric(leftPanelMaximumBaseWidth, 420, 680)
    readonly property int leftPanelPreferredWidth: scaleMetric(
        leftPanelBaseWidth,
        leftPanelMinimumWidth,
        leftPanelMaximumWidth
    )
    readonly property int mask_tool_width: scaleMetric(maskToolBaseWidth, 170, 300)

    function clamp(value, minValue, maxValue) {
        return Math.max(minValue, Math.min(maxValue, value))
    }

    function s(value) {
        return Math.round(value * scale)
    }

    function ws(value) {
        return Math.round(value * widthScale)
    }

    function hs(value) {
        return Math.round(value * heightScale)
    }

    function fs(value) {
        return Math.round(value * fontScale)
    }

    function scaleMetric(value, minValue, maxValue) {
        return clamp(s(value), minValue, maxValue)
    }

    function fontMetric(value, minValue, maxValue) {
        return clamp(fs(value), minValue, maxValue)
    }

    function boundedWidth(value, minValue, maxValue) {
        var availableWidth = Math.max(1, screenWidth - windowMargin * 2)
        return Math.min(scaleMetric(value, minValue, maxValue), availableWidth)
    }

    function boundedHeight(value, minValue, maxValue) {
        var availableHeight = Math.max(1, screenHeight - windowMargin * 2)
        return Math.min(scaleMetric(value, minValue, maxValue), availableHeight)
    }

    SettingsBase {
        category: "adaptive_" + root.adaptive_name
    }
}
