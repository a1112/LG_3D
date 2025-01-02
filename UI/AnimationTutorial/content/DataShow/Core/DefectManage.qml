import QtQuick

Item {

    function defect_is_show(name){
        return unShowDefectList.indexOf(name) < 0
    }
    property var unShowDefectList: ["塔形", "头尾", "背景","数据脏污"]    // 屏蔽类别
    property bool defect_show_enable: true
    property bool un_defect_show: false
    function setAllDefectShow(value){

    }
}
