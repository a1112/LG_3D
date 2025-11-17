import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
ColumnLayout {
    property bool isCurrentView:  leftCore.searchPageIndex == currentIndex
    onIsCurrentViewChanged: {
        swipe.height = height
    }


}
