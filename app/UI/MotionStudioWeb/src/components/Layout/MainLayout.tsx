import { useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertOutlined,
  ApiOutlined,
  BugOutlined,
  CloseOutlined,
  DatabaseOutlined,
  FullscreenOutlined,
  MenuOutlined,
  MinusOutlined,
  SettingOutlined,
} from '@ant-design/icons'

import OperationSidebar from '@/components/OperationSidebar'
import SettingsPanel from '@/components/SettingsPanel'
import { settingsApi } from '@/services/api'
import { hasTauriRuntime, tauriWindow } from '@/utils/tauriWindow'
import './MainLayout.css'

function ServiceLight({ label, state }: { label: string; state: 'ok' | 'warn' | 'error' }) {
  return (
    <span className={`service-light ${state}`}>
      <i />
      {label}
    </span>
  )
}

function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const isDefect = location.pathname.includes('defect')
  const [settingsOpen, setSettingsOpen] = useState(false)

  const { data: testModeStatus } = useQuery({
    queryKey: ['settings', 'testModeStatus'],
    queryFn: settingsApi.getTestModeStatus,
    retry: 1,
    staleTime: 30_000,
  })

  const testModeEnabled =
    !!testModeStatus &&
    typeof testModeStatus === 'object' &&
    Boolean((testModeStatus as Record<string, unknown>).developer_mode ?? (testModeStatus as Record<string, unknown>).test_mode)

  return (
    <div className="motion-shell">
      <header className="motion-titlebar" data-tauri-drag-region onDoubleClick={() => tauriWindow.toggleMaximize()}>
        <button className="icon-button" type="button" title="主菜单">
          <MenuOutlined />
        </button>
        <div className="brand-block" onClick={() => navigate('/data')}>
          <div className="brand-mark">MS</div>
          <div>
            <div className="brand-title">涟钢3D端面检测系统</div>
            <div className="brand-subtitle">Motion Studio · Tauri + React</div>
          </div>
        </div>

        <nav className="top-tabs" data-no-drag>
          <NavLink to="/data" className={({ isActive }) => (isActive || !isDefect ? 'active' : '')}>
            数据展示
          </NavLink>
          <NavLink to="/defect" className={({ isActive }) => (isActive ? 'active' : '')}>
            缺陷检测
          </NavLink>
        </nav>

        <div className="titlebar-tools" data-no-drag>
          <ServiceLight label="PLC" state="ok" />
          <ServiceLight label="Redis" state="ok" />
          <ServiceLight label="FastAPI" state="warn" />
          <span className={`test-mode-badge ${testModeEnabled ? 'enabled' : 'normal'}`}>
            {testModeEnabled ? '测试模式' : '生产模式'}
          </span>
          <span className="global-alarm">
            <AlertOutlined />
            全局报警
          </span>
          <button className="icon-button" type="button" title="接口">
            <ApiOutlined />
          </button>
          <button className="icon-button" type="button" title="缓存">
            <DatabaseOutlined />
          </button>
          <button className="icon-button" type="button" title="设置" onClick={() => setSettingsOpen(true)}>
            <SettingOutlined />
          </button>
          <button className="icon-button" type="button" title="最小化" onClick={() => tauriWindow.minimize()}>
            <MinusOutlined />
          </button>
          <button
            className="icon-button"
            type="button"
            title="最大化"
            onClick={() => tauriWindow.toggleMaximize()}
          >
            <FullscreenOutlined />
          </button>
          <button className="icon-button danger" type="button" title="关闭" onClick={() => tauriWindow.close()}>
            <CloseOutlined />
          </button>
        </div>
      </header>

      <main className="motion-main">
        <OperationSidebar />
        <section className="workspace">
          <Outlet />
        </section>
      </main>

      <footer className="motion-statusbar">
        <span>{hasTauriRuntime() ? 'Tauri native shell' : 'Web preview mode'}</span>
        <span>图像 / 缺陷 / 3D数据 分级加载</span>
        <span>
          <BugOutlined /> 缺陷数据随卷材与表面切换刷新
        </span>
      </footer>
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}

export default MainLayout
