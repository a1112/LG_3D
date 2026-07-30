import QtQuick

QtObject {
    id: root
    required property var controller
    readonly property int mouseMoveModel: 0
    readonly property int mouseSurveyModel:1
    property int currentMouseModel:mouseMoveModel
    property point hoverPoint: Qt.point(0,0)

    readonly property bool isMoveModel: currentMouseModel==mouseMoveModel
    readonly property bool isShowSurveyModel: currentMouseModel==mouseSurveyModel


    readonly property int surveyStateNone: 0
    readonly property int surveyStateRuning: 1
    readonly property int surveyStateEnd: 2
    property int currentSurveyState:surveyStateNone
    property bool isSurveyNone: currentSurveyState==surveyStateNone
    property bool isSurveying: currentSurveyState==surveyStateRuning
    property bool isSurveyEnd: currentSurveyState==surveyStateEnd

    property int surveyStartPointX: root.controller.toPx(surveyStartPoint.x)
    property int surveyStartPointY: root.controller.toPx(surveyStartPoint.y)

    property int surveyEndPointX: isSurveying ? hoverPoint.x
                                              : root.controller.toPx(surveyEndPoint.x)
    property int surveyEndPointY: isSurveying ? hoverPoint.y
                                              : root.controller.toPx(surveyEndPoint.y)

    property bool surveyCanView:isShowSurveyModel && (isSurveying||isSurveyEnd)

    property point surveyStartPoint: Qt.point(0,0)
    property point surveyEndPoint: Qt.point(0,0)

    function setSurveyPoint(point){
        if (isSurveyNone){
            surveyStartPoint = Qt.point(root.controller.pxto_top(point.x),
                                        root.controller.pxto_top(point.y))
            surveyEndPoint = surveyStartPoint
            currentSurveyState = surveyStateRuning

        }
        else if (isSurveying){
            surveyEndPoint = Qt.point(root.controller.pxto_top(point.x),
                                      root.controller.pxto_top(point.y))
            currentSurveyState = surveyStateEnd

        }
        else if (isSurveyEnd){
            currentSurveyState = surveyStateNone
        }

    }


    property bool taper_shape_annotation_enable:true
    property bool thumbnail_view_3d_enable:true
    property bool thumbnail_view_2d_enable:true


}
