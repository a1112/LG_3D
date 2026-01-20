import { Layout, Menu } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { BarsOutlined, BugOutlined } from '@ant-design/icons'
import './MainLayout.css'

const { Header, Sider, Content } = Layout

function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/data',
      icon: <BarsOutlined />,
      label: '数据展示',
      onClick: () => navigate('/data'),
    },
    {
      key: '/defect',
      icon: <BugOutlined />,
      label: '缺陷检测',
      onClick: () => navigate('/defect'),
    },
  ]

  return (
    <Layout className="main-layout">
      <Header className="layout-header">
        <div className="logo">Motion Studio - 3D卷材端面检测系统</div>
      </Header>
      <Layout>
        <Sider width={200} theme="light">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        <Content className="layout-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}

export default MainLayout
