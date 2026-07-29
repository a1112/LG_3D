import QtQuick
import QtQuick.Controls
import "_base_"
import "Core"
DataShowBackground {
    id: root

    required property var adaptiveMetrics
    required property var style
    required property var model
    required property var settings
    required property var viewControl

    property Binds binds_base:binds_s
    property Binds binds_s : Binds{
        surfaceData: root.model.surfaceS
    }
    property Binds binds_l : Binds{
        surfaceData: root.model.surfaceL
    }

    SplitView{
        anchors.fill: parent
        DataShowView{   // 单侧
            id: dataShowView_R
            surfaceData: root.model.surfaceS
            modelStore: root.model
            style: root.style
            settings: root.settings
            adaptiveMetrics: root.adaptiveMetrics
            dataShowCore : DataShowCore{
                surfaceData: root.model.surfaceS
                binds: root.viewControl.lockControl
                       ? root.binds_base : root.binds_s
            }
            SplitView.preferredWidth: root.is_half?root.viewWidth_half:root.viewWidth
        }

        DataShowView{    // 单侧
            surfaceData: root.model.surfaceL
            modelStore: root.model
            style: root.style
            settings: root.settings
            adaptiveMetrics: root.adaptiveMetrics
            dataShowCore : DataShowCore{
                surfaceData: root.model.surfaceL
                binds: root.viewControl.lockControl
                       ? root.binds_base : root.binds_l
            }
            id: dataShowView_L
            SplitView.preferredWidth : root.is_half?root.viewWidth_half:root.viewWidth
        }

    }

}

