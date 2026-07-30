import QtQuick
import QtQuick.Controls
import "_base_"
import "Core"
DataShowBackground {
    id: root

    required property var model
    required property var settings
    required property var viewControl
    required property var alarmInfo
    required property var apiClient
    required property var globalContext
    required property var toolService
    required property var imageCacheService
    leftView: dataShowView_L
    rightView: dataShowView_R

    property Binds binds_base:binds_s
    property Binds binds_s : Binds{
        surfaceData: root.model.surfaceS
        settings: root.settings
    }
    property Binds binds_l : Binds{
        surfaceData: root.model.surfaceL
        settings: root.settings
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
            alarmInfo: root.alarmInfo
            apiClient: root.apiClient
            globalContext: root.globalContext
            dataShowCore : DataShowCore{
                surfaceData: root.model.surfaceS
                apiClient: root.apiClient
                modelStore: root.model
                globalContext: root.globalContext
                toolService: root.toolService
                settings: root.settings
                style: root.style
                imageCacheService: root.imageCacheService
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
            alarmInfo: root.alarmInfo
            apiClient: root.apiClient
            globalContext: root.globalContext
            dataShowCore : DataShowCore{
                surfaceData: root.model.surfaceL
                apiClient: root.apiClient
                modelStore: root.model
                globalContext: root.globalContext
                toolService: root.toolService
                settings: root.settings
                style: root.style
                imageCacheService: root.imageCacheService
                binds: root.viewControl.lockControl
                       ? root.binds_base : root.binds_l
            }
            id: dataShowView_L
            SplitView.preferredWidth : root.is_half?root.viewWidth_half:root.viewWidth
        }

    }

}

