#!/usr/bin/env python3
"""
Context Engine Service Entry Point
Port: 8015

Case-centric context retrieval service providing WHO/WHAT/WHERE/WHEN/WHY
dimensions for legal document drafting.
"""
import uvicorn
from src.api.main import app

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8015,
        reload=True,
        log_level="info"
    )
