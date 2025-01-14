import QtQuick

// import QtQuick.Controls.Material
// import QtQuick.Layouts
// import "../../../../Pages/Header"
Item {
    id:root
    property alias model:list.model
    ListView{
        id:list
        anchors.fill:parent
        spacing:5
        orientation:ListView.Horizontal
        delegate:
            DefectLabelShowItem{
                height:25
        }


}
}
