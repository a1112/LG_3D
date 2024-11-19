import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Windows

import QtQuick.Controls.Material
import "./Api"
import "./Core"
import "PopupView/MsgPop"
import "PopupView/Export"
import "PopupView/Backup"
import "PopupView/ReDetection"
import "PopupView/ApiListPop"
import "PopupView/GlobalAlarm"
import "PopupView/ToolsMenu"
import "Tool/Graphs"
import "SettingPage"
import "Style"
import "Pages/AlarmPage"

ApplicationWindow {
    id:app
    visible: true



    visibility:control.visibility
    x:50;y:50
    Material.theme: coreStyle.theme
    width: Screen.width-100
    height: Screen.height-100
    title: "LG3D "
    Material.accent: coreStyle.accentColor
    CoreAction{}

    property CppInterFace cpp:CppInterFace{}

    MainLayout{ //          入口 <-
        anchors.fill: parent
    }
    property CoreAlarmInfo coreAlarmInfo : CoreAlarmInfo{}

    property Api api: Api{}
    property Core core: Core{}
    property Tool tool: Tool{}
    property CoreModel coreModel:CoreModel{}
    property Init init:Init{}
    property CoreStyle coreStyle: CoreStyle{}
    property CoreTimer coreTimer:CoreTimer{}
    property CoreSetting coreSetting: CoreSetting{}
    property ImageCache imageCache: ImageCache{}
    property LefeCore leftCore: LefeCore{}
    property Control control: Control{}
    property Auth auth: Auth{}
    function showDefectInfo(){
        msg_popup.popup()
    }
    function openSettingView(){
        coreSetting_view.open()
    }


    MsgPopView{id:msg_popup}
    SettingPageView{id:coreSetting_view}
    ConnectDialog{//连接设置
        id:connectDialog
    }
    StyleMenu{
        id:menuStyle
    }
    ExportView{
        id:exportView
    }
    BackupDataView{
        id:backupDataView
    }
    ReDetectionView{
        id:reDetectonView
    }
    GlobalAlarmView{
        id:globalAlarmView
    }
    ApiListPopView{
        id:apiListPop
    }
    ToolsMenuView{
        id:toolsMenu
    }

    ToolGraphs{ // 图表格弹窗
        id:toolGraths
    }
}


