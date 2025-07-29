import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { Trader, Position, Order, SystemStatus, TradingStats } from '@/types/trading';
import apiClient from '@/api/client';

interface TradingState {
  // Состояние системы
  systemStatus: SystemStatus | null
  isLoading: boolean
  error: string | null

  // Трейдеры
  traders: Trader[]
  selectedTraderId: string | null
  selectedTrader: Trader | null

  // Позиции и ордера
  positions: Position[]
  orders: Order[]

  // Статистика
  tradingStats: TradingStats | null

  // WebSocket состояние
  wsConnected: boolean
  realTimeUpdates: boolean

  // UI состояние
  refreshInterval: number
  autoRefresh: boolean
}

interface TradingActions {
  // Системные действия
  fetchSystemStatus: () => Promise<void>
  setError: (error: string | null) => void
  clearError: () => void

  // Действия с трейдерами
  fetchTraders: () => Promise<void>
  selectTrader: (traderId: string | null) => void
  createTrader: (config: any) => Promise<void>
  updateTrader: (traderId: string, config: any) => Promise<void>
  deleteTrader: (traderId: string) => Promise<void>
  startTrader: (traderId: string) => Promise<void>
  stopTrader: (traderId: string) => Promise<void>
  pauseTrader: (traderId: string) => Promise<void>

  // Действия с позициями
  fetchPositions: (traderId?: string) => Promise<void>
  closePosition: (positionId: string, percentage?: number) => Promise<void>
  updateStopLoss: (positionId: string, stopLoss: number) => Promise<void>
  updateTakeProfit: (positionId: string, takeProfit: number) => Promise<void>

  // Действия с ордерами
  fetchOrders: (traderId?: string) => Promise<void>
  cancelOrder: (orderId: string) => Promise<void>

  // Действия со статистикой
  fetchTradingStats: (traderId?: string, period?: string) => Promise<void>

  // WebSocket действия
  setWsConnected: (connected: boolean) => void
  setRealTimeUpdates: (enabled: boolean) => void

  // UI действия
  setRefreshInterval: (interval: number) => void
  setAutoRefresh: (enabled: boolean) => void

  // Обновления в реальном времени
  updateTraderFromWS: (trader: Trader) => void
  updatePositionFromWS: (position: Position) => void
  updateOrderFromWS: (order: Order) => void
  updateSystemStatusFromWS: (status: SystemStatus) => void
}

type TradingStore = TradingState & TradingActions

export const useTradingStore = create<TradingStore>()(
  subscribeWithSelector((set, get) => ({
    // Начальное состояние
    systemStatus: null,
    isLoading: false,
    error: null,
    traders: [],
    selectedTraderId: null,
    selectedTrader: null,
    positions: [],
    orders: [],
    tradingStats: null,
    wsConnected: false,
    realTimeUpdates: true,
    refreshInterval: 5000,
    autoRefresh: true,

    // Системные действия
    fetchSystemStatus: async () => {
      set({ isLoading: true, error: null });
      try {
        const response = await apiClient.getSystemStatus();
        if (response.success && response.data) {
          set({ systemStatus: response.data });
        }
      } catch (error) {
        set({ error: `Ошибка получения статуса системы: ${error}` });
      } finally {
        set({ isLoading: false });
      }
    },

    setError: (error) => set({ error }),
    clearError: () => set({ error: null }),

    // Действия с трейдерами
    fetchTraders: async () => {
      set({ isLoading: true, error: null });
      try {
        const response = await apiClient.getTraders();
        if (response.success && response.data) {
          set({ traders: response.data });

          // Обновляем выбранного трейдера если он есть
          const selectedTraderId = get().selectedTraderId;
          if (selectedTraderId) {
            const selectedTrader = response.data.find(t => t.id === selectedTraderId);
            set({ selectedTrader });
          }
        }
      } catch (error) {
        set({ error: `Ошибка получения списка трейдеров: ${error}` });
      } finally {
        set({ isLoading: false });
      }
    },

    selectTrader: (traderId) => {
      const traders = get().traders;
      const selectedTrader = traderId ? traders.find(t => t.id === traderId) || null : null;
      set({ selectedTraderId: traderId, selectedTrader });
    },

    createTrader: async (config) => {
      set({ isLoading: true, error: null });
      try {
        const response = await apiClient.createTrader(config);
        if (response.success && response.data) {
          const traders = [...get().traders, response.data];
          set({ traders });
        }
      } catch (error) {
        set({ error: `Ошибка создания трейдера: ${error}` });
      } finally {
        set({ isLoading: false });
      }
    },

    updateTrader: async (traderId, config) => {
      set({ isLoading: true, error: null });
      try {
        const response = await apiClient.updateTrader(traderId, config);
        if (response.success && response.data) {
          const traders = get().traders.map(t =>
            t.id === traderId ? response.data! : t,
          );
          set({ traders });

          // Обновляем выбранного трейдера если это он
          if (get().selectedTraderId === traderId) {
            set({ selectedTrader: response.data });
          }
        }
      } catch (error) {
        set({ error: `Ошибка обновления трейдера: ${error}` });
      } finally {
        set({ isLoading: false });
      }
    },

    deleteTrader: async (traderId) => {
      set({ isLoading: true, error: null });
      try {
        const response = await apiClient.deleteTrader(traderId);
        if (response.success) {
          const traders = get().traders.filter(t => t.id !== traderId);
          set({ traders });

          // Сбрасываем выбор если удаляем выбранного трейдера
          if (get().selectedTraderId === traderId) {
            set({ selectedTraderId: null, selectedTrader: null });
          }
        }
      } catch (error) {
        set({ error: `Ошибка удаления трейдера: ${error}` });
      } finally {
        set({ isLoading: false });
      }
    },

    startTrader: async (traderId) => {
      try {
        await apiClient.startTrader(traderId);
        // Обновляем список трейдеров
        get().fetchTraders();
      } catch (error) {
        set({ error: `Ошибка запуска трейдера: ${error}` });
      }
    },

    stopTrader: async (traderId) => {
      try {
        await apiClient.stopTrader(traderId);
        get().fetchTraders();
      } catch (error) {
        set({ error: `Ошибка остановки трейдера: ${error}` });
      }
    },

    pauseTrader: async (traderId) => {
      try {
        await apiClient.pauseTrader(traderId);
        get().fetchTraders();
      } catch (error) {
        set({ error: `Ошибка паузы трейдера: ${error}` });
      }
    },

    // Действия с позициями
    fetchPositions: async (traderId) => {
      set({ isLoading: true, error: null });
      try {
        const response = await apiClient.getPositions(traderId);
        if (response.success && response.data) {
          set({ positions: response.data });
        }
      } catch (error) {
        set({ error: `Ошибка получения позиций: ${error}` });
      } finally {
        set({ isLoading: false });
      }
    },

    closePosition: async (positionId, percentage) => {
      try {
        await apiClient.closePosition(positionId, percentage);
        get().fetchPositions();
      } catch (error) {
        set({ error: `Ошибка закрытия позиции: ${error}` });
      }
    },

    updateStopLoss: async (positionId, stopLoss) => {
      try {
        const response = await apiClient.updateStopLoss(positionId, stopLoss);
        if (response.success && response.data) {
          const positions = get().positions.map(p =>
            p.id === positionId ? response.data! : p,
          );
          set({ positions });
        }
      } catch (error) {
        set({ error: `Ошибка обновления стоп-лосса: ${error}` });
      }
    },

    updateTakeProfit: async (positionId, takeProfit) => {
      try {
        const response = await apiClient.updateTakeProfit(positionId, takeProfit);
        if (response.success && response.data) {
          const positions = get().positions.map(p =>
            p.id === positionId ? response.data! : p,
          );
          set({ positions });
        }
      } catch (error) {
        set({ error: `Ошибка обновления тейк-профита: ${error}` });
      }
    },

    // Действия с ордерами
    fetchOrders: async (traderId) => {
      set({ isLoading: true, error: null });
      try {
        const response = await apiClient.getOrders(traderId);
        if (response.success && response.data) {
          set({ orders: response.data.items });
        }
      } catch (error) {
        set({ error: `Ошибка получения ордеров: ${error}` });
      } finally {
        set({ isLoading: false });
      }
    },

    cancelOrder: async (orderId) => {
      try {
        await apiClient.cancelOrder(orderId);
        get().fetchOrders();
      } catch (error) {
        set({ error: `Ошибка отмены ордера: ${error}` });
      }
    },

    // Действия со статистикой
    fetchTradingStats: async (traderId, period) => {
      set({ isLoading: true, error: null });
      try {
        const response = await apiClient.getTradingStats(traderId, period);
        if (response.success && response.data) {
          set({ tradingStats: response.data });
        }
      } catch (error) {
        set({ error: `Ошибка получения статистики: ${error}` });
      } finally {
        set({ isLoading: false });
      }
    },

    // WebSocket действия
    setWsConnected: (connected) => set({ wsConnected: connected }),
    setRealTimeUpdates: (enabled) => set({ realTimeUpdates: enabled }),

    // UI действия
    setRefreshInterval: (interval) => set({ refreshInterval: interval }),
    setAutoRefresh: (enabled) => set({ autoRefresh: enabled }),

    // Обновления в реальном времени
    updateTraderFromWS: (trader) => {
      const traders = get().traders.map(t => t.id === trader.id ? trader : t);
      set({ traders });

      if (get().selectedTraderId === trader.id) {
        set({ selectedTrader: trader });
      }
    },

    updatePositionFromWS: (position) => {
      const positions = get().positions.map(p => p.id === position.id ? position : p);
      set({ positions });
    },

    updateOrderFromWS: (order) => {
      const orders = get().orders.map(o => o.id === order.id ? order : o);
      set({ orders });
    },

    updateSystemStatusFromWS: (status) => {
      set({ systemStatus: status });
    },
  })),
);

// Селекторы для производных данных
export const useActiveTraders = () =>
  useTradingStore(state => state.traders.filter(t => t.status === 'active'));

export const useSelectedTraderPositions = () =>
  useTradingStore(state => {
    const selectedTraderId = state.selectedTraderId;
    return selectedTraderId
      ? state.positions.filter(p => p.trader_id === selectedTraderId)
      : [];
  });

export const useSelectedTraderOrders = () =>
  useTradingStore(state => {
    const selectedTraderId = state.selectedTraderId;
    return selectedTraderId
      ? state.orders.filter(o => o.trader_id === selectedTraderId)
      : [];
  });
