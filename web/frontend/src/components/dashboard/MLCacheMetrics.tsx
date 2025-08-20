import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '@/services/apiService';
import { Database, TrendingUp, Target, Clock, Hash, Zap } from 'lucide-react';

interface CacheMetrics {
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
  cache_size: number;
  unique_symbols_processed: number;
  symbols_list: string[];
  cache_ttl_seconds: number;
  last_cleanup: string;
}

const MLCacheMetrics: React.FC = () => {
  const { data: metrics, isLoading } = useQuery<CacheMetrics>({
    queryKey: ['mlCacheMetrics'],
    queryFn: () => apiService.get('/api/ml/cache-stats'),
    refetchInterval: 10000, // Обновление каждые 10 секунд
  });

  const getHitRateColor = (rate: number) => {
    if (rate >= 0.7) return 'text-green-400';
    if (rate >= 0.5) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getCacheSizeColor = (size: number, max: number = 1000) => {
    const usage = size / max;
    if (usage < 0.5) return 'text-green-400';
    if (usage < 0.8) return 'text-yellow-400';
    return 'text-red-400';
  };

  if (isLoading || !metrics) {
    return (
      <div className="card animate-pulse">
        <div className="h-48 bg-gray-700 rounded-xl"></div>
      </div>
    );
  }

  const hitRate = metrics.cache_hit_rate * 100;
  const cacheUsage = (metrics.cache_size / 1000) * 100;

  return (
    <div className="card relative overflow-hidden">
      {/* Заголовок */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <Database className="w-6 h-6 text-purple-400 mr-3" />
          <h3 className="text-lg font-semibold text-white">ML Кэш Метрики</h3>
        </div>
        <div className="flex items-center text-xs text-gray-400">
          <Clock className="w-3 h-3 mr-1" />
          TTL: {metrics.cache_ttl_seconds}с
        </div>
      </div>

      {/* Основные метрики */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Hit Rate */}
        <div className="bg-gray-800/50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400">Hit Rate</span>
            <Target className="w-4 h-4 text-purple-400" />
          </div>
          <div className={`text-2xl font-bold ${getHitRateColor(metrics.cache_hit_rate)}`}>
            {hitRate.toFixed(1)}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {metrics.cache_hits} hits / {metrics.cache_misses} misses
          </div>
        </div>

        {/* Cache Size */}
        <div className="bg-gray-800/50 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400">Размер кэша</span>
            <Hash className="w-4 h-4 text-purple-400" />
          </div>
          <div className={`text-2xl font-bold ${getCacheSizeColor(metrics.cache_size)}`}>
            {metrics.cache_size}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            из 1000 макс ({cacheUsage.toFixed(0)}%)
          </div>
        </div>
      </div>

      {/* Прогресс-бары */}
      <div className="space-y-3 mb-6">
        {/* Hit Rate прогресс */}
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Эффективность кэша</span>
            <span>{hitRate.toFixed(0)}%</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${
                hitRate >= 70 ? 'bg-green-500' : hitRate >= 50 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${hitRate}%` }}
            />
          </div>
        </div>

        {/* Cache Usage прогресс */}
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Использование кэша</span>
            <span>{metrics.cache_size}/1000</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${
                cacheUsage < 50 ? 'bg-green-500' : cacheUsage < 80 ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              style={{ width: `${cacheUsage}%` }}
            />
          </div>
        </div>
      </div>

      {/* Уникальные символы */}
      <div className="bg-gray-800/50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-400">Уникальные символы</span>
          <span className="text-sm font-medium text-purple-400">
            {metrics.unique_symbols_processed}
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {metrics.symbols_list.slice(0, 6).map((symbol) => (
            <span 
              key={symbol}
              className="px-2 py-1 bg-gray-700/50 text-xs text-gray-300 rounded-md border border-gray-600/50"
            >
              {symbol}
            </span>
          ))}
          {metrics.symbols_list.length > 6 && (
            <span className="px-2 py-1 text-xs text-gray-500">
              +{metrics.symbols_list.length - 6} еще
            </span>
          )}
        </div>
      </div>

      {/* Последняя очистка */}
      <div className="mt-4 pt-4 border-t border-gray-700/50">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-400">Последняя очистка</span>
          <span className="text-gray-300">
            {new Date(metrics.last_cleanup).toLocaleTimeString('ru-RU')}
          </span>
        </div>
      </div>

      {/* Статистика производительности */}
      <div className="mt-4 grid grid-cols-3 gap-2">
        <div className="text-center">
          <div className="text-lg font-bold text-green-400">{metrics.cache_hits}</div>
          <div className="text-xs text-gray-500">Попадания</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-red-400">{metrics.cache_misses}</div>
          <div className="text-xs text-gray-500">Промахи</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-purple-400">
            {((metrics.cache_hits + metrics.cache_misses) / 60).toFixed(1)}/м
          </div>
          <div className="text-xs text-gray-500">Запросов/мин</div>
        </div>
      </div>

      {/* Декоративный градиент */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-purple-600/10 to-pink-600/10 rounded-full blur-3xl" />
    </div>
  );
};

export default MLCacheMetrics;