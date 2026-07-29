import QtQuick
import "JsonUtils.js" as JsonUtils
// 负责进行设置，反馈等级
Item {

    property int dataHasRequestId: 0

    function setCoilStatus(ccoil_id,level,msg,success,failure){
        api.setCoilStatus(ccoil_id,level,msg,success,failure)
    }

    function applyDataHas(requestId, requestedCoilId, text){
        if (requestId !== dataHasRequestId || core.currentCoilModel.coilId !== requestedCoilId) {
            return false
        }
        let data = JsonUtils.parse(text, null, "coil data availability")
        if (data === null) {
            return false
        }
        coreModel.setHasDataCache(requestedCoilId, data)
        coreModel.has_data = data
        coreModel.hasDataCoilId = requestedCoilId
        return true
    }

    function init_data_has(){
        let requestedCoilId = core.currentCoilModel.coilId
        dataHasRequestId += 1
        let requestId = dataHasRequestId
        let cachedData = coreModel.getHasDataCache(requestedCoilId)
        coreModel.hasDataCoilId = requestedCoilId

        if (cachedData) {
            coreModel.has_data = cachedData
        } else {
            coreModel.has_data = null
        }

        let fullApplied = false
        if (!cachedData) {
            api.has_data(requestedCoilId,
                         (text)=>{
                            if (fullApplied) {
                                return
                            }
                            applyDataHas(requestId, requestedCoilId, text)
                         },
                         (err)=>{},
                         true
                         )
        }

        api.has_data(requestedCoilId,
                     (text)=>{
                        fullApplied = true
                        applyDataHas(requestId, requestedCoilId, text)
                     },
                     (err)=>{
                        if (requestId === dataHasRequestId && core.currentCoilModel.coilId === requestedCoilId
                                && (!coreModel.has_data || coreModel.hasDataCoilId !== requestedCoilId)) {
                            coreModel.has_data = null
                            coreModel.hasDataCoilId = 0
                        }

                     }
                     )

    }
}
