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
                        // 过滤掉 null 值
                        let cleanIt = {}
                        for (let key in it) {
                            if (it[key] !== null && it[key] !== undefined) {
                                cleanIt[key] = it[key]
                            }
                        }
                        defectDictModel.append(cleanIt)
                    })
        filterCore.resetFilterDict()
    }

    property ListModel  currentListModel: coreModel.currentCoilListModel

    readonly property int top_ : currentListModel.count? currentListModel.get(0).Id:0
    readonly property int end_ : currentListModel.count? currentListModel.get(currentListModel.count-1).Id:0

    property int currentListStartIndex: Math.min(top_, end_)
    property int currentListEndIndex: Math.max(top_, end_)

    // 缺陷列表
    property var defectsModelAll: ListModel{
        dynamicRoles:true
        // 全部缺陷
    }

    property var defectsModel: ListModel{
        dynamicRoles:true
        // 全部缺陷
    }
    function flushModel(){

        let scanIndex = 0
        defectsModel.clear()
        tool.for_list_model(defectsModelAll, (item)=>{
                                // for(scanIndex;scanIndex<defectsModel.count;scanIndex){
                                //     let it = defectsModel.get(scanIndex)
                                //     if(filterCore.itemIsShow(it)){
                                //         scanIndex++
                                //     }
                                // }
                                // if(scanIndex >= defectsModel.count){
                                //     if(1){
                                //     }
                                // }
                                if (filterCore.itemIsShow(item)){
                                        // 过滤掉 null 值
                                        let cleanItem = {}
                                        for (let key in item) {
                                            if (item[key] !== null && item[key] !== undefined) {
                                                cleanItem[key] = item[key]
                                            }
                                        }
                                        defectsModel.append(cleanItem)
                                    }

                            })
    }


    function flushModelAll(){
         defectsModelAll.clear()

        defectJson.forEach(
                    (value)=>{
                        if (value && value.data !== null) {
                            root.defectsModelAll.append(value)
                        }
                    }
                    )
        flushModel()
    }

    property string defectText: ""
    property var defectJson: defectText ? JSON.parse(defectText) : []
    onDefectJsonChanged: {

        flushModelAll()
    }
}
