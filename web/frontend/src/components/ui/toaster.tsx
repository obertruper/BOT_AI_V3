import React from 'react';
import { useNotifications } from '@/store/useAppStore';
import { X, CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react';

export const Toaster: React.FC = () => {
  const notifications = useNotifications();

  const getIcon = (type: string) => {
    switch (type) {
      case 'success': return CheckCircle;
      case 'error': return XCircle;
      case 'warning': return AlertCircle;
      default: return Info;
    }
  };

  const getColors = (type: string) => {
    switch (type) {
      case 'success': return 'bg-green-600 text-green-100 border-green-500';
      case 'error': return 'bg-red-600 text-red-100 border-red-500';
      case 'warning': return 'bg-yellow-600 text-yellow-100 border-yellow-500';
      default: return 'bg-blue-600 text-blue-100 border-blue-500';
    }
  };

  if (notifications.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {notifications.map((notification) => {
        const Icon = getIcon(notification.type);
        const colors = getColors(notification.type);

        return (
          <div
            key={notification.id}
            className={`max-w-sm p-4 rounded-lg border shadow-lg ${colors} animate-slide-in`}
          >
            <div className="flex items-start space-x-3">
              <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="font-semibold text-sm">{notification.title}</div>
                <div className="text-sm opacity-90">{notification.message}</div>
              </div>
              <button 
                className="flex-shrink-0 opacity-70 hover:opacity-100"
                onClick={() => {/* Remove notification */}}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};