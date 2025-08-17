#!/usr/bin/env python3
"""
Comprehensive fix and start script for API
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def start_simple_api():
    """Start a simple API server for testing"""
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    # Create minimal FastAPI app
    app = FastAPI(title="BOT_AI_V3 API", version="3.0.0")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "message": "API is running",
            "version": "3.0.0"
        }
    
    @app.get("/api/trading/status")
    async def trading_status():
        """Trading status endpoint"""
        return {
            "status": "operational",
            "trading_active": False,
            "message": "Trading system status"
        }
    
    @app.get("/api/trading/balances")
    async def get_balances():
        """Get balances endpoint"""
        # Try to import and use Bybit client
        try:
            from exchanges.bybit.client import BybitClient
            from exchanges.base.api_key_manager import APIKeyManager
            
            api_key_manager = APIKeyManager()
            bybit_keys = api_key_manager.get_exchange_keys("bybit")
            
            if bybit_keys and bybit_keys.get("api_key"):
                client = BybitClient(
                    api_key=bybit_keys["api_key"],
                    api_secret=bybit_keys["api_secret"],
                    testnet=False
                )
                
                await client.connect()
                balances = await client.get_balances()
                await client.disconnect()
                
                return {
                    "status": "success",
                    "balances": {
                        asset: {
                            "free": str(balance.free),
                            "locked": str(balance.locked),
                            "total": str(balance.total)
                        }
                        for asset, balance in balances.items()
                    }
                }
            else:
                return {
                    "status": "error",
                    "message": "Bybit API keys not configured"
                }
                
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "BOT_AI_V3 API",
            "version": "3.0.0",
            "endpoints": [
                "/health",
                "/api/trading/status",
                "/api/trading/balances",
                "/docs"
            ]
        }
    
    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8080,
        log_level="info",
        access_log=True
    )
    
    # Create and run server
    server = uvicorn.Server(config)
    
    logger.info("Starting simple API server on http://localhost:8080")
    logger.info("API documentation available at http://localhost:8080/docs")
    
    await server.serve()

if __name__ == "__main__":
    try:
        asyncio.run(start_simple_api())
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
    except Exception as e:
        logger.error(f"Failed to start API: {e}")
        sys.exit(1)