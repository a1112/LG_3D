import QtQuick 2.15
// 定时器
Item {

    Timer{  // 数据刷新 定时器
        interval:  coreSetting.updataTime
        repeat: true
        running: true
        onTriggered: {
            api.getDataFlush(
                        coreModel.lastCoilId,(result)=>{
                            coreModel.updateData(JSON.parse(result))
                        },(error)=>{
                            console.log("刷新数据失败")
                        }
                    )
        }
    }

    Timer{  // 保持最新数据数据 定时器
        interval: 1000
        running: !coreModel.keepLatest
        repeat: true
        onTriggered: {
            coreModel.autoKeepTime+=1
            if(coreModel.autoKeepTime>=coreModel.autoKeepTimeMax){
                coreModel.keepLatest = true
                coreModel.autoKeepTime=0
            }
        }
    }
}
