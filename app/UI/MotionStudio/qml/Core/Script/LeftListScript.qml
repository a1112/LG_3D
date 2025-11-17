import QtQuick

Item {

    property var listModel:coreModel.currentCoilListModel
    onListModelChanged:setCheckCoilCount()
    property int listModelCount:coreModel.currentCoilListModel.count
    onListModelCountChanged:setCheckCoilCount()


    function setCheckCoilCount(){
        leftCore.userErrCoilCount = 0
        leftCore.userUnowCoilCount = 0
        leftCore.userOkCoilCount = 0

        tool.for_list_model(listModel,
                            (item)=>{
                                let childrenCoilCheck = item["childrenCoilCheck"]
                                if (childrenCoilCheck.count<1){
                                    leftCore.userUnowCoilCount+=1
                                }

                                tool.for_list_model(childrenCoilCheck,
                                                    (childrenCoilCheckItem)=>{
                                                        let status = childrenCoilCheckItem["status"]
                                                        if (status == 0){
                                                            leftCore.userUnowCoilCount += 1
                                                        }
                                                        if (status == 1){
                                                            leftCore.userOkCoilCount +=1

                                                        }
                                                        else{
                                                            leftCore.userErrCoilCount+=1
                                                        }
                                                    }
                                                    )
                            })

    }

}
