import QtQuick 2.15
import "Auth"

Item {

    property User currentUser: User{
        name:"用户模式"
        key: "user"
    }
    Component.onCompleted:{
        setUserByKey(currentUser.key)
    }
    function setUserByKey(key){
        currentUser.key = key
        let item=getItemByKey(key)
        currentUser.name =item.name
        currentUser.level =item.level
    }


    property bool isAdmin: currentUser.level > 1



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
            if (userModels.get(i).key == key){
                return userModels.get(i)
            }
        }
        return userModels.get(0)
    }


}
