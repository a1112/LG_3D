import QtQuick

Item {


    property SaveFileDuialog saveFileDuialog: SaveFileDuialog{}


    function save_sql(func){
        saveFileDuialog.nameFilters=["sql file (.sql )"]
        saveFileDuialog.acceptFunc=func

        saveFileDuialog.open()

    }
}
