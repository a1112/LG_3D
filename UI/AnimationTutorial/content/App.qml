import QtCore
import QtQuick
import QtQuick.Controls

import QtQuick.Controls.Material
import "./Api"
import "./Core"

import "Pages/AlarmPage"
import "Dialogs"
import "./Style/Adaptive"

AppBase {
    id:app
    visible: true
    visibility:control.visibility
    Material.theme: coreStyle.theme
    width: global.screenConfig.width-100
    height: global.screenConfig.height-100
    title: "LG3D "
    Material.accent: coreStyle.accentColor
    CoreAction{}
    property CppInterFace cpp:CppInterFace{}



    MainLayout{ //          入口,界面构成 <-
        anchors.fill: parent
    }

    property CoreAlarmInfo coreAlarmInfo : CoreAlarmInfo{}  // 全局的报警信息
    property Api api: Api{}     //    服务器 接口访问
    property Global global:Global{}  // 全局功能
    property Dialogs dialogs: Dialogs{} // 全局 弹窗
    property Core core: Core{}          // 核心
    property Tool tool: Tool{}          // 功能
    property CoreModel coreModel:CoreModel{}// 全局模型
    property Init init:Init{}               // 初始化
    property CoreStyle coreStyle: CoreStyle{}   // 样式
    property CoreTimer coreTimer:CoreTimer{}     // 定时器
    property CoreSetting coreSetting: CoreSetting{}// 设置
    property ImageCache imageCache: ImageCache{} // 缓冲
    property LefeCore leftCore: LefeCore{}  //列表全局
    property Control control: Control{}
    property Auth auth: Auth{}
    property CoreSignal coreSignal :CoreSignal{}
    property CoreState coreState: CoreState{}
    readonly property AdaptiveViewBase adaptive : coreStyle.currentAdaptive

    property CoreControl coreControl: CoreControl{}

    property Script autoScript:Script{}
    // Junp{}
    property AppCore app_core : AppCore{}

}


