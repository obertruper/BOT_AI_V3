import { useEffect, useRef, useState, useCallback } from 'react';
import useWebSocketLib, { ReadyState } from 'react-use-websocket';
import { WebSocketEvent } from '@/types/trading';

interface UseWebSocketOptions {
  onMessage?: (event: WebSocketEvent) => void
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  reconnectAttempts?: number
  reconnectInterval?: number
  shouldReconnect?: boolean
}

interface UseWebSocketReturn {
  sendMessage: (type: string, data: any) => void
  readyState: ReadyState
  connectionStatus: string
  lastMessage: WebSocketEvent | null
  isConnected: boolean
}

export function useWebSocket(
  endpoint: string,
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const {
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectAttempts = 5,
    reconnectInterval = 3000,
    shouldReconnect = true,
  } = options;

  const [lastMessage, setLastMessage] = useState<WebSocketEvent | null>(null);

  // Создаем WebSocket URL
  const socketUrl = `ws://localhost:8080/ws/${endpoint}`;

  const {
    sendJsonMessage,
    lastJsonMessage,
    readyState,
    getWebSocket,
  } = useWebSocketLib(socketUrl, {
    onOpen: () => {
      console.log(`WebSocket connected to ${endpoint}`);
      onConnect?.();
    },
    onClose: () => {
      console.log(`WebSocket disconnected from ${endpoint}`);
      onDisconnect?.();
    },
    onError: (error) => {
      console.error(`WebSocket error on ${endpoint}:`, error);
      onError?.(error);
    },
    shouldReconnect: () => shouldReconnect,
    reconnectAttempts,
    reconnectInterval,
    share: false, // Не делимся соединением между хуками
  });

  // Обработка входящих сообщений
  useEffect(() => {
    if (lastJsonMessage) {
      const event = lastJsonMessage as WebSocketEvent;
      setLastMessage(event);
      onMessage?.(event);
    }
  }, [lastJsonMessage, onMessage]);

  // Функция для отправки сообщений
  const sendMessage = useCallback((type: string, data: any) => {
    if (readyState === ReadyState.OPEN) {
      const message = {
        type,
        data,
        timestamp: Date.now(),
      };
      sendJsonMessage(message);
    } else {
      console.warn('WebSocket is not connected. Message not sent:', { type, data });
    }
  }, [readyState, sendJsonMessage]);

  // Определяем статус соединения
  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Подключение...',
    [ReadyState.OPEN]: 'Подключено',
    [ReadyState.CLOSING]: 'Отключение...',
    [ReadyState.CLOSED]: 'Отключено',
    [ReadyState.UNINSTANTIATED]: 'Не инициализировано',
  }[readyState];

  const isConnected = readyState === ReadyState.OPEN;

  return {
    sendMessage,
    readyState,
    connectionStatus,
    lastMessage,
    isConnected,
  };
}

// Специализированные хуки для разных типов WebSocket соединений

export function usePriceUpdates() {
  const [prices, setPrices] = useState<Record<string, number>>({});

  const { sendMessage, isConnected } = useWebSocket('price_updates', {
    onMessage: (event) => {
      if (event.type === 'price_update') {
        setPrices(prev => ({
          ...prev,
          [event.data.symbol]: event.data.price,
        }));
      }
    },
  });

  const subscribeToPrices = useCallback((symbols: string[]) => {
    if (isConnected) {
      sendMessage('subscribe_prices', { symbols });
    }
  }, [sendMessage, isConnected]);

  const unsubscribeFromPrices = useCallback((symbols: string[]) => {
    if (isConnected) {
      sendMessage('unsubscribe_prices', { symbols });
    }
  }, [sendMessage, isConnected]);

  return {
    prices,
    subscribeToPrices,
    unsubscribeFromPrices,
    isConnected,
  };
}

export function useTraderUpdates() {
  const [traderEvents, setTraderEvents] = useState<WebSocketEvent[]>([]);

  const { isConnected } = useWebSocket('trader_updates', {
    onMessage: (event) => {
      if (['trader_status', 'position_update', 'order_update'].includes(event.type)) {
        setTraderEvents(prev => [event, ...prev.slice(0, 99)]); // Храним последние 100 событий
      }
    },
  });

  return {
    traderEvents,
    isConnected,
  };
}

export function useSystemUpdates() {
  const [systemStatus, setSystemStatus] = useState<any>(null);

  const { isConnected } = useWebSocket('system_updates', {
    onMessage: (event) => {
      if (event.type === 'system_status') {
        setSystemStatus(event.data);
      }
    },
  });

  return {
    systemStatus,
    isConnected,
  };
}
