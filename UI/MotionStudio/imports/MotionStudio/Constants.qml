pragma Singleton
import QtQuick 6.3
import QtQuick.Studio.Application
import QtQuick.Window
QtObject {
    readonly property int width: Screen.width*0.8
    readonly property int height: Screen.height*0.8

    property string app_title: "热扎1580钢卷端面检测系统"

    property string titleText: Constants.currentViewShowModel
                === Constants.ViewShowModel.ModelsShowModel?
        "模型显示":"3D检测"

    property string relativeFontDirectory: "fonts"

    /* Edit this comment to add your custom font */
    readonly property font font: Qt.font({
                                             family: Qt.application.font.family,
                                             pixelSize: Qt.application.font.pixelSize
                                         })
    readonly property font largeFont: Qt.font({
                                                  family: Qt.application.font.family,
                                                  pixelSize: Qt.application.font.pixelSize * 1.6
                                              })

    readonly property color backgroundColor: "#c2c2c2"
    property string backgroundImage: "images/background-1.png"
    property string iconImage: "images/USTB.png"


    property StudioApplication application: StudioApplication {
        fontPath: Qt.resolvedUrl("../../content/" + relativeFontDirectory)
    }


    enum ViewShowModel{
        ModelsShowModel=0,  //  模型显示
        DefectShowModel=1    //  缺陷显示主题
    }
    property int currentViewShowModel: Constants.ViewShowModel.ModelsShowModel


    function changeViewModel(){
        // 改变 界面 显示模式
        if (currentViewShowModel===Constants.ViewShowModel.ModelsShowModel)
        {
        currentViewShowModel=Constants.ViewShowModel.DefectShowModel
        }
        else{
        currentViewShowModel=Constants.ViewShowModel.ModelsShowModel

        }
    }

    property ListModel titleList: ListModel{
            ListElement{
                title:"历史记录"
            }
            ListElement{
                title:"报警管理"
            }
            ListElement{
                title:"样本管理"
            }

    }
    property int currentViewIndex: 0

}
