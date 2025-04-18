import QtQuick
// 负责进行设置，反馈等级
Item {


    function setCoilStatus(ccoil_id,level,msg,success,failure){
        api.setCoilStatus(ccoil_id,level,msg,success,failure)
    }

    function init_data_has(){
        api.has_data(core.currentCoilModel.coilId,
                     (text)=>{
                        coreModel.has_data = JSON.parse(text)
                     },
                     (err)=>{

                     }
                     )

    }
}
