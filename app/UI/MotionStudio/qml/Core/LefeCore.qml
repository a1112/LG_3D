import QtQuick
import "../Model"

Item {

    // 数据统计
    property int userErrCoilCount:0
    property int userUnowCoilCount:0
    property int userOkCoilCount:0



    property int hovedCoilId: 0
    property bool searchViewShow: true

    property string leftMsg: ""

    property bool fliterEnable: false    // 对 list 界面 进行 筛选
    onFliterEnableChanged: {
        flushFliter()
    }

    property ListModel fliterListModel: ListModel{}

    Timer {
        id: filterRefreshTimer
        interval: 120
        repeat: false
        onTriggered: {
            if (fliterEnable) {
                flushModel()
            }
        }
    }

    Connections {
        target: coreModel.currentCoilListModel
        function onCountChanged() {
            filterRefreshTimer.restart()
        }
        function onDataChanged() {
            filterRefreshTimer.restart()
        }
    }

    property var fliterDict:{return {}}
    property var tempCoilModel :  CoilModel{}
    function flushModel(){
        fliterListModel.clear()
        tool.for_list_model(coreModel.currentCoilListModel,(item_data)=>{
                                let defects = item_data.childrenCoilDefect || item_data.defects || []
                                tempCoilModel._getDefectNameList_(defects).some((name)=>{
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
        // 缺陷是否显示
        let sharedName = global.defectClassProperty.shared_defect_name(defectName)
        if (sharedName in fliterDict){
            return fliterDict[sharedName]
        }
        return false
    }

    function indexForCoilId(model, coilId) {
        if (!model || !coilId) {
            return -1
        }
        for (let index = 0; index < model.count; index++) {
            let item = model.get(index)
            let itemId = item ? Number(item.Id || item.SecondaryCoilId) : 0
            if (itemId === Number(coilId)) {
                return index
            }
        }
        return -1
    }

    function visibleIndexForCoilId(coilId) {
        let model = fliterEnable ? fliterListModel : coreModel.currentCoilListModel
        return indexForCoilId(model, coilId)
    }

    function selectVisibleIndex(index) {
        let visibleModel = fliterEnable ? fliterListModel : coreModel.currentCoilListModel
        if (!visibleModel || index < 0 || index >= visibleModel.count) {
            return false
        }
        let item = visibleModel.get(index)
        let coilId = item ? Number(item.Id || item.SecondaryCoilId) : 0
        let sourceIndex = fliterEnable
                ? indexForCoilId(coreModel.currentCoilListModel, coilId)
                : index
        if (sourceIndex < 0) {
            return false
        }
        core.setCoilIndex(sourceIndex)
        return true
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

    property  CoilModel hovedCoilModel :CoilModel{}

    // ========== 悬停详情数据缓存 ==========
    property var detailCache: ({})  // 缓存已获取的详情数据
    property var detailCacheOrder: []
    property int detailCacheMax: 80
    property var pendingDetailRequests: ({})

    function cachedDetail(coilId) {
        let key = String(coilId)
        let cached = detailCache[key]
        if (cached === undefined) {
            return null
        }
        let order = detailCacheOrder
        let position = order.indexOf(key)
        if (position >= 0) {
            order.splice(position, 1)
        }
        order.push(key)
        detailCacheOrder = order
        return cached
    }

    onHovedIndexChanged: {
        if (hovedIndex < 0) return

        let sourceModel = fliterEnable ? fliterListModel : coreModel.currentCoilListModel
        let p = sourceModel.get(hovedIndex)
        if (!p) return

        let coilId = p.Id || p.SecondaryCoilId
        hovedCoilId = coilId

        // 检查缓存
        let cached = cachedDetail(coilId)
        if (cached) {
            // 使用缓存数据
            hovelCoilData = cached
            hovedCoilModel.init(cached)
            return
        }

        // 先用摘要数据显示
        hovelCoilData = p
        hovedCoilModel.init(p)

        // 异步获取完整详情
        fetchCoilDetail(coilId)
    }

    // ========== 获取卷材详情 ==========
    function cacheDetail(coilId, data) {
        let key = String(coilId)
        let cache = detailCache
        let order = detailCacheOrder
        if (cache[key] === undefined) {
            order.push(key)
        }
        cache[key] = data
        while (order.length > detailCacheMax) {
            let expiredKey = order.shift()
            delete cache[expiredKey]
        }
        detailCache = cache
        detailCacheOrder = order
    }

    function parseDetailResponse(data) {
        if (typeof data !== "string") {
            return data
        }
        try {
            return JSON.parse(data)
        } catch (error) {
            console.warn("coil detail parse failed:", error)
            return null
        }
    }

    function fetchCoilDetail(coilId) {
        let requestKey = String(coilId)
        if (!coilId || pendingDetailRequests[requestKey]) {
            return
        }

        pendingDetailRequests[requestKey] = app.api.getCoilDetail(coilId,
            function success(data) {
                delete pendingDetailRequests[requestKey]
                let parsed = parseDetailResponse(data)
                if (parsed && (parsed.Id || parsed.SecondaryCoilId)) {
                    let cached = JSON.parse(JSON.stringify(parsed))
                    cacheDetail(coilId, cached)

                    // 如果当前还是悬停在这个卷材上，更新显示
                    if (Number(hovedCoilId) === Number(coilId)) {
                        hovelCoilData = cached
                        hovedCoilModel.init(cached)
                    }
                }
            },
            function error(err) {
                delete pendingDetailRequests[requestKey]
                console.warn("coil detail request failed:", err)
            }
        )
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
