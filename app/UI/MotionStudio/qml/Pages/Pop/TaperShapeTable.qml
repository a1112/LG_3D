pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

Item {
    id: root

    required property var style
    property var coilModel: null

    readonly property var taperDataS: taperData("S")
    readonly property var taperDataL: taperData("L")

    function taperData(surface) {
        if (!root.coilModel || !root.coilModel.coilData)
            return null
        let items = root.coilModel.coilData.childrenAlarmTaperShape || []
        for (let index = 0; index < items.length; ++index) {
            if (items[index] && items[index].surface === surface)
                return items[index]
        }
        return null
    }

    Column {
        anchors.fill: parent
        spacing: 3

        Row {
            width: parent.width
            height: 22
            spacing: 1

            Repeater {
                model: [
                    qsTr("表面"),
                    qsTr("外塔最高 (x/y/值)"),
                    qsTr("外塔最低 (x/y/值)"),
                    qsTr("内塔最高 (x/y/值)"),
                    qsTr("内塔最低 (x/y/值)"),
                    qsTr("角度°")
                ]

                Label {
                    required property string modelData
                    width: (parent.width - 5) / 6
                    height: parent.height
                    text: modelData
                    color: root.style.titleColor
                    font.bold: true
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    background: Rectangle {
                        color: root.style.headerBackgroundColor
                    }
                }
            }
        }

        TaperShapeRow {
            width: parent.width
            height: 35
            visible: root.taperDataS !== null
            style: root.style
            data: root.taperDataS || ({})
            surfaceLabel: "S"
        }

        TaperShapeRow {
            width: parent.width
            height: 35
            visible: root.taperDataL !== null
            style: root.style
            data: root.taperDataL || ({})
            surfaceLabel: "L"
        }

        Label {
            width: parent.width
            height: 30
            text: qsTr("暂无塔形数据")
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
            visible: root.taperDataS === null && root.taperDataL === null
            color: root.style.secondaryTextColor
            font.pixelSize: 11
        }
    }
}
