import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Windows

import QtQuick.Controls.Material
import "./Api"
import "./Core"
import "PopupView"
import "Pages/AlarmPage"
import "Dialogs"
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
    property Global global:Global{}
    property Dialogs dialogs: Dialogs{}
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

    PopManagement{
            id:popManage
        }
}


