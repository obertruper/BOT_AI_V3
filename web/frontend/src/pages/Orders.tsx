import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const Orders: React.FC = () => {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Ордера</h1>
        <p className="text-muted-foreground">История и управление ордерами</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>История ордеров</CardTitle>
          <CardDescription>
            Здесь будет отображаться история всех ордеров
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            Страница в разработке...
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Orders;
