import QtQuick
// 负责进行设置，反馈等级
Item {


    function setCoilStatus(ccoil_id,level,msg,success,failure){
        api.setCoilStatus(ccoil_id,level,msg,success,failure)
    }

    function init_data_has(){
        let requestedCoilId = core.currentCoilModel.coilId
        coreModel.has_data = null
        coreModel.hasDataCoilId = requestedCoilId
        api.has_data(requestedCoilId,
                     (text)=>{
                        if (core.currentCoilModel.coilId !== requestedCoilId) {
                            return
                        }
                        coreModel.has_data = JSON.parse(text)
                        coreModel.hasDataCoilId = requestedCoilId
                     },
                     (err)=>{
                        if (core.currentCoilModel.coilId === requestedCoilId) {
                            coreModel.has_data = null
                            coreModel.hasDataCoilId = 0
                        }

                     }
                     )

    }
}
