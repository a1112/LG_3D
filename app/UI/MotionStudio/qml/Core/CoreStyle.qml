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
            name: "深色主题",
            isDark: true,
            accentColor: Material.Teal,
            cardBorderColor: Material.Blue,
            titleColor: Material.Teal,
            backgroundColor: "#000000",
            gridLineColor: "#02eeeeee",
            textColor: "#FFFFFF",
            itemBackColor: "#AA2f2f2f"
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
            itemBackColor: "#AAe2e2e2"
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
            itemBackColor: "#AA1a3a5c"
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
            itemBackColor: "#AA1a3a1a"
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
            itemBackColor: "#AA3a1a5c"
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
            itemBackColor: "#AA3a2a1a"
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
        console.log("Applied theme:", t.name)
    }

    readonly property var theme: isDark ? Material.Dark : Material.Light

    // ========== 颜色属性 ==========
    property color accentColor: Material.color(Material.accentColor)
    property color cardBorderColor: Material.color(Material.Blue)
    property color cardBorderErrorColor: Material.color(Material.Red)
    property color rootTitleColor: titleColor
    property color titleColor: Material.color(Material.Teal)

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
    property string backC: isDark ? "rgba(200, 200, 200, 0.005)" : "rgba(200, 200, 200, 0.07)"
    property string backColor: isDark ? Qt.rgba(0, 0, 0, 1) : Qt.rgba(200, 200, 200, 1)

    property string gridLineColor: isDark ? "#02eeeeee" : "#22222222"
    property string labelsColor: isDark ? "#FFF" : "#000"
    property string labelColor: isDark ? "#FFF" : "#000"
    property color textColor: isDark ? "#FFF" : "#000"

    property color itemDbackColor: isDark ? "#AA2f2f2f" : "#AAe2e2e2"

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
