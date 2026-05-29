import QtQuick
import QtQuick.Window
import QtQuick.Controls.Material
import "../Base"
import "../Style/Adaptive"

Item {
    id: root

    // ========== 主题预设 ==========
    property string themeName: "dark"  // 当前主题名称
    property string displayStyleName: "standard"
    readonly property var themes: ({
        "dark": {
            name: "黑色主题",
            isDark: true,
            accentColor: Material.Cyan,
            cardBorderColor: Material.BlueGrey,
            titleColor: Material.Cyan,
            backgroundColor: "#090F14",
            gridLineColor: "#32475A",
            textColor: "#F4FAFF",
            labelColor: "#D8E7F2",
            itemBackColor: "#17222C",
            panelColor: "#111B24",
            panelElevatedColor: "#1A2834",
            panelAlternateColor: "#20313E",
            headerColor: "#0E1821",
            headerBorderColor: "#3A5368",
            hoverColor: "#26394A",
            selectionColor: "#2F6F95"
        },
        "light": {
            name: "白色主题",
            isDark: false,
            accentColor: Material.Blue,
            cardBorderColor: Material.Blue,
            titleColor: Material.Blue,
            backgroundColor: "#E0E0E0",
            gridLineColor: "#22000000",
            textColor: "#000000",
            itemBackColor: "#E2E2E2",
            panelColor: "#F4F6F8",
            panelElevatedColor: "#FFFFFF",
            panelAlternateColor: "#E8EDF2",
            headerColor: "#E9EEF3",
            headerBorderColor: "#B7C2CD",
            hoverColor: "#DCE7F1",
            selectionColor: "#90CAF9"
        },
        "blue": {
            name: "蓝色主题",
            isDark: true,
            accentColor: Material.Blue,
            cardBorderColor: Material.Blue,
            titleColor: Material.LightBlue,
            backgroundColor: "#071A2B",
            gridLineColor: "#2E5574",
            textColor: "#F2F8FF",
            labelColor: "#D5E8F7",
            itemBackColor: "#12304A",
            panelColor: "#0C2338",
            panelElevatedColor: "#143453",
            panelAlternateColor: "#1A4164",
            headerColor: "#082034",
            headerBorderColor: "#356383",
            hoverColor: "#1E496D",
            selectionColor: "#2C78B2"
        }
    })

    readonly property var displayStyles: ({
        "standard": {
            name: "标准",
            topHeight: 45,
            windowButtonWidth: 46,
            headerButtonGap: 4,
            controlRadius: 3,
            titleSize: 22
        },
        "compact": {
            name: "紧凑",
            topHeight: 40,
            windowButtonWidth: 42,
            headerButtonGap: 2,
            controlRadius: 2,
            titleSize: 20
        },
        "comfortable": {
            name: "大屏",
            topHeight: 52,
            windowButtonWidth: 54,
            headerButtonGap: 6,
            controlRadius: 4,
            titleSize: 24
        }
    })

    // ========== 应用主题 ==========
    function applyTheme(themeKey) {
        if (!themes[themeKey]) {
            console.warn("Theme not found:", themeKey)
            return
        }
        var t = themes[themeKey]
        themeName = themeKey
        isDark = t.isDark
        accentColor = Material.color(t.accentColor)
        cardBorderColor = Material.color(t.cardBorderColor)
        titleColor = Material.color(t.titleColor)
        appBackgroundColor = t.backgroundColor || (isDark ? "#0B1117" : "#E0E0E0")
        panelBackgroundColor = t.panelColor || t.itemBackColor || (isDark ? "#111A23" : "#F4F6F8")
        panelElevatedColor = t.panelElevatedColor || t.itemBackColor || (isDark ? "#172330" : "#FFFFFF")
        panelAlternateColor = t.panelAlternateColor || t.itemBackColor || (isDark ? "#1C2A36" : "#E8EDF2")
        headerBackgroundColor = t.headerColor || t.backgroundColor || (isDark ? "#0F1A24" : "#E9EEF3")
        headerBorderColor = t.headerBorderColor || t.gridLineColor || (isDark ? "#2C4357" : "#B7C2CD")
        buttonHoverColor = t.hoverColor || t.itemBackColor || (isDark ? "#233447" : "#DCE7F1")
        selectionColor = t.selectionColor || Material.color(t.accentColor)
        gridLineColor = t.gridLineColor || gridLineColor
        labelColor = t.labelColor || t.textColor || labelColor
        labelsColor = labelColor
        textColor = t.textColor || labelColor
        itemDbackColor = t.itemBackColor || itemDbackColor
        console.log("Applied theme:", t.name)
    }

    function applyDisplayStyle(styleKey) {
        if (!displayStyles[styleKey]) {
            console.warn("Display style not found:", styleKey)
            return
        }
        var style = displayStyles[styleKey]
        displayStyleName = styleKey
        topHeight = style.topHeight
        windowButtonWidth = style.windowButtonWidth
        headerButtonGap = style.headerButtonGap
        controlRadius = style.controlRadius
        titleFontSize = style.titleSize
        console.log("Applied display style:", style.name)
    }

    readonly property var theme: isDark ? Material.Dark : Material.Light

    // ========== 颜色属性 ==========
    property color accentColor: Material.color(Material.accentColor)
    property color cardBorderColor: Material.color(Material.Blue)
    property color cardBorderErrorColor: Material.color(Material.Red)
    property color rootTitleColor: titleColor
    property color titleColor: Material.color(Material.Teal)
    property color appBackgroundColor: "#0B1117"
    property color panelBackgroundColor: "#111A23"
    property color panelElevatedColor: "#172330"
    property color panelAlternateColor: "#1C2A36"
    property color headerBackgroundColor: "#0F1A24"
    property color headerBorderColor: "#2C4357"
    property color buttonHoverColor: "#233447"
    property color selectionColor: "#2F5F82"

    // ========== 自适应视图 ==========
    property AdaptiveView adaptive_base: AdaptiveView {
        adaptive_name: "base"
    }
    property AdaptiveView1920_1080 adaptive_1920p: AdaptiveView1920_1080 {
        adaptive_name: "1920_1080"
    }
    property AdaptiveView2560_1440 adaptive_2560p: AdaptiveView2560_1440 {
        adaptive_name: "2560_1440"
    }

    property AdaptiveViewBase currentAdaptive: adaptive_base

    function autoGetAdaptiveView() {
        return adaptive_base
    }

    function getIcon(name) {
        if (!name || name.length === 0)
            return ""
        return "qrc:/resource/icon/" + name + ".png"
    }

    // ========== 样式属性 ==========
    property bool isDark: true
    property string backC: isDark ? "#15202A" : "#D6DEE6"
    property color backColor: appBackgroundColor

    property string gridLineColor: isDark ? "#263646" : "#CBD4DD"
    property string labelsColor: isDark ? "#E8F1F8" : "#111827"
    property string labelColor: isDark ? "#E8F1F8" : "#111827"
    property color textColor: isDark ? "#E8F1F8" : "#111827"

    property color itemDbackColor: isDark ? "#17212B" : "#E2E2E2"

    // ========== 尺寸属性 ==========
    property int leftWidth: 450
    property int topHeight: 45
    property int windowButtonWidth: 46
    property int headerButtonGap: 4
    property int controlRadius: 3
    property int titleFontSize: 22

    // ========== 持久化设置 ==========
    SettingsBase {
        location: "style.ini"
        property alias themeName: root.themeName
        property alias displayStyleName: root.displayStyleName
        property alias isDark: root.isDark
        property alias accentColor: root.accentColor
        property alias cardBorderColor: root.cardBorderColor
        property alias titleColor: root.titleColor
        property alias rootTitleColor: root.rootTitleColor
    }

    // ========== 组件完成时应用保存的主题 ==========
    Component.onCompleted: {
        if (!themes[themeName]) {
            themeName = "dark"
        }
        applyTheme(themeName)
        if (displayStyles[displayStyleName]) {
            applyDisplayStyle(displayStyleName)
        }
    }
}
