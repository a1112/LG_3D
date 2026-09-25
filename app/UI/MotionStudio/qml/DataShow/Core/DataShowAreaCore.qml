import QtQuick
import "../../Model"
Item {
    id: root

    required property var surfaceData
    required property var apiClient
    required property var modelStore
    required property var globalContext
    required property var settings
    required property var imageCacheService
    required property var defectController
    property string key: "AREA"

    property int _lastPreheatCoilId: -1
    property int _preheatRange: 2

    function _findCoilIndex(model, coilId) {
        if (!model || model.count === undefined) {
            return -1
        }
        for (let i = 0; i < model.count; i++) {
            let item = model.get(i)
            if (item && item.Id === coilId) {
                return i
            }
        }
        return -1
    }

    function _collectNeighborIds(model, index, range) {
        let ids = []
        if (!model || model.count === undefined || index < 0) {
            return ids
        }
        let start = Math.max(0, index - range)
        let end = Math.min(model.count - 1, index + range)
        for (let i = start; i <= end; i++) {
            if (i === index) {
                continue
            }
            let item = model.get(i)
            if (item && item.Id !== undefined) {
                ids.push(item.Id)
            }
        }
        return ids
    }

    function _preheatAreaForKey(key, coilId) {
        if (!coilId) {
            return
        }
        let areaUrl = root.apiClient.getFileSource(
                    key, coilId, root.surfaceData.areaViewKey, false)
        root.apiClient.ajax.get(root.appendQuery(areaUrl, "count=0"),
                                function(){}, function(){})
        root.imageCacheService.pushCache(root.apiClient.getFileSource(
                                             key, coilId,
                                             root.surfaceData.areaViewKey,
                                             true))
    }

    function appendQuery(url, query) {
        if (!url || url.length === 0) {
            return ""
        }
        return url + (url.indexOf("?") >= 0 ? "&" : "?") + query
    }

    function preheatAreaAround() {
        if (!surfaceData || !surfaceData.coilId) {
            return
        }
        if (_lastPreheatCoilId === surfaceData.coilId) {
            return
        }
        _lastPreheatCoilId = surfaceData.coilId
        let model = root.modelStore.currentCoilListModel
        let index = _findCoilIndex(model, surfaceData.coilId)
        let neighborIds = _collectNeighborIds(model, index, _preheatRange)
        for (let i = 0; i < neighborIds.length; i++) {
            let coilId = neighborIds[i]
            _preheatAreaForKey("S", coilId)
            _preheatAreaForKey("L", coilId)
        }
    }
    function flush(){
        surfaceData.error_visible=false
        if (surfaceData.coilId > 0 && surfaceData.area_source === "") {
            surfaceData.refreshAreaSource()
        }
        // 延迟加载缺陷数据，优先保证图像加载
        defectLoadTimer.restart()
    }

    Timer {
        id: defectLoadTimer
        interval: 800  // 比其他数据再晚一些加载
        onTriggered: root.defectController.flushDefect()
    }
      // 鍥炬爣鐨勬樉绀烘柟寮?
    property int chartShowType: 0



    readonly property int coilId: surfaceData.coilId
    readonly property string currentViewKey:surfaceData.currentViewKey
    property CoilModel currentCoilModel: surfaceData.currentCoilModel
    onCoilIdChanged: {
        flush()
    }

    property Flickable flick

    function defect_show(defectName) {
        if (!defectName) {
            return false
        }
        let sharedName = root.globalContext.defectClassProperty.shared_defect_name(
                    defectName)
        return root.globalContext.defectClassProperty.defectDictAll[sharedName]
                ?? false
    }

    readonly property bool hasAreaDecision:
        root.modelStore
        && root.modelStore.hasDataCoilId === root.surfaceData.coilId
        && root.modelStore.has_data !== null
        && root.modelStore.has_data !== undefined
    property int areaCacheVersion: 0
    property bool recacheInProgress: false
    property string lastRecacheMessage: ""
    readonly property string areaBaseSource: (!hasAreaDecision || surfaceData.hasViewData(surfaceData.areaViewKey)) ? surfaceData.area_source : ""
    property string source: areaCacheVersion > 0 ? appendQuery(areaBaseSource, "areaCacheVersion=" + areaCacheVersion) : areaBaseSource
    property string pre_source: surfaceData.getSouceByKey(surfaceData.areaViewKey, true)

    function resetImageStateForSource() {
        sourceWidth = 0
        sourceHeight = 0
        canvasScale = 1.0
        if (flick) {
            flick.contentX = 0
            flick.contentY = 0
        }
    }

    onSourceChanged: {
        resetImageStateForSource()
    }

    function recacheAreaTiles() {
        if (recacheInProgress || !surfaceData || surfaceData.coilId <= 0 || !surfaceData.key) {
            return
        }
        recacheInProgress = true
        lastRecacheMessage = "rebuilding"
        root.apiClient.recacheAreaTiles(surfaceData.key,
                             surfaceData.coilId,
                             surfaceData.areaViewKey,
                             function(result) {
                                 recacheInProgress = false
                                 lastRecacheMessage = result
                                 if (root.settings.useRustImageServer) {
                                     root.apiClient.clearRustImageCache(function() {
                                         console.log("Rust image cache cleared")
                                         refreshAreaTilesAfterRecache()
                                     }, function(error, status) {
                                         console.log("Rust image cache clear failed:", status, error)
                                         refreshAreaTilesAfterRecache()
                                     })
                                 } else {
                                     refreshAreaTilesAfterRecache()
                                 }
                                 console.log("AREA tile cache rebuilt:", result)
                             },
                             function(error, status) {
                                 recacheInProgress = false
                                 lastRecacheMessage = "failed: " + status + " " + error
                                 console.log("AREA tile cache rebuild failed:", status, error)
                             })
    }

    function refreshAreaTilesAfterRecache() {
        areaCacheVersion += 1
        surfaceData.refreshAreaSource()
        resetImageStateForSource()
    }

    // 琢诲竷鏁版嵁
    property real canvasScale: 1.0 // 鐢诲竷缂╂斁姣斾緥锛屽垵濮嬪€璁句负 1.0锛屽悗缁皢鑷姭璁★級

    function setToMaxScale(){
        canvasScale = maxScale
    }
    function setToMinScale(){
        canvasScale = minScale
    }


    onCanvasScaleChanged: {
        if(canvasScale<minScale){
            canvasScale = minScale
        }
    }

    property int canvasWidth: flick ? flick.width || 0 : 0
    property int canvasHeight: flick ? flick.height || 0 : 0
    readonly property real canvasWidthAspectRatio: canvasContentWidth > 0 ? canvasWidth/canvasContentWidth : 0
    readonly property real canvasHeightAspectRatio: canvasContentHeight > 0 ? canvasHeight/canvasContentHeight : 0

    property int showLeft: flick && canvasScale > 0 ? (flick.contentX || 0)/canvasScale : 0
    property int showTop: flick && canvasScale > 0 ? (flick.contentY || 0)/canvasScale : 0
    property int showRight: flick && canvasScale > 0 ? ((flick.contentX || 0)+(flick.width || 0))/canvasScale : 0
    property int showBottom: flick && canvasScale > 0 ? ((flick.contentY || 0)+(flick.height || 0))/canvasScale : 0

    property real max_mm: sourceWidth*surfaceData.scan3dScaleX
    property real showLeftmm: (showLeft - (surfaceData.inner_circle_centre && surfaceData.inner_circle_centre.length > 0 ? surfaceData.inner_circle_centre[0] : 0)) * surfaceData.scan3dScaleX
    property real showRightmm: (showRight - (surfaceData.inner_circle_centre && surfaceData.inner_circle_centre.length > 0 ? surfaceData.inner_circle_centre[0] : 0)) * surfaceData.scan3dScaleX

    readonly property int canvasContentX: flick ? flick.contentX || 0 : 0
    readonly property int canvasContentY: flick ? flick.contentY || 0 : 0
    readonly property real canvasContentXaspectRatio: canvasContentX/canvasContentWidth
    readonly property real canvasContentYaspectRatio: canvasContentY/canvasContentHeight

    readonly property int canvasContentWidth: sourceWidth * canvasScale
    readonly property int canvasContentHeight: sourceHeight * canvasScale

    // 鍥惧儚鏁版嵁
    property int sourceWidth: 0
    property int sourceHeight: 0

    // 防止除零错误
    property real aspectRatio: (sourceHeight > 0) ? (sourceWidth/sourceHeight) : 1.0


    property bool viewRendererListView: false
    property bool viewRendererMaxMinValue: false
    property bool viewDefectListView: true

    property int checkRendererIndex:0

    // 防止除零错误，当尺寸未知时返回 1.0
    property real minScale: (sourceWidth > 0 && sourceHeight > 0 && canvasWidth > 0 && canvasHeight > 0) ?
        Math.min(canvasWidth/sourceWidth, canvasHeight/sourceHeight) : 1.0
    property real maxScale: 1 // 鏈€澶х缉鏀炬瘮渚?
    property point scaleTempPoint: Qt.point(0,0)

    // ========== 当 minScale 变化且 canvasScale 为初始值时，自动设置缩放 ==========
    onMinScaleChanged: {
        // 只有当 minScale 有效（<1，说明图像大于视口）且 canvasScale 未被用户手动设置时才自动更新
        if (minScale < 1.0 && canvasScale === 1.0) {
            canvasScale = minScale
        }
    }

    function getAspectRatioByPoint(point){
        if (canvasContentWidth <= 0 || canvasContentHeight <= 0) {
            return Qt.point(0, 0)
        }
        let asX =(point.x+canvasContentX)/canvasContentWidth
        let asY =(point.y+canvasContentY)/canvasContentHeight
        return Qt.point(asX,asY)
    }

    function setFlickablebyPoint(point){
        if (!flick) {
            return
        }
        let newX = scaleTempPoint.x*canvasContentWidth
        let newY = scaleTempPoint.y*canvasContentHeight
        flick.contentX = newX-point.x
        flick.contentY = newY-point.y
    }

    function toPx(x){
        return x*canvasScale
    }
    function toMm(w){
        return canvasScale > 0 ? w/canvasScale*surfaceData.scan3dScaleX : 0
    }
    function pxto_top(px){
        return canvasScale > 0 ? parseInt(px/canvasScale) : 0
    }
    function px_to_width_mm(px){
        return px*surfaceData.scan3dScaleX
    }
    function px_to_height_mm(px){
        return px*surfaceData.scan3dScaleX
    }
    function px_to_pos_x_mm_from_centre(px){
        return (px-surfaceData.inner_circle_centre[0])*surfaceData.scan3dScaleX
    }
    function px_to_pos_y_mm_from_centre(px){
        return (px-surfaceData.inner_circle_centre[1])*surfaceData.scan3dScaleX
    }
    function pxtoPos(px){
        return (px-surfaceData.inner_circle_centre[0])*surfaceData.scan3dScaleX
    }
    property point perpendicularPoint: surfaceData.perpendicularPoint_xy(hoverdX,hoverdY)
    property int perpendicularPointX: perpendicularPoint.x
    property int perpendicularPointY: perpendicularPoint.y
    property real perpendicularPointXmm: pxtoPos(perpendicularPointX).toFixed(1)
    property real perpendicularPointYmm: pxtoPos(perpendicularPointY).toFixed(1)


    property point hoverPoint: Qt.point(0,0) // 榧犳爣鎮仠鐐?
    property int hoverdX: flick && canvasScale > 0 ? (hoverPoint.x+(flick.contentX || 0))/canvasScale : 0
    property int hoverdY: flick && canvasScale > 0 ? (hoverPoint.y+(flick.contentY || 0))/canvasScale : 0
    property real hoverdXmm: pxtoPos(hoverdX).toFixed(1)
    property real hoverdYmm: pxtoPos(hoverdY).toFixed(1)
    property real hoverdZmm : 0
    property real chartsHoverdZmm: 0

    function resetView(){
        canvasScale = minScale
        if (!flick) {
            return
        }
        flick.contentX = 0
        flick.contentY = 0
    }



    property bool txChartView: true

    property bool telescopedJointView: true // 鏄惁鏄剧ず濉斿舰

    readonly property ListModel pointDbData: surfaceData.pointDbData
    readonly property ListModel pointUserData: surfaceData.pointUserData
    property bool imageShowHovered: false

    property bool chartHovered: false


    Timer {
        id: errorDrawerTimer
        triggeredOnStart:false
        interval: 200
        running: false
        repeat: false
        onTriggered: {
            if (root.surfaceData.error_auto)
                root.errorDrawer()
        }
    }
    property var triggerErrorDrawer: surfaceData.coilId+surfaceData.scan3dScaleZ+medianZValue+tower_warning_threshold_downValue+tower_warning_threshold_upValue
    onTriggerErrorDrawerChanged: {
        errorDrawerTimer.restart()
    }

    property int medianZInt:surfaceData.medianZInt
    property int rangeZ: 20
    property real renderScale: 1
    property bool autoRender: false

    readonly property real medianZValue:surfaceData.medianZInt // #parseInt(Math.abs(medianZ/surfaceData.scan3dScaleZ))
    readonly property real medianZ: surfaceData.medianZ

    property int rangeZValue: rangeZ/surfaceData.scan3dScaleZ
    function renderDrawer()
    {
        surfaceData.source = root.apiClient.geRenderDrawerSource(surfaceData.key,
                                                      surfaceData.coilId,
                                                      renderScale.toFixed(2),
                                                      parseInt(medianZValue-rangeZValue)
                                                      ,parseInt(medianZValue+rangeZValue)
                                                      )
    }
    property int tower_warning_threshold_upValue: surfaceData.tower_warning_threshold_up/surfaceData.scan3dScaleZ
    property int tower_warning_threshold_downValue: surfaceData.tower_warning_threshold_down/surfaceData.scan3dScaleZ
    function errorDrawer()
    {
        // 检查设置中的叠加图层开关
        if (!root.settings.showErrorOverlay) {
            surfaceData.error_visible=false
            return
        }
        surfaceData.error_source = root.apiClient.geErrorDrawerSource(surfaceData.key,
                                                           surfaceData.coilId,
                                                           1,
                                                           surfaceData.tower_warning_threshold_down  // mm 值：蓝色阈值
                                                           , surfaceData.tower_warning_threshold_up     // mm 值：红色阈值
                                                           )
        surfaceData.error_visible=true
    }


    function setDefectShowView(defect){
        if (!flick || !defect) {
            return false
        }
        setToMaxScale()
        flick.contentX = Math.max(0, defect.defect_x - (flick.width - defect.defect_w) / 2)
        flick.contentY = Math.max(0, defect.defect_y - (flick.height - defect.defect_h) / 2)
        return true
    }

    // 监听从缺陷页面跳转时的待定位缺陷
    Timer {
        id: pendingDefectTimer
        interval: 500
        onTriggered: {
            if (root.modelStore.pendingDefect && root.flick
                    && root.surfaceData.isAreaRootView) {
                let pending = root.modelStore.pendingDefect
                let currentCoilId = currentCoilModel ? currentCoilModel.coilId : surfaceData.coilId
                let targetView = pending.viewMode || "AREA"
                if (targetView === "AREA"
                        && pending.surface === surfaceData.key
                        && Number(pending.coilId) === Number(currentCoilId)
                        && setDefectShowView(pending)) {
                    root.modelStore.pendingDefect = null
                }
            }
        }
    }

    Connections {
        target: root.modelStore
        function onPendingDefectChanged() {
            if (root.modelStore.pendingDefect) {
                pendingDefectTimer.restart()
            }
        }
    }


    // property View2DTool view2DTool:View2DTool{

    //     onSet_max: {
    //                    console.log("onSet_max")
    //                    setToMaxScale()
    //                    flick.contentX =defect.defect_x-(flick.width-defect.defect_w)/2
    //                    flick.contentY = defect.defect_y-(flick.height-defect.defect_h)/2
    //                }

    // }

    // ========== 初始加载：确保图像在界面打开时加载 ==========
    Component.onCompleted: {
        // 延迟检查，确保所有组件都已初始化
        initLoadTimer.restart()
    }

    Timer {
        id: initLoadTimer
        interval: 100
        onTriggered: {
            // 如果 coilId 已设置但图像未加载，触发加载
            if (root.surfaceData.coilId > 0
                    && root.surfaceData.area_source === "") {
                root.flush()
            }
        }
    }

}
