import QtQuick 2.15

Item {
    property int init_num: 200



    function initCoilByData(coilData){
        coreModel.coilListModel.clear()
        let data={
        "coilList":coilData
        }
        // coreModel.updateData(data)
        for(var i=0;i<coilData.length;i++){
            var coil = coilData[i]
            coreModel.coilListModel.insert(0,coil)
        }
    }


    function initApp(data){
        coreModel.errorMap = data.ErrorMap
        coreModel.rendererList = data.RendererList
        coreModel.colorMaps = data.ColorMaps
        coreModel.saveImageType = data.SaveImageType
        coreModel.previewSize = data.PreviewSize
        coreModel.surfaceS.initData(data.surfaceS)
        coreModel.surfaceL.initData(data.surfaceL)
    }

    function flushDefectDict(){
        api.getDefectDict((result)=>{
                        initCoilByData(JSON.parse(result))
                        },(error)=>{
                            console.log("error")
                        }
                    )
    }


    function flushList(){
        coreModel.coilListModel.clear()
        api.getDataFlush(0,(result)=>{
            initApp(JSON.parse(result))
        },(error)=>{
            console.log("error")
        })
        api.getCoilList(init_num,(result)=>{
                        initCoilByData(JSON.parse(result))
                        },(error)=>{
                            console.log("error")
                        }
                    )
    }

    Component.onCompleted: {
        console.log("app init")
                flushDefectDict()
                flushList()
    }
}
