import QtQuick

Item {

    property ListModel globDefectDictModel: global.defectClassProperty.defectDictModel
    property int globDefectDictModelCount:globDefectDictModel.count
    onGlobDefectDictModelCountChanged: {
        initDefectDictModel()
    }

    property ListModel defectDictModel:ListModel{}

    function initDefectDictModel(){
        defectDictModel.clear()
        tool.for_list_model(
                    globDefectDictModel,(item)=>{
                                let  it =  globalDefectClassItemModel.itemTodict(item)
                                defectDictModel.append(it)
                            })
    }

    property ListModel  currentListModel: coreModel.currentCoilListModel

    // 缺陷列表
    property ListModel defectsModel: ListModel{
        //全部缺陷
    }

}
