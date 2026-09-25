import QtQuick
import "../../Model"
import "../JsonUtils.js" as JsonUtils
Item {
    id: root
    required property var modelStore
    required property var apiClient
    required property var settings
    required property var coreController
    required property var imageCacheService
    required property var scriptLauncher

    property int rootViewIndex: 0
    readonly property bool is2DrootView : rootViewIndex == 0
    readonly property bool is3DrootView : rootViewIndex == 1
    readonly property bool isAreaRootView : rootViewIndex == 2

    property  PointTool pointTool  : PointTool{}     //  处理数据点
    property CircleTool circleTool : CircleTool{}   //  处理 圆相关数据
    function rootViewto2D(){
        rootViewIndex = 0
    }

    function rootViewto3D(){
        rootViewIndex = 1
    }
    function rootViewtoArea(){
        refreshAreaSource()
        rootViewIndex = 2
    }

    onRootViewIndexChanged: {
        if (rootViewIndex == 2) {
            refreshAreaSource()
        }
    }

    readonly property real defaultScan3dScaleZ: 0.016229506582021713
    readonly property real defaultScan3dScaleX: 0.33693358302116394
    readonly property real defaultScan3dScaleY: 0.33693358302116394
    property real scan3dScaleZ: defaultScan3dScaleZ
    property real scan3dScaleX: defaultScan3dScaleX
    property real scan3dScaleY: defaultScan3dScaleY
    property real scan3dCoordinateOffsetZ: 0
    property real medianZInt: 0
    property real medianZ: 0.0
    property bool coilInfoReady: false
    property var heightDataRequest: null
    property string heightDataRequestKey: ""
    property double heightDataRetryAfter: 0
    property int heightDataRequestId: 0
    property bool heightDataPending: false
    property var coilInfoRequest: null
    property var pointDataRequest: null
    property int surfaceLoadRequestId: 0


    readonly property int mm_pointValueShowType: 0
    readonly property int int_pointValueShowType: 1
    readonly property int mm_int_pointValueShowType: 2

    property int currentPointValueShowType:mm_pointValueShowType

    function i_to_info(value){
        if (currentPointValueShowType == mm_pointValueShowType){
            if(value<0.01){
                return "-inf"
                }
            return ""+iz_to_mm(value)
        }
        else if (currentPointValueShowType == int_pointValueShowType){
            return ""+value
        }
        else {
            return ""+iz_to_mm_int(value)

        }


    }
    function ix_to_mm(value){
        return (value*scan3dScaleX).toFixed(0)
    }
    function iy_to_mm(value){
        return (value*scan3dScaleY).toFixed(0)
    }
    function iz_to_mm(value){
        return zRawToRelativeMm(value).toFixed(2)
    }
    function iz_to_mm_int(value){
        return zRawToMm(value).toFixed(2)
    }

    function zRawToMm(value){
        let rawValue = Number(value)
        if (!isFinite(rawValue)) {
            return 0
        }
        return rawValue * scan3dScaleZ + scan3dCoordinateOffsetZ
    }

    function zRawToRelativeMm(value){
        let rawValue = Number(value)
        if (!isFinite(rawValue) || rawValue <= 0) {
            return 0
        }
        return zRawToMm(rawValue) - medianZ
    }

    function getZValue(z){
        return zRawToRelativeMm(z)
    }

    property bool showMax: false
    property bool quickImage: false

    onShowMaxChanged: {
        root.modelStore.setShowMax(key, showMax)
    }
    property bool show_visible: true
    property bool hasData: true

    onHasDataChanged: {
        if(!hasData){
            show_visible = false
        }
        else{
            show_visible = true
        }
    }

    function setCoilInfo(_coilInfo_){
        coilInfo = _coilInfo_
    }
    property var coilInfo: {return {}}
    onCoilInfoChanged: {
        if (coilInfo && coilInfo.scan3dCoordinateScaleX !== undefined && isFinite(Number(coilInfo.scan3dCoordinateScaleX))) {
            scan3dScaleX = Number(coilInfo.scan3dCoordinateScaleX)
        } else {
            scan3dScaleX = defaultScan3dScaleX
        }
        if (coilInfo && coilInfo.scan3dCoordinateScaleY !== undefined && isFinite(Number(coilInfo.scan3dCoordinateScaleY))) {
            scan3dScaleY = Number(coilInfo.scan3dCoordinateScaleY)
        } else {
            scan3dScaleY = defaultScan3dScaleY
        }
        if (coilInfo && coilInfo.scan3dCoordinateScaleZ !== undefined && isFinite(Number(coilInfo.scan3dCoordinateScaleZ))) {
            scan3dScaleZ = Number(coilInfo.scan3dCoordinateScaleZ)
        } else {
            scan3dScaleZ = defaultScan3dScaleZ
        }
        if (coilInfo && coilInfo.scan3dCoordinateOffsetZ !== undefined && isFinite(Number(coilInfo.scan3dCoordinateOffsetZ))) {
            scan3dCoordinateOffsetZ = Number(coilInfo.scan3dCoordinateOffsetZ)
        } else {
            scan3dCoordinateOffsetZ = 0
        }
        if (coilInfo && coilInfo.median_3d !== undefined) {
            medianZInt = Number(coilInfo.median_3d)
        }
        if (coilInfo && coilInfo.median_3d_mm !== undefined) {
            medianZ = Number(coilInfo.median_3d_mm)
        }
        coilInfoReady = coilInfo && coilInfo.median_3d !== undefined && coilInfo.median_3d_mm !== undefined
        if (coilInfo && coilInfo.circleConfig){
        let inner_circle = coilInfo.circleConfig.inner_circle
        // circleTool.init(coilInfo.circleConfig)

        lineData = []
        let circlex = inner_circle.circlex ? inner_circle.circlex : []
        inner_circle_centre = circlex
        inner_ellipse = inner_circle.ellipse
        if (circlex.length >= 2){
            let x = Number(circlex[0])
            let y = Number(circlex[1])
            if (isFinite(x) && isFinite(y)){
                p1 = Qt.point(x, y)
            }
        }

            }
    }

    function updataHeightData(){
        let x1 = Number(p1.x), y1 = Number(p1.y), x2 = Number(p2.x), y2 = Number(p2.y)
        if (!isFinite(x1) || !isFinite(y1) || !isFinite(x2) || !isFinite(y2) || !coilId || !key){
            return
        }
        let requestKey = `${key}:${coilId}:${x1}:${y1}:${x2}:${y2}`
        if (heightDataRequest) {
            if (heightDataRequestKey !== requestKey) {
                heightDataPending = true
            }
            return
        }
        let nowMs = new Date().getTime()
        if (nowMs < heightDataRetryAfter) {
            if (heightDataRequestKey !== requestKey) {
                heightDataPending = true
            }
            heightDataDebounceTimer.interval = Math.max(100, heightDataRetryAfter - nowMs)
            heightDataDebounceTimer.restart()
            return
        }

        heightDataDebounceTimer.interval = 100
        heightDataPending = false
        heightDataRequestId += 1
        let requestId = heightDataRequestId
        heightDataRequestKey = requestKey
        heightDataRequest = root.apiClient.getHeightData(key,coilId,x1,y1,x2,y2,
                           (result)=>{
                              if (requestId !== heightDataRequestId) {
                                  return
                              }
                              heightDataRequest = null
                              heightDataRetryAfter = 0
                              try {
                                  lineData = JSON.parse(result)
                              } catch (error) {
                                  console.log("getHeightData parse error", error)
                              }
                              if (heightDataPending) {
                                  heightDataPending = false
                                  heightDataDebounceTimer.restart()
                              }
                          },(error,status)=>{
                              if (requestId !== heightDataRequestId) {
                                  return
                              }
                              heightDataRequest = null
                              if (status === 0 || status === 429 || status === 503) {
                                  heightDataRetryAfter = new Date().getTime() + 3000
                              }
                              if (heightDataPending) {
                                  heightDataPending = false
                                  heightDataDebounceTimer.restart()
                              }
                              console.log("getHeightData error")
                          })
    }

    Timer {
        id: heightDataDebounceTimer
        interval: 100
        repeat: false
        onTriggered: root.updataHeightData()
    }

    function perpendicularPoint(p1, p2, p3) {
        // 解构点的坐标
        const { x: x1, y: y1 } = p1;
        const { x: x2, y: y2 } = p2;
        const { x: x3, y: y3 } = p3;

        // 计算 p1 到 p2 的向量
        const dx = x2 - x1;
        const dy = y2 - y1;

        // 计算 p3 到 p1 的向量
        const dx1 = x1 - x3;
        const dy1 = y1 - y3;

        // 计算 p1p2 向量的长度的平方
        const lengthSquared = dx * dx + dy * dy;

        // 如果 p1 和 p2 重合，返回 null
        if (lengthSquared === 0) return null;

        // 计算投影系数
        const t = (dx * dx1 + dy * dy1) / lengthSquared;

        // 计算垂线交点
        const x = x1 - t * dx;
        const y = y1 - t * dy;

        return Qt.point(x,y);
    }

    function perpendicularPoint_xy(x,y){
        return perpendicularPoint(p1,p2,Qt.point(x,y))
    }

    property var inner_circle_centre: []
    property var inner_ellipse: []
    onInner_circle_centreChanged: {
        if (inner_circle_centre && inner_circle_centre.length >= 2){
            let x = Number(inner_circle_centre[0])
            let y = Number(inner_circle_centre[1])
            if (isFinite(x) && isFinite(y)){
                p1 = Qt.point(x, y)
            }
        }
    }

    property var p1: Qt.point(0,0)
    property var p2: Qt.point(0,0)

    onP1Changed: {
        heightDataDebounceTimer.restart()
    }
    onP2Changed: {
        heightDataDebounceTimer.restart()
    }


    property string key: ""

    property string key_string : key=="S"?"操作":"传动"

    property string currentViewKey: "GRAY"


    property color keyColor: key==="S"?"#7DFFB4":"#4244FF"

    property string locRootSource:""
    property var locFromDataSourceList: []


    property int coilId:0


    readonly property bool imageMask: root.modelStore.imageMaskChecked
    readonly property string requestedAreaViewKey: imageMask ? "AREA_MASK" : "AREA"
    readonly property string areaViewKey: requestedAreaViewKey === "AREA_MASK" && hasViewData("AREA_MASK") ? "AREA_MASK" : "AREA"
    onImageMaskChanged: {
        source = getSource(coilId,currentViewKey)
        refreshAreaSource()
    }
    onAreaViewKeyChanged: {
        refreshAreaSource()
    }

    property string default_key: "GRAY"
    property string source: ""
    property string area_source: ""
    property string error_source: ""
    property bool error_visible: false
    property bool error_auto: false
    property int tower_warning_show_opacity: 50
    property var viewHasDataMap: ({})
    property int viewHasDataVersion: 0
    property var dataAvailabilitySource: root.modelStore.hasDataCoilId === coilId
                                     && root.modelStore.has_data && key
                                     ? root.modelStore.has_data[key] : null

    onDataAvailabilitySourceChanged: rebuildViewHasData()
    onKeyChanged: {
        rebuildViewHasData()
        refreshAreaSource()
    }

    function normalizeViewKey(viewKey) {
        return viewKey === "2D" ? "AREA" : viewKey
    }

    function resolveViewHasData(surfaceHasData, viewKey) {
        viewKey = normalizeViewKey(viewKey)
        if (!surfaceHasData || !viewKey) {
            return false
        }
        if (surfaceHasData[viewKey] === true) {
            return true
        }
        if (viewKey === "GRAY" || viewKey === "JET" || viewKey === "JPG") {
            return surfaceHasData["JPG"] === true || surfaceHasData["3D"] === true
        }
        if (viewKey === "AREA") {
            return surfaceHasData["2D"] === true
        }
        if (viewKey === "AREA_MASK") {
            return surfaceHasData["AREA_MASK"] === true || surfaceHasData["2D_MASK"] === true
        }
        return false
    }

    function refreshViewDataModelAvailability() {
        for (let index = 0; index < viewDataModel.count; index++) {
            let item = viewDataModel.get(index)
            viewDataModel.setProperty(index, "has_data", hasViewData(item.key))
        }
    }

    function rebuildViewHasData() {
        let surfaceHasData = dataAvailabilitySource
        let nextMap = {}
        let viewKeys = root.modelStore ? root.modelStore.allViewKeys || [] : []
        viewKeys.forEach(function(viewKey) {
            nextMap[viewKey] = resolveViewHasData(surfaceHasData, viewKey)
        })
        nextMap["AREA"] = resolveViewHasData(surfaceHasData, "AREA")
        nextMap["2D"] = nextMap["AREA"]
        nextMap["AREA_MASK"] = resolveViewHasData(surfaceHasData, "AREA_MASK")
        viewHasDataMap = nextMap
        viewHasDataVersion += 1
        refreshViewDataModelAvailability()
    }


    function getSouceByKey(_viewKey_,preView=false){
        return getSource(coilId,_viewKey_,preView)
    }
    function setViewSource(_viewKey_){
        _viewKey_ = normalizeViewKey(_viewKey_)
        if (_viewKey_ === "AREA" || _viewKey_ === "AREA_MASK") {
            rootViewtoArea()
            return
        }

        default_key=_viewKey_
        currentViewKey = _viewKey_
        source = getSouceByKey(_viewKey_)
        refreshAreaSource()
    }

    function hasViewData(viewKey){
        viewKey = normalizeViewKey(viewKey)
        viewHasDataVersion
        return viewHasDataMap && viewHasDataMap[viewKey] === true
    }

    function refreshAreaSource() {
        if (coilId > 0 && key) {
            area_source = getSource(coilId, areaViewKey, false)
        } else {
            area_source = ""
        }
    }

    property CoilModel currentCoilModel

    function setCoilId(coilId_){
        // 切换时进行的设置
        let type_= default_key
        surfaceLoadRequestId += 1
        heightDataRequestId += 1
        if (heightDataRequest) {
            heightDataRequest.abort()
            heightDataRequest = null
        }
        if (coilInfoRequest) {
            coilInfoRequest.abort()
            coilInfoRequest = null
        }
        if (pointDataRequest) {
            pointDataRequest.abort()
            pointDataRequest = null
        }
        heightDataRequestKey = ""
        heightDataRetryAfter = 0
        heightDataPending = false
        coilId = coilId_
        coilInfoReady = false
        medianZInt = 0
        medianZ = 0
        error_visible = false
        rebuildViewHasData()
        source = getSource(coilId_,type_,false)
        refreshAreaSource()

        viewDataModel.clear()
        root.modelStore.allViewKeys.forEach(function(viewKey){
            viewDataModel.append({
                "image_source": getSource(coilId, viewKey, true),
                "key": viewKey,
                "has_data": hasViewData(viewKey)
            })
        })

        // 延迟加载其他数据，优先保证图像加载
        delayDataLoadTimer.restart()
    }

    // 延迟加载其他数据的定时器
    Timer {
        id: delayDataLoadTimer
        interval: 500  // 图像加载开始后500ms再加载其他数据
        onTriggered: {
            let requestedCoilId = coilId
            let requestedKey = key
            let requestId = surfaceLoadRequestId
            // 预缓存所有视图（延迟）
            root.modelStore.allViewKeys.forEach(function(viewKey){
                if (hasViewData(viewKey)) {
                    root.imageCacheService.pushCache(getSource(coilId,viewKey,false))
                }
            })

            // 获取钢卷信息
            coilInfoRequest = root.apiClient.getCoilInfo(requestedCoilId,requestedKey,
                            (result)=>{
                                if (requestId !== surfaceLoadRequestId
                                        || requestedCoilId !== coilId || requestedKey !== key) {
                                    return
                                }
                                coilInfoRequest = null
                                let payload = JsonUtils.parse(result, null, "coil surface info")
                                if (payload !== null) {
                                    setCoilInfo(payload)
                                }
                            },
                            (error)=>{
                                if (requestId === surfaceLoadRequestId) {
                                    coilInfoRequest = null
                                }
                                console.log("error")
                            }
                            )

            // 获取点数据
            pointTool.clear()
            pointDataRequest = root.apiClient.getPointDatas(
                        requestedCoilId,requestedKey,(result)=>{
                            if (requestId !== surfaceLoadRequestId
                                    || requestedCoilId !== coilId || requestedKey !== key) {
                                return
                            }
                            pointDataRequest = null
                            pointTool.setDatas(JsonUtils.parse(result, [], "coil point data"))
                        },
                        (error)=>{
                            if (requestId === surfaceLoadRequestId) {
                                pointDataRequest = null
                            }
                            console.log("getPointDatas error")
                        }
                        )
        }
    }

    Component.onDestruction: {
        heightDataRequestId += 1
        surfaceLoadRequestId += 1
        if (heightDataRequest) {
            heightDataRequest.abort()
        }
        if (coilInfoRequest) {
            coilInfoRequest.abort()
        }
        if (pointDataRequest) {
            pointDataRequest.abort()
        }
    }


    // 本机数据保存根目录（由服务端返回），格式如 file:///D:/Save_S
    function initData(data){
        locRootSource = "file:///" + data.saveFolder
        locFromDataSourceList = data.folderList
    }

    function getSourceByNet(_key_,_coilId_,_viewKey_, preView=false){ // 从网络获取
        return root.apiClient.getFileSource(_key_, _coilId_, normalizeViewKey(_viewKey_), preView, imageMask)
    }

    function getSourceByLocal(_key_,_coilId_,_viewKey_,preView=false){ // 本机
        let baseFolder = "/jpg/"
        let baseType = ".jpg"
        if (!root.modelStore.quickLyImage){
            baseFolder = "/png/"
            baseType = ".png"
        }
        return locRootSource + "/" + _coilId_ + baseFolder + _viewKey_ + baseType
    }

    // 共享文件夹根路径（UNC），用于远程服务器访问
    function getSharedFolderBase(__key__,_coilId_){
        return "file:////" + root.apiClient.apiConfig.hostname + "/" + root.settings.sharedFolderBaseName
                + __key__ + "/" + _coilId_
    }

    // 当前服务器是否在本机（127.0.0.1 / localhost）
    readonly property bool serverIsLocal: root.apiClient.apiConfig.hostname === "127.0.0.1"
                                          || root.apiClient.apiConfig.hostname === "localhost"

    // 本机保存目录：基于服务端返回的 saveFolder 构造
    function getLocalFolderBase(__key__, _coilId_) {
        if (!locRootSource || locRootSource.length === 0)
            return getSharedFolderBase(__key__, _coilId_)
        var base = locRootSource
        // 去掉末尾的 /
        if (base.charAt(base.length - 1) === "/")
            base = base.substring(0, base.length - 1)
        return base + "/" + _coilId_
    }

    function getBaseUrl(id_){
        if (serverIsLocal)
            return getLocalFolderBase(key, id_)
        return getSharedFolderBase(key, id_)
    }

    function getSourceBySharedFolder(_key_,_coilId_,_viewKey_,preView=false){ // 共享文件夹
        var baseFolder = getSharedFolderBase(_key_,_coilId_)
        let baseFolderName = "/png/"
        let baseType= ".png"

        if(preView){
            return baseFolder+"/preView/"+_viewKey_+".png"
        }
        else{
            if (imageMask){
                return baseFolder+"/mask/"+_viewKey_+".png"
            }
            if (root.modelStore.quickLyImage){
                baseFolderName = "/jpg/"
                baseType = ".jpg"
            }
            return baseFolder + baseFolderName + _viewKey_ + baseType

        }

    }

    function getSource(_coilId_,_viewKey_, preView=false){
        _viewKey_ = normalizeViewKey(_viewKey_)
        let res_url=""
        if ("AREA"==_viewKey_ || "AREA_MASK"==_viewKey_){// 2D AREA 瓦片视图必须使用 HTTP
            res_url = getSourceByNet(key, _coilId_, _viewKey_, preView)
        }
        else if(root.settings.useLoc){
            res_url = getSourceByLocal(key, _coilId_, _viewKey_, preView)
        }
        else{
            if (root.settings.useSharedFolder){
                res_url = getSourceBySharedFolder(key, _coilId_, _viewKey_, preView)
            }
            else
                res_url = getSourceByNet(key, _coilId_, _viewKey_, preView)
        }
        return res_url
    }

    property ListModel viewDataModel: ListModel{
    }


    property var lineData: []
    onLineDataChanged:{
        setTxModel()
    }

    function max_n_value(index,n){
        let temp=0
        for(let i=index;i<index+n;i++){
            if (lineData[i]>temp){
                temp = lineData[i]
            }
        }
        return temp
    }

    function min_n_value(index,n){
        let temp=0
        for(let i=index;i<index+n;i++){
            if (lineData[i]<temp){
                temp = lineData[i]
            }
        }
        return temp
    }

    function distance(x1,y1,x2,y2){
        return Math.sqrt((x1-x2)*(x1-x2)+(y1-y2)*(y1-y2))
    }

    function setTxModel(){
        txModel.clear()
        if (!lineData || lineData.length === 0) {
            return
        }
        for(let key in lineData){
            let datas = lineData[key] && lineData[key]["points"]
            if (!Array.isArray(datas) || datas.length === 0) {
                continue
            }
            let startX =0
            let startY =0
            let startZ =0
            let start_z_mm =0
            let reverse =0
            datas.forEach(
                        function(data,index){
                            let x = data[0]
                            let y = data[1]
                            let z = data[2]
                            let z_mm = getZValue(z)
                            if(z_mm>tower_warning_threshold_up){
                                if (reverse == 0){
                                    startX = x
                                    startY = y
                                    startZ = z
                                    start_z_mm = z_mm
                                    reverse = 1
                                }
                            }
                            else if (z_mm<tower_warning_threshold_down){
                                if (reverse == 0){
                                    startX = x
                                    startY = y
                                    startZ = z
                                    start_z_mm = z_mm
                                    reverse = -1
                                }
                            }
                            else{
                                if (distance(startX,startY,x,y)>20){
                                    if(reverse!=0){
                                        let v={
                                            "startX":startX,
                                            "startY":startY,
                                            "startZ":startZ,
                                            "endX":x,
                                            "endY":y,
                                            "endZ":z,
                                            "endZ":z,
                                            "start_z_mm":start_z_mm,
                                            "end_z_mm":z_mm,
                                            "reverse":reverse
                                        }
                                        txModel.append(v)
                                        // console.log("vvvvvvvvvv")
                                        // console.log(JSON.stringify(v))
                                        reverse=0
                                    }
                                }
                            }
                        }
                    )
        }
    }

    property ListModel txModel: ListModel{}


    readonly property ListModel pointUserData: pointTool.pointUserData

    readonly property ListModel pointDbData: pointTool.pointDbData

    function addSignPoint(p){
        return pointTool.addUserPoint(p.x,p.y)
    }

    function removeSignPoint(index){
        pointUserData.remove(index)
    }

    //  报警相关设置
    property real tower_warning_threshold_up: 100
    property real tower_warning_threshold_down: -100



    function openSaveFolderById(coilId){
        return Qt.openUrlExternally(getBaseUrl(coilId))
    }
    readonly property string productionMeshPath: "\\\\" + root.apiClient.apiConfig.hostname + "/"
                                                 + root.settings.sharedFolderBaseName + key + "/" + coilId
                                                 + "/meshes/defaultobject_mesh.mesh"
    readonly property string productionMeshUrl: getSharedFolderBase(key, coilId)
                                                + "/meshes/defaultobject_mesh.mesh"
    readonly property string testDataMeshPath: root.scriptLauncher && root.coreController.developer_mode
                                               ? root.scriptLauncher.testDataMeshPath(key, coilId) : ""
    readonly property string testDataMeshUrl: root.scriptLauncher && root.coreController.developer_mode
                                              ? root.scriptLauncher.testDataMeshUrl(key, coilId) : ""
    readonly property string meshUrl: root.coreController.developer_mode && testDataMeshUrl !== ""
                                      ? testDataMeshUrl : productionMeshUrl

    property bool meshExits: root.scriptLauncher
                            ? (root.coreController.developer_mode
                               ? root.scriptLauncher.testDataMeshExists(key, coilId)
                               : root.scriptLauncher.fileExists(productionMeshPath))
                            : false
}
