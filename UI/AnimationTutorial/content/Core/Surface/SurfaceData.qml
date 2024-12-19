import QtQuick
import "../../Model"
Item {
    id:root
    property int rootViewIndex: 0
    readonly property bool is2DrootView:rootViewIndex==0
    readonly property bool is3DrootView:rootViewIndex==1

    property  PointTool pointTool  : PointTool{}     //  处理数据点
    property CircleTool circleTool : CircleTool{}   //  处理 圆相关数据
    function rootViewto2D(){
        rootViewIndex=0
    }

    function rootViewto3D(){
        rootViewIndex=1
    }

    readonly property real scan3dScaleZ: 0.016229506582021713
    readonly property real scan3dScaleX: 0.33693358302116394
    readonly property real scan3dScaleY: 0.33693358302116394
    property real medianZInt: 0
    property real medianZ: 0.0

    function i_to_info(value){
        if(value<0.01)
            return "-inf"
        return ""+iz_to_mm(value)
    }

    function iz_to_mm(value){
        return ((value-medianZInt)*scan3dScaleZ).toFixed(2)
    }

    function getZValue(z){
        return ((z*scan3dScaleZ).toFixed(2)-medianZ)
    }

    property bool showMax: false
    property bool quickImage: false

    onShowMaxChanged: {
        coreModel.setShowMax(key,showMax)
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
        if (coilInfo && coilInfo.circleConfig){
        let inner_circle=coilInfo.circleConfig.inner_circle
            circleTool.init("")
        console.log("coilInfo.circleConfig")
            console.log(JSON.stringify(coilInfo.circleConfig))yyc
        lineData = []
        inner_circle_centre =inner_circle.circlex
        inner_ellipse = inner_circle.ellipse
        p1 = Qt.point(inner_circle.circlex[0],inner_circle.circlex[1])
            }
    }

    function updataHeightData(){
        api.getHeightData(key,coilId,p1.x,p1.y,p2.x,p2.y,
                          (result)=>{
                              lineData = JSON.parse(result)
                          },(error)=>{
                              console.log("getHeightData error")
                          })
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
        p1 = Qt.point(inner_circle_centre[0],inner_circle_centre[1])
    }

    property var p1: Qt.point(0,0)
    property var p2: Qt.point(0,0)

    onP1Changed: {
        updataHeightData()
    }
    onP2Changed: {
        updataHeightData()
    }


    property string key: ""

    property string currentViewKey: "GRAY"


    property color keyColor: key==="S"?"#7DFFB4":"#4244FF"

    property string locRootSource:""
    property var locFromDataSourceList: []


    property int coilId:0


    readonly property bool imageMask: coreModel.imageMaskChecked
    onImageMaskChanged: {
        source=getSource(coilId,currentViewKey)
    }

    property string default_key:"GRAY"
    property string source: ""
    property string error_source: ""
    property bool error_visible: true
    property bool error_auto: true
    property int tower_warning_show_opacity: 50


    function getSouceByKey(_viewKey_,preView=false){
        return getSource(coilId,_viewKey_,preView)
    }
    function setViewSource(_viewKey_){

        default_key=_viewKey_
        currentViewKey = _viewKey_
        source = getSouceByKey(_viewKey_)
    }

    property CoilModel currentCoilModel

    function setCoilId(coilId_){
        // 切换时进行的设置
        let type_= default_key
        coilId = coilId_
        source = getSource(coilId_,type_,false)
        viewDataModel.clear()
        coreModel.allViewKeys.forEach(function(viewKey){
            viewDataModel.append({"image_source":getSource(coilId,viewKey,true),"key":viewKey})
            imageCache.pushCache(getSource(coilId,viewKey,false))
        })

        api.getCoilInfo(coilId_,key,
                        (result)=>{
                            setCoilInfo(JSON.parse(result))
                        },
                        (error)=>{
                            console.log("error")
                        }
                        )

        pointTool.clear()
        api.getPointDatas(
                    coilId_,key,(result)=>{
                        pointTool.setDatas(JSON.parse(result))
                    },
                    (error)=>{
                        console.log("getPointDatas error")
                        console.log("error")
                    }
                    )

    }


    function initData(data){
        locRootSource ="file:///"+ data.saveFolder
        locFromDataSourceList = data.folderList
    }

    function getSourceByNet(_key_,_coilId_,_viewKey_, preView=false){ // 从网络获取
        return api.getFileSource(_key_,_coilId_,_viewKey_,preView=preView,imageMask)
    }

    function getSourceByLocal(_key_,_coilId_,_viewKey_,preView=false){ // 本机
        let baseFolder = "/jpg/"
        let baseType= ".jpg"
        if (!coreModel.quickLyImage){
                let baseFolder = "/png/"
                let baseType= ".png"
            }
        return locRootSource+"/"+coilId+baseFolder+_viewKey_+baseType
    }

    function getSharedFolderBase(__key__,_coilId_){
        return "file:////"+api.apiConfig.hostname+"/"+coreSetting.sharedFolderBaseName+__key__+"/"+_coilId_
    }

    function getBaseUrl(id_){
        return getSharedFolderBase(key,id_)
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
            if (coreModel.quickLyImage){
                let baseFolderName = "/jpg/"
                let baseType= ".jpg"
                }
            return baseFolder+baseFolderName+_viewKey_+baseType

        }

    }

    function getSource(_coilId_,_viewKey_, preView=false){
        if(coreSetting.useLoc){
            return getSourceByLocal(key,_coilId_,_viewKey_, preView=preView)
        }
        else{
            if (coreSetting.useSharedFolder){
                return getSourceBySharedFolder(key,_coilId_,_viewKey_, preView=preView)
            }
            else
                return getSourceByNet(key,_coilId_,_viewKey_, preView=preView)
        }
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
        for(let key in lineData){
            let datas= lineData[key]["points"]
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
    property real tower_warning_threshold_up: 50
    property real tower_warning_threshold_down: -50

}
