import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Controls.Material

import "../../../animation"
Item{
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
                currentIndex: core.coilIndex
                onCurrentIndexChanged: {
                    core.setCoilIndex(currentIndex)
                }

                model: leftCore.fliterEnable?leftCore.fliterListModel : coreModel.currentCoilListModel

                delegate:DataListViewIten{    //    -----------------------------
                    width: listView.width
                }
            }
        }
    }
    Rectangle{
        id:mask
        anchors.fill: parent
        color: "#00000000"
        border.width: 1
        border.color: Material.color(Material.Blue)
    }
    HoverHandler{
        onPointChanged: {
            leftCore.hoverPoint = Qt.point(point.position.x,point.position.y+100) // point.position
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
