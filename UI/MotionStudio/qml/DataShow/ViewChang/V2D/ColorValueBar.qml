import QtQuick

Row {
    id:root
    x:parent.width+10
    spacing:5
    property real maxValue:127
    property real minValue:-127

    property real itemHeight:height/listView.model

    property bool hoved :hov.hovered
    property color labelColor:"#FFF"
    function getHovText(pos_y){
        return (((height - pos_y) /height) *(maxValue-minValue)  +  minValue).toFixed(1)
    }
    function getValueByModelIndex(index_){
        let count = listView.model
        return ""+((count-index_)/count *(maxValue-minValue)  +  minValue).toFixed(0)

    }
    GetRec{
            width:20; height: parent.height

    HoverHandler{
        id:hov
        onPointChanged:{

        }
        onHoveredChanged:{}


    }


    HovedLabel{
        y:hov.point.position.y-height/2
        anchors.right:parent.left
        visible:hov.hovered
        text:getHovText(hov.point.position.y)
        background:Rectangle{
            color:"black"
        }
    }
    }
    // Rectangle {

    //     gradient: Gradient {
    //         orientation: Gradient.Horizontal
    //         GradientStop { position: 0/255; color: Qt.rgba( (128,0,0) }
    //         GradientStop { position: 1.0; color: "red" }
    //     }
    // }

    ListView{
        id:listView
        // orientation:ListView.Horizontal
        height:parent.height
        width:30
        model:10
        delegate:ValueItemItem{

        }
    }

}
