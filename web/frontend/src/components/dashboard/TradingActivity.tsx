import React from 'react';
import { useOrders } from '@/store/useAppStore';
import { Activity, Clock, CheckCircle, XCircle, AlertCircle, TrendingUp, TrendingDown } from 'lucide-react';

const TradingActivity: React.FC = () => {
  const orders = useOrders();

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'filled':
      case 'closed': return CheckCircle;
      case 'cancelled':
      case 'rejected': return XCircle;
      case 'pending':
      case 'open': return Clock;
      default: return AlertCircle;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'filled':
      case 'closed': return 'text-green-400';
      case 'cancelled':
      case 'rejected': return 'text-red-400';
      case 'pending':
      case 'open': return 'text-yellow-400';
      default: return 'text-gray-400';
    }
  };


  const getSideIcon = (side: string) => {
    return side === 'buy' ? TrendingUp : TrendingDown;
  };

  const getSideColor = (side: string) => {
    return side === 'buy' ? 'text-green-400' : 'text-red-400';
  };


  const formatPrice = (price?: number) => {
    if (!price) return 'Market';
    return `$${price.toFixed(2)}`;
  };

  const formatAmount = (amount: number) => {
    return amount.toFixed(4);
  };

  const recentOrders = orders.slice(0, 10);
  const activeOrders = orders.filter(o => ['pending', 'open'].includes(o.status));
  const completedOrders = orders.filter(o => ['filled', 'closed'].includes(o.status));
  const cancelledOrders = orders.filter(o => ['cancelled', 'rejected'].includes(o.status));

  return (
    <div className="card animate-scale-in relative overflow-hidden">
      {/* Background gradient effect */}
      <div className="absolute inset-0 bg-gradient-to-br from-orange-600/10 to-amber-600/10 pointer-events-none"></div>
      <div className="relative z-10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-white flex items-center">
          <Activity className="w-5 h-5 mr-2 text-orange-400" />
          Trading Activity
        </h3>
        
        <div className="flex items-center space-x-3">
          <div className="px-3 py-2 bg-yellow-400/20 rounded-lg backdrop-blur-sm border border-yellow-400/30">
            <div className="text-lg font-bold text-yellow-400">{activeOrders.length}</div>
            <div className="text-xs text-gray-300 font-medium">Active</div>
          </div>
          <div className="px-3 py-2 bg-green-400/20 rounded-lg backdrop-blur-sm border border-green-400/30">
            <div className="text-lg font-bold text-green-400">{completedOrders.length}</div>
            <div className="text-xs text-gray-300 font-medium">Completed</div>
          </div>
          <div className="px-3 py-2 bg-red-400/20 rounded-lg backdrop-blur-sm border border-red-400/30">
            <div className="text-lg font-bold text-red-400">{cancelledOrders.length}</div>
            <div className="text-xs text-gray-300 font-medium">Cancelled</div>
          </div>
        </div>
      </div>

      {/* Order Summary Cards */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-orange-600/20 to-amber-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-orange-500/50 transition-all">
            <div className="text-2xl font-bold text-white">{orders.length}</div>
            <div className="text-xs text-gray-400 font-medium">Total Orders</div>
          </div>
        </div>
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-yellow-600/20 to-amber-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-yellow-500/50 transition-all">
            <div className="text-2xl font-bold text-yellow-400">{activeOrders.length}</div>
            <div className="text-xs text-gray-400 font-medium">Active</div>
          </div>
        </div>
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-green-600/20 to-emerald-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-green-500/50 transition-all">
            <div className="text-2xl font-bold text-green-400">{completedOrders.length}</div>
            <div className="text-xs text-gray-400 font-medium">Completed</div>
          </div>
        </div>
        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-red-600/20 to-rose-600/20 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity"></div>
          <div className="relative bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 text-center border border-gray-700/50 hover:border-red-500/50 transition-all">
            <div className="text-2xl font-bold text-red-400">{cancelledOrders.length}</div>
            <div className="text-xs text-gray-400 font-medium">Cancelled</div>
          </div>
        </div>
      </div>

      {/* Recent Orders Table */}
      <div>
        <h4 className="text-sm font-medium text-gray-400 mb-4 flex items-center">
          <Clock className="w-4 h-4 mr-2" />
          Recent Orders
        </h4>

        {recentOrders.length > 0 ? (
          <div className="space-y-2">
            {/* Header */}
            <div className="grid grid-cols-7 gap-4 text-xs font-medium text-gray-300 px-4 py-3 bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50">
              <div>Symbol</div>
              <div>Side</div>
              <div>Type</div>
              <div>Amount</div>
              <div>Price</div>
              <div>Status</div>
              <div>Time</div>
            </div>

            {/* Orders */}
            {recentOrders.map((order) => {
              const StatusIcon = getStatusIcon(order.status);
              const SideIcon = getSideIcon(order.side);
              const statusColor = getStatusColor(order.status);
              const sideColor = getSideColor(order.side);

              return (
                <div key={order.id} className="relative group">
                  <div className="absolute inset-0 bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl blur-sm"
                       style={{
                         background: order.side === 'buy' 
                           ? 'linear-gradient(90deg, rgba(34,197,94,0.05) 0%, rgba(16,185,129,0.05) 100%)'
                           : 'linear-gradient(90deg, rgba(239,68,68,0.05) 0%, rgba(220,38,38,0.05) 100%)'
                       }}></div>
                  <div className="relative grid grid-cols-7 gap-4 text-sm px-4 py-3 bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-700/50 hover:border-gray-600/50 transition-all">
                    <div className="font-semibold text-white">{order.symbol}</div>
                    
                    <div className="flex items-center space-x-1">
                      <SideIcon className={`w-4 h-4 ${sideColor}`} />
                      <span className={`capitalize font-medium ${sideColor}`}>{order.side}</span>
                    </div>
                    
                    <div className="text-gray-300 capitalize">{order.type}</div>
                    
                    <div className="text-white">
                      {formatAmount(order.amount)}
                      {order.filled > 0 && (
                        <div className="text-xs text-gray-400">
                          Filled: {formatAmount(order.filled)}
                        </div>
                      )}
                    </div>
                    
                    <div className="text-white font-medium">{formatPrice(order.price)}</div>
                    
                    <div className="flex items-center space-x-1">
                      <StatusIcon className={`w-4 h-4 ${statusColor}`} />
                      <span className={`capitalize text-xs font-medium ${statusColor}`}>{order.status}</span>
                    </div>
                    
                    <div className="text-xs text-gray-400">
                      {new Date(order.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12 bg-gray-800/30 rounded-xl border border-gray-700/50">
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-orange-600/20 to-amber-600/20 rounded-full mb-4">
              <Activity className="w-10 h-10 text-orange-400" />
            </div>
            <div className="text-gray-300 font-medium text-lg">No trading activity</div>
            <div className="text-sm text-gray-500 mt-2">Orders will appear here when trading begins</div>
          </div>
        )}
      </div>

      {/* Trading Statistics */}
      <div className="mt-6 pt-4 border-t border-gray-700/50">
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gradient-to-br from-blue-600/10 to-cyan-600/10 rounded-xl p-4 text-center border border-gray-700/50">
            <div className="text-xl font-bold text-white">
              {completedOrders.length > 0 ? 
                ((completedOrders.length / orders.length) * 100).toFixed(1) : 
                '0.0'
              }%
            </div>
            <div className="text-xs text-gray-400 font-medium">Fill Rate</div>
          </div>
          
          <div className="bg-gradient-to-br from-yellow-600/10 to-orange-600/10 rounded-xl p-4 text-center border border-gray-700/50">
            <div className="text-xl font-bold text-white">
              ${orders.reduce((sum, o) => sum + (o.fees || 0), 0).toFixed(2)}
            </div>
            <div className="text-xs text-gray-400 font-medium">Total Fees</div>
          </div>
          
          <div className="bg-gradient-to-br from-purple-600/10 to-pink-600/10 rounded-xl p-4 text-center border border-gray-700/50">
            <div className="text-xl font-bold text-white">
              {orders.length > 0 ? 
                (orders.reduce((sum, o) => sum + o.amount, 0) / orders.length).toFixed(2) : 
                '0.00'
              }
            </div>
            <div className="text-xs text-gray-400 font-medium">Avg Order Size</div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};

export default TradingActivity;