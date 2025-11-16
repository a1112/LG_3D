import QtQuick
import QtQuick.Controls


Item {
    property string name: ""

        property string key: ""

    property string password: ""
    property string email: ""

    property int level: 0

    property Role roles: Role{

    }
    property Session session
    property Token token

}
