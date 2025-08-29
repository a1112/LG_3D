import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// TiledImageViewer.qml
Rectangle {
    id: root
    property int tileSize: 8000
    property int count_ : 0
    property string imageUrl: ""
    color: "#00000000"
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
                         console.log("imageUrl, ", imageUrl)
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

        Loader{
            asynchronous:true
            sourceComponent: TiledImageItem{}
        }




    }
}
