import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, InputNumber, Modal, Radio, Tabs, message } from 'antd'

import { area2dApi } from '@/services/api'
import { useUiSettingsStore } from '@/stores/uiSettingsStore'
import {
  buildAreaClipPayloadFromSettings,
  buildQmlAreaClipSettingsFromStatus,
  normalizeAreaSurfaceKey,
  type AreaClipMode,
  type AreaSurfaceKey,
  type QmlAreaClipSettings,
} from '@/utils/area2d'
import './ClipSettingModal.css'

interface ClipSettingModalProps {
  open: boolean
  onClose: () => void
}

interface ClipSurfacePanelProps {
  setting: QmlAreaClipSettings
  saving: boolean
  onApply: (setting: QmlAreaClipSettings) => void
  onChange: (patch: Partial<QmlAreaClipSettings>) => void
}

function numberValue(value: number | null, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function ClipSurfacePanel({ setting, saving, onApply, onChange }: ClipSurfacePanelProps) {
  const dynamicDisabled = setting.mode !== 'dynamic'
  const fixedDisabled = setting.mode !== 'fixed'

  return (
    <div className="clip-setting-panel">
      <div className="clip-setting-row">
        <span>裁剪模式</span>
        <Radio.Group
          value={setting.mode}
          onChange={(event) => onChange({ mode: event.target.value as AreaClipMode })}
        >
          <Radio value="fixed">固定</Radio>
          <Radio value="dynamic">动态</Radio>
        </Radio.Group>
      </div>

      <div className="clip-setting-row">
        <span>固定裁剪值</span>
        <InputNumber
          disabled={fixedDisabled}
          min={0}
          max={10000}
          precision={0}
          value={setting.fixed}
          onChange={(value) => onChange({ fixed: numberValue(value, setting.fixed) })}
        />
      </div>

      <div className="clip-setting-row">
        <span>基础距离(c)</span>
        <InputNumber
          disabled={dynamicDisabled}
          min={-100000}
          max={100000}
          step={0.001}
          precision={3}
          value={setting.c}
          onChange={(value) => onChange({ c: numberValue(value, setting.c) })}
        />
      </div>

      <div className="clip-setting-row">
        <span>一次方程 a</span>
        <InputNumber
          disabled={dynamicDisabled}
          min={-100000}
          max={100000}
          step={0.001}
          precision={3}
          value={setting.a}
          onChange={(value) => onChange({ a: numberValue(value, setting.a) })}
        />
      </div>

      <div className="clip-setting-row">
        <span>一次方程 b</span>
        <InputNumber
          disabled={dynamicDisabled}
          min={-100000}
          max={100000}
          step={0.001}
          precision={3}
          value={setting.b}
          onChange={(value) => onChange({ b: numberValue(value, setting.b) })}
        />
      </div>

      <div className="clip-setting-formula">公式: (x-c)*a+b</div>

      <div className="clip-setting-actions">
        <Button type="primary" loading={saving} onClick={() => onApply(setting)}>
          应用 {setting.label}
        </Button>
      </div>
    </div>
  )
}

export default function ClipSettingModal({ open, onClose }: ClipSettingModalProps) {
  const [activeSurface, setActiveSurface] = useState<AreaSurfaceKey>('S')
  const [savingSurface, setSavingSurface] = useState<AreaSurfaceKey | null>(null)
  const lastHydratedStatusRef = useRef<unknown>(null)
  const areaClipSettings = useUiSettingsStore((state) => state.areaClipSettings)
  const setAreaClipSetting = useUiSettingsStore((state) => state.setAreaClipSetting)
  const { data: areaStatusData } = useQuery({
    queryKey: ['area2d', 'clipSettingStatus'],
    queryFn: area2dApi.getStatus,
    enabled: open,
    retry: 1,
  })

  useEffect(() => {
    if (!open) {
      lastHydratedStatusRef.current = null
      return
    }
    if (!areaStatusData || lastHydratedStatusRef.current === areaStatusData) return

    lastHydratedStatusRef.current = areaStatusData
    const settingsFromStatus = buildQmlAreaClipSettingsFromStatus(
      areaStatusData,
      useUiSettingsStore.getState().areaClipSettings,
    )
    settingsFromStatus.forEach((setting) => {
      setAreaClipSetting(setting.surfaceKey, setting)
    })
  }, [areaStatusData, open, setAreaClipSetting])

  const updateSetting = (surfaceKey: AreaSurfaceKey, patch: Partial<QmlAreaClipSettings>) => {
    const current = areaClipSettings.find((item) => item.surfaceKey === surfaceKey)
    if (!current) return
    setAreaClipSetting(surfaceKey, { ...current, ...patch, surfaceKey })
  }

  const applySetting = async (setting: QmlAreaClipSettings) => {
    setSavingSurface(setting.surfaceKey)
    try {
      await area2dApi.setClipConfig(setting.surfaceKey, buildAreaClipPayloadFromSettings(setting))
      message.success(`${setting.label}裁剪参数已发送`)
    } catch {
      message.error(`${setting.label}裁剪参数发送失败`)
    } finally {
      setSavingSurface(null)
    }
  }

  return (
    <Modal
      className="clip-setting-window"
      title={null}
      open={open}
      width={720}
      footer={null}
      onCancel={onClose}
      destroyOnHidden
    >
      <div className="clip-setting-modal" data-qml-clip-setting-view>
        <h3 className="clip-setting-title" data-qml-clip-setting-title>
          裁剪设置
        </h3>
        <Tabs
          activeKey={activeSurface}
          onChange={(key) => setActiveSurface(normalizeAreaSurfaceKey(key))}
          items={areaClipSettings.map((setting) => ({
            key: setting.surfaceKey,
            label: setting.label,
            children: (
              <fieldset className="clip-setting-group" data-qml-clip-group-box>
                <legend data-qml-clip-group-title>{setting.label}</legend>
                <ClipSurfacePanel
                  setting={setting}
                  saving={savingSurface === setting.surfaceKey}
                  onApply={applySetting}
                  onChange={(patch) => updateSetting(setting.surfaceKey, patch)}
                />
              </fieldset>
            ),
          }))}
        />
        <div className="clip-setting-footer">
          <Button onClick={onClose}>关闭</Button>
        </div>
      </div>
    </Modal>
  )
}
