"""
VPN Router - VPN management endpoints
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List
from app.models.vpn_manager import vpn_manager
from app.database.models import get_db, VPNUsage, User
from app.auth import get_current_user
from sqlalchemy.orm import Session

router = APIRouter(prefix="/vpn", tags=["vpn"])


@router.get("/status")
async def get_vpn_status(current_user: User = Depends(get_current_user)):
    proxies = []
    for proxy in vpn_manager.proxies:
        proxies.append({
            "host": proxy.host,
            "port": proxy.port,
            "country": proxy.country,
            "latency_ms": proxy.latency_ms,
            "success_rate": proxy.success_rate,
            "is_active": proxy.is_active,
            "failure_count": proxy.failure_count
        })

    return {
        "vpn_enabled": True,
        "total_proxies": len(vpn_manager.proxies),
        "active_proxies": len([p for p in vpn_manager.proxies if p.is_active]),
        "failed_proxies": len(vpn_manager.failed_proxies),
        "total_requests": vpn_manager.request_count,
        "proxies": proxies
    }


@router.get("/usage")
async def get_vpn_usage(current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    usages = db.query(VPNUsage).filter(VPNUsage.user_id == current_user.id).order_by(VPNUsage.created_at.desc()).limit(50).all()
    return {
        "usage": [
            {
                "id": usage.id,
                "proxy_host": usage.proxy_host,
                "proxy_country": usage.proxy_country,
                "target_url": usage.target_url,
                "success": usage.success,
                "latency_ms": usage.latency_ms,
                "created_at": str(usage.created_at)
            }
            for usage in usages
        ]
    }


@router.post("/test")
async def test_proxy(url: str = "https://www.google.com",
                    current_user: User = Depends(get_current_user)):
    result = await vpn_manager.fetch_url(url)
    return result


@router.post("/rotate")
async def rotate_proxy(current_user: User = Depends(get_current_user)):
    proxy = vpn_manager.get_proxy()
    if proxy:
        return {
            "success": True,
            "proxy": {
                "host": proxy.host,
                "port": proxy.port,
                "country": proxy.country
            }
        }
    return {"success": False, "error": "No available proxies"}
