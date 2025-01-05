import QtQuick 2.15
import QtQuick.Controls.Material
import "../Base"
import "../Style/Adaptive"
Item {
    id:root
    readonly property var theme: isDark ? Material.Dark : Material.Light

    property color accentColor:Material.color( Material.accentColor)
    property color cardBorderColor:Material.color( Material.Blue)
    property color cardBorderErrorColor:Material.color( Material.Red)
    property color rootTitleColor:titleColor
    property color titleColor:Material.color(Material.Teal)

    property AdaptiveView adaptive_1080p:AdaptiveView{}
    property AdaptiveView adaptive_base:AdaptiveView{}

    property AdaptiveView currentAdaptive:adaptive_base

    function getIcon(name){
        return "../icons/" + name + ".png"

    }

    property bool isDark: true
    property string backC:isDark?"rgba(200, 200, 200, 0.005)":"rgba(200, 200, 200, 0.07)"
    property string backColor:isDark?Qt.rgba(0, 0, 0,1):Qt.rgba(200, 200, 200,1)

    property string gridLineColor: isDark ? "#02eeeeee" : "#22222222"
    property string labelsColor: isDark ? "#FFF" : "#000"
    property string labelColor: isDark ? "#FFF" : "#000"
    property color textColor: isDark ? "#FFF" : "#000"


    property int leftWidth: 400
    property int topHeight: 45

    SettingsBase{
        property alias isDark: root.isDark
         fileName: "style.ini"
         property alias accentColor: root.accentColor
         property alias cardBorderColor: root.cardBorderColor
         property alias titleColor: root.titleColor
         property alias rootTitleColor: root.rootTitleColor
    }
}
