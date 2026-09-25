import QtQuick

Item {
    id: root
    required property var modelStore
    required property var leftController
    required property var toolService

    property var listModel: root.modelStore.currentCoilListModel
    onListModelChanged:setCheckCoilCount()
    property int listModelCount: root.modelStore.currentCoilListModel.count
    onListModelCountChanged:setCheckCoilCount()


    function setCheckCoilCount(){
        root.leftController.userErrCoilCount = 0
        root.leftController.userUnowCoilCount = 0
        root.leftController.userOkCoilCount = 0

        root.toolService.for_list_model(root.listModel,
                            (item)=>{
                                let childrenCoilCheck = item["childrenCoilCheck"]
                                if (!childrenCoilCheck || childrenCoilCheck.count < 1){
                                    root.leftController.userUnowCoilCount += 1
                                    return
                                }

                                root.toolService.for_list_model(childrenCoilCheck,
                                                    (childrenCoilCheckItem)=>{
                                                        let status = childrenCoilCheckItem["status"]
                                                        if (status == 0){
                                                            root.leftController.userUnowCoilCount += 1
                                                        }
                                                        else if (status == 1){
                                                            root.leftController.userOkCoilCount += 1
                                                        }
                                                        else{
                                                            root.leftController.userErrCoilCount += 1
                                                        }
                                                    }
                                                    )
                            })

    }

}
