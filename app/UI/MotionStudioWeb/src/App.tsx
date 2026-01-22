import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from 'antd'
import MainLayout from './components/Layout/MainLayout'
import DataShowPage from './pages/DataShow'
import DefectShowPage from './pages/DefectShow'

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Layout style={{ height: '100vh' }}>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<DataShowPage />} />
            <Route path="data" element={<DataShowPage />} />
            <Route path="defect" element={<DefectShowPage />} />
          </Route>
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
