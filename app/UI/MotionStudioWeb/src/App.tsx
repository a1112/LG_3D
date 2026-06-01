import { BrowserRouter, Routes, Route } from 'react-router-dom'
import MainLayout from './components/Layout/MainLayout'
import DataShowPage from './pages/DataShow'
import DefectShowPage from './pages/DefectShow'

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<DataShowPage />} />
          <Route path="data" element={<DataShowPage />} />
          <Route path="defect" element={<DefectShowPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
