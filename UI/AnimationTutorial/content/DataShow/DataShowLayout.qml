import QtQuick 2.15
import QtQuick.Controls 2.15
import "../GlobalView"
Item {
    id: root
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
        sourceComponent:    Watermark{
            anchors.fill:parent
         }
    }
    SplitView{
        anchors.fill: parent
        DataShowView{
            id: dataShowView_L
            surfaceData : coreModel.surfaceS
            SplitView.preferredWidth : root.is_half?root.viewWidth_half:root.viewWidth
        }
        // DataShowLabelsViewAll{      //    全部的报警参数
        //     visible:auth.isAdmin && dataShowView_L.visible || dataShowView_R.visible
        //     surfaceData: coreModel.surfaceS
        //     dataShowCore: dataShowView_L.dataShowCore
        //     SplitView.fillHeight: true
        //     SplitView.preferredWidth: 300
        //     SplitView.fillWidth: true
        //     SplitView.maximumWidth: 400
        // }
        DataShowView{
            id: dataShowView_R
            surfaceData: coreModel.surfaceL
            SplitView.preferredWidth: root.is_half?root.viewWidth_half:root.viewWidth
        }
    }

}

