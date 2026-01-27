import QtQuick
import "../../Model"
import "../../Core/Surface"
import "../../DataShow/2dShow/ViewTool"
import "_base_"
DataShowCore_ {
    // OBJ
    id:root

    property DataShowControl controls:  DataShowControl{
        hoverPoint:root.hoverPoint
    }
    property DataShowControl3D controls3D:  DataShowControl3D{
    }
    property DataShowAreaCore dataShowAreaCore: DataShowAreaCore{
    }

    function flush(){
        surfaceData.error_visible=false
        // 第一阶段：立即触发图像渲染
        renderDrawer()
        // 第二阶段：延迟加载缺陷数据，优先保证图像加载完成
        defectLoadTimer.restart()
    }

    Timer {
        id: defectLoadTimer
        interval: 1200  // 确保图像加载完成后再加载缺陷（增加延迟）
        onTriggered: {
            // 第三阶段：加载缺陷数据和缺陷图像
            flushDefect()
        }
    }
      // 图标的显示方式
    property int chartShowType: 0



    readonly property int coilId: surfaceData.coilId
    readonly property string key:surfaceData.key
    readonly property string currentViewKey:surfaceData.currentViewKey
    onCoilIdChanged: {
        flush()
    }

    property Flickable flick

    property CoilModel currentCoilModel: surfaceData.currentCoilModel

    property string source: surfaceData.source

    // 画布数据
    property real canvasScale: minScale // 画布缩放比例

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

    property int canvasWidth: flick ? flick.width : 0
    property int canvasHeight: flick ? flick.height : 0
    readonly property real canvasWidthAspectRatio: canvasContentWidth === 0 ? 0 : canvasWidth/canvasContentWidth
    readonly property real canvasHeightAspectRatio: canvasContentHeight === 0 ? 0 : canvasHeight/canvasContentHeight

    property int showLeft: flick ? flick.contentX/canvasScale : 0
    property int showTop: flick ? flick.contentY/canvasScale : 0
    property int showRight: flick ? (flick.contentX+flick.width)/canvasScale : 0
    property int showBottom: flick ? (flick.contentY+flick.height)/canvasScale : 0

    property real max_mm: sourceWidth*surfaceData.scan3dScaleX
    property real showLeftmm: (showLeft-surfaceData.inner_circle_centre[0])*surfaceData.scan3dScaleX
    property real showRightmm: (showRight-surfaceData.inner_circle_centre[0])*surfaceData.scan3dScaleX

    readonly property int canvasContentX: flick ? flick.contentX : 0
    readonly property int canvasContentY: flick ? flick.contentY : 0
    readonly property real canvasContentXaspectRatio: canvasContentWidth === 0 ? 0 : canvasContentX/canvasContentWidth
    readonly property real canvasContentYaspectRatio: canvasContentHeight === 0 ? 0 : canvasContentY/canvasContentHeight

    readonly property int canvasContentWidth: sourceWidth * canvasScale
    readonly property int canvasContentHeight: sourceHeight * canvasScale

    // 图像数据
    property int sourceWidth: 0
    property int sourceHeight: 0

    property real aspectRatio: sourceWidth/sourceHeight


    property bool viewRendererListView: false
    property bool viewRendererMaxMinValue: false
    property bool viewDefectListView: true

    property int checkRendererIndex:0

    property real minScale:Math.min(canvasHeight/sourceWidth,canvasHeight/sourceHeight) //Math.min(canvasWidth/sourceWidth,canvasWidth/sourceHeight) // 最小缩放比例
    property real maxScale: 1 // 最大缩放比例
    property point scaleTempPoint: Qt.point(0,0)

    function getAspectRatioByPoint(point){
        let asX =(point.x+canvasContentX)/canvasContentWidth
        let asY =(point.y+canvasContentY)/canvasContentHeight
        return Qt.point(asX,asY)
    }

    function setFlickablebyPoint(point){
        let newX = scaleTempPoint.x*canvasContentWidth
        let newY = scaleTempPoint.y*canvasContentHeight
        flick.contentX = newX-point.x
        flick.contentY = newY-point.y
    }

    function toPx(x){
        return x*canvasScale
    }
    function toMm(w){
        return w/canvasScale*surfaceData.scan3dScaleX
    }
    function pxto_top(px){
        return parseInt(px/canvasScale)
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


    property point hoverPoint: Qt.point(0,0) // 鼠标悬停点
    property int hoverdX: (hoverPoint.x+flick.contentX)/canvasScale
    property int hoverdY: (hoverPoint.y+flick.contentY)/canvasScale
    property real hoverdXmm: pxtoPos(hoverdX).toFixed(1)


    property real hoverdYmm: pxtoPos(hoverdY).toFixed(1)
    onHoverdXChanged: {
        get_zValue()
    }
    function get_zValue(){
        api.get_zValueData(surfaceData.key,surfaceData.coilId,
                           hoverdX,
                           hoverdY,
                           (result)=>{
                               hoverdZmm = (parseInt(result)*surfaceData.scan3dScaleZ-medianZ).toFixed(2)
                           },
                           (error)=>{
                               console.log("get_zValueData error:",error)
                           }
                        )
    }


    property real hoverdZmm : 0
    property real chartsHoverdZmm: 0

    function resetView(){
        canvasScale = minScale
        flick.contentX = 0
        flick.contentY = 0
    }



    property bool txChartView: true

    property bool telescopedJointView: true // 是否显示塔形

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
            if (surfaceData.error_auto)
                errorDrawer()
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

    // ========== 新增：图像类型状态 ==========
    property string currentImageType: "none"  // "gray", "jet", "none"
    property string imageTypeText: "未加载"
    property color imageTypeColor: "#999999"

    readonly property real medianZValue:surfaceData.medianZInt // #parseInt(Math.abs(medianZ/surfaceData.scan3dScaleZ))
    readonly property real medianZ: surfaceData.medianZ

    property int rangeZValue: rangeZ/surfaceData.scan3dScaleZ
    function renderDrawer()
    {
        // 第一阶段：加载 GRAY 缓存图（快速显示）
        surfaceData.source = api.geRenderDrawerSource(
            surfaceData.key,
            surfaceData.coilId,
            renderScale.toFixed(2),
            parseInt(medianZValue-rangeZValue),
            parseInt(medianZValue+rangeZValue),
            mask=true,
            grayscale=true  // GRAY 模式，使用 GRAY 缓存
        )
        currentImageType = "gray"
        imageTypeText = "灰度预览"
        imageTypeColor = "#999999"

        // 第二阶段：延迟加载 JET 图像（更高质量）
        renderTimer.restart()
    }

    Timer {
        id: renderTimer
        interval: 500  // 500ms 后切换到 JET 图像
        onTriggered: {
            surfaceData.source = api.geRenderDrawerSource(
                surfaceData.key,
                surfaceData.coilId,
                renderScale.toFixed(2),
                parseInt(medianZValue-rangeZValue),
                parseInt(medianZValue+rangeZValue),
                mask=true,
                grayscale=false  // JET 模式，使用 JET 缓存
            )
            currentImageType = "jet"
            imageTypeText = "彩色显示"
            imageTypeColor = "#52c41a"
        }
    }
    property int tower_warning_threshold_upValue: surfaceData.tower_warning_threshold_up/surfaceData.scan3dScaleZ
    property int tower_warning_threshold_downValue: surfaceData.tower_warning_threshold_down/surfaceData.scan3dScaleZ
    function errorDrawer()
    {
        // 检查设置中的叠加图层开关
        if (!coreSetting.showErrorOverlay) {
            surfaceData.error_visible=false
            return
        }
        surfaceData.error_source = api.geErrorDrawerSource(surfaceData.key,
                                                           surfaceData.coilId,
                                                           1,
                                                           surfaceData.tower_warning_threshold_down  // mm 值：蓝色阈值
                                                           , surfaceData.tower_warning_threshold_up     // mm 值：红色阈值
                                                           )
        surfaceData.error_visible=true
    }

    function setDefectShowView(defect){
        setToMaxScale()
        flick.contentX =defect.defect_x-(flick.width-defect.defect_w)/2
        flick.contentY = defect.defect_y-(flick.height-defect.defect_h)/2
    }

    // 监听从缺陷页面跳转时的待定位缺陷
    Timer {
        id: pendingDefectTimer
        interval: 500
        onTriggered: {
            if (coreModel.pendingDefect && flick) {
                let pending = coreModel.pendingDefect
                let currentCoilId = currentCoilModel ? currentCoilModel.coilId : surfaceData.coilId
                console.log("DataShowCore pendingDefect:", pending.surface, pending.coilId, "current:", surfaceData.key, currentCoilId)
                // 检查是否匹配当前表面和卷材（使用 currentCoilModel.coilId）
                if (pending.surface === surfaceData.key && pending.coilId === currentCoilId) {
                    setDefectShowView(pending)
                    console.log("定位到缺陷")
                }
                // 清除待定位缺陷
                coreModel.pendingDefect = null
            }
        }
    }

    Connections {
        target: coreModel
        function onPendingDefectChanged() {
            if (coreModel.pendingDefect) {
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
}
