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

    readonly property int top_ : currentListModel.count? currentListModel.get(0).coilId:0
    readonly property int end_ : currentListModel.count? currentListModel.get(currentListModel.count-1).coilId:0

    property int currentListStartIndex: min(top_, end_)
    property int currentListEndIndex: max(top_, end_)

    // 缺陷列表
    property ListModel defectsModel: ListModel{
        // 全部缺陷
    }

}
