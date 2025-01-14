import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material
import "DataListMenu"
import "Core"
import "../../../Model"
import "../../../animation"
DataListViewItenBase {
    id:root

        RowLayout{
            width: parent.width
            Rectangle{
                implicitWidth: 2
                implicitHeight: 1
            }
            ColumnLayout{
                spacing: 0
                Layout.fillWidth: true
                implicitHeight: 30
                RowLayout{
                    Label{
                        font.pointSize: 11
                        font.bold: true
                        text: " "+root.coilModel.coilId
                        color:root.listItemCoil.detectionStatuColor
                    }
                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 1
                    }
                    Label{
                        text:root.coilModel.coilNo
                        font.bold: true
                        font.pointSize: 12
                    }

                    StateWrapper{
                        // c_state:coilState
                    }

                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 1
                    }
                    Label{
                        font.pointSize: 11
                        text: root.coilModel.coilType
                    }
                    Item {
                        Layout.fillWidth: true
                        implicitHeight: 1
                    }

                    StatusMsg{
                    }
                }
            }
            Item{
                implicitWidth: 5
                implicitHeight: 2
            }
        }
}
