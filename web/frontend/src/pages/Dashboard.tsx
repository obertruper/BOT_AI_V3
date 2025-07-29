import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useTradingStore } from '@/store/tradingStore';
import { formatCurrency, formatPercentage } from '@/lib/utils';

const Dashboard: React.FC = () => {
  const {
    systemStatus,
    traders,
    positions,
    wsConnected,
    isLoading,
  } = useTradingStore();

  const activeTraders = traders.filter(t => t.status === 'active');
  const totalPnL = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);
  const totalEquity = traders.reduce((sum, t) => sum + t.equity, 0);

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Заголовок */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">BOT_Trading v3.0</h1>
          <p className="text-muted-foreground">Панель управления торговыми ботами</p>
        </div>
        <div className="flex items-center gap-4">
          <div className={`flex items-center gap-2 px-3 py-2 rounded-full text-sm ${
            wsConnected ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              wsConnected ? 'bg-profit animate-pulse' : 'bg-loss'
            }`} />
            {wsConnected ? 'Подключено' : 'Отключено'}
          </div>
          <Button variant="outline" disabled={isLoading}>
            {isLoading ? 'Загрузка...' : 'Обновить'}
          </Button>
        </div>
      </div>

      {/* Системная статистика */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Активные трейдеры</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeTraders.length}</div>
            <p className="text-xs text-muted-foreground">
              из {traders.length} общих
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Общий капитал</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalEquity)}</div>
            <p className="text-xs text-muted-foreground">
              Всех трейдеров
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Текущий P&L</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              totalPnL >= 0 ? 'text-profit' : 'text-loss'
            }`}>
              {formatCurrency(totalPnL)}
            </div>
            <p className="text-xs text-muted-foreground">
              Нереализованная прибыль/убыток
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Открытые позиции</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{positions.length}</div>
            <p className="text-xs text-muted-foreground">
              Активных позиций
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Быстрый обзор трейдеров */}
      <Card>
        <CardHeader>
          <CardTitle>Активные трейдеры</CardTitle>
          <CardDescription>
            Обзор всех активных торговых ботов
          </CardDescription>
        </CardHeader>
        <CardContent>
          {activeTraders.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Нет активных трейдеров
            </div>
          ) : (
            <div className="space-y-4">
              {activeTraders.slice(0, 5).map((trader) => (
                <div key={trader.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-4">
                    <div className="w-3 h-3 bg-profit rounded-full animate-pulse" />
                    <div>
                      <h4 className="font-medium">{trader.name}</h4>
                      <p className="text-sm text-muted-foreground">
                        {trader.exchange} • {trader.symbol}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-semibold ${
                      trader.pnl >= 0 ? 'text-profit' : 'text-loss'
                    }`}>
                      {formatCurrency(trader.pnl)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {formatPercentage(trader.pnl_percentage)}
                    </div>
                  </div>
                </div>
              ))}
              {activeTraders.length > 5 && (
                <div className="text-center pt-4">
                  <Button variant="outline" size="sm">
                    Показать еще {activeTraders.length - 5} трейдеров
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Системный статус */}
      {systemStatus && (
        <Card>
          <CardHeader>
            <CardTitle>Состояние системы</CardTitle>
            <CardDescription>
              Текущий статус торговой системы
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="trading-metric">
                <span className="trading-metric-label">Статус</span>
                <span className={`trading-metric-value ${
                  systemStatus.status === 'running' ? 'text-profit' : 'text-warning'
                }`}>
                  {systemStatus.status === 'running' ? 'Работает' : 'Остановлена'}
                </span>
              </div>
              <div className="trading-metric">
                <span className="trading-metric-label">Время работы</span>
                <span className="trading-metric-value">
                  {Math.floor(systemStatus.uptime / 3600)}ч {Math.floor((systemStatus.uptime % 3600) / 60)}м
                </span>
              </div>
              <div className="trading-metric">
                <span className="trading-metric-label">Память</span>
                <span className="trading-metric-value">
                  {systemStatus.system_metrics.memory_usage.toFixed(1)}%
                </span>
              </div>
              <div className="trading-metric">
                <span className="trading-metric-label">CPU</span>
                <span className="trading-metric-value">
                  {systemStatus.system_metrics.cpu_usage.toFixed(1)}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;
