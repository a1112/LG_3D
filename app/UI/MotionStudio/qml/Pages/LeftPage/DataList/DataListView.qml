import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material

import "../../../animation"
Item{
    SplitView.fillWidth: true
    SplitView.fillHeight: true
    Layout.fillWidth: true
    Layout.fillHeight: true

    id:root
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
                currentIndex: leftCore.fliterEnable
                              ? leftCore.visibleIndexForCoilId(core.currentCoilModel.coilId)
                              : core.coilIndex
                model: leftCore.fliterEnable?leftCore.fliterListModel : coreModel.currentCoilListModel
                delegate:DataListViewIten{    //    -----------------------------
                    width: ListView.view ? ListView.view.width : 0
                    style: coreStyle
                    coreController: core
                    modelController: coreModel
                    leftController: leftCore
                    popupManager: popManage
                }
            }
        }
    }
    Rectangle{
        id:mask
        anchors.fill: parent
        z: -1
        color: coreStyle.panelBackgroundColor
        border.width: 1
        border.color: coreStyle.headerBorderColor
    }
    HoverHandler{
        onPointChanged: {
            var nextPoint = Qt.point(point.position.x, point.position.y + 100)
            if (Math.abs(leftCore.hoverPoint.x - nextPoint.x) >= 2
                    || Math.abs(leftCore.hoverPoint.y - nextPoint.y) >= 2) {
                leftCore.hoverPoint = nextPoint
            }
        }

        onHoveredChanged: {
            if(hovered){
                leftCore.isHoved = true
            }
            else{
                leftCore.isHoved=false
            }
        }
    }
}
