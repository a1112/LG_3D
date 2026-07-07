import { Modal, Spin, Tag } from 'antd'
import { useQuery } from '@tanstack/react-query'

import { coilApi } from '@/services/api'
import type { CoilData } from '@/types'
import {
  buildCurrentCoilAlarmSections,
  buildCurrentCoilBaseRows,
  buildCurrentCoilPlcRows,
  buildCurrentCoilStateSections,
  type CoilAlarmSection,
  type DetailRow,
} from '@/utils/currentCoilDetail'
import './CurrentCoilDetailModal.css'

interface CurrentCoilDetailModalProps {
  open: boolean
  coil: CoilData | null
  onClose: () => void
}

function DetailGrid({ rows }: { rows: DetailRow[] }) {
  return (
    <div className="current-detail-grid">
      {rows.map((row, index) => (
        <div className="current-detail-row" key={`${row.key}-${index}`}>
          <span>{row.key}:</span>
          <strong data-qml-msg-row-value>{row.value}</strong>
        </div>
      ))}
    </div>
  )
}

function alarmLevelColor(level: number): string {
  if (level >= 3) return 'red'
  if (level === 2) return 'gold'
  if (level === 1) return 'green'
  return 'default'
}

function alarmLevelText(level: number): string {
  if (level >= 3) return '严重'
  if (level === 2) return '预警'
  if (level === 1) return '正常'
  return '无数据'
}

function AlarmSectionGrid({ sections }: { sections: CoilAlarmSection[] }) {
  return (
    <div className="current-detail-alarm-sections">
      {sections.map((section) => (
        <section key={section.title}>
          <h3>
            {section.title}
            <Tag color={alarmLevelColor(section.level)}>{alarmLevelText(section.level)}</Tag>
          </h3>
          <DetailGrid rows={section.rows} />
        </section>
      ))}
    </div>
  )
}

export default function CurrentCoilDetailModal({ open, coil, onClose }: CurrentCoilDetailModalProps) {
  const coilId = coil?.id ?? 0
  const enabled = open && coilId > 0
  const { data: plcData, isFetching: isFetchingPlc } = useQuery({
    queryKey: ['coil', 'plcData', coilId],
    queryFn: () => coilApi.getPlcData(coilId),
    enabled,
  })
  const { data: coilStateData, isFetching: isFetchingState } = useQuery({
    queryKey: ['coil', 'state', coilId],
    queryFn: () => coilApi.getCoilState(coilId),
    enabled,
  })
  const { data: coilAlarmData, isFetching: isFetchingAlarm } = useQuery({
    queryKey: ['coil', 'alarm', coilId],
    queryFn: () => coilApi.getCoilAlarm(coilId),
    enabled,
  })

  const baseRows = [...buildCurrentCoilBaseRows(coil), ...buildCurrentCoilPlcRows(plcData)]
  const stateSections = buildCurrentCoilStateSections(coilStateData)
  const alarmSections = buildCurrentCoilAlarmSections(coilAlarmData)
  const loading = isFetchingPlc || isFetchingState || isFetchingAlarm

  return (
    <Modal
      className="current-detail-window"
      title={null}
      open={open}
      width={700}
      footer={null}
      onCancel={onClose}
      destroyOnHidden
    >
      <div className="current-detail-modal" data-qml-msg-pop-view>
        <h3 className="current-detail-title" data-qml-msg-pop-title>
          详细信息
        </h3>
        {loading && (
          <div className="current-detail-loading">
            <Spin size="small" />
          </div>
        )}
        <DetailGrid rows={baseRows} />
        <div className="current-detail-surfaces">
          <section>
            <h3>{stateSections.S.title}</h3>
            <DetailGrid rows={stateSections.S.rows} />
          </section>
          <section>
            <h3>{stateSections.L.title}</h3>
            <DetailGrid rows={stateSections.L.rows} />
          </section>
        </div>
        <AlarmSectionGrid sections={alarmSections} />
      </div>
    </Modal>
  )
}
