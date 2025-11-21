#!/usr/bin/env python3
"""
Minimal entry point - just start the main engine without health check for now
"""
import asyncio
import sys

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    from main_engine import ScraperOrchestrator
    orchestrator = ScraperOrchestrator()
    
    print("🚀 Starting Scraper Orchestrator...")
    print("✅ System ready - waiting for tasks")
    
    asyncio.run(orchestrator.run())
