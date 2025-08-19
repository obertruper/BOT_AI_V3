import React, { useEffect, useState } from 'react';
import { X, Bell, CheckCircle, AlertTriangle, Info, XCircle, TrendingUp, Zap } from 'lucide-react';

interface Notification {
  id: string;
  type: 'success' | 'warning' | 'error' | 'info' | 'trade' | 'signal';
  title: string;
  message: string;
  timestamp: Date;
  autoClose?: boolean;
  duration?: number;
}

interface NotificationCenterProps {
  notifications: Notification[];
  onRemove: (id: string) => void;
  maxVisible?: number;
}

const NotificationCenter: React.FC<NotificationCenterProps> = ({ 
  notifications, 
  onRemove,
  maxVisible = 5 
}) => {
  const [visibleNotifications, setVisibleNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    setVisibleNotifications(notifications.slice(0, maxVisible));
  }, [notifications, maxVisible]);

  useEffect(() => {
    const timers = visibleNotifications.map(notification => {
      if (notification.autoClose !== false) {
        const duration = notification.duration || 5000;
        return setTimeout(() => {
          onRemove(notification.id);
        }, duration);
      }
      return null;
    }).filter(Boolean);

    return () => {
      timers.forEach(timer => timer && clearTimeout(timer));
    };
  }, [visibleNotifications, onRemove]);

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success': return CheckCircle;
      case 'warning': return AlertTriangle;
      case 'error': return XCircle;
      case 'info': return Info;
      case 'trade': return TrendingUp;
      case 'signal': return Zap;
      default: return Bell;
    }
  };

  const getNotificationColors = (type: string) => {
    switch (type) {
      case 'success':
        return {
          bg: 'bg-green-900/90 border-green-500/50',
          icon: 'text-green-400',
          text: 'text-green-100',
          accent: 'bg-green-500'
        };
      case 'warning':
        return {
          bg: 'bg-yellow-900/90 border-yellow-500/50',
          icon: 'text-yellow-400',
          text: 'text-yellow-100',
          accent: 'bg-yellow-500'
        };
      case 'error':
        return {
          bg: 'bg-red-900/90 border-red-500/50',
          icon: 'text-red-400',
          text: 'text-red-100',
          accent: 'bg-red-500'
        };
      case 'trade':
        return {
          bg: 'bg-blue-900/90 border-blue-500/50',
          icon: 'text-blue-400',
          text: 'text-blue-100',
          accent: 'bg-blue-500'
        };
      case 'signal':
        return {
          bg: 'bg-purple-900/90 border-purple-500/50',
          icon: 'text-purple-400',
          text: 'text-purple-100',
          accent: 'bg-purple-500'
        };
      default:
        return {
          bg: 'bg-gray-900/90 border-gray-500/50',
          icon: 'text-gray-400',
          text: 'text-gray-100',
          accent: 'bg-gray-500'
        };
    }
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  if (visibleNotifications.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-3 max-w-md">
      {visibleNotifications.map((notification, index) => {
        const Icon = getNotificationIcon(notification.type);
        const colors = getNotificationColors(notification.type);
        
        return (
          <div
            key={notification.id}
            className={`${colors.bg} backdrop-blur-sm border ${colors.bg} rounded-xl p-4 shadow-2xl 
              transform transition-all duration-500 ease-out animate-slide-in-right relative overflow-hidden`}
            style={{
              animationDelay: `${index * 100}ms`,
              animation: `slideInFromRight 0.5s ease-out ${index * 0.1}s both`
            }}
          >
            {/* Progress Bar */}
            {notification.autoClose !== false && (
              <div 
                className={`absolute bottom-0 left-0 h-1 ${colors.accent} rounded-full transition-all`}
                style={{
                  width: '100%',
                  animation: `progress ${notification.duration || 5000}ms linear`
                }}
              />
            )}
            
            <div className="flex items-start space-x-3">
              {/* Icon */}
              <div className={`flex-shrink-0 ${colors.icon} animate-pulse`}>
                <Icon className="w-5 h-5" />
              </div>
              
              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className={`text-sm font-semibold ${colors.text} mb-1`}>
                  {notification.title}
                </div>
                <div className={`text-sm ${colors.text} opacity-90 mb-2`}>
                  {notification.message}
                </div>
                <div className={`text-xs ${colors.text} opacity-60`}>
                  {formatTime(notification.timestamp)}
                </div>
              </div>
              
              {/* Close Button */}
              <button
                onClick={() => onRemove(notification.id)}
                className={`flex-shrink-0 ${colors.text} hover:opacity-80 transition-opacity`}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        );
      })}
      
      <style jsx>{`
        @keyframes slideInFromRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
        
        @keyframes progress {
          from {
            width: 100%;
          }
          to {
            width: 0%;
          }
        }
        
        .animate-slide-in-right {
          animation: slideInFromRight 0.5s ease-out;
        }
      `}</style>
    </div>
  );
};

// Helper function to create notifications
export const createNotification = (
  type: Notification['type'],
  title: string,
  message: string,
  options?: Partial<Pick<Notification, 'autoClose' | 'duration'>>
): Notification => ({
  id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
  type,
  title,
  message,
  timestamp: new Date(),
  autoClose: options?.autoClose ?? true,
  duration: options?.duration ?? 5000,
});

export default NotificationCenter;