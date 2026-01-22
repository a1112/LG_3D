import QtQuick

Item {
    property int init_num: 150
    // CoreInfo 中路径是否已初始化（避免帮助里路径文本频繁刷新）
    property bool coreInfoPathLoaded: false
    // 列表加载状态标志，防止并发修改
    property bool isListLoading: false

    function initDefectDict(defectDictData){
        // 初始化 缺陷图谱
        global.defectClassProperty.setDefectDict(defectDictData)
    }

    function initCoilByData(coilData){
        // 初始化
        // 初始化 卷 数据
        coreModel.coilListModel.clear()
        let data={
            "coilList":coilData
        }
        // API 返回的数据已经是按 ID 倒序排列，直接 append 即可
        for(var i=0;i<coilData.length;i++){
            var coil = coilData[i]
            coreModel.coilListModel.append(coil)
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

        // 全局路径信息填充到 app.coreInfo
        try {
            if (app && app.coreInfo) {
                var s = data.surfaceS
                var l = data.surfaceL
                app.coreInfo.saveImageFolderS = s && s.saveFolder ? s.saveFolder : ""
                app.coreInfo.saveImageFolderL = l && l.saveFolder ? l.saveFolder : ""

                function joinSources(surface) {
                    if (!surface || !surface.folderList)
                        return ""
                    var res = []
                    surface.folderList.forEach(function (item) {
                        if (item && item.source)
                            res.push(item.source)
                    })
                    return res.join("\n")
                }

                app.coreInfo.originalImageFolderS = joinSources(s)
                app.coreInfo.originalImageFolderL = joinSources(l)
            }
        } catch(e) {
            console.log("CoreInfo initApp error:", e)
        }
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

        // 运行环境信息
        api.getRuntimeInfo((result)=>{
            try{
                var data = JSON.parse(result)
                if (app && app.coreInfo){
                    app.coreInfo.pythonVersion = data.python_version || ""
                    app.coreInfo.cacheMode = data.cache_mode || ""
                    app.coreInfo.cpuModel = data.cpu_model || ""
                    if (data.gpus && data.gpus.length){
                        app.coreInfo.gpuModels = data.gpus.join("\n")
                    }else{
                        app.coreInfo.gpuModels = ""
                    }
                }
            }catch(e){
                console.log("runtime_info parse error", e)
            }
        },(error)=>{
            console.log("runtime_info error", error)
        })

        // 数据库信息
        api.getDatabaseInfo((result)=>{
            try{
                var data = JSON.parse(result)
                if (app && app.coreInfo){
                    app.coreInfo.databaseUrl = data.url || ""
                }
            }catch(e){
                console.log("database_info parse error", e)
            }
        },(error)=>{
            console.log("database_info error", error)
        })

        // 服务版本
        api.getServerVersion((result)=>{
            try{
                if (app && app.coreInfo){
                    app.coreInfo.serverVersion = String(result)
                }
            }catch(e){
                console.log("version parse error", e)
            }
        },(error)=>{
            console.log("version error", error)
        })

        coreModel.coilListModel.clear()//实时数据

        // 添加加载状态保护，防止并发
        if (isListLoading) {
            console.log("List is already loading, skipping flushList")
            return
        }
        isListLoading = true

        api.getCoilList(init_num, (result)=>{
                             console.log("init_num")
                        initCoilByData(JSON.parse(result))
                        isListLoading = false  // 完成后重置状态
                        },(error)=>{
                            console.log("error")
                            isListLoading = false  // 错误时也要重置状态
                        }
                    )
        core.setCoilIndex(0)

    }
}
