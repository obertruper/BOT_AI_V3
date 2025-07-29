import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const Analytics: React.FC = () => {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Аналитика</h1>
        <p className="text-muted-foreground">Статистика и аналитика торговли</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Торговая статистика</CardTitle>
          <CardDescription>
            Здесь будет отображаться подробная аналитика торговых результатов
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            Страница в разработке...
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default Analytics