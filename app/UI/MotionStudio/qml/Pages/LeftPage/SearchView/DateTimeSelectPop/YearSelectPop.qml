pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../../../Header"
import "../../../../types"
BaseSelectPop {
    id: root

    required property DateTime dateTime

    width: 280
    height: 125

    GridView {
        anchors.fill: parent
        anchors.margins: 8
        model: root.dateTime.yearModel
        cellWidth: 86
        cellHeight: 35

        delegate: CheckRec {
                required property int value
                style: root.style
                height: 30
                width: 82
                checked: root.dateTime.fullYear === value
                checkColor: checked ? root.style.statusWarningColor
                                    : "transparent"
                fillWidth: true
                text: value
                onClicked: {
                    root.dateTime.setYear(value)
                    root.close()
                }
            }
    }
}

