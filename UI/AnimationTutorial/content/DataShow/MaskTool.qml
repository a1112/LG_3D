import QtQuick
import "ViewChang"
import "2dShow"
import "Menu/MainShow"
Item {
    id:root
    width:parent.width
    height:parent.height

    MouseArea{
        anchors.fill:parent
        acceptedButtons:Qt.RightButton
        onClicked:{
            mainShowMenu.popup()
        }
    }


    ShowInfos{
        width: root.width
        height: root.height
    }
    ViewChangView{  // 右侧的数据切换
        height:root.height
        x:root.width- width -70
        y:25
    }

    MainShowMenu{
        id: mainShowMenu


    }
}
