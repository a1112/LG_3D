import QtQuick
import "JsonUtils.js" as JsonUtils
// 负责进行设置，反馈等级
Item {
    id: root
    required property var apiClient
    required property var coreController
    required property var modelStore

    property int dataHasRequestId: 0
    signal redetectionCompleted(int coilId)

    function setCoilStatus(ccoil_id,level,msg,success,failure){
        root.apiClient.setCoilStatus(ccoil_id,level,msg,success,failure)
    }

    function applyDataHas(requestId, requestedCoilId, text){
        if (requestId !== root.dataHasRequestId
                || root.coreController.currentCoilModel.coilId !== requestedCoilId) {
            return false
        }
        let data = JsonUtils.parse(text, null, "coil data availability")
        if (data === null) {
            return false
        }
        root.modelStore.setHasDataCache(requestedCoilId, data)
        root.modelStore.has_data = data
        root.modelStore.hasDataCoilId = requestedCoilId
        return true
    }

    function init_data_has(){
        let requestedCoilId = Number(root.coreController.currentCoilModel.coilId || 0)
        root.dataHasRequestId += 1
        let requestId = root.dataHasRequestId
        if (requestedCoilId <= 0) {
            root.modelStore.has_data = null
            root.modelStore.hasDataCoilId = 0
            return
        }
        let cachedData = root.modelStore.getHasDataCache(requestedCoilId)
        root.modelStore.hasDataCoilId = requestedCoilId

        if (cachedData) {
            root.modelStore.has_data = cachedData
        } else {
            root.modelStore.has_data = null
        }

        let fullApplied = false
        if (!cachedData) {
            root.apiClient.has_data(requestedCoilId,
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

            root.apiClient.has_data(requestedCoilId,
                     (text)=>{
                        fullApplied = true
                        applyDataHas(requestId, requestedCoilId, text)
                     },
                     (err)=>{
                        if (requestId === root.dataHasRequestId
                                && root.coreController.currentCoilModel.coilId === requestedCoilId
                                && (!root.modelStore.has_data
                                    || root.modelStore.hasDataCoilId !== requestedCoilId)) {
                            root.modelStore.has_data = null
                            root.modelStore.hasDataCoilId = 0
                        }

                     }
                     )

    }

    // Re-detection rewrites 3D files asynchronously. Drop the per-coil
    // availability cache and notify surface views so they can reload.
    function refreshAfterRedetection(){
        let coilId = Number(root.coreController.currentCoilModel.coilId || 0)
        if (coilId <= 0) {
            return
        }
        root.modelStore.invalidateHasDataCache(coilId)
        root.modelStore.has_data = null
        root.modelStore.hasDataCoilId = coilId
        root.init_data_has()
        root.modelStore.surfaceS.setCoilId(coilId)
        root.modelStore.surfaceL.setCoilId(coilId)
        root.redetectionCompleted(coilId)
    }
}
