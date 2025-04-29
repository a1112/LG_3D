import QtQuick
import QtQuick.Window
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

    property AdaptiveView adaptive_base:AdaptiveView{
        adaptive_name:"base"
    }
    property AdaptiveView1920_1080 adaptive_1920p:AdaptiveView1920_1080{
        adaptive_name:"1920_1080"
    }
    property AdaptiveView2560_1440 adaptive_2560p:AdaptiveView2560_1440{
        adaptive_name:"2560_1440"
    }


    function autoGetAdaptiveView(){
        return adaptive_base
    }

    property AdaptiveViewBase currentAdaptive:autoGetAdaptiveView()

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

    property color itemDbackColor:isDark?"#AA2f2f2f":"#AAe2e2e2"

    property int leftWidth: 400
    property int topHeight: 45

    SettingsBase{
        property alias isDark: root.isDark
         location: "style.ini"
         property alias accentColor: root.accentColor
         property alias cardBorderColor: root.cardBorderColor
         property alias titleColor: root.titleColor
         property alias rootTitleColor: root.rootTitleColor
    }
}
