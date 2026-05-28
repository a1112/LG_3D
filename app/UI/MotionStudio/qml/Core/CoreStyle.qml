import QtQuick
import QtQuick.Window
import QtQuick.Controls.Material
import "../Base"
import "../Style/Adaptive"

Item {
    id: root

    // ========== 主题预设 ==========
    property string themeName: "dark"  // 当前主题名称
    readonly property var themes: ({
        "dark": {
            name: "工业深色主题",
            isDark: true,
            accentColor: Material.Cyan,
            cardBorderColor: Material.BlueGrey,
            titleColor: Material.Cyan,
            backgroundColor: "#0B1117",
            gridLineColor: "#263646",
            textColor: "#E8F1F8",
            itemBackColor: "#17212B",
            panelColor: "#111A23",
            panelElevatedColor: "#172330",
            panelAlternateColor: "#1C2A36",
            headerColor: "#0F1A24",
            headerBorderColor: "#2C4357",
            hoverColor: "#233447",
            selectionColor: "#2F5F82"
        },
        "light": {
            name: "浅色主题",
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
        "ocean": {
            name: "海洋主题",
            isDark: true,
            accentColor: Material.Cyan,
            cardBorderColor: Material.Cyan,
            titleColor: Material.Cyan,
            backgroundColor: "#001a2c",
            gridLineColor: "#1a3a5c",
            textColor: "#E0F7FA",
            itemBackColor: "#1a3a5c"
        },
        "forest": {
            name: "森林主题",
            isDark: true,
            accentColor: Material.Green,
            cardBorderColor: Material.Green,
            titleColor: Material.Green,
            backgroundColor: "#0a1a0a",
            gridLineColor: "#1a3a1a",
            textColor: "#E8F5E9",
            itemBackColor: "#1a3a1a"
        },
        "purple": {
            name: "紫色主题",
            isDark: true,
            accentColor: Material.Purple,
            cardBorderColor: Material.Purple,
            titleColor: Material.Purple,
            backgroundColor: "#1a0a2c",
            gridLineColor: "#3a1a5c",
            textColor: "#F3E5F5",
            itemBackColor: "#3a1a5c"
        },
        "sunset": {
            name: "日落主题",
            isDark: true,
            accentColor: Material.Orange,
            cardBorderColor: Material.Orange,
            titleColor: Material.DeepOrange,
            backgroundColor: "#1a0f00",
            gridLineColor: "#3a2a1a",
            textColor: "#FFF3E0",
            itemBackColor: "#3a2a1a"
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
        labelColor = t.textColor || labelColor
        labelsColor = labelColor
        textColor = labelColor
        itemDbackColor = t.itemBackColor || itemDbackColor
        console.log("Applied theme:", t.name)
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

    // ========== 持久化设置 ==========
    SettingsBase {
        location: "style.ini"
        property alias themeName: root.themeName
        property alias isDark: root.isDark
        property alias accentColor: root.accentColor
        property alias cardBorderColor: root.cardBorderColor
        property alias titleColor: root.titleColor
        property alias rootTitleColor: root.rootTitleColor
    }

    // ========== 组件完成时应用保存的主题 ==========
    Component.onCompleted: {
        if (themes[themeName]) {
            applyTheme(themeName)
        }
    }
}
