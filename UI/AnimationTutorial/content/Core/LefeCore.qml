import QtQuick
import "../Model"

Item {
    property int hovedCoilId: 0
    property bool searchViewShow: true

    property string leftMsg:""

    property bool fliterEnable:false    // 对 list 界面 进行 筛选
    onFliterEnableChanged:{
        flushFliter()
    }

    property ListModel fliterListModel: ListModel{}


    property var fliterDict:{return {}}
    property var tempCoilModel :  CoilModel{}
    function flushModel(){
        fliterListModel.clear()
        tool.for_list_model(coreModel.currentCoilListModel,(item_data)=>{
                                tempCoilModel._getDefectNameList_(item_data).some((name)=>{
                                                                    if(isShowDefect(name)){
                                                                            fliterListModel.append(item_data)
                                                                            return true//throw new Error('End Loop'); // 抛出异常终止循环
                                                                        }
                                                                    })
                            })

    }

    function flushFliter(){
    flushFliterDict()
    flushModel()
    }

    function flushFliterDict(){
        let temp = fliterDict
        fliterDict={}
        fliterDict=temp
    }
    function setLiewViewFilterClass(defectClass,show){
        // 设置 列表 筛选的显示类别
        fliterDict[defectClass] = show
        flushFliter()
    }

    function isShowDefect(defectName){
        return fliterDict[defectName]
    }


    onSearchViewShowChanged: {
        // 显示隐藏 查询界面
        if (! searchViewShow){
            coreModel.currentCoilListIndex = 0
        }
    }
    property var hovelCoilData:{return {}}
    property int searchPageIndex   : 0
    onHovedCoilIdChanged: {

        preSourceModelS.setProperty(0,"image_source",coreModel.surfaceS.getSource(hovedCoilId,"GRAY",true))
        preSourceModelS.setProperty(1,"image_source",coreModel.surfaceS.getSource(hovedCoilId,"JET",true))
        preSourceModelL.setProperty(0,"image_source",coreModel.surfaceL.getSource(hovedCoilId,"GRAY",true))
        preSourceModelL.setProperty(1,"image_source",coreModel.surfaceL.getSource(hovedCoilId,"JET",true))
    }

    property int hovedIndex:-1

    property  CoilModel hovedCoilModel

    onHovedIndexChanged: {
        let p = coreModel.currentCoilListModel.get(hovedIndex)
        hovelCoilData=p
        hovedCoilId = p.SecondaryCoilId
    }

    property bool isHoved:false
    property point hoverPoint: Qt.point(0,0)

    property ListModel preSourceModelS: ListModel{
        ListElement{
            key:"GRAY"
            image_source:""
        }
        ListElement{
            key:"JET"
            image_source:""
        }

    }
    property ListModel preSourceModelL: ListModel{
        ListElement{
            key:"GRAY"
            image_source:""
        }
        ListElement{
            key:"JET"
            image_source:""
        }

    }

}
