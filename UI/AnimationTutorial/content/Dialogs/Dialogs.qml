import QtQuick

Item {


    property SaveFileDuialog saveFileDuialog: SaveFileDuialog{}


    function save_sql(func){
        saveFileDuialog.nameFilters=["sql file (*.sql)","sqlite3 file (*.db)","csv file(*.csv)"]
        saveFileDuialog.acceptFunc=func

        saveFileDuialog.open()

    }
}
