"""Dedicated worker entry point: python -m nova.worker.

Set EMBEDDED_SCHEDULER=false on web instances when independently deployed.
No deployment is performed by this module or by the remediation branch.
"""
import asyncio

from .scheduler import loop


if __name__ == '__main__':
    asyncio.run(loop())
