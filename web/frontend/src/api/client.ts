// API клиент для BOT_Trading v3.0

import { 
  Trader, 
  Position, 
  Order, 
  SystemStatus, 
  TradingStats, 
  ApiResponse, 
  PaginatedResponse 
} from '@/types/trading'

class APIClient {
  private baseURL: string
  private defaultHeaders: Record<string, string>

  constructor(baseURL: string = '/api') {
    this.baseURL = baseURL
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`
    
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (error) {
      console.error(`API request failed: ${endpoint}`, error)
      throw error
    }
  }

  // Методы для работы с системой
  async getSystemStatus(): Promise<ApiResponse<SystemStatus>> {
    return this.request<SystemStatus>('/system/status')
  }

  async getHealth(): Promise<ApiResponse<{ status: string }>> {
    return this.request<{ status: string }>('/health')
  }

  // Методы для работы с трейдерами
  async getTraders(): Promise<ApiResponse<Trader[]>> {
    return this.request<Trader[]>('/traders')
  }

  async getTrader(traderId: string): Promise<ApiResponse<Trader>> {
    return this.request<Trader>(`/traders/${traderId}`)
  }

  async createTrader(config: any): Promise<ApiResponse<Trader>> {
    return this.request<Trader>('/traders', {
      method: 'POST',
      body: JSON.stringify(config),
    })
  }

  async updateTrader(traderId: string, config: any): Promise<ApiResponse<Trader>> {
    return this.request<Trader>(`/traders/${traderId}`, {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  }

  async deleteTrader(traderId: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/traders/${traderId}`, {
      method: 'DELETE',
    })
  }

  async startTrader(traderId: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/traders/${traderId}/start`, {
      method: 'POST',
    })
  }

  async stopTrader(traderId: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/traders/${traderId}/stop`, {
      method: 'POST',
    })
  }

  async pauseTrader(traderId: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/traders/${traderId}/pause`, {
      method: 'POST',
    })
  }

  // Методы для работы с позициями
  async getPositions(traderId?: string): Promise<ApiResponse<Position[]>> {
    const endpoint = traderId ? `/traders/${traderId}/positions` : '/positions'
    return this.request<Position[]>(endpoint)
  }

  async getPosition(positionId: string): Promise<ApiResponse<Position>> {
    return this.request<Position>(`/positions/${positionId}`)
  }

  async closePosition(positionId: string, percentage?: number): Promise<ApiResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/positions/${positionId}/close`, {
      method: 'POST',
      body: JSON.stringify({ percentage }),
    })
  }

  async updateStopLoss(positionId: string, stopLoss: number): Promise<ApiResponse<Position>> {
    return this.request<Position>(`/positions/${positionId}/stop-loss`, {
      method: 'PUT',
      body: JSON.stringify({ stop_loss: stopLoss }),
    })
  }

  async updateTakeProfit(positionId: string, takeProfit: number): Promise<ApiResponse<Position>> {
    return this.request<Position>(`/positions/${positionId}/take-profit`, {
      method: 'PUT',
      body: JSON.stringify({ take_profit: takeProfit }),
    })
  }

  // Методы для работы с ордерами
  async getOrders(traderId?: string): Promise<ApiResponse<PaginatedResponse<Order>>> {
    const endpoint = traderId ? `/traders/${traderId}/orders` : '/orders'
    return this.request<PaginatedResponse<Order>>(endpoint)
  }

  async getOrder(orderId: string): Promise<ApiResponse<Order>> {
    return this.request<Order>(`/orders/${orderId}`)
  }

  async cancelOrder(orderId: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/orders/${orderId}/cancel`, {
      method: 'POST',
    })
  }

  // Методы для работы со статистикой
  async getTradingStats(traderId?: string, period?: string): Promise<ApiResponse<TradingStats>> {
    const params = new URLSearchParams()
    if (traderId) params.append('trader_id', traderId)
    if (period) params.append('period', period)
    
    const query = params.toString()
    const endpoint = `/stats/trading${query ? `?${query}` : ''}`
    
    return this.request<TradingStats>(endpoint)
  }

  // Методы для работы с биржами
  async getExchanges(): Promise<ApiResponse<any[]>> {
    return this.request<any[]>('/exchanges')
  }

  async getExchangeInfo(exchange: string): Promise<ApiResponse<any>> {
    return this.request<any>(`/exchanges/${exchange}/info`)
  }

  async testExchangeConnection(exchange: string): Promise<ApiResponse<{ success: boolean }>> {
    return this.request<{ success: boolean }>(`/exchanges/${exchange}/test`, {
      method: 'POST',
    })
  }

  // Методы для работы с конфигурацией
  async getConfig(): Promise<ApiResponse<any>> {
    return this.request<any>('/config')
  }

  async updateConfig(config: any): Promise<ApiResponse<any>> {
    return this.request<any>('/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  }

  // Методы для логов
  async getLogs(lines?: number, filter?: string): Promise<ApiResponse<string[]>> {
    const params = new URLSearchParams()
    if (lines) params.append('lines', lines.toString())
    if (filter) params.append('filter', filter)
    
    const query = params.toString()
    const endpoint = `/logs${query ? `?${query}` : ''}`
    
    return this.request<string[]>(endpoint)
  }
}

// Создаем экземпляр клиента
const apiClient = new APIClient()

export default apiClient

// Экспортируем отдельные методы для удобства
export const {
  getSystemStatus,
  getHealth,
  getTraders,
  getTrader,
  createTrader,
  updateTrader,
  deleteTrader,
  startTrader,
  stopTrader,
  pauseTrader,
  getPositions,
  getPosition,
  closePosition,
  updateStopLoss,
  updateTakeProfit,
  getOrders,
  getOrder,
  cancelOrder,
  getTradingStats,
  getExchanges,
  getExchangeInfo,
  testExchangeConnection,
  getConfig,
  updateConfig,
  getLogs,
} = apiClient