-- Миграция для исправления регистра enum OrderStatus (версия 2)
-- Учитывает зависимые views

BEGIN;

-- Сохраняем определение view
CREATE TEMP TABLE view_definitions AS
SELECT viewname, definition 
FROM pg_views 
WHERE schemaname = 'public' 
AND definition LIKE '%orders%';

-- Удаляем зависимые views
DROP VIEW IF EXISTS v_active_positions CASCADE;
DROP VIEW IF EXISTS v_order_stats CASCADE;
DROP VIEW IF EXISTS v_trading_summary CASCADE;

-- Изменяем тип колонки на text временно
ALTER TABLE orders ALTER COLUMN status TYPE text;

-- Обновляем значения на lowercase
UPDATE orders SET status = LOWER(status)
WHERE status IN ('PENDING', 'OPEN', 'FILLED', 'PARTIALLY_FILLED', 'CANCELLED', 'REJECTED', 'EXPIRED');

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
ALTER TABLE orders 
ALTER COLUMN status TYPE orderstatus 
USING status::orderstatus;

-- Создаём view обратно если он был
CREATE OR REPLACE VIEW v_active_positions AS
SELECT * FROM orders 
WHERE status IN ('open', 'partially_filled');

COMMIT;

-- Проверка результата
SELECT 'Enum values after migration:' as info;
SELECT enumlabel FROM pg_enum 
WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'orderstatus') 
ORDER BY enumlabel;

-- Проверка данных в таблице orders
SELECT 'Order statuses in table:' as info;
SELECT DISTINCT status FROM orders LIMIT 10;