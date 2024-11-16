import QtQuick 2.15
import QtQuick.Controls.Material
import "../btns"
Item {
    id:item
    property alias text: itemDelegate.text
    property bool checked: coreModel.toolDict[key]
    onCheckedChanged:{
        if(tool_visible_v!==checked)
        {
        tool_visible_v=checked
        }
    }
    property bool tool_visible_v:tool_visible
    onTool_visible_vChanged: {
        if (coreModel.toolDict[key]!==tool_visible_v){
        coreModel.toolDict[key]=tool_visible_v
        let temp = coreModel.toolDict
        coreModel.toolDict = {}
        coreModel.toolDict = temp
            }
    }

    width: itemDelegate.width
    property var checkColor: Material.color(Material.Blue)
    property bool item_selected: checked
    property bool fillWidth: false
    property int fillWidthWidth: 1
    signal clicked
    property alias source:image.source
    property string tipText:tipText_info
    height: width

    Pane{
        anchors.centerIn: parent
        width: parent.width
        height: parent.height
        Material.elevation: 5
    }
    Rectangle{
        anchors.horizontalCenter: parent.horizontalCenter
        width: item_selected?parent.width:0
        height: 1
        anchors.top: parent.top
        color: checkColor
        visible: item.checked
    }
    Rectangle{
        anchors.horizontalCenter: parent.horizontalCenter
        width:  item_selected?parent.width:0
        height: 1
        anchors.bottom: parent.bottom
        color: checkColor
        visible: item.checked
    }
    Rectangle{
        anchors.verticalCenter: parent.verticalCenter
        width: 1
        height: item_selected?parent.height:0
        anchors.left: parent.left
        color: checkColor
        visible: item.checked
    }
    Rectangle{
        anchors.verticalCenter: parent.verticalCenter
        width: 1
        height: item_selected?parent.height:0
        anchors.right: parent.right
        color: checkColor
        visible: item.checked
    }

ItemDelegate{
    anchors.fill: parent
    font.bold: true
    font.pixelSize: 15
    id:itemDelegate
    onClicked: {
    item.checked = !item.checked
        item.clicked()
    }
}

ColorImageButton{
    id: image
    anchors.fill: parent
}
MouseArea{
    acceptedButtons: Qt.NoButton
    id: mouseArea
    cursorShape: Qt.PointingHandCursor
    hoverEnabled: true
    anchors.fill: parent
    ToolTip.visible: item.tipText!=="" && containsMouse
    ToolTip.text: item.tipText
}


}
