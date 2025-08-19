import { useEffect, useRef, useCallback } from 'react';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { useAppStore } from '@/store/useAppStore';
import { SystemStatus, Position, MLSignal, Order, MarketData } from '@/services/apiService';

interface WebSocketMessage {
  type: 'system_status' | 'position_update' | 'order_update' | 'ml_signal' | 'market_data' | 'notification';
  data: any;
  timestamp: string;
}

export const useWebSocketConnection = () => {
  const {
    setSystemStatus,
    setSystemConnected,
    setPositions,
    setOrders,
    setMLSignals,
    setMarketData,
    addNotification,
  } = useAppStore();
  
  const lastJsonMessage = useRef<WebSocketMessage | null>(null);

  const { sendMessage, lastMessage, readyState } = useWebSocket(
    'ws://localhost:8083/ws', 
    {
      onOpen: () => {
        console.log('WebSocket connection established');
        setSystemConnected(true);
      },
      onClose: () => {
        console.log('WebSocket connection closed');
        setSystemConnected(false);
      },
      onError: (error) => {
        console.error('WebSocket error:', error);
        setSystemConnected(false);
      },
      shouldReconnect: () => true,
      reconnectAttempts: 10,
      reconnectInterval: 3000,
    }
  );

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'system_status':
        setSystemStatus(message.data as SystemStatus);
        break;
        
      case 'position_update':
        if (Array.isArray(message.data)) {
          setPositions(message.data as Position[]);
        }
        break;
        
      case 'order_update':
        if (Array.isArray(message.data)) {
          setOrders(message.data as Order[]);
        }
        break;
        
      case 'ml_signal':
        if (Array.isArray(message.data)) {
          setMLSignals(message.data as MLSignal[]);
        }
        break;
        
      case 'market_data':
        setMarketData(message.data as MarketData[]);
        break;
        
      case 'notification':
        addNotification({
          type: message.data.type || 'info',
          title: message.data.title || 'System Notification',
          message: message.data.message || 'No message provided',
        });
        break;
        
      default:
        console.warn('Unknown WebSocket message type:', message.type);
    }
  }, [setSystemStatus, setPositions, setOrders, setMLSignals, setMarketData, addNotification]);

  useEffect(() => {
    if (lastMessage !== null) {
      try {
        const message: WebSocketMessage = JSON.parse(lastMessage.data);
        lastJsonMessage.current = message;
        handleMessage(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    }
  }, [lastMessage, handleMessage]);

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Open',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Closed',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];

  const sendWebSocketMessage = useCallback((type: string, data: any) => {
    if (readyState === ReadyState.OPEN) {
      sendMessage(JSON.stringify({
        type,
        data,
        timestamp: new Date().toISOString(),
      }));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, [sendMessage, readyState]);

  return {
    connectionStatus,
    isConnected: readyState === ReadyState.OPEN,
    sendMessage: sendWebSocketMessage,
    lastMessage: lastJsonMessage.current,
  };
};