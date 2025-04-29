import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// TiledImageViewer.qml
Rectangle {
    id: root
    property int tileSize: 8000
    property int count_ : 0
    property string imageUrl: ""

    property int source_item_width: parseInt(dataAreaShowCore.sourceWidth/count_)
    property int source_item_height: parseInt(dataAreaShowCore.sourceHeight/count_)

    function get_num(px_width){
        let i = 1
        while (true){
            if (px_width/i<= tileSize)
            {
                return i
            }
            i++
        }
    }

    onImageUrlChanged: {
        count_= 1
        api.ajax.get(imageUrl,(text)=>{
                         console.log(text)
                         let json_data=JSON.parse(text)
                         dataAreaShowCore.sourceWidth = json_data["width"]
                         dataAreaShowCore.sourceHeight = json_data["height"]
                         count_ = Math.max(get_num(json_data["width"]), get_num(json_data["height"]))
                     },(err)=>{
                        console.log(err)
                     })


    }

    Repeater {
        id: tiledImage
        model: count_ * count_
        Item{
            property int row_:parseInt(index/count_)
            property int col_:parseInt(index%count_)
            x: parseInt(index / count_)*width
            y: parseInt(index%count_)*height
            width: root.width/count_
            height: root.height/count_
            Rectangle{
                anchors.fill: parent
                border.width: 1
                color:"#00000000"
                border.color: "red"
            }
        Image {
            width: parent.width
            height: parent.height
            source: imageUrl+"?row=-1" //+ "?row=" + parseInt(index/count_) + "&col=" + parseInt(index%count_) + "&count=" +count_
            sourceClipRect:Qt.rect(
                                row_*source_item_width,
                               col_*source_item_height,
                               source_item_width,
                               source_item_height)
            asynchronous: true
            fillMode: Image.PreserveAspectFit
            // sourceSize.width:parent.width
            // sourceSize.height:parent.width
        }
        }
    }
}
