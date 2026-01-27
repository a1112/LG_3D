import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../../Base"
import "../../btns"
import "../../Model/server"
CheckDelegate {
    height:25

    // 直接使用 model 数据
    property string defectName: model.name || ""
    property int defectLevel: model.level || 0
    property color defectColor: model.color || "#00000000"
    property bool defectShow: model.show !== undefined ? model.show : false
    property bool filterShow: model.filter !== undefined ? model.filter : true

    text: defectName
    Material.accent: defectColor
    visible: defectShow || (!defectShow && defectViewCore.filterCore.fliterShowBgDefect)
    checked: filterShow
    onCheckedChanged:{
        model.filter = checked
        defectViewCore.filterCore.resetFilterDict()
    }
}
