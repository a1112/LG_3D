import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../BaseSetting"

ColumnLayout{
    spacing: 12
    Layout.margins: 16

    Label{
        text: qsTr("\u56fe\u50cf\u670d\u52a1")
        font.pixelSize: 16
    }
    RowLayout{
        spacing: 12
        Label{
            text: qsTr("\u540e\u7aef")
            font.pixelSize: 14
        }
        ComboBox{
            id: imageBackendBox
            model: [qsTr("Python"), qsTr("Rust")]
            currentIndex: coreSetting.useRustImageServer ? 1 : 0
            onActivated: coreSetting.useRustImageServer = currentIndex === 1
        }
        Label{
            text: coreSetting.useRustImageServer
                  ? qsTr("\u5f53\u524d\u4f7f\u7528 Rust \u56fe\u50cf\u670d\u52a1")
                  : qsTr("\u5f53\u524d\u4f7f\u7528 Python \u56fe\u50cf\u670d\u52a1\uff085010\uff09")
            font.pixelSize: 14
        }
    }
    RowLayout{
        spacing: 8
        enabled: coreSetting.useRustImageServer
        Label{
            text: qsTr("Rust \u7aef\u53e3")
            font.pixelSize: 14
        }
        SpinBox{
            id: rustPortBox
            from: 1
            to: 65535
            value: coreSetting.rustImageServerPort
            editable: true
            onValueModified: coreSetting.rustImageServerPort = value
        }
        Label{
            text: qsTr("\u9ed8\u8ba4 6013")
            font.pixelSize: 14
        }
    }

    Rectangle{
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: "#40000000"
    }

    Label{
        text: qsTr("AREA \u74e6\u683c\u521d\u59cb\u5206\u5757")
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
            text: qsTr("\u6bcf\u8fb9\u5757\u6570\uff08\u9ed8\u8ba4 3\uff0c\u52a0\u8f7d\u5b8c\u6210\u540e\u6309\u5c3a\u5bf8\u81ea\u52a8\u8c03\u6574\uff09")
            font.pixelSize: 14
        }
    }

    Rectangle{
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: "#40000000"
    }

    Label{
        text: qsTr("\u7f13\u5b58\u8bbe\u7f6e")
        font.pixelSize: 16
    }
    RowLayout{
        spacing: 8
        CheckBox{
            id: enable1024CacheCheckBox
            checked: coreSetting.enable1024CacheMode
            onCheckedChanged: coreSetting.enable1024CacheMode = checked
        }
        Label{
            text: qsTr("\u542f\u75281024\u7f13\u5b58\u6a21\u5f0f\uff08falsecolor\u7f29\u7565\u56fe\uff09")
            font.pixelSize: 14
        }
    }

    Rectangle{
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        color: "#40000000"
    }

    Label{
        text: qsTr("\u663e\u793a\u8bbe\u7f6e")
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
            text: qsTr("\u663e\u793a\u53e0\u52a0\u56fe\u5c42\uff08\u5854\u5f62\u62a5\u8b66 Error \u56fe\u5c42\uff09")
            font.pixelSize: 14
        }
    }
}
