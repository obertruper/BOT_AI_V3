import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTradingStore } from '@/store/tradingStore';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import {
  Bot,
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  Clock,
  Settings,
  Play,
  Pause,
  Plus,
  BarChart3,
  AlertCircle,
  CheckCircle,
  Target,
} from 'lucide-react';

const Traders: React.FC = () => {
  const { traders, isLoading } = useTradingStore();

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-muted-foreground">Загрузка трейдеров...</p>
          </div>
        </div>
      </div>
    );
  }

  const activeTraders = traders.filter(t => t.status === 'active');
  const totalEquity = traders.reduce((sum, t) => sum + t.equity, 0);
  const totalPnL = traders.reduce((sum, t) => sum + t.pnl, 0);
  const avgPnLPercentage = traders.length > 0
    ? traders.reduce((sum, t) => sum + t.pnl_percentage, 0) / traders.length
    : 0;

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Заголовок */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Трейдеры</h1>
          <p className="text-muted-foreground">Управление торговыми ботами</p>
        </div>
        <Button className="flex items-center">
          <Plus className="h-4 w-4 mr-2" />
          Создать трейдера
        </Button>
      </div>

      {/* Сводная статистика трейдеров */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Bot className="h-4 w-4 mr-2 text-blue-500" />
              Активные
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeTraders.length}</div>
            <p className="text-xs text-muted-foreground">
              из {traders.length} всего
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <DollarSign className="h-4 w-4 mr-2 text-green-500" />
              Общий капитал
            </CardTitle>
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
            <CardTitle className="text-sm font-medium flex items-center">
              <TrendingUp className="h-4 w-4 mr-2 text-purple-500" />
              Общий P&L
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              totalPnL >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {formatCurrency(totalPnL)}
            </div>
            <p className="text-xs text-muted-foreground">
              Суммарная прибыль/убыток
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <BarChart3 className="h-4 w-4 mr-2 text-orange-500" />
              Средний ROI
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              avgPnLPercentage >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {formatPercentage(avgPnLPercentage)}
            </div>
            <p className="text-xs text-muted-foreground">
              В среднем по трейдерам
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Список трейдеров */}
      <Card>
        <CardHeader>
          <CardTitle>Список трейдеров</CardTitle>
          <CardDescription>
            Детальный обзор всех торговых ботов
          </CardDescription>
        </CardHeader>
        <CardContent>
          {traders.length === 0 ? (
            <div className="text-center py-12">
              <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Нет активных трейдеров
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                Создайте своего первого торгового бота для начала работы
              </p>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Создать трейдера
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {traders.map((trader) => (
                <div key={trader.id} className="border rounded-lg p-6 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  {/* Заголовок трейдера */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-3">
                        <div className={`w-3 h-3 rounded-full ${
                          trader.status === 'active'
                            ? 'bg-green-500 animate-pulse'
                            : 'bg-gray-400'
                        }`} />
                        <h3 className="text-lg font-semibold">{trader.name}</h3>
                      </div>
                      <Badge
                        variant={trader.status === 'active' ? 'default' : 'secondary'}
                        className="text-xs"
                      >
                        {trader.status === 'active' ? 'Активен' : 'Остановлен'}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {trader.exchange}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {trader.symbol}
                      </Badge>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button size="sm" variant="outline">
                        <Settings className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant={trader.status === 'active' ? 'destructive' : 'default'}
                      >
                        {trader.status === 'active' ? (
                          <>
                            <Pause className="h-4 w-4 mr-1" />
                            Стоп
                          </>
                        ) : (
                          <>
                            <Play className="h-4 w-4 mr-1" />
                            Старт
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Основные метрики */}
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mb-4">
                    <div className="text-center">
                      <div className="text-sm text-muted-foreground">Капитал</div>
                      <div className="font-semibold">{formatCurrency(trader.equity)}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-sm text-muted-foreground">P&L</div>
                      <div className={`font-semibold ${
                        trader.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatCurrency(trader.pnl)}
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-sm text-muted-foreground">ROI</div>
                      <div className={`font-semibold ${
                        trader.pnl_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatPercentage(trader.pnl_percentage)}
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-sm text-muted-foreground">Сделки</div>
                      <div className="font-semibold">{trader.total_trades || 0}</div>
                    </div>
                    <div className="text-center">
                      <div className="text-sm text-muted-foreground">Винрейт</div>
                      <div className="font-semibold">
                        {trader.win_rate ? formatPercentage(trader.win_rate) : '0%'}
                      </div>
                    </div>
                    <div className="text-center">
                      <div className="text-sm text-muted-foreground">Время работы</div>
                      <div className="font-semibold">
                        {trader.uptime ? `${Math.floor(trader.uptime / 3600)}ч` : '0ч'}
                      </div>
                    </div>
                  </div>

                  {/* Статус и дополнительная информация */}
                  <div className="flex items-center justify-between text-sm pt-4 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-6">
                      <div className="flex items-center space-x-2">
                        {trader.status === 'active' ? (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-gray-400" />
                        )}
                        <span className="text-muted-foreground">
                          Статус: {trader.status === 'active' ? 'Работает' : 'Остановлен'}
                        </span>
                      </div>
                      {trader.last_trade_at && (
                        <div className="flex items-center space-x-2">
                          <Clock className="h-4 w-4 text-gray-400" />
                          <span className="text-muted-foreground">
                            Последняя сделка: {new Date(trader.last_trade_at).toLocaleString()}
                          </span>
                        </div>
                      )}
                      {trader.strategy && (
                        <div className="flex items-center space-x-2">
                          <Target className="h-4 w-4 text-gray-400" />
                          <span className="text-muted-foreground">
                            Стратегия: {trader.strategy}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                      <Activity className="h-3 w-3" />
                      <span>Обновлено: {new Date(trader.updated_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Traders;
