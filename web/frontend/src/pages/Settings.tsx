import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import apiClient from '@/api/client';

const Settings: React.FC = () => {
  const [config, setConfig] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setError(null);
        // Берём безопасный полный конфиг для отображения
        const resp = await fetch('/api/system/config/raw');
        const data = await resp.json();
        if (data?.success && data?.data) {
          setConfig(data.data);
        }
      } catch (e: any) {
        setError(String(e));
      }
    };
    load();
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      // Пример: сохраняем только раздел system.web_interface и system.environment
      const updates: any = {};
      if (config?.system?.web_interface) {
        updates.web_interface = config.system.web_interface;
      }
      if (config?.system?.environment) {
        updates.environment = config.system.environment;
      }
      const resp = await fetch('/api/system/config/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates }),
      });
      const data = await resp.json();
      if (!data?.success) {
        throw new Error(data?.error || 'Не удалось сохранить настройки');
      }
    } catch (e: any) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Настройки</h1>
        <p className="text-muted-foreground">Конфигурация системы и интерфейса</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Системная конфигурация</CardTitle>
          <CardDescription>
            Просмотр и базовое редактирование раздела system (без секретов)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="text-red-500 text-sm mb-4">{error}</div>
          )}

          {!config ? (
            <div className="text-center py-8 text-muted-foreground">Загрузка...</div>
          ) : (
            <div className="space-y-4">
              <div>
                <div className="text-sm text-muted-foreground mb-1">Environment</div>
                <input
                  className="w-full rounded border bg-background p-2 text-sm"
                  value={config?.system?.environment || ''}
                  onChange={(e) =>
                    setConfig((prev: any) => ({
                      ...prev,
                      system: { ...(prev?.system || {}), environment: e.target.value },
                    }))
                  }
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Web host</div>
                  <input
                    className="w-full rounded border bg-background p-2 text-sm"
                    value={config?.system?.web_interface?.host || ''}
                    onChange={(e) =>
                      setConfig((prev: any) => ({
                        ...prev,
                        system: {
                          ...(prev?.system || {}),
                          web_interface: { ...(prev?.system?.web_interface || {}), host: e.target.value },
                        },
                      }))
                    }
                  />
                </div>
                <div>
                  <div className="text-sm text-muted-foreground mb-1">Web port</div>
                  <input
                    className="w-full rounded border bg-background p-2 text-sm"
                    type="number"
                    value={config?.system?.web_interface?.port || 8080}
                    onChange={(e) =>
                      setConfig((prev: any) => ({
                        ...prev,
                        system: {
                          ...(prev?.system || {}),
                          web_interface: { ...(prev?.system?.web_interface || {}), port: Number(e.target.value) },
                        },
                      }))
                    }
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? 'Сохранение...' : 'Сохранить'}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default Settings;
