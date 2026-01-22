import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider } from 'antd'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import zhCN from 'antd/locale/zh_CN'
import App from './App'
import './index.css'

// 创建 QueryClient 实例
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 数据保持新鲜时间（毫秒）
      staleTime: 5 * 60 * 1000, // 5分钟
      // 缓存时间（毫秒）
      gcTime: 30 * 60 * 1000, // 30分钟
      // 失败重试次数
      retry: 1,
      // 重试延迟
      retryDelay: 1000,
      // 窗口焦点时是否重新获取
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={zhCN}>
        <App />
      </ConfigProvider>
      {/* React Query DevTools - 需要先安装依赖: npm install */}
      {/* <ReactQueryDevtools
        initialIsOpen={false}
        position="bottom-right"
      /> */}
    </QueryClientProvider>
  </React.StrictMode>,
)
