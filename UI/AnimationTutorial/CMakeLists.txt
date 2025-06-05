cmake_minimum_required(VERSION 3.18)

set(BUILD_QDS_COMPONENTS ON CACHE BOOL "Build design studio components")

project(AnimationTutorialApp LANGUAGES CXX)

set(CMAKE_INCLUDE_CURRENT_DIR ON)
set(CMAKE_AUTOMOC ON)


find_package(QT NAMES Qt6 COMPONENTS Charts Core Gui Quick Qml Graphs REQUIRED)

find_package(Qt6 REQUIRED COMPONENTS Charts)
find_package(Qt6 REQUIRED COMPONENTS Core)
find_package(Qt6 REQUIRED COMPONENTS Qml)
find_package(Qt6 REQUIRED COMPONENTS Quick)
find_package(Qt6 REQUIRED COMPONENTS Graphs)
# qt_standard_project_setup() requires Qt 6.3 or higher. See https://doc.qt.io/qt-6/qt-standard-project-setup.html for details.
if (${QT_VERSION_MINOR} GREATER_EQUAL 3)
qt6_standard_project_setup()
endif()


# set(CMAKE_WIN32_EXECUTABLE OFF)



if(WIN32)
    set(RCSOURCES ${RCSOURCES} resources.rc)
endif()

qt_add_executable(${CMAKE_PROJECT_NAME} WIN32
    src/main.cpp
    ${RCSOURCES}
    src/scriptlauncher.cpp src/scriptlauncher.h
    src/clipboard.cpp src/clipboard.h
    src/filedownloader.h src/filedownloader.cpp
    src/consolecontroller.h src/consolecontroller.cpp
)

qt_add_resources(${CMAKE_PROJECT_NAME} "configuration"
    PREFIX "/"
    FILES
        qtquickcontrols2.conf
)

target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE
    Qt${QT_VERSION_MAJOR}::Charts
    Qt${QT_VERSION_MAJOR}::Core
    Qt${QT_VERSION_MAJOR}::Gui
    Qt${QT_VERSION_MAJOR}::Quick
    Qt${QT_VERSION_MAJOR}::Qml
    Qt${QT_VERSION_MAJOR}::Graphs
)
if (${BUILD_QDS_COMPONENTS})
    include(${CMAKE_CURRENT_SOURCE_DIR}/qmlcomponents)
endif ()
include(${CMAKE_CURRENT_SOURCE_DIR}/qmlmodules)
