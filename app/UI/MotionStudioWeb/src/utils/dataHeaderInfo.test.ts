import { describe, expect, it } from 'vitest'

import { buildDataHeaderInfoSections } from './dataHeaderInfo'

describe('dataHeaderInfo', () => {
  it('builds QML DataShowItemInfos taper-shape and flat-roll fields from /coilAlarm data', () => {
    const sections = buildDataHeaderInfoSections({
      TaperShape: {
        S: [
          {
            out_taper_max_value: 12.34,
            out_taper_min_value: -18.6,
            in_taper_max_value: 4.4,
            in_taper_min_value: -6.7,
            level: 1,
          },
        ],
        L: [
          {
            out_taper_max_value: 80.1,
            out_taper_min_value: -21,
            in_taper_max_value: 3.1,
            in_taper_min_value: -2.9,
            level: 3,
          },
        ],
      },
      FlatRoll: {
        S: {
          inner_circle_width: 2000,
          inner_circle_center_x: 3210.4,
          inner_circle_center_y: 2860.6,
          inner_circle_radius: 89.55,
          accuracy_x: 0.34,
        },
        L: {
          inner_circle_width: 1980,
          inner_circle_center_x: 3458.2,
          inner_circle_center_y: 2867.5,
          inner_circle_radius: 83.25,
          accuracy_x: 0.34,
        },
      },
    })

    expect(sections).toEqual([
      {
        title: '塔形报警',
        level: 3,
        fields: [
          { label: '外塔(mm)', value: '80.1' },
          { label: '内塔(mm)', value: '6.7' },
          { label: 'S端外塔', value: '12.3' },
          { label: 'S端内塔', value: '4.4' },
          { label: 'L端外塔', value: '80.1' },
          { label: 'L端内塔', value: '3.1' },
        ],
      },
      {
        title: '扁卷信息',
        level: 2,
        fields: [
          { label: '内径(mm)', value: '677' },
          { label: '等级', value: '2' },
          { label: 'S端内径', value: '680' },
          { label: 'L端内径', value: '673' },
          { label: 'S端中心', value: '3210,2861' },
          { label: 'L端中心', value: '3458,2868' },
          { label: 'S端旋转', value: '89.5' },
          { label: 'L端旋转', value: '83.3' },
        ],
      },
    ])
  })

  it('uses QML DataShowItemInfos defaults when alarm data is missing', () => {
    const sections = buildDataHeaderInfoSections({})

    expect(sections[0]).toMatchObject({
      title: '塔形报警',
      level: 1,
      fields: [
        { label: '外塔(mm)', value: '0.0' },
        { label: '内塔(mm)', value: '0.0' },
        { label: 'S端外塔', value: '--' },
        { label: 'S端内塔', value: '--' },
        { label: 'L端外塔', value: '--' },
        { label: 'L端内塔', value: '--' },
      ],
    })
    expect(sections[1]).toMatchObject({
      title: '扁卷信息',
      level: 0,
      fields: [
        { label: '内径(mm)', value: '--' },
        { label: '等级', value: '--' },
        { label: 'S端内径', value: '--' },
        { label: 'L端内径', value: '--' },
        { label: 'S端中心', value: '--' },
        { label: 'L端中心', value: '--' },
        { label: 'S端旋转', value: '--' },
        { label: 'L端旋转', value: '--' },
      ],
    })
  })

  it('uses QML DataShowItemInfos taper thresholds instead of row alarm level for the data-header dot', () => {
    const [taperSection] = buildDataHeaderInfoSections({
      TaperShape: {
        S: [
          {
            out_taper_max_value: 12,
            out_taper_min_value: -18,
            in_taper_max_value: 4,
            in_taper_min_value: -6,
            level: 3,
          },
        ],
        L: [
          {
            out_taper_max_value: 20,
            out_taper_min_value: -21,
            in_taper_max_value: 3,
            in_taper_min_value: -2,
            level: 3,
          },
        ],
      },
    })

    expect(taperSection.title).toBe('塔形报警')
    expect(taperSection.level).toBe(1)
    expect(taperSection.fields.slice(0, 2)).toEqual([
      { label: '外塔(mm)', value: '21.0' },
      { label: '内塔(mm)', value: '6.0' },
    ])
  })

  it('uses QML CoreFlatRollItem numeric defaults when a side record exists with missing fields', () => {
    const [, flatRollSection] = buildDataHeaderInfoSections({
      FlatRoll: {
        S: {},
      },
    })

    expect(flatRollSection).toMatchObject({
      title: '扁卷信息',
      level: 0,
      fields: [
        { label: '内径(mm)', value: '--' },
        { label: '等级', value: '--' },
        { label: 'S端内径', value: '-1' },
        { label: 'L端内径', value: '--' },
        { label: 'S端中心', value: '0,0' },
        { label: 'L端中心', value: '--' },
        { label: 'S端旋转', value: '0.0' },
        { label: 'L端旋转', value: '--' },
      ],
    })
  })
})
