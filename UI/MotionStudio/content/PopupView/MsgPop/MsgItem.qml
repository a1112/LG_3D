import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
// import "../../Core"
Item {
    id:root
    Layout.fillWidth: true
    Layout.fillHeight: true
    property string title: "S端"
    // property SurfaceData surface
    // property string currentCoilNo: core.currentCoilModel.coilNo
    // onCurrentCoilNoChanged: {
    //     model.clear()
    //     model.append({
    //                      key: "X 标定",
    //                      value: surface.scan3dScaleX.toFixed(3)+""
    //                  }
    //                  )
    //     model.append({
    //                      key: "Y 标定",
    //                      value: surface.scan3dScaleY.toFixed(3)+""
    //                  }
    //                  )
    //     model.append({
    //                      key: "Z 标定",
    //                      value: surface.scan3dScaleZ.toFixed(3)+""
    //                  }
    //                  )
    // }

    property alias model: gridView.model
ColumnLayout {
    anchors.fill: parent
    Label {
        font.bold: true
        font.pixelSize: 24
        text: root.title
        Layout.alignment: Qt.AlignHCenter
    }

GridView {
    id: gridView
    Layout.fillWidth: true
    Layout.fillHeight: true
    cellWidth: gridView.width/2-5
    cellHeight: 25
    model: ListModel {}
    delegate: RowItemView {

}
}
}
}
