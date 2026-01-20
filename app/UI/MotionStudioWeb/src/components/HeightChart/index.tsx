import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { HeightLineData } from '@/types'
import './HeightChart.css'

interface HeightChartProps {
  data?: HeightLineData
}

function HeightChart({ data }: HeightChartProps) {
  const chartData = useMemo(() => {
    if (!data?.points || data.points.length === 0) {
      return []
    }

    // 将点数据转换为图表数据格式
    return data.points.map((point, index) => ({
      index,
      x: point.x.toFixed(2),
      y: point.y.toFixed(2),
      z: point.z.toFixed(2),
    }))
  }, [data])

  if (!data || chartData.length === 0) {
    return <div className="height-chart-empty">暂无高度数据</div>
  }

  return (
    <div className="height-chart-container">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="index"
            label={{ value: '采样点', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            label={{ value: '高度 (mm)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value: string) => [value, '高度']}
            labelFormatter={(label) => `采样点: ${label}`}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="z"
            stroke="#1890ff"
            name="高度值"
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default HeightChart
