"""
Web Access Router - Website scraping and access endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.models.web_scraper import web_scraper
from app.models.vpn_manager import vpn_manager
from app.database.models import get_db, WebAccess, User
from app.auth import get_current_user
from sqlalchemy.orm import Session

router = APIRouter(prefix="/web", tags=["web_access"])


class ScrapeRequest(BaseModel):
    url: str
    type: str = "article"
    extract_images: bool = True
    extract_links: bool = False


class VPNRequest(BaseModel):
    url: str
    prefer_country: Optional[str] = None
    use_js: bool = True


@router.post("/scrape")
async def scrape_website(request: ScrapeRequest,
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if request.type == "article":
        result = await web_scraper.scrape_article(request.url)
    elif request.type == "product":
        result = await web_scraper.scrape_product(request.url)
    elif request.type == "markdown":
        result = await web_scraper.convert_to_markdown(request.url)
    else:
        result = await web_scraper.scrape_article(request.url)

    if not result.get("success", True):
        raise HTTPException(status_code=500, detail=result.get("error", "Scraping failed"))

    web_access = WebAccess(
        user_id=current_user.id,
        url=request.url,
        proxy_used=result.get("proxy_used"),
        latency_ms=result.get("latency_ms"),
        content_type=request.type,
        extracted_data=result
    )
    db.add(web_access)
    db.commit()

    return result


@router.post("/fetch")
async def fetch_url(request: VPNRequest,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    result = await vpn_manager.fetch_url(
        url=request.url,
        prefer_country=request.prefer_country,
        use_js=request.use_js
    )

    if not result.get("success", True):
        raise HTTPException(status_code=500, detail=result.get("error", "Fetch failed"))

    return result


@router.get("/history")
async def get_web_access_history(current_user: User = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    accesses = db.query(WebAccess).filter(WebAccess.user_id == current_user.id).order_by(WebAccess.created_at.desc()).all()
    return {
        "accesses": [
            {
                "id": access.id,
                "url": access.url,
                "proxy_used": access.proxy_used,
                "content_type": access.content_type,
                "created_at": str(access.created_at)
            }
            for access in accesses
        ]
    }
