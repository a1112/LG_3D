import QtQuick

Item {
    id:root
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

    readonly property int top_ : currentListModel.count? currentListModel.get(0).Id:0
    readonly property int end_ : currentListModel.count? currentListModel.get(currentListModel.count-1).Id:0

    property int currentListStartIndex: Math.min(top_, end_)
    property int currentListEndIndex: Math.max(top_, end_)

    // 缺陷列表
    property var defectsModel: ListModel{
        dynamicRoles:true
        // 全部缺陷
    }

    function flushModel(){
         defectsModel.clear()

        defectJson.forEach(
                    (value)=>{

                        root.defectsModel.append(value)
                    }
                    )
    }

    property string defectText: ""
    property var defectJson: JSON.parse(defectText)
    onDefectJsonChanged: {

        flushModel()
    }
}
