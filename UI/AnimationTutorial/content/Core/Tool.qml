import QtQuick

Item {

    function url_to_str(url){
        // 将url 转换为 string
        return url.toString().substring(8)
    }

    function fileFolderPath(path) {
        //   格式化字符串
        var lastSlashIndex = path.lastIndexOf("/")
        if (lastSlashIndex === -1) {
            lastSlashIndex = path.lastIndexOf("\\")  // Check for Windows-style backslashes
        }
        return lastSlashIndex !== -1 ? path.substring(0, lastSlashIndex) : ""
    }

    function for_list_model(list_model,func){
        //    for 循环
        for (let i=0;i<list_model.count;i++){
            if (func(list_model.get(i),i) === true)return
        }
    }

    function list_model_to_json(list_model){
        print("list_model_to_json",list_model )
        let res=[]
        for_list_model(list_model,(item)=>{
                           let item_value={}
                        let keys = Object.keys(item)
                           keys.forEach((key_item)=>{
                                        item_value[key_item]=item[key_item]
                                        })
                       res.push(item_value)

                       })
        return res
    }

}
