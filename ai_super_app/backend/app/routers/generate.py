"""
Generate Router - Image & Video Generation Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from app.models.image_generator import image_generator
from app.models.video_generator import video_generator
from app.database.models import get_db, Generation, User
from app.auth import get_current_user
from sqlalchemy.orm import Session

router = APIRouter(prefix="/generate", tags=["generate"])


class ImageRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    style: Optional[str] = None
    provider: Optional[str] = None


class VideoRequest(BaseModel):
    prompt: str
    duration: int = 4
    resolution: str = "720p"
    style: Optional[str] = None
    provider: Optional[str] = None


class GenerationResponse(BaseModel):
    success: bool
    type: str
    provider: str
    result_url: Optional[str] = None
    result_data: Optional[str] = None
    generation_time: float


@router.post("/image", response_model=GenerationResponse)
async def generate_image(request: ImageRequest, background_tasks: BackgroundTasks,
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    result = await image_generator.generate(
        prompt=request.prompt,
        size=request.size,
        style=request.style,
        provider=request.provider
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

    generation = Generation(
        user_id=current_user.id,
        type="image",
        prompt=request.prompt,
        provider=result["provider"],
        result_data=result.get("image_data"),
        parameters={"size": request.size, "style": request.style},
        status="completed",
        generation_time=result.get("generation_time", 0)
    )
    db.add(generation)
    db.commit()

    return GenerationResponse(
        success=True,
        type="image",
        provider=result["provider"],
        result_url=None,
        result_data=result.get("image_data"),
        generation_time=result.get("generation_time", 0)
    )


@router.post("/video", response_model=GenerationResponse)
async def generate_video(request: VideoRequest, background_tasks: BackgroundTasks,
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    result = await video_generator.generate(
        prompt=request.prompt,
        duration=request.duration,
        resolution=request.resolution,
        style=request.style,
        provider=request.provider
    )

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

    generation = Generation(
        user_id=current_user.id,
        type="video",
        prompt=request.prompt,
        provider=result["provider"],
        result_url=result.get("video_url"),
        parameters={"duration": request.duration, "resolution": request.resolution, "style": request.style},
        status="completed",
        generation_time=result.get("generation_time", 0)
    )
    db.add(generation)
    db.commit()

    return GenerationResponse(
        success=True,
        type="video",
        provider=result["provider"],
        result_url=result.get("video_url"),
        result_data=None,
        generation_time=result.get("generation_time", 0)
    )


@router.get("/history")
async def get_generation_history(current_user: User = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    generations = db.query(Generation).filter(Generation.user_id == current_user.id).order_by(Generation.created_at.desc()).all()
    return {
        "generations": [
            {
                "id": gen.id,
                "type": gen.type,
                "prompt": gen.prompt,
                "provider": gen.provider,
                "status": gen.status,
                "created_at": str(gen.created_at)
            }
            for gen in generations
        ]
    }
