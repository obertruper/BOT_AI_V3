import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const Traders: React.FC = () => {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Трейдеры</h1>
          <p className="text-muted-foreground">Управление торговыми ботами</p>
        </div>
        <Button>Создать трейдера</Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Список трейдеров</CardTitle>
          <CardDescription>
            Здесь будет отображаться список всех торговых ботов
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

export default Traders