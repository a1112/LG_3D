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
}
