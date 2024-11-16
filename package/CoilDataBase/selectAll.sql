SELECT anon_1.`SecondaryCoil_Id` AS `anon_1_SecondaryCoil_Id`,
       anon_1.`SecondaryCoil_CoilNo` AS `anon_1_SecondaryCoil_CoilNo`,
       anon_1.`SecondaryCoil_CoilType` AS `anon_1_SecondaryCoil_CoilType`,
       anon_1.`SecondaryCoil_CoilInside` AS `anon_1_SecondaryCoil_CoilInside`,
       anon_1.`SecondaryCoil_CoilDia` AS `anon_1_SecondaryCoil_CoilDia`,
       anon_1.`SecondaryCoil_Thickness` AS `anon_1_SecondaryCoil_Thickness`,
       anon_1.`SecondaryCoil_Width` AS `anon_1_SecondaryCoil_Width`,
       anon_1.`SecondaryCoil_Weight` AS `anon_1_SecondaryCoil_Weight`,
       anon_1.`SecondaryCoil_ActWidth` AS `anon_1_SecondaryCoil_ActWidth`,
       anon_1.`SecondaryCoil_CreateTime` AS `anon_1_SecondaryCoil_CreateTime`,
       `Coil_1`.`Id` AS `Coil_1_Id`,
       `Coil_1`.`SecondaryCoilId` AS `Coil_1_SecondaryCoilId`,
       `Coil_1`.`DetectionTime` AS `Coil_1_DetectionTime`,
       `Coil_1`.`DefectCountS` AS `Coil_1_DefectCountS`,
       `Coil_1`.`DefectCountL` AS `Coil_1_DefectCountL`,
       `Coil_1`.`CheckStatus` AS `Coil_1_CheckStatus`,
       `Coil_1`.`Status_L` AS `Coil_1_Status_L`,
       `Coil_1`.`Status_S` AS `Coil_1_Status_S`,
       `Coil_1`.`Grade` AS `Coil_1_Grade`,
       `Coil_1`.`Msg` AS `Coil_1_Msg`,
       `CoilState_1`.`Id` AS `CoilState_1_Id`,
       `CoilState_1`.`secondaryCoilId` AS `CoilState_1_secondaryCoilId`,
       `CoilState_1`.surface AS `CoilState_1_surface`,
       `CoilState_1`.`startTime` AS `CoilState_1_startTime`,
       `CoilState_1`.`scan3dCoordinateScaleX` AS `CoilState_1_scan3dCoordinateScaleX`,
       `CoilState_1`.`scan3dCoordinateScaleY` AS `CoilState_1_scan3dCoordinateScaleY`,
       `CoilState_1`.`scan3dCoordinateScaleZ` AS `CoilState_1_scan3dCoordinateScaleZ`,
       `CoilState_1`.rotate AS `CoilState_1_rotate`,
       `CoilState_1`.x_rotate AS `CoilState_1_x_rotate`,
       `CoilState_1`.median_3d AS `CoilState_1_median_3d`,
       `CoilState_1`.median_3d_mm AS `CoilState_1_median_3d_mm`,
       `CoilState_1`.`colorFromValue_mm` AS `CoilState_1_colorFromValue_mm`,
       `CoilState_1`.`colorToValue_mm` AS `CoilState_1_colorToValue_mm`,
       `CoilState_1`.start AS `CoilState_1_start`,
       `CoilState_1`.step AS `CoilState_1_step`,
       `CoilState_1`.`upperLimit` AS `CoilState_1_upperLimit`,
       `CoilState_1`.`lowerLimit` AS `CoilState_1_lowerLimit`,
       `CoilState_1`.`lowerArea` AS `CoilState_1_lowerArea`,
       `CoilState_1`.`upperArea` AS `CoilState_1_upperArea`,
       `CoilState_1`.`lowerArea_percent` AS `CoilState_1_lowerArea_percent`,
       `CoilState_1`.`upperArea_percent` AS `CoilState_1_upperArea_percent`,
       `CoilState_1`.mask_area AS `CoilState_1_mask_area`,
       `CoilState_1`.width AS `CoilState_1_width`,
       `CoilState_1`.height AS `CoilState_1_height`,
       `CoilState_1`.`jsonData` AS `CoilState_1_jsonData`,
       `CoilDefect_1`.`Id` AS `CoilDefect_1_Id`,
       `CoilDefect_1`.`secondaryCoilId` AS `CoilDefect_1_secondaryCoilId`,
       `CoilDefect_1`.surface AS `CoilDefect_1_surface`,
       `CoilDefect_1`.`defectClass` AS `CoilDefect_1_defectClass`,
       `CoilDefect_1`.`defectName` AS `CoilDefect_1_defectName`,
       `CoilDefect_1`.`defectStatus` AS `CoilDefect_1_defectStatus`,
       `CoilDefect_1`.`defectTime` AS `CoilDefect_1_defectTime`,
       `CoilDefect_1`.`defectX` AS `CoilDefect_1_defectX`,
       `CoilDefect_1`.`defectY` AS `CoilDefect_1_defectY`,
       `CoilDefect_1`.`defectW` AS `CoilDefect_1_defectW`,
       `CoilDefect_1`.`defectH` AS `CoilDefect_1_defectH`,
       `CoilDefect_1`.`defectSource` AS `CoilDefect_1_defectSource`,
       `CoilDefect_1`.`defectData` AS `CoilDefect_1_defectData`,
       `CoilAlarmStatus_1`.`Id` AS `CoilAlarmStatus_1_Id`,
       `CoilAlarmStatus_1`.`secondaryCoilId` AS `CoilAlarmStatus_1_secondaryCoilId`,
       `CoilAlarmStatus_1`.surface AS `CoilAlarmStatus_1_surface`,
       `CoilAlarmStatus_1`.level AS `CoilAlarmStatus_1_level`,
       `CoilAlarmStatus_1`.`alarmStatus` AS `CoilAlarmStatus_1_alarmStatus`,
       `CoilAlarmStatus_1`.`alarmFlatRoll` AS `CoilAlarmStatus_1_alarmFlatRoll`,
       `CoilAlarmStatus_1`.`alarmTaper` AS `CoilAlarmStatus_1_alarmTaper`,
       `CoilAlarmStatus_1`.`alarmFolding` AS `CoilAlarmStatus_1_alarmFolding`,
       `CoilAlarmStatus_1`.`alarmDefect` AS `CoilAlarmStatus_1_alarmDefect`,
       `CoilAlarmStatus_1`.`crateTime` AS `CoilAlarmStatus_1_crateTime`,
       `CoilAlarmStatus_1`.data AS `CoilAlarmStatus_1_data`,
       `AlarmFlatRoll_1`.`Id` AS `AlarmFlatRoll_1_Id`,
       `AlarmFlatRoll_1`.`secondaryCoilId` AS `AlarmFlatRoll_1_secondaryCoilId`,
       `AlarmFlatRoll_1`.surface AS `AlarmFlatRoll_1_surface`,
       `AlarmFlatRoll_1`.out_circle_width AS `AlarmFlatRoll_1_out_circle_width`,
       `AlarmFlatRoll_1`.out_circle_height AS `AlarmFlatRoll_1_out_circle_height`,
       `AlarmFlatRoll_1`.out_circle_center_x AS `AlarmFlatRoll_1_out_circle_center_x`,
       `AlarmFlatRoll_1`.out_circle_center_y AS `AlarmFlatRoll_1_out_circle_center_y`,
       `AlarmFlatRoll_1`.out_circle_radius AS `AlarmFlatRoll_1_out_circle_radius`,
       `AlarmFlatRoll_1`.inner_circle_width AS `AlarmFlatRoll_1_inner_circle_width`,
       `AlarmFlatRoll_1`.inner_circle_height AS `AlarmFlatRoll_1_inner_circle_height`,
       `AlarmFlatRoll_1`.inner_circle_center_x AS `AlarmFlatRoll_1_inner_circle_center_x`,
       `AlarmFlatRoll_1`.inner_circle_center_y AS `AlarmFlatRoll_1_inner_circle_center_y`,
       `AlarmFlatRoll_1`.inner_circle_radius AS `AlarmFlatRoll_1_inner_circle_radius`,
       `AlarmFlatRoll_1`.accuracy_x AS `AlarmFlatRoll_1_accuracy_x`,
       `AlarmFlatRoll_1`.accuracy_y AS `AlarmFlatRoll_1_accuracy_y`,
       `AlarmFlatRoll_1`.level AS `AlarmFlatRoll_1_level`,
       `AlarmFlatRoll_1`.err_msg AS `AlarmFlatRoll_1_err_msg`,
       `AlarmFlatRoll_1`.`crateTime` AS `AlarmFlatRoll_1_crateTime`,
       `AlarmFlatRoll_1`.data AS `AlarmFlatRoll_1_data`,
       `TaperShapePoint_1`.`Id` AS `TaperShapePoint_1_Id`,
       `TaperShapePoint_1`.`secondaryCoilId` AS `TaperShapePoint_1_secondaryCoilId`,
       `TaperShapePoint_1`.surface AS `TaperShapePoint_1_surface`,
       `TaperShapePoint_1`.x AS `TaperShapePoint_1_x`,
       `TaperShapePoint_1`.y AS `TaperShapePoint_1_y`,
       `TaperShapePoint_1`.value AS `TaperShapePoint_1_value`,
       `TaperShapePoint_1`.level AS `TaperShapePoint_1_level`,
       `TaperShapePoint_1`.err_msg AS `TaperShapePoint_1_err_msg`,
       `TaperShapePoint_1`.`crateTime` AS `TaperShapePoint_1_crateTime`,
       `TaperShapePoint_1`.data AS `TaperShapePoint_1_data`,
       `AlarmInfo_1`.`Id` AS `AlarmInfo_1_Id`,
       `AlarmInfo_1`.`secondaryCoilId` AS `AlarmInfo_1_secondaryCoilId`,
       `AlarmInfo_1`.surface AS `AlarmInfo_1_surface`,
       `AlarmInfo_1`.`nextCode` AS `AlarmInfo_1_nextCode`,
       `AlarmInfo_1`.`nextName` AS `AlarmInfo_1_nextName`,
       `AlarmInfo_1`.`taperShapeGrad` AS `AlarmInfo_1_taperShapeGrad`,
       `AlarmInfo_1`.`taperShapeMsg` AS `AlarmInfo_1_taperShapeMsg`,
       `AlarmInfo_1`.`looseCoilGrad` AS `AlarmInfo_1_looseCoilGrad`,
       `AlarmInfo_1`.`looseCoilMsg` AS `AlarmInfo_1_looseCoilMsg`,
       `AlarmInfo_1`.`flatRollGrad` AS `AlarmInfo_1_flatRollGrad`,
       `AlarmInfo_1`.`flatRollMsg` AS `AlarmInfo_1_flatRollMsg`,
       `AlarmInfo_1`.`defectGrad` AS `AlarmInfo_1_defectGrad`,
       `AlarmInfo_1`.`defectMsg` AS `AlarmInfo_1_defectMsg`,
       `AlarmInfo_1`.grad AS `AlarmInfo_1_grad`,
       `AlarmInfo_1`.`crateTime` AS `AlarmInfo_1_crateTime`,
       `AlarmInfo_1`.data AS `AlarmInfo_1_data`,
       `PlcData_1`.`Id` AS `PlcData_1_Id`,
       `PlcData_1`.`secondaryCoilId` AS `PlcData_1_secondaryCoilId`,
       `PlcData_1`.`location_S` AS `PlcData_1_location_S`,
       `PlcData_1`.`location_L` AS `PlcData_1_location_L`,
       `PlcData_1`.location_laser AS `PlcData_1_location_laser`,
       `PlcData_1`.`startTime` AS `PlcData_1_startTime`,
       `PlcData_1`.`pclData` AS `PlcData_1_pclData`,
       `AlarmTaperShape_1`.`Id` AS `AlarmTaperShape_1_Id`,
       `AlarmTaperShape_1`.`secondaryCoilId` AS `AlarmTaperShape_1_secondaryCoilId`,
       `AlarmTaperShape_1`.surface AS `AlarmTaperShape_1_surface`,
       `AlarmTaperShape_1`.out_taper_max_x AS `AlarmTaperShape_1_out_taper_max_x`,
       `AlarmTaperShape_1`.out_taper_max_y AS `AlarmTaperShape_1_out_taper_max_y`,
       `AlarmTaperShape_1`.out_taper_max_value AS `AlarmTaperShape_1_out_taper_max_value`,
       `AlarmTaperShape_1`.out_taper_min_x AS `AlarmTaperShape_1_out_taper_min_x`,
       `AlarmTaperShape_1`.out_taper_min_y AS `AlarmTaperShape_1_out_taper_min_y`,
       `AlarmTaperShape_1`.out_taper_min_value AS `AlarmTaperShape_1_out_taper_min_value`,
       `AlarmTaperShape_1`.in_taper_max_x AS `AlarmTaperShape_1_in_taper_max_x`,
       `AlarmTaperShape_1`.in_taper_max_y AS `AlarmTaperShape_1_in_taper_max_y`,
       `AlarmTaperShape_1`.in_taper_max_value AS `AlarmTaperShape_1_in_taper_max_value`,
       `AlarmTaperShape_1`.in_taper_min_x AS `AlarmTaperShape_1_in_taper_min_x`,
       `AlarmTaperShape_1`.in_taper_min_y AS `AlarmTaperShape_1_in_taper_min_y`,
       `AlarmTaperShape_1`.in_taper_min_value AS `AlarmTaperShape_1_in_taper_min_value`,
       `AlarmTaperShape_1`.rotation_angle AS `AlarmTaperShape_1_rotation_angle`,
       `AlarmTaperShape_1`.level AS `AlarmTaperShape_1_level`,
       `AlarmTaperShape_1`.err_msg AS `AlarmTaperShape_1_err_msg`,
       `AlarmTaperShape_1`.`crateTime` AS `AlarmTaperShape_1_crateTime`,
       `AlarmTaperShape_1`.data AS `AlarmTaperShape_1_data`,
       `AlarmLooseCoil_1`.`Id` AS `AlarmLooseCoil_1_Id`,
       `AlarmLooseCoil_1`.`secondaryCoilId` AS `AlarmLooseCoil_1_secondaryCoilId`,
       `AlarmLooseCoil_1`.surface AS `AlarmLooseCoil_1_surface`,
       `AlarmLooseCoil_1`.max_width AS `AlarmLooseCoil_1_max_width`,
       `AlarmLooseCoil_1`.rotation_angle AS `AlarmLooseCoil_1_rotation_angle`,
       `AlarmLooseCoil_1`.level AS `AlarmLooseCoil_1_level`,
       `AlarmLooseCoil_1`.err_msg AS `AlarmLooseCoil_1_err_msg`,
       `AlarmLooseCoil_1`.`crateTime` AS `AlarmLooseCoil_1_crateTime`,
       `AlarmLooseCoil_1`.data AS `AlarmLooseCoil_1_data`,
       `DetectionSpeed_1`.`Id` AS `DetectionSpeed_1_Id`,
       `DetectionSpeed_1`.`secondaryCoilId` AS `DetectionSpeed_1_secondaryCoilId`,
       `DetectionSpeed_1`.surface AS `DetectionSpeed_1_surface`,
       `DetectionSpeed_1`.`startTime` AS `DetectionSpeed_1_startTime`,
       `DetectionSpeed_1`.`endTime` AS `DetectionSpeed_1_endTime`,
       `DetectionSpeed_1`.`allTime` AS `DetectionSpeed_1_allTime`
FROM
    (
    SELECT
        `SecondaryCoil`.`Id` AS `SecondaryCoil_Id`,
        `SecondaryCoil`.`CoilNo` AS `SecondaryCoil_CoilNo`,
        `SecondaryCoil`.`CoilType` AS `SecondaryCoil_CoilType`,
        `SecondaryCoil`.`CoilInside` AS `SecondaryCoil_CoilInside`,
        `SecondaryCoil`.`CoilDia` AS `SecondaryCoil_CoilDia`,
        `SecondaryCoil`.`Thickness` AS `SecondaryCoil_Thickness`,
        `SecondaryCoil`.`Width` AS `SecondaryCoil_Width`,
        `SecondaryCoil`.`Weight` AS `SecondaryCoil_Weight`,
        `SecondaryCoil`.`ActWidth` AS `SecondaryCoil_ActWidth`,
        `SecondaryCoil`.`CreateTime` AS `SecondaryCoil_CreateTime`
    FROM
        `SecondaryCoil`
    ORDER BY
        `SecondaryCoil`.`Id` DESC
 LIMIT %(param_1)s) AS anon_1
        LEFT OUTER JOIN
        `Coil` AS `Coil_1`
            ON anon_1.`SecondaryCoil_Id` = `Coil_1`.`SecondaryCoilId`
        LEFT OUTER JOIN
        `CoilState` AS `CoilState_1`
            ON anon_1.`SecondaryCoil_Id` = `CoilState_1`.`secondaryCoilId`
        LEFT OUTER JOIN
        `CoilDefect` AS `CoilDefect_1`
            ON anon_1.`SecondaryCoil_Id` = `CoilDefect_1`.`secondaryCoilId`
        LEFT OUTER JOIN
        `CoilAlarmStatus` AS `CoilAlarmStatus_1`
            ON anon_1.`SecondaryCoil_Id` = `CoilAlarmStatus_1`.`secondaryCoilId`
        LEFT OUTER JOIN
        `AlarmFlatRoll` AS `AlarmFlatRoll_1`
            ON anon_1.`SecondaryCoil_Id` = `AlarmFlatRoll_1`.`secondaryCoilId`
        LEFT OUTER JOIN
        `TaperShapePoint` AS `TaperShapePoint_1`
            ON anon_1.`SecondaryCoil_Id` = `TaperShapePoint_1`.`secondaryCoilId`
        LEFT OUTER JOIN `AlarmInfo` AS `AlarmInfo_1`
            ON anon_1.`SecondaryCoil_Id` = `AlarmInfo_1`.`secondaryCoilId`
        LEFT OUTER JOIN `PlcData` AS `PlcData_1`
            ON anon_1.`SecondaryCoil_Id` = `PlcData_1`.`secondaryCoilId`
        LEFT OUTER JOIN `AlarmTaperShape` AS `AlarmTaperShape_1`
            ON anon_1.`SecondaryCoil_Id` = `AlarmTaperShape_1`.`secondaryCoilId`
        LEFT OUTER JOIN `AlarmLooseCoil` AS `AlarmLooseCoil_1`
            ON anon_1.`SecondaryCoil_Id` = `AlarmLooseCoil_1`.`secondaryCoilId`
        LEFT OUTER JOIN `DetectionSpeed` AS `DetectionSpeed_1`
            ON anon_1.`SecondaryCoil_Id` = `DetectionSpeed_1`.`secondaryCoilId`
ORDER BY
    anon_1.`SecondaryCoil_Id` DESC