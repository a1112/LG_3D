import QtQuick
import QtQuick.Layouts
import "Base"
import "ShowDataInfo"
DataShowItemBase{
    id:root
    RowLayout{
        anchors.fill:parent

    EllipseShow{
        implicitWidth: root.height
    }
    Rectangle{
        Layout.fillWidth:true
        Layout.fillHeight:true

    }
    }
}
