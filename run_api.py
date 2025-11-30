#!/usr/bin/env python3
"""
Run the PoE Price Checker API server.

Usage:
    python run_api.py
    python run_api.py --port 8080
    python run_api.py --host 0.0.0.0 --port 8000
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Run PoE Price Checker API server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="Log level (default: info)",
    )

    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)

    print(f"Starting PoE Price Checker API on http://{args.host}:{args.port}")
    print(f"API docs: http://{args.host}:{args.port}/docs")
    print(f"Health check: http://{args.host}:{args.port}/health")
    print()

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    main()
