pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material

import "../../../animation"
Item{
    id:root

    required property var style
    required property var coreController
    required property var modelController
    required property var leftController
    required property var popupManager

    SplitView.fillWidth: true
    SplitView.fillHeight: true
    Layout.fillWidth: true
    Layout.fillHeight: true

    property bool showFilterIcon:true
    ColumnLayout {
        anchors.fill: parent

        HeadView{
        }

        ListTitleView{}  // 列表头

        Item{
            clip: true
            Layout.fillWidth: true
            Layout.fillHeight: true
            AnimListView{
                id: listView
                anchors.fill: parent
                currentIndex: root.leftController.fliterEnable
                              ? root.leftController.visibleIndexForCoilId(
                                    root.coreController.currentCoilModel.coilId)
                              : root.coreController.coilIndex
                model: root.leftController.fliterEnable
                       ? root.leftController.fliterListModel
                       : root.modelController.currentCoilListModel
                delegate:DataListViewIten{    //    -----------------------------
                    width: ListView.view ? ListView.view.width : 0
                    style: root.style
                    coreController: root.coreController
                    modelController: root.modelController
                    leftController: root.leftController
                    popupManager: root.popupManager
                }
            }
        }
    }
    Rectangle{
        id:mask
        anchors.fill: parent
        z: -1
        color: root.style.panelBackgroundColor
        border.width: 1
        border.color: root.style.headerBorderColor
    }
    HoverHandler{
        onPointChanged: {
            var nextPoint = Qt.point(point.position.x, point.position.y + 100)
            if (Math.abs(root.leftController.hoverPoint.x - nextPoint.x) >= 2
                    || Math.abs(root.leftController.hoverPoint.y - nextPoint.y) >= 2) {
                root.leftController.hoverPoint = nextPoint
            }
        }

        onHoveredChanged: {
            if(hovered){
                root.leftController.isHoved = true
            }
            else{
                root.leftController.isHoved=false
            }
        }
    }
}
