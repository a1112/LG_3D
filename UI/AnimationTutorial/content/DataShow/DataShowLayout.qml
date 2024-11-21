import QtQuick 2.15
import QtQuick.Controls 2.15
import "_base_"
// import "../GlobalView"
import "Core"
DataShowBackground {
    id: root

    SplitView{
        anchors.fill: parent
        DataShowView{
            id: dataShowView_L
            surfaceData : coreModel.surfaceS
            SplitView.preferredWidth : root.is_half?root.viewWidth_half:root.viewWidth
        }
        DataShowView{
            id: dataShowView_R
            surfaceData: coreModel.surfaceL
            SplitView.preferredWidth: root.is_half?root.viewWidth_half:root.viewWidth
        }
    }

}

