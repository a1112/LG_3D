import QtQuick

Item {
    property int init_num: 200

    function initDefectDict(defectDictData){
        // 初始化 缺陷图谱
        global.defectClassProperty.setDefectDict(defectDictData)
    }

    function initCoilByData(coilData){
        // 初始化 卷 数据
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
                        initDefectDict(JSON.parse(result))
                        },(error)=>{
                            console.log("error")
                        }
                    )
    }


    function flushList(){
        api.getInfo((result)=>{
            initApp(JSON.parse(result))
        },(error)=>{
            console.log("error")
        })
        coreModel.coilListModel.clear()
        api.getCoilList(init_num,(result)=>{
                        initCoilByData(JSON.parse(result))
                        },(error)=>{
                            console.log("error")
                        }
                    )
    }
}
