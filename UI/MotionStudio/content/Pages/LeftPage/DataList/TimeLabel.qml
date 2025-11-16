import QtQuick 2.15
import QtQuick.Controls 2.15
Row {
    spacing: 10
    Label{
        text: CreateTime["year"]+"年"+CreateTime["month"]+"月"+CreateTime["day"]+"日"
        color: "#747474"
    }
    Label{
        text: CreateTime["hour"]+"点"+CreateTime["minute"]+"分"+CreateTime["second"]

    }
}
