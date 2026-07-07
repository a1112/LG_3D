import { describe, expect, it } from 'vitest'

import {
  buildCurrentCoilAlarmSections,
  buildCurrentCoilBaseRows,
  buildCurrentCoilPlcRows,
  buildCurrentCoilStateSections,
} from './currentCoilDetail'

describe('currentCoilDetail', () => {
  it('builds QML-compatible current coil base rows from normalized and raw fields', () => {
    const rows = buildCurrentCoilBaseRows({
      id: 42,
      coilNo: 'C-42',
      dateTime: '',
      status: 2,
      surfaceKey: 'S',
      raw: {
        coilType: 'SPHC',
        coilInside: 610,
        coilDia: 1800,
        coilThickness: 2.5,
        coilWidth: 1250,
        coilActWidth: 1248,
        nextInfo: 'A1',
      },
    })

    expect(rows).toEqual([
      { key: '流水号', value: '42' },
      { key: '卷号', value: 'C-42' },
      { key: '钢种', value: 'SPHC' },
      { key: '内径', value: '610' },
      { key: '外径', value: '1800' },
      { key: '厚度', value: '2.5' },
      { key: '生产宽度', value: '1250' },
      { key: '实际宽度', value: '1248' },
      { key: '去向', value: 'A1' },
    ])
  })

  it('uses Python/Rust summary field aliases in current coil base rows', () => {
    const rows = buildCurrentCoilBaseRows({
      id: 1701,
      coilNo: 'LG-1701',
      dateTime: '',
      status: 2,
      surfaceKey: 'L',
      raw: {
        CoilType: 'SPCC',
        CoilInside: 610,
        CoilDia: 1810,
        Thickness: 2.75,
        Width: 1260,
        ActWidth: 1256,
        NextInfo: '精整',
      },
    })

    expect(rows).toContainEqual({ key: '厚度', value: '2.75' })
    expect(rows).toContainEqual({ key: '生产宽度', value: '1260' })
    expect(rows).toContainEqual({ key: '实际宽度', value: '1256' })
    expect(rows).toContainEqual({ key: '去向', value: '精整' })
  })

  it('adds PLC rows only for QML-supported non-null fields', () => {
    expect(
      buildCurrentCoilPlcRows({
        location_S: 10.5,
        location_L: null,
        location_laser: 88,
      }),
    ).toEqual([
      { key: '设备位置_S', value: '10.5' },
      { key: '激光', value: '88' },
    ])
  })

  it('formats S and L coil-state sections with QML labels and precision', () => {
    const sections = buildCurrentCoilStateSections([
      {
        surface: 'S',
        scan3dCoordinateScaleX: 0.339436,
        scan3dCoordinateScaleY: 1,
        scan3dCoordinateScaleZ: 0.0161155,
        colorFromValue_mm: -20,
        colorToValue_mm: 20,
        lowerLimit: -3102.597,
        upperLimit: 6205.195,
        start: 46595.4,
        step: 2483,
        rotate: -90,
        x_rotate: 10,
        median_3d: 47837.4,
        median_3d_mm: 770.9248,
        width: 6995,
        height: 5180,
        mask_area: 25249781,
        lowerArea: 178691,
        upperArea: 925,
        lowerArea_percent: 0.00707693,
        upperArea_percent: 0.0000366339,
      },
      {
        surface: 'L',
        scan3dCoordinateScaleX: 0.1,
      },
    ])

    expect(sections.S.rows.slice(0, 3)).toEqual([
      { key: '标定X', value: '0.3394' },
      { key: '标定Y', value: '1.0000' },
      { key: '标定Z', value: '0.0161' },
    ])
    expect(sections.S.rows).toContainEqual({ key: '下报警%', value: '0.71' })
    expect(sections.S.rows).toContainEqual({ key: '上报警%', value: '0.00' })
    expect(sections.L.rows[0]).toEqual({ key: '标定X', value: '0.1000' })
  })

  it('summarizes QML coilAlarm data for flat-roll, taper-shape, and loose-coil sections', () => {
    const sections = buildCurrentCoilAlarmSections({
      FlatRoll: {
        S: { inner_circle_width: 2000, out_circle_width: 3600, accuracy_x: 0.34, level: 1 },
        L: { inner_circle_width: 1980, out_circle_width: 3610, accuracy_x: 0.34, level: 2 },
      },
      TaperShape: {
        S: [
          {
            out_taper_max_value: 12.34,
            out_taper_min_value: -18.6,
            in_taper_max_value: 4.4,
            in_taper_min_value: -6.7,
            rotation_angle: 90,
            level: 1,
          },
        ],
        L: [
          {
            out_taper_max_value: 80.1,
            out_taper_min_value: -21,
            in_taper_max_value: 3.1,
            in_taper_min_value: -2.9,
            rotation_angle: 180,
            level: 3,
          },
        ],
      },
      LooseCoil: {
        S: [{ max_width: 130, data: '{"max_width_unit":"px","max_width_px":130}' }],
        L: [{ max_width: 26.5, data: '{"max_width_unit":"mm","max_width_mm":26.5}' }],
      },
    })

    expect(sections.map((section) => `${section.title}:${section.level}`)).toEqual([
      '扁卷检测:2',
      '塔形检测:3',
      '松卷检测:3',
    ])
    expect(sections[0].rows).toContainEqual({ key: '内径测量', value: '676.60 mm' })
    expect(sections[0].rows).toContainEqual({ key: 'S端内径', value: '680.00 mm' })
    expect(sections[1].rows).toContainEqual({ key: 'L端外塔形最高', value: '80.1' })
    expect(sections[1].rows).toContainEqual({ key: 'S端内塔形最低', value: '-6.7' })
    expect(sections[2].rows).toContainEqual({ key: '最大松卷宽度', value: '130.00 mm' })
  })
})
