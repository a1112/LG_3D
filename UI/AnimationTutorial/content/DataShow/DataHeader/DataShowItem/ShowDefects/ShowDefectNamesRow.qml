import QtQuick
// import QtQuick.Controls.Material
// import QtQuick.Layouts
// import "../../../../Pages/Header"
Item {
    id:root
    ListView{
        anchors.fill:parent
        spacing:5
        model:dataShowCore.currentDefectDictModel
        orientation:ListView.Horizontal
        delegate:
            DefectLabelShowItem{
                height:25
        }


}
}
