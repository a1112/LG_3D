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
        //    for 循环 ListModel
        for (let i=0;i<list_model.count;i++){
            if (func(list_model.get(i),i) === true)return
        }
    }

    function for_list(list,func){
        return list.forEach(
                    func
                    )
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


    function getNowString(){
       return Qt.formatDateTime(new Date(), "yyyy_MM_dd hh_mm_ss")
    }
    function getNowTimeString(){
       return Qt.formatDateTime(new Date(), "hh:mm:ss")
    }

    function getDataByJson(date_time){
            return new Date(date_time["year"],date_time["month"]-1,date_time["day"],date_time["hour"],date_time["minute"],date_time["second"])
        }

    function getDelTimeStr(newTime, oldTime) {
        // 计算时间差（以毫秒为单位）
        let timeDifference = newTime - oldTime;

        // 定义时间单位（毫秒）
        const msInSecond = 1000;
        const msInMinute = msInSecond * 60;
        const msInHour = msInMinute * 60;
        const msInDay = msInHour * 24;
        const msInMonth = msInDay * 30; // 近似值
        const msInYear = msInDay * 365; // 近似值

        // 计算各时间单位
        let years = Math.floor(timeDifference / msInYear);
        timeDifference %= msInYear;

        let months = Math.floor(timeDifference / msInMonth);
        timeDifference %= msInMonth;

        let days = Math.floor(timeDifference / msInDay);
        timeDifference %= msInDay;

        let hours = Math.floor(timeDifference / msInHour);
        timeDifference %= msInHour;

        let minutes = Math.floor(timeDifference / msInMinute);
        timeDifference %= msInMinute;

        let seconds = Math.floor(timeDifference / msInSecond);

        // 构建结果字符串
        let result = [];
        if (years > 0) result.push(years + " 年");
        if (months > 0) result.push(months + " 月");
        if (days > 0) result.push(days + " 天");
        if (hours > 0) result.push(hours + " 小时");
        if (minutes > 0) result.push(minutes + " 分");
        if (seconds > 0) result.push(seconds + " 秒");

        // 如果没有差值，返回 "0 秒"
        if (result.length === 0) return "0 秒";

        return result.join(" ");
    }
}
