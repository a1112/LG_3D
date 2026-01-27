import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../BaseSetting"

ColumnLayout{
    spacing: 12
    Layout.margins: 16

    Label{
        text: qsTr("AREA 宫格初始分块")
        font.pixelSize: 16
    }
    RowLayout{
        spacing: 8
        SpinBox{
            id: tileCountBox
            from: 1
            to: 10
            value: coreSetting.defaultAreaTileCount
            onValueChanged: coreSetting.defaultAreaTileCount = value
        }
        Label{
            text: qsTr("每边块数（默认 3，加载完成后按尺寸自动调整）")
            font.pixelSize: 14
        }
    }

    // ========== 分隔线 ==========
    Rectangle{
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: "#40000000"
    }

    // ========== 显示叠加图层设置 ==========
    Label{
        text: qsTr("显示设置")
        font.pixelSize: 16
    }
    RowLayout{
        spacing: 8
        CheckBox{
            id: errorOverlayCheckBox
            checked: coreSetting.showErrorOverlay
            onCheckedChanged: coreSetting.showErrorOverlay = checked
        }
        Label{
            text: qsTr("显示叠加图层（塔形报警 Error 图层）")
            font.pixelSize: 14
        }
    }
}
