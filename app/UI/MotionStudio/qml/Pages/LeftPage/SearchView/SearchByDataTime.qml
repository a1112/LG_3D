import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../../types"
import "../../Header"
ColumnLayout {
    id: root

    required property var modelStore
    required property var style

    height: 35
    spacing: 5
    // DateTimeSelectItem{
    //     title_:"起始日期:"
    //     id:fromDateSelect
    //     dateTime_:DateTime{
    //         hour:0
    //         minute:0
    //         second:0
    //     }
    // }
    DateTimeSelectLineItem{
        title_:"起始:"
        id:fromDateSelect
        style: root.style
        dateTime_:DateTime{
            hour:0
            minute:0
            second:0
        }
    }

    // Rectangle{
    //     Layout.fillWidth: true
    //     implicitHeight: 2
    // }
    DateTimeSelectLineItem{
        title_:"结束:"
        id:toDateSelect
        style: root.style
        dateTime_:DateTime{
        }
    }
    // DateTimeSelectItem{
    //     title_:"结束日期:"
    //     id:toDateSelect
    //     dateTime_:DateTime{
    //     }
    // }
    RowLayout{
        implicitHeight: 30
        Layout.fillWidth: true
        Item{
            Layout.fillWidth: true
            implicitHeight: 1
        }
        Item{
            implicitHeight: 30
            implicitWidth: 60
            CheckRec {
                style: root.style
                fillWidth: true
                height: 30
                text: qsTr("查询")
                onClicked: {
                    root.modelStore.searchByCoilDateTime(
                                fromDateSelect.dateTime_.dateTimeString,
                                toDateSelect.dateTime_.dateTimeString)
                }
            }
        }
        Item{
            implicitWidth: 15
            implicitHeight: 1
        }

    }

    Item{
        Layout.fillWidth: true
        Layout.fillHeight: true
    }

}
