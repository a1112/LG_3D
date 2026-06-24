pyinstaller -i app.ico -n lis --add-data "main.qml;." --add-data "qml;qml" --add-data "qtquickcontrols2.conf;." --add-data "config;config" main.py
