import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { SystemStatus, Position, MLSignal, TradingStrategy, Order, ExchangeInfo, MarketData } from '@/services/apiService';

interface AppState {
  // System Status
  systemStatus: SystemStatus | null;
  isSystemConnected: boolean;
  
  // Trading Data
  positions: Position[];
  orders: Order[];
  strategies: TradingStrategy[];
  mlSignals: MLSignal[];
  
  // Exchange Data
  exchanges: ExchangeInfo[];
  marketData: MarketData[];
  
  // UI State
  selectedSymbol: string;
  selectedTimeframe: string;
  theme: 'dark' | 'light';
  sidebarCollapsed: boolean;
  activeTab: string;
  
  // Notification State
  notifications: Array<{
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message: string;
    timestamp: Date;
  }>;
  
  // Loading States
  loading: {
    system: boolean;
    positions: boolean;
    orders: boolean;
    strategies: boolean;
    mlSignals: boolean;
    exchanges: boolean;
    marketData: boolean;
  };
}

interface AppActions {
  // System Actions
  setSystemStatus: (status: SystemStatus | null) => void;
  setSystemConnected: (connected: boolean) => void;
  
  // Trading Actions
  setPositions: (positions: Position[]) => void;
  setOrders: (orders: Order[]) => void;
  setStrategies: (strategies: TradingStrategy[]) => void;
  setMLSignals: (signals: MLSignal[]) => void;
  updateStrategy: (id: string, updates: Partial<TradingStrategy>) => void;
  
  // Exchange Actions
  setExchanges: (exchanges: ExchangeInfo[]) => void;
  setMarketData: (data: MarketData[]) => void;
  
  // UI Actions
  setSelectedSymbol: (symbol: string) => void;
  setSelectedTimeframe: (timeframe: string) => void;
  setTheme: (theme: 'dark' | 'light') => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveTab: (tab: string) => void;
  
  // Notification Actions
  addNotification: (notification: Omit<AppState['notifications'][0], 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
  
  // Loading Actions
  setLoading: (key: keyof AppState['loading'], loading: boolean) => void;
  
  // Utility Actions
  reset: () => void;
}

const initialState: AppState = {
  systemStatus: null,
  isSystemConnected: false,
  positions: [],
  orders: [],
  strategies: [],
  mlSignals: [],
  exchanges: [],
  marketData: [],
  selectedSymbol: 'BTCUSDT',
  selectedTimeframe: '1h',
  theme: 'dark',
  sidebarCollapsed: false,
  activeTab: 'dashboard',
  notifications: [],
  loading: {
    system: false,
    positions: false,
    orders: false,
    strategies: false,
    mlSignals: false,
    exchanges: false,
    marketData: false,
  },
};

export const useAppStore = create<AppState & AppActions>()(
  devtools(
    (set) => ({
        ...initialState,
        
        // System Actions
        setSystemStatus: (status) => set({ systemStatus: status }),
        setSystemConnected: (connected) => set({ isSystemConnected: connected }),
        
        // Trading Actions
        setPositions: (positions) => set({ positions }),
        setOrders: (orders) => set({ orders }),
        setStrategies: (strategies) => set({ strategies }),
        setMLSignals: (signals) => set({ mlSignals: signals }),
        updateStrategy: (id, updates) => set((state) => ({
          strategies: state.strategies.map(strategy =>
            strategy.id === id ? { ...strategy, ...updates } : strategy
          )
        })),
        
        // Exchange Actions
        setExchanges: (exchanges) => set({ exchanges }),
        setMarketData: (data) => set({ marketData: data }),
        
        // UI Actions
        setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
        setSelectedTimeframe: (timeframe) => set({ selectedTimeframe: timeframe }),
        setTheme: (theme) => set({ theme }),
        setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
        setActiveTab: (tab) => set({ activeTab: tab }),
        
        // Notification Actions
        addNotification: (notification) => {
          const id = Date.now().toString();
          const timestamp = new Date();
          set((state) => ({
            notifications: [...state.notifications, { ...notification, id, timestamp }]
          }));
          
          // Auto-remove after 5 seconds
          setTimeout(() => {
            set((state) => ({
              notifications: state.notifications.filter(n => n.id !== id)
            }));
          }, 5000);
        },
        removeNotification: (id) => set((state) => ({
          notifications: state.notifications.filter(n => n.id !== id)
        })),
        clearNotifications: () => set({ notifications: [] }),
        
        // Loading Actions
        setLoading: (key, loading) => set((state) => ({
          loading: { ...state.loading, [key]: loading }
        })),
        
        // Utility Actions
        reset: () => set(initialState),
    }),
    {
      name: 'bot-trading-store',
    }
  )
);

// Selectors for better performance
export const useSystemStatus = () => useAppStore((state) => state.systemStatus);
export const usePositions = () => useAppStore((state) => state.positions);
export const useOrders = () => useAppStore((state) => state.orders);
export const useStrategies = () => useAppStore((state) => state.strategies);
export const useMLSignals = () => useAppStore((state) => state.mlSignals);
export const useExchanges = () => useAppStore((state) => state.exchanges);
export const useMarketData = () => useAppStore((state) => state.marketData);
export const useNotifications = () => useAppStore((state) => state.notifications);
export const useLoading = () => useAppStore((state) => state.loading);
export const useUI = () => useAppStore((state) => ({
  selectedSymbol: state.selectedSymbol,
  selectedTimeframe: state.selectedTimeframe,
  theme: state.theme,
  sidebarCollapsed: state.sidebarCollapsed,
  activeTab: state.activeTab,
}));