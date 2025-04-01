import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../CardBase"

RowLayout{
    CardBaseView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            card_id:"defectViewL"
        }
    CardBaseView {
        Layout.fillWidth: true
        Layout.fillHeight: true
        card_id:"defectViewR"
    }
}
