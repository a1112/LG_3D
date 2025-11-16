import QtQuick 2.15
import "../"
Item {
    width: 1980
    height: 1080
    property int tooolWidth: 0
    property bool is_half: (dataShowView_L.visible && dataShowView_R.visible)
    property int viewWidth_half: (root.width - tooolWidth)/2
    property int viewWidth: root.width - tooolWidth
    Loader{
        clip:true
        anchors.fill:parent
        active:!(dataShowView_L.visible || dataShowView_R.visible)
        asynchronous:true
        sourceComponent:   Watermark{
            anchors.fill:parent
         }
    }

}
