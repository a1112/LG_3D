import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item{
        Layout.fillWidth: true
        height: col.height
ColumnLayout{
    id:col
    width: parent.width
    Label{
        anchors.horizontalCenter: parent.horizontalCenter
        text:defectName
        font.pointSize: 18
    }
    Item{
        Layout.fillWidth: true
        width: parent.width
        height: 50
GridView {
    id:grid
    width: parent.width
    cellWidth: grid.width/2
    cellHeight: 25
    height:50
    model:ListModel{
        id:msgModel
    }
    delegate:RowItemView{

    }
    Component.onCompleted: {
        msgModel.clear()
        // msgModel.append({
        //                 key:"id",
        //                 value:Id
        //                 })
        // msgModel.append({
        //                 key:"名称",
        //                 value:defectName
        //                 })
        msgModel.append({
                        key:"x",
                        value:dataShowCore.px_to_pos_x_mm_from_centre(defectX).toFixed(0)
                        })
        msgModel.append({
                        key:"y",
                        value:dataShowCore.px_to_pos_y_mm_from_centre(defectY).toFixed(0)
                        })
        msgModel.append({
                        key:"宽",
                        value:dataShowCore.px_to_width_mm(defectW).toFixed(0)
                        })
        msgModel.append({
                        key:"高",
                        value:dataShowCore.px_to_width_mm(defectH).toFixed(0)
                        })

    }
}
}
}
}
