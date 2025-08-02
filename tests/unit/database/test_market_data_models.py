"""
Unit тесты для моделей базы данных market_data
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from database.connections import Base
from database.models.market_data import (
    MarketDataSnapshot,
    MarketType,
    ProcessedMarketData,
    RawMarketData,
    TechnicalIndicators,
)


@pytest.mark.unit
@pytest.mark.database
class TestMarketDataModels:
    """Тесты для моделей market_data"""

    @pytest.fixture
    def test_engine(self):
        """Создание тестовой базы данных в памяти"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def test_session(self, test_engine):
        """Создание тестовой сессии"""
        SessionLocal = sessionmaker(bind=test_engine)
        session = SessionLocal()
        yield session
        session.close()

    def test_raw_market_data_creation(self, test_session):
        """Тест создания записи RawMarketData"""
        raw_data = RawMarketData(
            symbol="BTCUSDT",
            timestamp=1704067200000,  # 2024-01-01 00:00:00
            datetime=datetime(2024, 1, 1),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000.50"),
            turnover=Decimal("50250000.00"),
            interval_minutes=15,
            market_type=MarketType.SPOT,
            exchange="binance",
        )

        test_session.add(raw_data)
        test_session.commit()

        # Проверяем сохранение
        saved = test_session.query(RawMarketData).first()
        assert saved is not None
        assert saved.symbol == "BTCUSDT"
        assert saved.close == Decimal("50500.00")
        assert saved.market_type == MarketType.SPOT
        assert saved.interval_minutes == 15

    def test_raw_market_data_unique_constraint(self, test_session):
        """Тест уникального ограничения для RawMarketData"""
        # Создаем первую запись
        data1 = RawMarketData(
            symbol="BTCUSDT",
            timestamp=1704067200000,
            datetime=datetime(2024, 1, 1),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000.00"),
            interval_minutes=15,
            exchange="binance",
        )
        test_session.add(data1)
        test_session.commit()

        # Пытаемся создать дубликат
        data2 = RawMarketData(
            symbol="BTCUSDT",
            timestamp=1704067200000,
            datetime=datetime(2024, 1, 1),
            open=Decimal("50100.00"),
            high=Decimal("51100.00"),
            low=Decimal("49100.00"),
            close=Decimal("50600.00"),
            volume=Decimal("1100.00"),
            interval_minutes=15,
            exchange="binance",
        )
        test_session.add(data2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_processed_market_data_creation(self, test_session):
        """Тест создания записи ProcessedMarketData"""
        # Сначала создаем raw_data
        raw_data = RawMarketData(
            symbol="BTCUSDT",
            timestamp=1704067200000,
            datetime=datetime(2024, 1, 1),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000.00"),
            interval_minutes=15,
        )
        test_session.add(raw_data)
        test_session.commit()

        # Создаем processed_data
        processed_data = ProcessedMarketData(
            raw_data_id=raw_data.id,
            symbol="BTCUSDT",
            timestamp=1704067200000,
            datetime=datetime(2024, 1, 1),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000.00"),
            technical_indicators={
                "rsi": 65.5,
                "macd": {"line": 150.0, "signal": 140.0, "histogram": 10.0},
                "bb": {"upper": 52000.0, "middle": 50000.0, "lower": 48000.0},
            },
            ml_features={
                "features": [0.1, 0.2, 0.3] * 80,
                "version": "1.0.0",
            },  # 240 features
            direction_15m=0,  # LONG
            direction_1h=0,
            direction_4h=1,  # SHORT
            direction_12h=2,  # FLAT
            future_return_15m=0.002,
            future_return_1h=0.005,
            processing_version="1.0.0",
        )

        test_session.add(processed_data)
        test_session.commit()

        # Проверяем сохранение и JSONB поля
        saved = test_session.query(ProcessedMarketData).first()
        assert saved is not None
        assert saved.technical_indicators["rsi"] == 65.5
        assert saved.ml_features["version"] == "1.0.0"
        assert len(saved.ml_features["features"]) == 240
        assert saved.direction_15m == 0
        assert saved.future_return_1h == 0.005

    def test_technical_indicators_creation(self, test_session):
        """Тест создания записи TechnicalIndicators"""
        indicators = TechnicalIndicators(
            symbol="BTCUSDT",
            timestamp=1704067200000,
            datetime=datetime(2024, 1, 1),
            interval_minutes=15,
            sma_10=50100.0,
            sma_20=50000.0,
            sma_50=49800.0,
            ema_10=50150.0,
            ema_20=50050.0,
            rsi_14=65.5,
            rsi_7=70.2,
            stoch_k=80.5,
            stoch_d=75.3,
            macd_line=150.0,
            macd_signal=140.0,
            macd_histogram=10.0,
            atr_14=250.0,
            bb_upper=52000.0,
            bb_middle=50000.0,
            bb_lower=48000.0,
            bb_width=4000.0,
            obv=1500000.0,
            vwap=50050.0,
            mfi=72.5,
            additional_indicators={
                "williams_r": -25.0,
                "cci": 120.0,
                "adx": 35.0,
                "di_plus": 30.0,
                "di_minus": 15.0,
            },
        )

        test_session.add(indicators)
        test_session.commit()

        # Проверяем сохранение
        saved = test_session.query(TechnicalIndicators).first()
        assert saved is not None
        assert saved.rsi_14 == 65.5
        assert saved.macd_histogram == 10.0
        assert saved.additional_indicators["williams_r"] == -25.0

    def test_market_data_snapshot_creation(self, test_session):
        """Тест создания записи MarketDataSnapshot"""
        snapshot = MarketDataSnapshot(
            symbol="BTCUSDT",
            last_price=Decimal("50500.00"),
            last_volume=Decimal("100.50"),
            last_update=datetime.utcnow(),
            price_24h_change=500.0,
            price_24h_change_pct=1.0,
            volume_24h=Decimal("50000.00"),
            high_24h=Decimal("51500.00"),
            low_24h=Decimal("49500.00"),
            ml_direction_prediction=0,  # LONG
            ml_confidence=0.85,
            ml_predicted_return=0.02,
            ml_prediction_time=datetime.utcnow(),
            is_active=True,
            data_quality_score=0.95,
        )

        test_session.add(snapshot)
        test_session.commit()

        # Проверяем сохранение
        saved = test_session.query(MarketDataSnapshot).first()
        assert saved is not None
        assert saved.last_price == Decimal("50500.00")
        assert saved.ml_confidence == 0.85
        assert saved.is_active is True

    def test_market_data_snapshot_unique_symbol(self, test_session):
        """Тест уникальности символа в MarketDataSnapshot"""
        # Создаем первый snapshot
        snapshot1 = MarketDataSnapshot(symbol="BTCUSDT", last_price=Decimal("50000.00"))
        test_session.add(snapshot1)
        test_session.commit()

        # Пытаемся создать второй с тем же символом
        snapshot2 = MarketDataSnapshot(symbol="BTCUSDT", last_price=Decimal("51000.00"))
        test_session.add(snapshot2)

        with pytest.raises(IntegrityError):
            test_session.commit()

    def test_raw_market_data_relationships(self, test_session):
        """Тест связей RawMarketData с ProcessedMarketData"""
        # Создаем raw_data
        raw_data = RawMarketData(
            symbol="BTCUSDT",
            timestamp=1704067200000,
            datetime=datetime(2024, 1, 1),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000.00"),
            interval_minutes=15,
        )
        test_session.add(raw_data)
        test_session.commit()

        # Создаем несколько processed_data
        for i in range(3):
            processed = ProcessedMarketData(
                raw_data_id=raw_data.id,
                symbol="BTCUSDT",
                timestamp=1704067200000 + i * 1000,
                datetime=datetime(2024, 1, 1),
                open=Decimal("50000.00"),
                high=Decimal("51000.00"),
                low=Decimal("49000.00"),
                close=Decimal("50500.00"),
                volume=Decimal("1000.00"),
                technical_indicators={},
                processing_version=f"1.0.{i}",
            )
            test_session.add(processed)

        test_session.commit()

        # Проверяем связи
        raw = test_session.query(RawMarketData).first()
        assert len(raw.processed_data) == 3

        # Проверяем обратную связь
        processed = test_session.query(ProcessedMarketData).first()
        assert processed.raw_data.symbol == "BTCUSDT"

    def test_market_type_enum(self, test_session):
        """Тест enum MarketType"""
        # Создаем записи с разными типами рынка
        for market_type in [MarketType.SPOT, MarketType.FUTURES, MarketType.PERP]:
            data = RawMarketData(
                symbol=f"{market_type.value}_BTCUSDT",
                timestamp=1704067200000,
                datetime=datetime(2024, 1, 1),
                open=Decimal("50000.00"),
                high=Decimal("51000.00"),
                low=Decimal("49000.00"),
                close=Decimal("50500.00"),
                volume=Decimal("1000.00"),
                interval_minutes=15,
                market_type=market_type,
            )
            test_session.add(data)

        test_session.commit()

        # Проверяем сохранение
        spot = (
            test_session.query(RawMarketData).filter_by(symbol="SPOT_BTCUSDT").first()
        )
        assert spot.market_type == MarketType.SPOT

        futures = (
            test_session.query(RawMarketData)
            .filter_by(symbol="FUTURES_BTCUSDT")
            .first()
        )
        assert futures.market_type == MarketType.FUTURES

    def test_jsonb_field_updates(self, test_session):
        """Тест обновления JSONB полей"""
        # Создаем запись
        processed = ProcessedMarketData(
            raw_data_id=1,
            symbol="BTCUSDT",
            timestamp=1704067200000,
            datetime=datetime(2024, 1, 1),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000.00"),
            technical_indicators={"rsi": 50.0},
        )
        test_session.add(processed)
        test_session.commit()

        # Обновляем JSONB поле
        saved = test_session.query(ProcessedMarketData).first()
        saved.technical_indicators["macd"] = {"line": 100.0, "signal": 90.0}
        saved.technical_indicators["rsi"] = 65.0
        test_session.commit()

        # Проверяем обновление
        updated = test_session.query(ProcessedMarketData).first()
        assert updated.technical_indicators["rsi"] == 65.0
        assert updated.technical_indicators["macd"]["line"] == 100.0

    def test_query_by_timestamp_range(self, test_session):
        """Тест запросов по диапазону времени"""
        # Создаем данные за несколько дней
        base_time = datetime(2024, 1, 1)
        for i in range(10):
            data = RawMarketData(
                symbol="BTCUSDT",
                timestamp=int((base_time + timedelta(hours=i)).timestamp() * 1000),
                datetime=base_time + timedelta(hours=i),
                open=Decimal("50000.00"),
                high=Decimal("51000.00"),
                low=Decimal("49000.00"),
                close=Decimal("50500.00"),
                volume=Decimal("1000.00"),
                interval_minutes=60,
                exchange="binance",
            )
            test_session.add(data)

        test_session.commit()

        # Запрос по диапазону
        start_time = base_time + timedelta(hours=2)
        end_time = base_time + timedelta(hours=7)

        results = (
            test_session.query(RawMarketData)
            .filter(
                RawMarketData.datetime >= start_time, RawMarketData.datetime <= end_time
            )
            .all()
        )

        assert len(results) == 6  # hours 2-7 inclusive

    def test_bulk_insert_performance(self, test_session):
        """Тест производительности bulk insert"""
        # Создаем большое количество записей
        bulk_data = []
        base_time = datetime(2024, 1, 1)

        for i in range(1000):
            data = RawMarketData(
                symbol="BTCUSDT",
                timestamp=int((base_time + timedelta(minutes=i)).timestamp() * 1000),
                datetime=base_time + timedelta(minutes=i),
                open=Decimal("50000.00") + Decimal(str(i)),
                high=Decimal("51000.00") + Decimal(str(i)),
                low=Decimal("49000.00") + Decimal(str(i)),
                close=Decimal("50500.00") + Decimal(str(i)),
                volume=Decimal("1000.00"),
                interval_minutes=1,
                exchange="binance",
            )
            bulk_data.append(data)

        # Bulk insert
        test_session.bulk_save_objects(bulk_data)
        test_session.commit()

        # Проверяем количество
        count = test_session.query(RawMarketData).count()
        assert count == 1000

    def test_complex_queries(self, test_session):
        """Тест сложных запросов с JOIN и агрегацией"""
        # Создаем тестовые данные
        raw_data = RawMarketData(
            symbol="BTCUSDT",
            timestamp=1704067200000,
            datetime=datetime(2024, 1, 1),
            open=Decimal("50000.00"),
            high=Decimal("51000.00"),
            low=Decimal("49000.00"),
            close=Decimal("50500.00"),
            volume=Decimal("1000.00"),
            interval_minutes=15,
        )
        test_session.add(raw_data)
        test_session.commit()

        # Создаем обработанные данные с разными версиями
        for version in ["1.0.0", "1.1.0", "2.0.0"]:
            processed = ProcessedMarketData(
                raw_data_id=raw_data.id,
                symbol="BTCUSDT",
                timestamp=1704067200000,
                datetime=datetime(2024, 1, 1),
                open=Decimal("50000.00"),
                high=Decimal("51000.00"),
                low=Decimal("49000.00"),
                close=Decimal("50500.00"),
                volume=Decimal("1000.00"),
                technical_indicators={},
                processing_version=version,
                direction_1h=0,
                ml_confidence=0.7 + float(version[0]) * 0.05,
            )
            test_session.add(processed)

        test_session.commit()

        # Запрос с JOIN для получения последней версии обработки
        from sqlalchemy import and_, func

        subquery = (
            test_session.query(
                ProcessedMarketData.raw_data_id,
                func.max(ProcessedMarketData.processing_version).label("max_version"),
            )
            .group_by(ProcessedMarketData.raw_data_id)
            .subquery()
        )

        latest_processed = (
            test_session.query(ProcessedMarketData)
            .join(
                subquery,
                and_(
                    ProcessedMarketData.raw_data_id == subquery.c.raw_data_id,
                    ProcessedMarketData.processing_version == subquery.c.max_version,
                ),
            )
            .first()
        )

        assert latest_processed is not None
        assert latest_processed.processing_version == "2.0.0"
