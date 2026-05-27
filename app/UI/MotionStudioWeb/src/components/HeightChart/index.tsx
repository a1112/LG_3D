import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import type { HeightLineSegment } from '@/types'
import './HeightChart.css'

interface HeightChartProps {
  data?: HeightLineSegment[]
}

function HeightChart({ data }: HeightChartProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) {
      return []
    }

    return data.flatMap((segment, segmentIndex) =>
      segment.points.map(([x, y, z], pointIndex) => ({
        index: `${segmentIndex + 1}-${pointIndex + 1}`,
        x: x.toFixed(2),
        y: y.toFixed(2),
        z: z.toFixed(2),
      }))
    )
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
