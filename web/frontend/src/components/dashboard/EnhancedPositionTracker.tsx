import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, TrendingUp, TrendingDown, Clock, DollarSign, Activity } from 'lucide-react';

interface Position {
  position_id: string;
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  current_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  status: string;
  health: string;
  unrealized_pnl: number;
  roi_percent: number;
  hold_time_minutes: number;
  exchange: string;
  created_at: string;
  updated_at: string;
}

interface TrackerStats {
  total_tracked: number;
  active_positions: number;
  updates_count: number;
  sync_errors: number;
  last_update: string | null;
  health_distribution: {
    healthy: number;
    warning: number;
    critical: number;
  };
  total_unrealized_pnl: number;
  avg_hold_time: number;
  is_running: boolean;
}

export const EnhancedPositionTracker: React.FC = () => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [stats, setStats] = useState<TrackerStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Получаем активные позиции
      const positionsResponse = await fetch('/api/positions/active');
      const positionsData = await positionsResponse.json();

      // Получаем статистику трекера
      const statsResponse = await fetch('/api/positions/stats/tracker');
      const statsData = await statsResponse.json();

      if (positionsResponse.ok && Array.isArray(positionsData)) {
        setPositions(positionsData);
      }

      if (statsResponse.ok) {
        setStats(statsData);
      }

      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Автообновление каждые 30 секунд
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const getHealthBadgeColor = (health: string) => {
    switch (health.toLowerCase()) {
      case 'healthy': return 'bg-green-500';
      case 'warning': return 'bg-yellow-500';
      case 'critical': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getSideBadgeColor = (side: string) => {
    return side.toLowerCase() === 'long' ? 'bg-green-600' : 'bg-red-600';
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  const formatPercent = (value: number) => {
    const color = value >= 0 ? 'text-green-600' : 'text-red-600';
    const sign = value >= 0 ? '+' : '';
    return (
      <span className={color}>
        {sign}{value.toFixed(2)}%
      </span>
    );
  };

  const formatTime = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}ч ${mins}м`;
    }
    return `${mins}м`;
  };

  if (error) {
    return (
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Ошибка загрузки позиций</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-red-500 mb-4">{error}</p>
          <Button onClick={fetchData} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Повторить
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Статистика трекера */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Активные позиции</p>
                  <p className="text-2xl font-bold">{stats.active_positions}</p>
                </div>
                <Activity className={`w-8 h-8 ${stats.is_running ? 'text-green-500' : 'text-red-500'}`} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Общий PnL</p>
                  <p className={`text-2xl font-bold ${stats.total_unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(stats.total_unrealized_pnl)}
                  </p>
                </div>
                <DollarSign className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Среднее время</p>
                  <p className="text-2xl font-bold">{formatTime(stats.avg_hold_time)}</p>
                </div>
                <Clock className="w-8 h-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Статус здоровья</p>
                  <div className="flex space-x-2 mt-1">
                    <Badge className="bg-green-500 text-white text-xs px-2 py-1">
                      {stats.health_distribution.healthy}
                    </Badge>
                    <Badge className="bg-yellow-500 text-white text-xs px-2 py-1">
                      {stats.health_distribution.warning}
                    </Badge>
                    <Badge className="bg-red-500 text-white text-xs px-2 py-1">
                      {stats.health_distribution.critical}
                    </Badge>
                  </div>
                </div>
                <TrendingUp className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Заголовок и кнопка обновления */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl font-bold">Enhanced Position Tracker</CardTitle>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-500">
                Обновлено: {lastUpdated.toLocaleTimeString('ru-RU')}
              </span>
              <Button onClick={fetchData} disabled={loading} size="sm">
                <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Обновить
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin mr-2" />
              <span>Загрузка позиций...</span>
            </div>
          ) : positions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Активные позиции не найдены</p>
            </div>
          ) : (
            <div className="space-y-4">
              {positions.map((position) => (
                <Card key={position.position_id} className="border-l-4 border-l-blue-500">
                  <CardContent className="p-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
                      {/* Основная информация */}
                      <div>
                        <div className="flex items-center space-x-2 mb-2">
                          <Badge className={`${getSideBadgeColor(position.side)} text-white`}>
                            {position.side.toUpperCase()}
                          </Badge>
                          <Badge className={getHealthBadgeColor(position.health)}>
                            {position.health}
                          </Badge>
                        </div>
                        <h3 className="font-bold text-lg">{position.symbol}</h3>
                        <p className="text-sm text-gray-600">{position.exchange}</p>
                      </div>

                      {/* Размер и цены */}
                      <div>
                        <p className="text-sm font-medium text-gray-600">Размер</p>
                        <p className="font-bold">{position.size}</p>
                        <p className="text-sm text-gray-500">
                          Вход: ${position.entry_price.toFixed(4)}
                        </p>
                      </div>

                      {/* Текущая цена */}
                      <div>
                        <p className="text-sm font-medium text-gray-600">Текущая цена</p>
                        <p className="font-bold">${position.current_price.toFixed(4)}</p>
                        <div className="flex items-center text-sm">
                          {position.current_price > position.entry_price ? (
                            <TrendingUp className="w-4 h-4 text-green-500 mr-1" />
                          ) : (
                            <TrendingDown className="w-4 h-4 text-red-500 mr-1" />
                          )}
                          {formatPercent(position.roi_percent)}
                        </div>
                      </div>

                      {/* PnL */}
                      <div>
                        <p className="text-sm font-medium text-gray-600">Нереализованный PnL</p>
                        <p className={`font-bold text-lg ${position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(position.unrealized_pnl)}
                        </p>
                      </div>

                      {/* SL/TP */}
                      <div>
                        <p className="text-sm font-medium text-gray-600">SL/TP</p>
                        <div className="space-y-1">
                          {position.stop_loss && (
                            <p className="text-sm text-red-600">
                              SL: ${position.stop_loss.toFixed(4)}
                            </p>
                          )}
                          {position.take_profit && (
                            <p className="text-sm text-green-600">
                              TP: ${position.take_profit.toFixed(4)}
                            </p>
                          )}
                          {!position.stop_loss && !position.take_profit && (
                            <p className="text-sm text-gray-500">Не установлены</p>
                          )}
                        </div>
                      </div>

                      {/* Время */}
                      <div>
                        <p className="text-sm font-medium text-gray-600">Время держания</p>
                        <p className="font-bold">{formatTime(position.hold_time_minutes)}</p>
                        <p className="text-xs text-gray-500">
                          {new Date(position.created_at).toLocaleString('ru-RU')}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};