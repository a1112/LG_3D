import QtQuick
import "../Model"

Item {
    id: root

    required property var modelStore
    required property var coreController
    required property var globalContext
    required property var toolService
    required property var apiClient

    // 数据统计
    property int userErrCoilCount:0
    property int userUnowCoilCount:0
    property int userOkCoilCount:0



    property int hovedCoilId: 0
    property bool searchViewShow: true

    property string leftMsg: ""

    property bool fliterEnable: false    // 对 list 界面 进行 筛选
    onFliterEnableChanged: {
        root.flushFliter()
    }

    property ListModel fliterListModel: ListModel{}

    Timer {
        id: filterRefreshTimer
        interval: 120
        repeat: false
        onTriggered: {
            if (root.fliterEnable) {
                root.flushModel()
            }
        }
    }

    Connections {
        target: root.modelStore.currentCoilListModel
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
        root.fliterListModel.clear()
        root.toolService.for_list_model(root.modelStore.currentCoilListModel,(item_data)=>{
                                let defects = item_data.childrenCoilDefect || item_data.defects || []
                                let defectNames = root.tempCoilModel._getDefectNameList_(defects)
                                if (defectNames.length === 0
                                        && root.isShowDefect(
                                            root.globalContext.defectClassProperty.unDefectClassItemName)) {
                                    root.fliterListModel.append(item_data)
                                    return
                                }
                                defectNames.some((name)=>{
                                                                    if(root.isShowDefect(name)){
                                                                            root.fliterListModel.append(item_data)
                                                                            return true//throw new Error('End Loop'); // 抛出异常终止循环
                                                                        }
                                                                    })
                            })

    }

    function flushFliter(){
        root.flushFliterDict()
        root.flushModel()
    }

    function flushFliterDict(){
        let temp = root.fliterDict
        root.fliterDict = {}
        root.fliterDict = temp
    }
    function setLiewViewFilterClass(defectClass,show){
        // 设置 列表 筛选的显示类别
        root.fliterDict[defectClass] = show
        root.flushFliter()
    }

    function setListViewFilterClasses(defectClasses, show) {
        for (let index = 0; index < defectClasses.length; index++) {
            root.fliterDict[defectClasses[index]] = show
        }
        root.flushFliter()
    }

    function filterClassEnabled(defectName) {
        let sharedName = root.globalContext.defectClassProperty.shared_defect_name(defectName)
        return !(sharedName in root.fliterDict) || root.fliterDict[sharedName] === true
    }

    function isShowDefect(defectName){
        // 缺陷是否显示
        return root.filterClassEnabled(defectName)
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
        let model = root.fliterEnable ? root.fliterListModel
                                      : root.modelStore.currentCoilListModel
        return root.indexForCoilId(model, coilId)
    }

    function selectVisibleIndex(index) {
        let visibleModel = root.fliterEnable ? root.fliterListModel
                                             : root.modelStore.currentCoilListModel
        if (!visibleModel || index < 0 || index >= visibleModel.count) {
            return false
        }
        let item = visibleModel.get(index)
        let coilId = item ? Number(item.Id || item.SecondaryCoilId) : 0
        let sourceIndex = root.fliterEnable
                ? root.indexForCoilId(root.modelStore.currentCoilListModel, coilId)
                : index
        if (sourceIndex < 0) {
            return false
        }
        root.coreController.setCoilIndex(sourceIndex)
        return true
    }


    onSearchViewShowChanged: {
        // 显示隐藏 查询界面
        if (!root.searchViewShow){
            root.modelStore.currentCoilListIndex = 0
        }
    }
    property var hovelCoilData:{return {}}
    property int searchPageIndex   : 0
    onHovedCoilIdChanged: {

        root.preSourceModelS.setProperty(
                    0, "image_source",
                    root.modelStore.surfaceS.getSource(root.hovedCoilId, "GRAY", true))
        root.preSourceModelS.setProperty(
                    1, "image_source",
                    root.modelStore.surfaceS.getSource(root.hovedCoilId, "JET", true))
        root.preSourceModelL.setProperty(
                    0, "image_source",
                    root.modelStore.surfaceL.getSource(root.hovedCoilId, "GRAY", true))
        root.preSourceModelL.setProperty(
                    1, "image_source",
                    root.modelStore.surfaceL.getSource(root.hovedCoilId, "JET", true))
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
        let cached = root.detailCache[key]
        if (cached === undefined) {
            return null
        }
        let order = root.detailCacheOrder
        let position = order.indexOf(key)
        if (position >= 0) {
            order.splice(position, 1)
        }
        order.push(key)
        root.detailCacheOrder = order
        return cached
    }

    onHovedIndexChanged: {
        if (root.hovedIndex < 0) return

        let sourceModel = root.fliterEnable ? root.fliterListModel
                                            : root.modelStore.currentCoilListModel
        let p = sourceModel.get(root.hovedIndex)
        if (!p) return

        let coilId = p.Id || p.SecondaryCoilId
        root.hovedCoilId = coilId

        // 检查缓存
        let cached = root.cachedDetail(coilId)
        if (cached) {
            // 使用缓存数据
            root.hovelCoilData = cached
            root.hovedCoilModel.init(cached)
            return
        }

        // 先用摘要数据显示
        root.hovelCoilData = p
        root.hovedCoilModel.init(p)

        // 异步获取完整详情
        root.fetchCoilDetail(coilId)
    }

    // ========== 获取卷材详情 ==========
    function cacheDetail(coilId, data) {
        let key = String(coilId)
        let cache = root.detailCache
        let order = root.detailCacheOrder
        if (cache[key] === undefined) {
            order.push(key)
        }
        cache[key] = data
        while (order.length > root.detailCacheMax) {
            let expiredKey = order.shift()
            delete cache[expiredKey]
        }
        root.detailCache = cache
        root.detailCacheOrder = order
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
        if (!coilId || root.pendingDetailRequests[requestKey]) {
            return
        }

        root.pendingDetailRequests[requestKey] = root.apiClient.getCoilDetail(coilId,
            function success(data) {
                delete root.pendingDetailRequests[requestKey]
                let parsed = root.parseDetailResponse(data)
                if (parsed && (parsed.Id || parsed.SecondaryCoilId)) {
                    let cached = JSON.parse(JSON.stringify(parsed))
                    root.cacheDetail(coilId, cached)

                    // 如果当前还是悬停在这个卷材上，更新显示
                    if (Number(root.hovedCoilId) === Number(coilId)) {
                        root.hovelCoilData = cached
                        root.hovedCoilModel.init(cached)
                    }
                }
            },
            function error(err) {
                delete root.pendingDetailRequests[requestKey]
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
