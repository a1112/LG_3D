import QtQuick

Item {


    property SaveFileDuialog saveFileDuialog: SaveFileDuialog{}

    SelectColorDialog{
        id:selectColorDialog

    }


    function save_sql(func){
        saveFileDuialog.nameFilters=["sql file (*.sql)","sqlite3 file (*.db)","csv file(*.csv)"]
        saveFileDuialog.acceptFunc=func

        saveFileDuialog.open()
    }

    function selectColor(func){
        console.log("selectColor")
        selectColorDialog.acceptFunc = func
        selectColorDialog.open()


    }
}
