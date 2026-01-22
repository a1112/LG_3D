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


    property var fliterDict:{return {}}
    property var tempCoilModel :  CoilModel{}
    function flushModel(){
        fliterListModel.clear()
        tool.for_list_model(coreModel.currentCoilListModel,(item_data)=>{
                                tempCoilModel._getDefectNameList_(item_data).some((name)=>{
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
        if (defectName in fliterDict){
            return fliterDict[defectName]
        }
        return false
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
    property int pendingDetailCoilId: 0  // 正在请求的coilId

    onHovedIndexChanged: {
        if (hovedIndex < 0) return

        let p = coreModel.currentCoilListModel.get(hovedIndex)
        if (!p) return

        let coilId = p.Id || p.SecondaryCoilId
        hovedCoilId = coilId

        // 检查缓存
        if (detailCache[coilId]) {
            // 使用缓存数据
            hovelCoilData = detailCache[coilId]
            hovedCoilModel.init(detailCache[coilId])
            return
        }

        // 先用摘要数据显示
        hovelCoilData = p
        hovedCoilModel.init(p)

        // 异步获取完整详情
        fetchCoilDetail(coilId)
    }

    // ========== 获取卷材详情 ==========
    function fetchCoilDetail(coilId) {
        // 避免重复请求
        if (pendingDetailCoilId === coilId) return
        pendingDetailCoilId = coilId

        app.api.getCoilDetail(coilId,
            function success(data) {
                // 请求成功
                pendingDetailCoilId = 0

                if (data && data.Id) {
                    // 缓存数据 - 使用深拷贝避免引用问题
                    detailCache[coilId] = JSON.parse(JSON.stringify(data))

                    // 如果当前还是悬停在这个卷材上，更新显示
                    if (hovedCoilId === coilId) {
                        hovelCoilData = detailCache[coilId]
                        hovedCoilModel.init(detailCache[coilId])
                    }
                }
            },
            function error(err) {
                // 请求失败，保持摘要数据显示
                pendingDetailCoilId = 0
                console.log("Failed to fetch coil detail:", err)
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
