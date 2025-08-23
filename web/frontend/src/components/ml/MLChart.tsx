import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  ReferenceLine,
  Legend,
  ComposedChart,
  Area,
  AreaChart,
} from 'recharts';

interface MLChartProps {
  data: any[];
  type: 'line' | 'bar' | 'composed' | 'area';
  title: string;
  height?: number;
  color?: string;
  dataKey: string;
  xDataKey?: string;
  showGrid?: boolean;
  showTooltip?: boolean;
  showLegend?: boolean;
  referenceLine?: number;
  additionalLines?: Array<{
    dataKey: string;
    color: string;
    name: string;
  }>;
}

const MLChart: React.FC<MLChartProps> = ({
  data,
  type,
  title,
  height = 300,
  color = '#8884d8',
  dataKey,
  xDataKey = 'name',
  showGrid = true,
  showTooltip = true,
  showLegend = false,
  referenceLine,
  additionalLines = [],
}) => {
  const commonProps = {
    width: '100%',
    height,
    data,
  };

  const renderChart = () => {
    switch (type) {
      case 'line':
        return (
          <LineChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#374151" />}
            <XAxis dataKey={xDataKey} stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" />
            {showTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#F9FAFB',
                }}
              />
            )}
            {showLegend && <Legend />}
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6, fill: color }}
            />
            {additionalLines.map((line, index) => (
              <Line
                key={index}
                type="monotone"
                dataKey={line.dataKey}
                stroke={line.color}
                strokeWidth={2}
                dot={false}
                name={line.name}
              />
            ))}
            {referenceLine && (
              <ReferenceLine y={referenceLine} stroke="#EF4444" strokeDasharray="5 5" />
            )}
          </LineChart>
        );

      case 'bar':
        return (
          <BarChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#374151" />}
            <XAxis dataKey={xDataKey} stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" />
            {showTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#F9FAFB',
                }}
              />
            )}
            {showLegend && <Legend />}
            <Bar dataKey={dataKey} fill={color} />
            {referenceLine && (
              <ReferenceLine y={referenceLine} stroke="#EF4444" strokeDasharray="5 5" />
            )}
          </BarChart>
        );

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#374151" />}
            <XAxis dataKey={xDataKey} stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" />
            {showTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#F9FAFB',
                }}
              />
            )}
            {showLegend && <Legend />}
            <Area
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              fill={color}
              fillOpacity={0.3}
            />
            {additionalLines.map((line, index) => (
              <Area
                key={index}
                type="monotone"
                dataKey={line.dataKey}
                stroke={line.color}
                fill={line.color}
                fillOpacity={0.2}
              />
            ))}
          </AreaChart>
        );

      case 'composed':
        return (
          <ComposedChart {...commonProps}>
            {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#374151" />}
            <XAxis dataKey={xDataKey} stroke="#9CA3AF" />
            <YAxis stroke="#9CA3AF" />
            {showTooltip && (
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1F2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#F9FAFB',
                }}
              />
            )}
            {showLegend && <Legend />}
            <Bar dataKey={dataKey} fill={color} />
            {additionalLines.map((line, index) => (
              <Line
                key={index}
                type="monotone"
                dataKey={line.dataKey}
                stroke={line.color}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </ComposedChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
      <h3 className="text-lg font-semibold text-white mb-4">{title}</h3>
      <ResponsiveContainer>{renderChart()}</ResponsiveContainer>
    </div>
  );
};

export default MLChart;