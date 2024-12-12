import QtQuick
import "ViewChang"
Item {
    id:root
    width:parent.width
    height:parent.height


    ViewChangView{  // 右侧的数据切换
        height:root.height-60
        x:root.width- width -20 -50
        y:25
    }
}
