import QtQuick
import "Export"
import "Connect"
import "DefectClass"
import "ToolsMenu"
import "ApiListPop"
import "MsgPop"
import "Backup"
import "ReDetection"
import "GlobalAlarm"
import "../SettingPage"
import "../Style"
import "ServerMange"
import "ListValueChange"
import "HelpPop"
import "AlgTest"
import "ClipSetting"
import "../Pages/LeftPage/DataList/DataListMenu"
Item {
    ConnectDialog{ id:connectDialog }//连接 菜單
    function popupConnectDialog(){connectDialog.open()}
    ExportView{id:exportView}   //导出菜单
    function popupExportView(){exportView.popup()}
    ToolsMenuView{id:toolsMenu} // 右侧功能菜单
    function popupToolsMenuView(){toolsMenu.popup()}
    DefectClassPop{id:defectClassPop}// 缺陷列表
    function popupDefectClassPop(){defectClassPop.popup()}
    ApiListPopView{id:apiListPop} // API 调用记录表
    function popupApiList(){apiListPop.popup()}
    MsgPopView{id:msg_popup}    // 詳細信息
    function popupMsgPopView(){msg_popup.popup()}
    SettingPageView{id:coreSetting_view}    // 设置界面
    function openSettingPageView(){coreSetting_view.open()}
    StyleMenu{id:menuStyle} // 主题菜单
    function popupStyleMenu(){menuStyle.popup()}
    ClipSettingView{id:clipSettingView}
    function popupClipSettingView(){clipSettingView.openDialog()}
    BackupDataView{id:backupDataView}   // 数据备份
    function popupBackupDataView(){backupDataView.popup()}
    ReDetectionView{id:reDetectonView}  //重新识别
    function popupReDetectionView(fromId, toId){
        if (fromId !== undefined && toId !== undefined){
            reDetectonView.setRange(fromId, toId)
        }else{
            reDetectonView.useAutoRange = true
        }
        reDetectonView.popup()
    }
    GlobalAlarmView{id:globalAlarmView} // 设备报警
    function popupGlobalAlarmView(){globalAlarmView.popup()}
    ServerMangeView{id:serverMangeView}
    function popupServerMangeView(){serverMangeView.popup()}
    ListValueChangeView{id:listValueChangeView} // 列表数值变化取消
    function popupListValueChangeView(){listValueChangeView.popup()}
    DataListItemMenu{id:lefeListMemu} // 左侧列表
    function popupDataListItemMenu(coilModel){
        lefeListMemu.coilModel = coilModel
        lefeListMemu.popup()}
    HelpPopView{id:helpMenu}
    function popupHelpView(){helpMenu.popup()}
    AlgTestDialog{id:algTestDialog}
    function popupAlgTestDialog(){algTestDialog.openDialog()}
}
