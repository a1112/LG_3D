import QtQuick
import "Auth"
import "../Base"
Item {
    id:root
    property string key:"user"
    onKeyChanged:{
        setUserByKey(key)
    }


    property User currentUser: User{
        name:"用户模式"
        key: "user"
    }
    function setUserKey(key){
        root.key=key
    }

    function setUserByKey(key){
        let item=getItemByKey(key)
        currentUser.name =item.name
        currentUser.level =item.level
        currentUser.key =item.key
        }


    readonly property bool isAdmin: currentUser.level > 1



    property ListModel userModels:
    ListModel{
        ListElement{
            name: "用户模式"
            key:"user"
            level:1
        }
        ListElement{
            name: "维护模式"
            key:"maintainer"
            level:2
        }

        ListElement{
            name: "开发者模式"
            key:"developer"
            level:3
        }

    }

    function getItemByKey(key){
        for (var i = 0; i < userModels.count; i++){
            if (userModels.get(i).key === key){
                return userModels.get(i)
            }
        }
        return userModels.get(0)
    }

    SettingsBase{
        category:"authModel"
        property alias key: root.key
    }

}
