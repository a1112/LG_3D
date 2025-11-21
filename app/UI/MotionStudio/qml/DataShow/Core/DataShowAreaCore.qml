import QtQuick
import "_base_"
import "../../Core/Surface"
import "../../DataShow/2dShow/ViewTool"
Item {
        property string key: "AREA"
    id:root
    function flush(){
        surfaceData.error_visible=false
        flushDefect()
    }
      // 鍥炬爣鐨勬樉绀烘柟寮?
    property int chartShowType: 0



    readonly property int coilId: surfaceData.coilId
    readonly property string currentViewKey:surfaceData.currentViewKey
    onCoilIdChanged: {
        flush()
    }

    property Flickable flick

    property string source: surfaceData.area_source //"http://127.0.0.1:5012/image/area/S/66252?"//
    // 棰勮鍥撅細鐩存帴浣跨敤鏈嶅姟绔?preview 鎺ュ彛锛岄伩鍏?row=-2 杩斿洖浠呭楂?    property string pre_source: surfaceData.getSouceByKey("AREA", true)


    // 鐢诲竷鏁版嵁
    property real canvasScale: minScale // 鐢诲竷缂╂斁姣斾緥

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

    property int canvasWidth: flick.width
    property int canvasHeight: flick.height
    readonly property real canvasWidthAspectRatio: canvasWidth/canvasContentWidth
    readonly property real canvasHeightAspectRatio: canvasHeight/canvasContentHeight

    property int showLeft: flick.contentX/canvasScale
    property int showTop: flick.contentY/canvasScale
    property int showRight: (flick.contentX+flick.width)/canvasScale
    property int showBottom: (flick.contentY+flick.height)/canvasScale

    property real max_mm: sourceWidth*surfaceData.scan3dScaleX
    property real showLeftmm: (showLeft-surfaceData.inner_circle_centre[0])*surfaceData.scan3dScaleX
    property real showRightmm: (showRight-surfaceData.inner_circle_centre[0])*surfaceData.scan3dScaleX

    readonly property int canvasContentX: flick.contentX
    readonly property int canvasContentY: flick.contentY
    readonly property real canvasContentXaspectRatio: canvasContentX/canvasContentWidth
    readonly property real canvasContentYaspectRatio: canvasContentY/canvasContentHeight

    readonly property int canvasContentWidth: sourceWidth * canvasScale
    readonly property int canvasContentHeight: sourceHeight * canvasScale

    // 鍥惧儚鏁版嵁
    property int sourceWidth: 0
    property int sourceHeight: 0

    property real aspectRatio: sourceWidth/sourceHeight


    property bool viewRendererListView: false
    property bool viewRendererMaxMinValue: false
    property bool viewDefectListView: true

    property int checkRendererIndex:0

    property real minScale:Math.min(canvasHeight/sourceWidth, canvasHeight/sourceHeight) //Math.min(canvasWidth/sourceWidth,canvasWidth/sourceHeight) // 鏈€灏忕缉鏀炬瘮渚?
    property real maxScale: 1 // 鏈€澶х缉鏀炬瘮渚?
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


    property point hoverPoint: Qt.point(0,0) // 榧犳爣鎮仠鐐?
    property int hoverdX: (hoverPoint.x+flick.contentX)/canvasScale
    property int hoverdY: (hoverPoint.y+flick.contentY)/canvasScale
    property real hoverdXmm: pxtoPos(hoverdX).toFixed(1)
    property real hoverdYmm: pxtoPos(hoverdY).toFixed(1)
    property real hoverdZmm : 0
    property real chartsHoverdZmm: 0

    function resetView(){
        canvasScale = minScale
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

    readonly property real medianZValue:surfaceData.medianZInt // #parseInt(Math.abs(medianZ/surfaceData.scan3dScaleZ))
    readonly property real medianZ: surfaceData.medianZ

    property int rangeZValue: rangeZ/surfaceData.scan3dScaleZ
    function renderDrawer()
    {
        surfaceData.source = api.geRenderDrawerSource(surfaceData.key,
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
        surfaceData.error_source = api.geErrorDrawerSource(surfaceData.key,
                                                           surfaceData.coilId,
                                                           1,
                                                           parseInt(medianZValue+tower_warning_threshold_downValue)
                                                           ,parseInt(medianZValue+tower_warning_threshold_upValue)
                                                           )
        surfaceData.error_visible=true
    }


    function setDefectShowView(defect){
        setToMaxScale()
        flick.contentX =defect.defect_x-(flick.width-defect.defect_w)/2
        flick.contentY = defect.defect_y-(flick.height-defect.defect_h)/2
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
