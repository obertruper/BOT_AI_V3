"""
ML Visualization API Endpoints

REST API для визуализации ML данных:
- Графики предсказаний модели
- Анализ входных признаков
- Метрики производительности модели
- Интерактивные дашборды
"""

from datetime import datetime, timedelta
from typing import Any, Optional, List
from pathlib import Path
import json
import base64
import io

import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.offline import plot
import plotly.io as pio
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from core.logging.logger_factory import get_global_logger_factory
from database.connections.postgres import AsyncPGPool

logger_factory = get_global_logger_factory()
logger = logger_factory.get_logger("ml_visualization_api")

router = APIRouter(prefix="/api/ml-viz", tags=["ml-visualization"])

# =================== MODELS ===================

class PredictionVisualization(BaseModel):
    """Визуализация предсказания модели"""
    symbol: str
    prediction_data: dict
    chart_type: str  # "interactive", "static", "heatmap"
    timeframe: str = "1h"
    include_features: bool = False

class MLMetrics(BaseModel):
    """Метрики ML модели"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    last_updated: datetime
    predictions_count: int

class FeatureImportance(BaseModel):
    """Важность признаков"""
    feature_name: str
    importance_score: float
    category: str  # "technical", "market", "volatility", etc.

class MLVisualizationResponse(BaseModel):
    """Ответ с данными визуализации"""
    chart_url: Optional[str] = None
    chart_data: Optional[dict] = None
    image_base64: Optional[str] = None
    metadata: dict

# =================== CONSTANTS ===================

CHARTS_DIR = Path("data/charts")
CHARTS_DIR.mkdir(exist_ok=True)

# =================== ENDPOINTS ===================

@router.get("/predictions/{symbol}", response_model=MLVisualizationResponse)
async def get_prediction_visualization(
    symbol: str,
    chart_type: str = Query("interactive", description="Тип графика: interactive, static, heatmap"),
    timeframe: str = Query("1h", description="Таймфрейм для анализа"),
    include_features: bool = Query(False, description="Включить анализ признаков")
):
    """Получить визуализацию предсказаний ML модели для символа"""
    try:
        logger.info(f"Запрос визуализации предсказаний: {symbol}, тип: {chart_type}")
        
        # Получаем ML менеджер
        ml_manager = get_ml_manager()
        if not ml_manager:
            raise HTTPException(status_code=503, detail="ML система недоступна")
        
        # Загружаем данные для символа
        market_data = await get_market_data(symbol, limit=100)
        if not market_data:
            raise HTTPException(status_code=404, detail=f"Данные для {symbol} не найдены")
        
        # Получаем предсказание
        prediction = await ml_manager.predict(market_data)
        
        # Создаем визуализацию в зависимости от типа
        if chart_type == "interactive":
            chart_data = create_interactive_chart(symbol, prediction, market_data)
            return MLVisualizationResponse(
                chart_data=chart_data,
                metadata={
                    "symbol": symbol,
                    "chart_type": chart_type,
                    "timestamp": datetime.now().isoformat(),
                    "prediction": {
                        "signal_type": prediction.get("signal_type"),
                        "confidence": prediction.get("confidence"),
                        "strength": prediction.get("signal_strength")
                    }
                }
            )
        
        elif chart_type == "static":
            image_b64 = create_static_chart(symbol, prediction, market_data)
            return MLVisualizationResponse(
                image_base64=image_b64,
                metadata={
                    "symbol": symbol,
                    "chart_type": chart_type,
                    "format": "png",
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        elif chart_type == "heatmap" and include_features:
            features_data = await get_features_data(symbol, ml_manager)
            if features_data:
                heatmap_data = create_features_heatmap_data(symbol, features_data)
                return MLVisualizationResponse(
                    chart_data=heatmap_data,
                    metadata={
                        "symbol": symbol,
                        "chart_type": "heatmap",
                        "features_count": len(features_data),
                        "timestamp": datetime.now().isoformat()
                    }
                )
        
        else:
            raise HTTPException(status_code=400, detail=f"Неподдерживаемый тип графика: {chart_type}")

    except Exception as e:
        logger.error(f"Ошибка создания визуализации для {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания визуализации: {str(e)}")


@router.get("/features/{symbol}", response_model=List[FeatureImportance])
async def get_feature_importance(
    symbol: str,
    limit: int = Query(50, description="Количество топ признаков")
):
    """Получить важность признаков для символа"""
    try:
        ml_manager = get_ml_manager()
        if not ml_manager:
            raise HTTPException(status_code=503, detail="ML система недоступна")
        
        # Получаем данные о важности признаков
        features_data = await get_features_importance(symbol, ml_manager, limit)
        
        return features_data

    except Exception as e:
        logger.error(f"Ошибка получения важности признаков для {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.get("/metrics", response_model=MLMetrics)
async def get_ml_metrics():
    """Получить общие метрики ML модели"""
    try:
        ml_manager = get_ml_manager()
        if not ml_manager:
            raise HTTPException(status_code=503, detail="ML система недоступна")
        
        # Получаем метрики модели
        metrics = await get_model_metrics(ml_manager)
        
        return MLMetrics(
            model_name=metrics.get("model_name", "UnifiedPatchTST"),
            accuracy=metrics.get("accuracy", 0.0),
            precision=metrics.get("precision", 0.0),
            recall=metrics.get("recall", 0.0),
            f1_score=metrics.get("f1_score", 0.0),
            last_updated=metrics.get("last_updated", datetime.now()),
            predictions_count=metrics.get("predictions_count", 0)
        )

    except Exception as e:
        logger.error(f"Ошибка получения метрик ML: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.post("/generate-report")
async def generate_ml_report(
    background_tasks: BackgroundTasks,
    symbols: List[str] = Query(["BTCUSDT", "ETHUSDT"], description="Символы для анализа"),
    include_features: bool = Query(True, description="Включить анализ признаков")
):
    """Сгенерировать полный отчет по ML системе"""
    try:
        report_id = f"ml_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Запускаем генерацию отчета в фоновом режиме
        background_tasks.add_task(
            generate_comprehensive_report,
            report_id,
            symbols,
            include_features
        )
        
        return {
            "report_id": report_id,
            "status": "generating",
            "message": f"Отчет генерируется для {len(symbols)} символов",
            "symbols": symbols
        }

    except Exception as e:
        logger.error(f"Ошибка запуска генерации отчета: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.get("/report/{report_id}")
async def get_report_status(report_id: str):
    """Получить статус генерации отчета"""
    try:
        # Проверяем статус отчета
        report_file = CHARTS_DIR / f"{report_id}.json"
        
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            return {
                "report_id": report_id,
                "status": "completed",
                "data": report_data,
                "download_url": f"/api/ml-viz/download/{report_id}"
            }
        else:
            return {
                "report_id": report_id,
                "status": "generating",
                "message": "Отчет еще генерируется"
            }

    except Exception as e:
        logger.error(f"Ошибка получения статуса отчета {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.get("/download/{report_id}")
async def download_report(report_id: str):
    """Скачать сгенерированный отчет"""
    try:
        report_file = CHARTS_DIR / f"{report_id}.json"
        
        if not report_file.exists():
            raise HTTPException(status_code=404, detail="Отчет не найден")
        
        return FileResponse(
            path=str(report_file),
            media_type='application/json',
            filename=f"{report_id}.json"
        )

    except Exception as e:
        logger.error(f"Ошибка скачивания отчета {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


# =================== HELPER FUNCTIONS ===================

def create_interactive_chart(symbol: str, prediction: dict, market_data: pd.DataFrame) -> dict:
    """Создает данные для интерактивного графика Plotly"""
    
    # Подготавливаем данные для фронтенда
    recent_data = market_data.tail(50)
    
    chart_data = {
        "symbol": symbol,
        "ohlc_data": {
            "x": recent_data.index.astype(str).tolist(),
            "open": recent_data['open'].tolist(),
            "high": recent_data['high'].tolist(), 
            "low": recent_data['low'].tolist(),
            "close": recent_data['close'].tolist(),
            "volume": recent_data['volume'].tolist()
        },
        "prediction": prediction,
        "current_price": float(market_data['close'].iloc[-1]),
        "timestamp": datetime.now().isoformat()
    }
    
    # Добавляем данные предсказаний по таймфреймам
    if "predictions" in prediction:
        pred_details = prediction["predictions"]
        
        if "direction_probabilities" in pred_details:
            chart_data["probabilities"] = {
                "timeframes": ["15m", "1h", "4h", "12h"],
                "data": pred_details["direction_probabilities"]
            }
        
        if "returns_15m" in pred_details:
            chart_data["returns"] = {
                "15m": pred_details.get("returns_15m", 0),
                "1h": pred_details.get("returns_1h", 0),
                "4h": pred_details.get("returns_4h", 0),
                "12h": pred_details.get("returns_12h", 0)
            }
    
    return chart_data


def create_static_chart(symbol: str, prediction: dict, market_data: pd.DataFrame) -> str:
    """Создает статический график и возвращает base64"""
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.patch.set_facecolor('black')
    
    recent_data = market_data.tail(100)
    
    # График 1: Цена
    axes[0,0].plot(recent_data.index, recent_data['close'], color='white', linewidth=1.5)
    axes[0,0].set_title(f'{symbol} - Price', color='white')
    axes[0,0].grid(True, alpha=0.3)
    
    # График 2: Объем
    axes[0,1].bar(recent_data.index, recent_data['volume'], color='cyan', alpha=0.7)
    axes[0,1].set_title(f'{symbol} - Volume', color='white')
    axes[0,1].grid(True, alpha=0.3)
    
    # График 3: Предсказания (если есть)
    if "predictions" in prediction:
        pred_details = prediction["predictions"]
        returns_data = [
            pred_details.get("returns_15m", 0),
            pred_details.get("returns_1h", 0), 
            pred_details.get("returns_4h", 0),
            pred_details.get("returns_12h", 0)
        ]
        timeframes = ["15m", "1h", "4h", "12h"]
        colors = ['red' if r < 0 else 'green' for r in returns_data]
        
        axes[1,0].bar(timeframes, returns_data, color=colors)
        axes[1,0].set_title(f'{symbol} - Predicted Returns', color='white')
        axes[1,0].grid(True, alpha=0.3)
    
    # График 4: Сигнал
    signal_colors = {"LONG": "green", "SHORT": "red", "NEUTRAL": "yellow"}
    signal_type = prediction.get("signal_type", "NEUTRAL")
    confidence = prediction.get("confidence", 0)
    
    axes[1,1].bar([signal_type], [confidence], 
                  color=signal_colors.get(signal_type, 'gray'))
    axes[1,1].set_title(f'{symbol} - Signal Confidence', color='white')
    axes[1,1].set_ylim(0, 1)
    axes[1,1].grid(True, alpha=0.3)
    
    # Настройка стиля
    for ax in axes.flat:
        ax.set_facecolor('black')
        ax.tick_params(colors='white')
        for spine in ax.spines.values():
            spine.set_color('white')
    
    plt.tight_layout()
    
    # Конвертируем в base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight',
                facecolor='black', edgecolor='black')
    plt.close()
    
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    buffer.close()
    
    return image_base64


def create_features_heatmap_data(symbol: str, features_data: list) -> dict:
    """Создает данные для тепловой карты признаков"""
    
    # Преобразуем в формат для фронтенда
    if isinstance(features_data[0], dict):
        feature_names = [f["name"] for f in features_data]
        feature_values = [f["value"] for f in features_data]
    else:
        feature_names = [f"Feature_{i}" for i in range(len(features_data))]
        feature_values = features_data
    
    return {
        "symbol": symbol,
        "features": {
            "names": feature_names[:50],  # Топ-50 для визуализации
            "values": feature_values[:50],
            "count": len(features_data)
        },
        "timestamp": datetime.now().isoformat()
    }


async def get_market_data(symbol: str, limit: int = 100) -> pd.DataFrame:
    """Загружает рыночные данные для символа"""
    query = f"""
    SELECT * FROM raw_market_data
    WHERE symbol = '{symbol}'
    ORDER BY datetime DESC
    LIMIT {limit}
    """
    
    raw_data = await AsyncPGPool.fetch(query)
    
    if not raw_data:
        return None
    
    df_data = [dict(row) for row in raw_data]
    df = pd.DataFrame(df_data)
    
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = df[col].astype(float)
    
    # Исправление проблемы с datetime
    if 'datetime' in df.columns:
        df = df.sort_values("datetime")
        df = df.set_index('datetime', drop=True)
    
    # Убеждаемся, что нет дублирующихся колонок
    df = df.loc[:, ~df.columns.duplicated()]
    
    return df


async def get_features_data(symbol: str, ml_manager) -> list:
    """Получает данные о признаках модели"""
    try:
        if hasattr(ml_manager, 'get_latest_features'):
            return await ml_manager.get_latest_features(symbol)
        else:
            # Заглушка с фиктивными данными для демонстрации
            return [{"name": f"feature_{i}", "value": 0.5} for i in range(240)]
    except Exception as e:
        logger.warning(f"Не удалось получить признаки для {symbol}: {e}")
        return []


async def get_features_importance(symbol: str, ml_manager, limit: int) -> List[FeatureImportance]:
    """Получает важность признаков"""
    # Заглушка - в реальном проекте должно получать данные из модели
    features = []
    categories = ["technical", "market", "volatility", "momentum", "trend"]
    
    for i in range(limit):
        features.append(FeatureImportance(
            feature_name=f"feature_{i}",
            importance_score=0.8 - (i * 0.01),
            category=categories[i % len(categories)]
        ))
    
    return features


async def get_model_metrics(ml_manager) -> dict:
    """Получает метрики модели"""
    # Заглушка - в реальном проекте должно получать реальные метрики
    return {
        "model_name": "UnifiedPatchTST",
        "accuracy": 0.75,
        "precision": 0.72,
        "recall": 0.78,
        "f1_score": 0.75,
        "last_updated": datetime.now(),
        "predictions_count": 1547
    }


async def generate_comprehensive_report(report_id: str, symbols: List[str], include_features: bool):
    """Генерирует комплексный отчет по ML системе"""
    try:
        report_data = {
            "report_id": report_id,
            "generated_at": datetime.now().isoformat(),
            "symbols": symbols,
            "include_features": include_features,
            "charts": [],
            "summary": {}
        }
        
        # Генерируем данные для каждого символа
        for symbol in symbols:
            try:
                market_data = await get_market_data(symbol)
                if market_data is not None:
                    # Здесь должна быть логика генерации ML предсказаний
                    symbol_data = {
                        "symbol": symbol,
                        "status": "completed",
                        "charts_generated": 3,
                        "prediction_confidence": 0.75
                    }
                    report_data["charts"].append(symbol_data)
                else:
                    report_data["charts"].append({
                        "symbol": symbol,
                        "status": "no_data",
                        "error": "Нет данных"
                    })
            except Exception as e:
                report_data["charts"].append({
                    "symbol": symbol,
                    "status": "error",
                    "error": str(e)
                })
        
        # Сохраняем отчет
        report_file = CHARTS_DIR / f"{report_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Отчет {report_id} сгенерирован успешно")
        
    except Exception as e:
        logger.error(f"Ошибка генерации отчета {report_id}: {e}")


# =================== DEPENDENCY INJECTION ===================

def get_ml_manager():
    """Получить ML менеджер из глобального контекста"""
    try:
        from web.integration.dependencies import get_ml_manager_dependency
        return get_ml_manager_dependency()
    except ImportError:
        logger.warning("ML менеджер недоступен через dependency injection")
        return None