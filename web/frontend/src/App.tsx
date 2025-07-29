import React, { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'

import { useTradingStore } from '@/store/tradingStore'
import { useWebSocket } from '@/hooks/useWebSocket'

// Страницы (пока заглушки)
import Dashboard from '@/pages/Dashboard'
import Traders from '@/pages/Traders'
import Positions from '@/pages/Positions'
import Orders from '@/pages/Orders'
import Analytics from '@/pages/Analytics'
import Settings from '@/pages/Settings'

import './App.css'

// Создаем клиент React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 минут
    },
  },
})

function App() {
  const { 
    fetchSystemStatus, 
    fetchTraders, 
    setWsConnected,
    updateTraderFromWS,
    updatePositionFromWS,
    updateOrderFromWS,
    updateSystemStatusFromWS,
    autoRefresh,
    refreshInterval,
  } = useTradingStore()

  // WebSocket для системных обновлений
  const { isConnected: systemWsConnected } = useWebSocket('system_updates', {
    onMessage: (event) => {
      switch (event.type) {
        case 'system_status':
          updateSystemStatusFromWS(event.data)
          break
        case 'trader_status':
          updateTraderFromWS(event.data)
          break
        case 'position_update':
          updatePositionFromWS(event.data)
          break
        case 'order_update':
          updateOrderFromWS(event.data)
          break
      }
    },
    onConnect: () => {
      setWsConnected(true)
    },
    onDisconnect: () => {
      setWsConnected(false)
    },
  })

  // Начальная загрузка данных
  useEffect(() => {
    fetchSystemStatus()
    fetchTraders()
  }, [fetchSystemStatus, fetchTraders])

  // Автообновление данных
  useEffect(() => {
    if (!autoRefresh || systemWsConnected) return

    const interval = setInterval(() => {
      fetchSystemStatus()
      fetchTraders()
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefresh, systemWsConnected, refreshInterval, fetchSystemStatus, fetchTraders])

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-background">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/traders" element={<Traders />} />
            <Route path="/positions" element={<Positions />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </Router>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}

export default App