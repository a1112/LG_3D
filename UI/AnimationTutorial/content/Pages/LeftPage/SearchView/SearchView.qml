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
    title: "     查询      "
    max_height: 95
    content_head_tool:
        ComboBox{
        implicitHeight: 30
        y:5
        currentIndex: leftCore.searchPageIndex
        onCurrentIndexChanged: {
            leftCore.searchPageIndex = currentIndex
        }

        model: ListModel{
            ListElement{ text: "卷号" }
            ListElement{ text: "时间" }
            ListElement{ text: "流水号" }
        }
    }

    content_body:
        SwipeView{
        clip: true
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentIndex: leftCore.searchPageIndex
        width: root.width-5
        id:swipe

        onCurrentIndexChanged: {
            leftCore.searchPageIndex = currentIndex
            max_height = [95,130,95][currentIndex]
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
                tipText:"筛选"
                width: parent.width
                height: parent.height
                source:coreStyle.isDark?coreStyle.getIcon("filter_light"):coreStyle.getIcon("filter")
                onClicked: {
                    fliterView.open()

                    }
            }
        }
        FilterView{
            x: fliterBtn.x
            id:fliterView
        }
    }

}
