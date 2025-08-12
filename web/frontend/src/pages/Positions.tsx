import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useTradingStore } from '@/store/tradingStore';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { TrendingUp, TrendingDown, Minus, DollarSign, Clock, Target } from 'lucide-react';

const Positions: React.FC = () => {
  const { positions, isLoading } = useTradingStore();

  if (isLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-muted-foreground">Загрузка позиций...</p>
          </div>
        </div>
      </div>
    );
  }

  const activePositions = positions.filter(p => p.size !== 0);
  const totalPnL = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);
  const totalValue = positions.reduce((sum, p) => sum + Math.abs(p.size * p.entry_price), 0);

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Заголовок */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Позиции</h1>
          <p className="text-muted-foreground">Управление открытыми позициями</p>
        </div>
      </div>

      {/* Сводная статистика */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <TrendingUp className="h-4 w-4 mr-2 text-blue-500" />
              Активные позиции
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activePositions.length}</div>
            <p className="text-xs text-muted-foreground">
              из {positions.length} всего
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <DollarSign className="h-4 w-4 mr-2 text-green-500" />
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
              Нереализованная прибыль/убыток
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center">
              <Target className="h-4 w-4 mr-2 text-purple-500" />
              Общая стоимость
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatCurrency(totalValue)}</div>
            <p className="text-xs text-muted-foreground">
              Суммарная стоимость позиций
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Список позиций */}
      <Card>
        <CardHeader>
          <CardTitle>Открытые позиции</CardTitle>
          <CardDescription>
            Детальный обзор всех активных торговых позиций
          </CardDescription>
        </CardHeader>
        <CardContent>
          {activePositions.length === 0 ? (
            <div className="text-center py-12">
              <Minus className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Нет открытых позиций
              </h3>
              <p className="text-gray-500 dark:text-gray-400">
                Активные позиции будут отображены здесь после их открытия
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {activePositions.map((position, index) => (
                <div key={`${position.symbol}-${index}`} className="border rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center space-x-2">
                        {position.side === 'LONG' ? (
                          <TrendingUp className="h-5 w-5 text-green-500" />
                        ) : (
                          <TrendingDown className="h-5 w-5 text-red-500" />
                        )}
                        <h4 className="text-lg font-semibold">{position.symbol}</h4>
                      </div>
                      <Badge
                        variant={position.side === 'LONG' ? 'default' : 'destructive'}
                        className="text-xs"
                      >
                        {position.side}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {position.exchange}
                      </Badge>
                    </div>
                    <div className="text-right">
                      <div className={`text-lg font-bold ${
                        position.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatCurrency(position.unrealized_pnl)}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {formatPercentage(position.unrealized_pnl_percentage)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Размер:</span>
                      <div className="font-medium">{Math.abs(position.size).toFixed(4)}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Цена входа:</span>
                      <div className="font-medium">${position.entry_price.toFixed(4)}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Текущая цена:</span>
                      <div className="font-medium">${position.mark_price.toFixed(4)}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Маржа:</span>
                      <div className="font-medium">{formatCurrency(position.margin)}</div>
                    </div>
                  </div>

                  {/* Дополнительная информация */}
                  <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center">
                          <Clock className="h-3 w-3 mr-1" />
                          <span>Открыто: {new Date(position.created_at).toLocaleString()}</span>
                        </div>
                        {position.leverage && (
                          <div>Плечо: {position.leverage}x</div>
                        )}
                      </div>
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

export default Positions;
