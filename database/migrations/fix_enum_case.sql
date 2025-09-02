-- Миграция для исправления регистра enum OrderStatus
-- Приводим к lowercase для совместимости с кодом

BEGIN;

-- Сохраняем текущие данные
CREATE TEMP TABLE temp_orders AS 
SELECT * FROM orders;

-- Удаляем foreign key constraints если есть
ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_status_check;

-- Изменяем тип колонки на text временно
ALTER TABLE orders ALTER COLUMN status TYPE text;

-- Обновляем значения на lowercase
UPDATE orders SET status = LOWER(status);

-- Удаляем старый enum тип
DROP TYPE IF EXISTS orderstatus CASCADE;

-- Создаём новый enum тип с lowercase значениями
CREATE TYPE orderstatus AS ENUM (
    'pending',
    'open', 
    'filled',
    'partially_filled',
    'cancelled',
    'rejected',
    'expired'
);

-- Меняем колонку обратно на enum тип
ALTER TABLE orders ALTER COLUMN status TYPE orderstatus USING status::orderstatus;

-- Добавляем обратно constraint если нужно
ALTER TABLE orders ADD CONSTRAINT orders_status_check CHECK (status IS NOT NULL);

COMMIT;

-- Проверка результата
SELECT enumlabel FROM pg_enum 
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'orderstatus') 
ORDER BY enumlabel;