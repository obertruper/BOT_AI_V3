import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/apiService';
import { BarChart3, TrendingUp, TrendingDown, MinusCircle, AlertCircle } from 'lucide-react';

interface DirectionStats {
  total_predictions: number;
  long_count: number;
  short_count: number;
  flat_count: number;
  long_percentage: number;
  short_percentage: number;
  flat_percentage: number;
  last_hour_distribution: {
    LONG: number;
    SHORT: number;
    FLAT: number;
  };
  confidence_by_direction: {
    LONG: number;
    SHORT: number;
    FLAT: number;
  };
}

const MLDirectionDistribution: React.FC = () => {
  const { data: stats, isLoading } = useQuery<DirectionStats>({
    queryKey: ['mlDirectionStats'],
    queryFn: () => apiService.get('/api/ml/direction-stats'),
    refetchInterval: 30000, // Обновление каждые 30 секунд
  });

  const getDistributionWarning = (longPct: number, shortPct: number, flatPct: number) => {
    if (longPct > 70 || shortPct > 70) {
      return { level: 'high', message: 'Высокий дисбаланс направлений!' };
    }
    if (flatPct > 50) {
      return { level: 'medium', message: 'Много нейтральных сигналов' };
    }
    if (Math.abs(longPct - shortPct) < 10 && flatPct < 20) {
      return { level: 'good', message: 'Сбалансированное распределение' };
    }
    return null;
  };

  if (isLoading || !stats) {
    return (
      <div className="card animate-pulse">
        <div className="h-64 bg-gray-700 rounded-xl"></div>
      </div>
    );
  }

  const warning = getDistributionWarning(
    stats.long_percentage,
    stats.short_percentage,
    stats.flat_percentage
  );

  return (
    <div className="card relative overflow-hidden">
      {/* Заголовок */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <BarChart3 className="w-6 h-6 text-blue-400 mr-3" />
          <h3 className="text-lg font-semibold text-white">Распределение классов направлений</h3>
        </div>
        <div className="text-xs text-gray-400">
          Всего: {stats.total_predictions} предсказаний
        </div>
      </div>

      {/* Предупреждение о дисбалансе */}
      {warning && (
        <div className={`mb-4 p-3 rounded-lg flex items-center ${
          warning.level === 'high' ? 'bg-red-900/20 border border-red-700/50' :
          warning.level === 'medium' ? 'bg-yellow-900/20 border border-yellow-700/50' :
          'bg-green-900/20 border border-green-700/50'
        }`}>
          <AlertCircle className={`w-4 h-4 mr-2 ${
            warning.level === 'high' ? 'text-red-400' :
            warning.level === 'medium' ? 'text-yellow-400' :
            'text-green-400'
          }`} />
          <span className="text-sm text-gray-300">{warning.message}</span>
        </div>
      )}

      {/* Основное распределение */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* LONG */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-green-600/20">
          <div className="flex items-center justify-between mb-2">
            <TrendingUp className="w-5 h-5 text-green-400" />
            <span className="text-xs text-gray-400">LONG</span>
          </div>
          <div className="text-2xl font-bold text-green-400">
            {stats.long_percentage.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500">
            {stats.long_count} сигналов
          </div>
          <div className="mt-2 text-xs text-gray-400">
            Увер: {(stats.confidence_by_direction.LONG * 100).toFixed(0)}%
          </div>
        </div>

        {/* SHORT */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-red-600/20">
          <div className="flex items-center justify-between mb-2">
            <TrendingDown className="w-5 h-5 text-red-400" />
            <span className="text-xs text-gray-400">SHORT</span>
          </div>
          <div className="text-2xl font-bold text-red-400">
            {stats.short_percentage.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500">
            {stats.short_count} сигналов
          </div>
          <div className="mt-2 text-xs text-gray-400">
            Увер: {(stats.confidence_by_direction.SHORT * 100).toFixed(0)}%
          </div>
        </div>

        {/* FLAT */}
        <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-600/20">
          <div className="flex items-center justify-between mb-2">
            <MinusCircle className="w-5 h-5 text-gray-400" />
            <span className="text-xs text-gray-400">FLAT</span>
          </div>
          <div className="text-2xl font-bold text-gray-400">
            {stats.flat_percentage.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500">
            {stats.flat_count} сигналов
          </div>
          <div className="mt-2 text-xs text-gray-400">
            Увер: {(stats.confidence_by_direction.FLAT * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Визуальная гистограмма */}
      <div className="mb-6">
        <div className="text-sm text-gray-400 mb-3">Визуальное распределение</div>
        <div className="h-32 flex items-end gap-4">
          {/* LONG бар */}
          <div className="flex-1 flex flex-col items-center">
            <div 
              className="w-full bg-gradient-to-t from-green-600 to-green-400 rounded-t-lg transition-all duration-500"
              style={{ height: `${stats.long_percentage}%` }}
            />
            <div className="text-xs text-gray-400 mt-2">LONG</div>
          </div>
          
          {/* SHORT бар */}
          <div className="flex-1 flex flex-col items-center">
            <div 
              className="w-full bg-gradient-to-t from-red-600 to-red-400 rounded-t-lg transition-all duration-500"
              style={{ height: `${stats.short_percentage}%` }}
            />
            <div className="text-xs text-gray-400 mt-2">SHORT</div>
          </div>
          
          {/* FLAT бар */}
          <div className="flex-1 flex flex-col items-center">
            <div 
              className="w-full bg-gradient-to-t from-gray-600 to-gray-400 rounded-t-lg transition-all duration-500"
              style={{ height: `${stats.flat_percentage}%` }}
            />
            <div className="text-xs text-gray-400 mt-2">FLAT</div>
          </div>
        </div>
      </div>

      {/* Распределение за последний час */}
      <div className="bg-gray-800/50 rounded-lg p-4">
        <div className="text-sm text-gray-400 mb-3">Последний час</div>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-400 rounded-full mr-2"></div>
            <span className="text-xs text-gray-300">
              LONG: {stats.last_hour_distribution.LONG}
            </span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-red-400 rounded-full mr-2"></div>
            <span className="text-xs text-gray-300">
              SHORT: {stats.last_hour_distribution.SHORT}
            </span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-gray-400 rounded-full mr-2"></div>
            <span className="text-xs text-gray-300">
              FLAT: {stats.last_hour_distribution.FLAT}
            </span>
          </div>
        </div>
      </div>

      {/* Рекомендации */}
      <div className="mt-4 p-3 bg-blue-900/10 border border-blue-700/30 rounded-lg">
        <div className="text-xs text-blue-400 font-medium mb-1">Рекомендации</div>
        <div className="text-xs text-gray-300">
          {stats.flat_percentage > 40 
            ? 'Высокий процент FLAT может указывать на неопределенность рынка. Рассмотрите снижение размера позиций.'
            : stats.long_percentage > 60
            ? 'Преобладание LONG сигналов. Возможен бычий тренд, но будьте осторожны с перекупленностью.'
            : stats.short_percentage > 60
            ? 'Преобладание SHORT сигналов. Возможен медвежий тренд, следите за уровнями поддержки.'
            : 'Сбалансированное распределение сигналов. Рынок в равновесии.'}
        </div>
      </div>

      {/* Декоративный градиент */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-600/10 to-purple-600/10 rounded-full blur-3xl" />
    </div>
  );
};

export default MLDirectionDistribution;