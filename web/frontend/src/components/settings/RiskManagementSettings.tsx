import React, { useState } from 'react';
import { Shield, TrendingUp, Target, AlertTriangle, Save, Activity, DollarSign, Zap, BarChart3, Lock, Layers, AlertCircle } from 'lucide-react';

interface RiskManagementSettingsProps {
  onSave: () => void;
}

const RiskManagementSettings: React.FC<RiskManagementSettingsProps> = ({ onSave }) => {
  // Состояние для всех настроек риска
  const [config, setConfig] = useState({
    // Основные параметры риска
    riskPerTrade: 2.0,
    fixedRiskBalance: 500,
    maxTotalRisk: 10.0,
    maxPositions: 5,
    defaultLeverage: 5,
    maxLeverage: 20,
    
    // Профили риска
    riskProfile: 'standard',
    profiles: {
      standard: { multiplier: 1.0, confidence: 60, maxSize: 50 },
      conservative: { multiplier: 0.7, confidence: 70, maxSize: 35 },
      veryConservative: { multiplier: 0.5, confidence: 80, maxSize: 25 }
    },
    
    // Трейлинг стоп
    trailingStop: {
      enabled: true,
      activationPercent: 1.0,
      stepPercent: 0.5,
      minDistance: 0.3,
      adaptiveStep: true,
      maxUpdates: 15
    },
    
    // Частичный тейк-профит
    partialTP: {
      enabled: true,
      levels: [
        { percent: 1.0, closeRatio: 30 },
        { percent: 2.0, closeRatio: 30 },
        { percent: 3.0, closeRatio: 40 }
      ],
      moveToBreakeven: true
    },
    
    // Защита прибыли
    profitProtection: {
      enabled: true,
      breakevenAt: 0.5,
      levels: [
        { trigger: 1.0, lock: 0.5 },
        { trigger: 2.0, lock: 1.0 },
        { trigger: 3.0, lock: 1.5 }
      ]
    },
    
    // Динамические SL/TP
    dynamicSLTP: {
      minSL: 1.0,
      maxSL: 2.0,
      minTP: 3.6,
      maxTP: 6.0,
      weights: {
        volatility: 50,
        rsi: 15,
        volume: 15,
        trend: 20
      }
    }
  });

  // Функция обновления конфигурации
  const updateConfig = (path: string, value: any) => {
    const keys = path.split('.');
    setConfig(prevConfig => {
      const newConfig = { ...prevConfig };
      let current: any = newConfig;
      
      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) current[keys[i]] = {};
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      
      return newConfig;
    });
  };

  // Добавление нового уровня частичного TP
  const addPartialTPLevel = () => {
    const currentLevels = config.partialTP.levels;
    if (currentLevels.length < 5) {
      const lastPercent = currentLevels[currentLevels.length - 1]?.percent || 0;
      updateConfig('partialTP.levels', [
        ...currentLevels,
        { percent: lastPercent + 1, closeRatio: 20 }
      ]);
    }
  };

  // Удаление уровня частичного TP
  const removePartialTPLevel = (index: number) => {
    updateConfig('partialTP.levels', 
      config.partialTP.levels.filter((_, i) => i !== index)
    );
  };

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-semibold text-white">Risk Management Configuration</h3>
          <p className="text-gray-400 text-sm mt-1">Настройка параметров управления рисками, стоп-лоссов и тейк-профитов</p>
        </div>
        <button
          onClick={onSave}
          className="flex items-center space-x-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-white font-medium transition-colors"
        >
          <Save className="w-4 h-4" />
          <span>Сохранить настройки</span>
        </button>
      </div>

      {/* 1. Основные параметры риска */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-red-600 to-orange-600 rounded-xl flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Основные параметры риска</h4>
              <p className="text-sm text-gray-400">Базовые настройки управления капиталом</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Риск на сделку: {config.riskPerTrade}%
              </label>
              <input
                type="range"
                min="0.5"
                max="5"
                step="0.1"
                value={config.riskPerTrade}
                onChange={(e) => updateConfig('riskPerTrade', parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0.5%</span>
                <span>5%</span>
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Фиксированный баланс для расчетов (USD)
              </label>
              <input
                type="number"
                value={config.fixedRiskBalance}
                onChange={(e) => updateConfig('fixedRiskBalance', parseFloat(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Максимальный общий риск: {config.maxTotalRisk}%
              </label>
              <input
                type="range"
                min="1"
                max="20"
                step="0.5"
                value={config.maxTotalRisk}
                onChange={(e) => updateConfig('maxTotalRisk', parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Максимум позиций: {config.maxPositions}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={config.maxPositions}
                onChange={(e) => updateConfig('maxPositions', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Дефолтное плечо: {config.defaultLeverage}x
              </label>
              <select
                value={config.defaultLeverage}
                onChange={(e) => updateConfig('defaultLeverage', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
              >
                {[1, 2, 3, 5, 10, 15, 20].map(leverage => (
                  <option key={leverage} value={leverage}>{leverage}x</option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Максимальное плечо: {config.maxLeverage}x
              </label>
              <select
                value={config.maxLeverage}
                onChange={(e) => updateConfig('maxLeverage', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:ring-2 focus:ring-blue-500"
              >
                {[5, 10, 15, 20, 25, 30].map(leverage => (
                  <option key={leverage} value={leverage}>{leverage}x</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Профили риска */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Профили риска</h4>
              <p className="text-sm text-gray-400">Выберите подходящий профиль торговли</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(config.profiles).map(([key, profile]) => (
              <div
                key={key}
                onClick={() => updateConfig('riskProfile', key)}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  config.riskProfile === key
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <div className="text-lg font-semibold text-white mb-2">
                  {key === 'standard' ? 'Стандартный' : 
                   key === 'conservative' ? 'Консервативный' : 
                   'Очень консервативный'}
                </div>
                <div className="space-y-1 text-sm">
                  <div className="text-gray-400">
                    Множитель: <span className="text-white">{profile.multiplier}x</span>
                  </div>
                  <div className="text-gray-400">
                    Уверенность: <span className="text-white">{profile.confidence}%</span>
                  </div>
                  <div className="text-gray-400">
                    Макс. размер: <span className="text-white">${profile.maxSize}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 3. Трейлинг стоп */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-r from-green-600 to-blue-600 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-white">Трейлинг стоп</h4>
                <p className="text-sm text-gray-400">Автоматическое следование за ценой</p>
              </div>
            </div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.trailingStop.enabled}
                onChange={(e) => updateConfig('trailingStop.enabled', e.target.checked)}
                className="w-5 h-5 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500"
              />
              <span className="text-white">Включено</span>
            </label>
          </div>
          
          {config.trailingStop.enabled && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Активация при прибыли: {config.trailingStop.activationPercent}%
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="5"
                  step="0.1"
                  value={config.trailingStop.activationPercent}
                  onChange={(e) => updateConfig('trailingStop.activationPercent', parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Шаг трейлинга: {config.trailingStop.stepPercent}%
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="2"
                  step="0.1"
                  value={config.trailingStop.stepPercent}
                  onChange={(e) => updateConfig('trailingStop.stepPercent', parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Минимальная дистанция: {config.trailingStop.minDistance}%
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.1"
                  value={config.trailingStop.minDistance}
                  onChange={(e) => updateConfig('trailingStop.minDistance', parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Максимум обновлений: {config.trailingStop.maxUpdates}
                </label>
                <input
                  type="range"
                  min="5"
                  max="50"
                  step="1"
                  value={config.trailingStop.maxUpdates}
                  onChange={(e) => updateConfig('trailingStop.maxUpdates', parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>
              
              <div className="md:col-span-2">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={config.trailingStop.adaptiveStep}
                    onChange={(e) => updateConfig('trailingStop.adaptiveStep', e.target.checked)}
                    className="w-5 h-5 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500"
                  />
                  <div>
                    <span className="text-white font-medium">Адаптивный трейлинг</span>
                    <div className="text-xs text-gray-400">Автоматическая корректировка шага на основе волатильности</div>
                  </div>
                </label>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 4. Частичный тейк-профит */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl flex items-center justify-center">
                <Layers className="w-6 h-6 text-white" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-white">Частичный тейк-профит</h4>
                <p className="text-sm text-gray-400">Поэтапное закрытие позиции</p>
              </div>
            </div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.partialTP.enabled}
                onChange={(e) => updateConfig('partialTP.enabled', e.target.checked)}
                className="w-5 h-5 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500"
              />
              <span className="text-white">Включено</span>
            </label>
          </div>
          
          {config.partialTP.enabled && (
            <>
              <div className="space-y-3 mb-4">
                {config.partialTP.levels.map((level, index) => (
                  <div key={index} className="flex items-center space-x-4 p-3 bg-gray-800/50 rounded-lg">
                    <div className="flex-1 grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm text-gray-400">При прибыли %</label>
                        <input
                          type="number"
                          value={level.percent}
                          onChange={(e) => {
                            const newLevels = [...config.partialTP.levels];
                            newLevels[index].percent = parseFloat(e.target.value);
                            updateConfig('partialTP.levels', newLevels);
                          }}
                          step="0.1"
                          className="w-full mt-1 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-sm text-gray-400">Закрыть %</label>
                        <input
                          type="number"
                          value={level.closeRatio}
                          onChange={(e) => {
                            const newLevels = [...config.partialTP.levels];
                            newLevels[index].closeRatio = parseInt(e.target.value);
                            updateConfig('partialTP.levels', newLevels);
                          }}
                          className="w-full mt-1 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                        />
                      </div>
                    </div>
                    <button
                      onClick={() => removePartialTPLevel(index)}
                      className="text-red-400 hover:text-red-300"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
              
              {config.partialTP.levels.length < 5 && (
                <button
                  onClick={addPartialTPLevel}
                  className="w-full py-2 border border-dashed border-gray-600 rounded-lg text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
                >
                  + Добавить уровень
                </button>
              )}
              
              <div className="mt-4 pt-4 border-t border-gray-700">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={config.partialTP.moveToBreakeven}
                    onChange={(e) => updateConfig('partialTP.moveToBreakeven', e.target.checked)}
                    className="w-5 h-5 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500"
                  />
                  <div>
                    <span className="text-white font-medium">Перенос в безубыток</span>
                    <div className="text-xs text-gray-400">Переносить SL в безубыток после первого частичного закрытия</div>
                  </div>
                </label>
              </div>
              
              {/* Визуализация распределения */}
              <div className="mt-4 p-4 bg-gray-800/50 rounded-lg">
                <div className="text-sm text-gray-400 mb-2">Визуализация закрытий:</div>
                <div className="flex h-8 rounded overflow-hidden">
                  {config.partialTP.levels.map((level, index) => (
                    <div
                      key={index}
                      style={{ width: `${level.closeRatio}%` }}
                      className={`flex items-center justify-center text-xs text-white ${
                        index === 0 ? 'bg-blue-600' :
                        index === 1 ? 'bg-green-600' :
                        index === 2 ? 'bg-purple-600' :
                        index === 3 ? 'bg-orange-600' :
                        'bg-pink-600'
                      }`}
                    >
                      {level.closeRatio}%
                    </div>
                  ))}
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  {config.partialTP.levels.map((level, index) => (
                    <span key={index}>+{level.percent}%</span>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 5. Защита прибыли */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 bg-gradient-to-r from-yellow-600 to-orange-600 rounded-xl flex items-center justify-center">
                <Lock className="w-6 h-6 text-white" />
              </div>
              <div>
                <h4 className="text-lg font-semibold text-white">Защита прибыли</h4>
                <p className="text-sm text-gray-400">Фиксация достигнутой прибыли</p>
              </div>
            </div>
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={config.profitProtection.enabled}
                onChange={(e) => updateConfig('profitProtection.enabled', e.target.checked)}
                className="w-5 h-5 text-green-600 bg-gray-700 border-gray-600 rounded focus:ring-green-500"
              />
              <span className="text-white">Включено</span>
            </label>
          </div>
          
          {config.profitProtection.enabled && (
            <>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Безубыток при прибыли: {config.profitProtection.breakevenAt}%
                </label>
                <input
                  type="range"
                  min="0.1"
                  max="2"
                  step="0.1"
                  value={config.profitProtection.breakevenAt}
                  onChange={(e) => updateConfig('profitProtection.breakevenAt', parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
                />
              </div>
              
              <div className="space-y-3">
                <div className="text-sm font-medium text-gray-300 mb-2">Уровни защиты прибыли:</div>
                {config.profitProtection.levels.map((level, index) => (
                  <div key={index} className="grid grid-cols-2 gap-4 p-3 bg-gray-800/50 rounded-lg">
                    <div>
                      <label className="text-xs text-gray-400">При прибыли %</label>
                      <input
                        type="number"
                        value={level.trigger}
                        onChange={(e) => {
                          const newLevels = [...config.profitProtection.levels];
                          newLevels[index].trigger = parseFloat(e.target.value);
                          updateConfig('profitProtection.levels', newLevels);
                        }}
                        step="0.1"
                        className="w-full mt-1 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-400">Защитить %</label>
                      <input
                        type="number"
                        value={level.lock}
                        onChange={(e) => {
                          const newLevels = [...config.profitProtection.levels];
                          newLevels[index].lock = parseFloat(e.target.value);
                          updateConfig('profitProtection.levels', newLevels);
                        }}
                        step="0.1"
                        className="w-full mt-1 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* 6. Динамические SL/TP */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-indigo-600 to-blue-600 rounded-xl flex items-center justify-center">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Динамические SL/TP</h4>
              <p className="text-sm text-gray-400">Адаптивные уровни на основе рыночных условий</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Stop Loss диапазон</label>
              <div className="flex items-center space-x-3">
                <input
                  type="number"
                  value={config.dynamicSLTP.minSL}
                  onChange={(e) => updateConfig('dynamicSLTP.minSL', parseFloat(e.target.value))}
                  step="0.1"
                  className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm"
                  placeholder="Мин %"
                />
                <span className="text-gray-400">—</span>
                <input
                  type="number"
                  value={config.dynamicSLTP.maxSL}
                  onChange={(e) => updateConfig('dynamicSLTP.maxSL', parseFloat(e.target.value))}
                  step="0.1"
                  className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm"
                  placeholder="Макс %"
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Take Profit диапазон</label>
              <div className="flex items-center space-x-3">
                <input
                  type="number"
                  value={config.dynamicSLTP.minTP}
                  onChange={(e) => updateConfig('dynamicSLTP.minTP', parseFloat(e.target.value))}
                  step="0.1"
                  className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm"
                  placeholder="Мин %"
                />
                <span className="text-gray-400">—</span>
                <input
                  type="number"
                  value={config.dynamicSLTP.maxTP}
                  onChange={(e) => updateConfig('dynamicSLTP.maxTP', parseFloat(e.target.value))}
                  step="0.1"
                  className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm"
                  placeholder="Макс %"
                />
              </div>
            </div>
          </div>
          
          <div className="space-y-4">
            <div className="text-sm font-medium text-gray-300 mb-2">Веса факторов влияния:</div>
            
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Волатильность</span>
                <span className="text-white">{config.dynamicSLTP.weights.volatility}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={config.dynamicSLTP.weights.volatility}
                onChange={(e) => updateConfig('dynamicSLTP.weights.volatility', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">RSI</span>
                <span className="text-white">{config.dynamicSLTP.weights.rsi}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={config.dynamicSLTP.weights.rsi}
                onChange={(e) => updateConfig('dynamicSLTP.weights.rsi', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Объем</span>
                <span className="text-white">{config.dynamicSLTP.weights.volume}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={config.dynamicSLTP.weights.volume}
                onChange={(e) => updateConfig('dynamicSLTP.weights.volume', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">Тренд</span>
                <span className="text-white">{config.dynamicSLTP.weights.trend}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={config.dynamicSLTP.weights.trend}
                onChange={(e) => updateConfig('dynamicSLTP.weights.trend', parseInt(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              />
            </div>
            
            <div className="mt-4 p-3 bg-yellow-600/10 border border-yellow-600/30 rounded-lg">
              <div className="flex items-start space-x-2">
                <AlertCircle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-300">
                  Сумма весов: {Object.values(config.dynamicSLTP.weights).reduce((a, b) => a + b, 0)}%. 
                  Рекомендуется использовать 100% для оптимального баланса.
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 7. Симулятор риска */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center space-x-3 mb-6">
            <div className="w-12 h-12 bg-gradient-to-r from-cyan-600 to-blue-600 rounded-xl flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h4 className="text-lg font-semibold text-white">Симулятор риска</h4>
              <p className="text-sm text-gray-400">Оценка потенциальных результатов с текущими настройками</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-gray-800/50 rounded-xl text-center">
              <div className="text-2xl font-bold text-green-400">
                ${(config.fixedRiskBalance * config.riskPerTrade / 100).toFixed(2)}
              </div>
              <div className="text-sm text-gray-400 mt-1">Риск на сделку</div>
            </div>
            
            <div className="p-4 bg-gray-800/50 rounded-xl text-center">
              <div className="text-2xl font-bold text-blue-400">
                {((config.dynamicSLTP.minTP + config.dynamicSLTP.maxTP) / 2 / 
                  ((config.dynamicSLTP.minSL + config.dynamicSLTP.maxSL) / 2)).toFixed(2)}:1
              </div>
              <div className="text-sm text-gray-400 mt-1">Risk/Reward</div>
            </div>
            
            <div className="p-4 bg-gray-800/50 rounded-xl text-center">
              <div className="text-2xl font-bold text-purple-400">
                {(100 / ((config.dynamicSLTP.minTP + config.dynamicSLTP.maxTP) / 2 / 
                  ((config.dynamicSLTP.minSL + config.dynamicSLTP.maxSL) / 2) + 1)).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-400 mt-1">Точка безубытка</div>
            </div>
          </div>
          
          <div className="mt-4 p-4 bg-gray-800/50 rounded-xl">
            <div className="text-sm text-gray-400 mb-3">Потенциальные результаты (10 сделок):</div>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Лучший сценарий (70% winrate):</span>
                <span className="text-green-400 font-medium">
                  +${(config.fixedRiskBalance * config.riskPerTrade / 100 * 
                    (7 * (config.dynamicSLTP.minTP + config.dynamicSLTP.maxTP) / 2 / 100 - 
                     3 * (config.dynamicSLTP.minSL + config.dynamicSLTP.maxSL) / 2 / 100) * 10).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Средний сценарий (50% winrate):</span>
                <span className="text-blue-400 font-medium">
                  +${(config.fixedRiskBalance * config.riskPerTrade / 100 * 
                    (5 * (config.dynamicSLTP.minTP + config.dynamicSLTP.maxTP) / 2 / 100 - 
                     5 * (config.dynamicSLTP.minSL + config.dynamicSLTP.maxSL) / 2 / 100) * 10).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Худший сценарий (30% winrate):</span>
                <span className="text-red-400 font-medium">
                  -${Math.abs(config.fixedRiskBalance * config.riskPerTrade / 100 * 
                    (3 * (config.dynamicSLTP.minTP + config.dynamicSLTP.maxTP) / 2 / 100 - 
                     7 * (config.dynamicSLTP.minSL + config.dynamicSLTP.maxSL) / 2 / 100) * 10).toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Информационное сообщение */}
      <div className="bg-blue-600/10 border border-blue-600/30 rounded-xl p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="text-blue-400 font-medium mb-1">Важная информация</h4>
            <p className="text-blue-300 text-sm">
              Настройки управления рисками критически важны для сохранения капитала. 
              Рекомендуется начинать с консервативных настроек и постепенно корректировать их 
              на основе результатов торговли. Всегда тестируйте новые настройки на демо-счете.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskManagementSettings;