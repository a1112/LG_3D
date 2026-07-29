import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material
import QtQuick.Layouts 1.15
import "../../Header"
import "../../../Base"
import "../../../Comp/Card"
import "../../../btns"
CardBase{
    id:root

    required property var adaptiveMetrics
    required property var style
    required property var leftController
    required property var authManager

    cardStyle: root.style
    cardAuthManager: root.authManager

    title: qsTr("     查询      ")
    max_height: 95
    content_head_tool:
        ComboBox{
        implicitHeight: 30
        y:5
        currentIndex: root.leftController.searchPageIndex
        onCurrentIndexChanged: {
            root.leftController.searchPageIndex = currentIndex
        }

        model: ListModel{
            ListElement{ text: qsTr("卷号") }
            ListElement{ text: qsTr("时间") }
            ListElement{ text: qsTr("流水号") }
        }
    }

    content_body:
        SwipeView{
        clip: true
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentIndex: root.leftController.searchPageIndex
        width: root.width-5
        id:swipe
        onCurrentIndexChanged: {
            root.leftController.searchPageIndex = swipe.currentIndex
            root.max_height = [95,130,95][swipe.currentIndex]
        }

        SearchByCoilNo {
            width: root.width
        }
        SearchByDataTime {
            id: secondPage
        }
        SearchByCoilId {
        }
    }
    Item{
        anchors.right: root.right
        width: 35
        height:35
        Item{
            anchors.centerIn: parent
            width: 30
            height: 30

            ImageButton{
                id:fliterBtn
                tipText:qsTr("筛选")
                width: parent.width
                height: parent.height
                source: root.style.isDark ? root.style.getIcon("filter_light")
                                          : root.style.getIcon("filter")
                onClicked: {
                    fliterView.open()
                    }
            }
        }

        FilterView{
            x: fliterBtn.x
            id:fliterView
            adaptiveMetrics: root.adaptiveMetrics
            style: root.style
        }
    }

}
