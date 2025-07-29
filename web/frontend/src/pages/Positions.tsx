import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const Positions: React.FC = () => {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Позиции</h1>
        <p className="text-muted-foreground">Управление открытыми позициями</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Открытые позиции</CardTitle>
          <CardDescription>
            Здесь будет отображаться список всех открытых позиций
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

export default Positions;
