import sys
import os

# Add src to path
sys.path.append("./src")

# 自动加载环境变量
def load_env_file(env_file=None):
    """从 env.sh 文件加载环境变量"""
    if env_file is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        env_file = os.path.join(script_dir, "scripts", "env.sh")
    
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and 'export' in line:
                        line = line.replace('export ', '')
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key not in os.environ:
                                os.environ[key] = value
        except Exception as e:
            print(f"Warning: Failed to load environment variables from {env_file}: {e}")

# 在导入其他模块之前加载环境变量
load_env_file()

import asyncio
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from api_config import (
    API_TITLE, API_DESCRIPTION, API_VERSION, API_HOST, API_PORT,
    GENERATE_ENDPOINT, HEALTH_ENDPOINT,
    ALLOWED_ORIGINS, LOG_LEVEL, LOG_FORMAT, REQUEST_TIMEOUT,
    CONFIG_PATH, EXAMPLE_PATH, USE_INSPIRATION, BRAINSTORM_MODE
)

# Import SciPIP backend
from app_pages.button_interface import Backend

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Global variables for shared resources
backend: Optional[Backend] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global backend
    
    # Startup
    logger.info("Starting SciPIP API Service...")
    
    try:
        # Initialize backend
        backend = Backend()
        logger.info("✅ Backend initialized successfully")
        logger.info("🚀 SciPIP API Service started successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down SciPIP API Service...")


# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request model for idea generation."""
    background: str = Field(..., description="Background information for idea generation", min_length=1)
    stream: bool = Field(False, description="Whether to stream responses")


async def generate_streaming_response(background: str) -> AsyncGenerator[str, None]:
    """
    Generate streaming response for idea generation.
    
    Args:
        background: User's background information
        
    Yields:
        JSON strings for streaming response
    """
    newline = "\n\n"
    extract_msg = "Extracting entities from the user's input..."
    understand_msg = "Understanding the user's input..."
    try:
        logger.info(f"Processing background: {background[:100]}...")
        
        # Send initial acknowledgment
        yield f"data: {json.dumps({'type': 'query_received', 'data': {'background': background[:100] + '...' if len(background) > 100 else background}})}{newline}"
        
        # Step 1: Extract entities
        yield f"data: {json.dumps({'type': 'step_start', 'data': {'step': 'extract_entities', 'message': extract_msg}})}{newline}"
        
        try:
            entities_bg = backend.background2entities_callback(background)
            if entities_bg is None:
                entities_bg = []
            yield f"data: {json.dumps({'type': 'step_complete', 'data': {'step': 'extract_entities', 'entities': entities_bg, 'message': f'Successfully extracted {len(entities_bg)} entities'}})}{newline}"
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'step': 'extract_entities', 'message': f'Entity extraction failed: {str(e)}'}})}{newline}"
            return
        
        # Step 2: Expand background
        yield f"data: {json.dumps({'type': 'step_start', 'data': {'step': 'expand_background', 'message': understand_msg}})}{newline}"
        
        try:
            expanded_background = backend.background2expandedbackground_callback(background, entities_bg)
            if expanded_background is None:
                yield f"data: {json.dumps({'type': 'error', 'data': {'step': 'expand_background', 'message': 'Failed to expand background (API timeout or error)'}})}{newline}"
                return
            yield f"data: {json.dumps({'type': 'step_complete', 'data': {'step': 'expand_background', 'expanded_background': expanded_background, 'message': 'Background expanded successfully'}})}{newline}"
        except Exception as e:
            logger.error(f"Background expansion error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'step': 'expand_background', 'message': f'Background expansion failed: {str(e)}'}})}{newline}"
            return
        
        # Step 3: Brainstorming
        yield f"data: {json.dumps({'type': 'step_start', 'data': {'step': 'brainstorm', 'message': 'Brainstorming...'}})}{newline}"
        
        try:
            brainstorms = backend.background2brainstorm_callback(expanded_background)
            if brainstorms is None:
                yield f"data: {json.dumps({'type': 'error', 'data': {'step': 'brainstorm', 'message': 'Failed to generate brainstorm (API timeout or error)'}})}{newline}"
                return
            yield f"data: {json.dumps({'type': 'step_complete', 'data': {'step': 'brainstorm', 'brainstorms': brainstorms, 'message': 'Brainstorming completed successfully'}})}{newline}"
        except Exception as e:
            logger.error(f"Brainstorm error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'step': 'brainstorm', 'message': f'Brainstorming failed: {str(e)}'}})}{newline}"
            return
        
        # Step 4: Extract entities for literature retrieval
        yield f"data: {json.dumps({'type': 'step_start', 'data': {'step': 'extract_entities_literature', 'message': 'Extracting entities for literature retrieval...'}})}{newline}"
        
        try:
            entities_all = backend.brainstorm2entities_callback(brainstorms, entities_bg)
            if entities_all is None:
                entities_all = []
            yield f"data: {json.dumps({'type': 'step_complete', 'data': {'step': 'extract_entities_literature', 'entities': entities_all, 'message': f'Successfully extracted {len(entities_all)} entities for literature retrieval'}})}{newline}"
        except Exception as e:
            logger.error(f"Entity extraction for literature error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'step': 'extract_entities_literature', 'message': f'Entity extraction failed: {str(e)}'}})}{newline}"
            return
        
        # Step 5: Retrieve related works
        yield f"data: {json.dumps({'type': 'step_start', 'data': {'step': 'retrieve_literature', 'message': 'Retrieving related works...'}})}{newline}"
        
        try:
            related_works, related_works_intact = backend.entities2literature_callback(expanded_background, entities_all)
            yield f"data: {json.dumps({'type': 'step_complete', 'data': {'step': 'retrieve_literature', 'related_works': related_works, 'related_works_count': len(related_works_intact), 'message': f'Successfully retrieved {len(related_works_intact)} related papers'}})}{newline}"
        except Exception as e:
            logger.error(f"Literature retrieval error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'step': 'retrieve_literature', 'message': f'Literature retrieval failed: {str(e)}'}})}{newline}"
            return
        
        # Step 6: Generate ideas
        yield f"data: {json.dumps({'type': 'step_start', 'data': {'step': 'generate_ideas', 'message': 'Generating ideas... (This may take up to 5 minutes)'}})}{newline}"
        
        try:
            initial_ideas, final_ideas = backend.literature2initial_ideas_callback(background, brainstorms, related_works_intact)
            
            # Format ideas
            ideas_result = []
            for i in range(len(initial_ideas)):
                idea_data = {
                    "index": i + 1,
                    "concise_idea": initial_ideas[i] if i < len(initial_ideas) else None,
                    "idea_in_detail": final_ideas[i] if i < len(final_ideas) and final_ideas[i] is not None else None
                }
                ideas_result.append(idea_data)
            
            yield f"data: {json.dumps({'type': 'final_result', 'data': {'initial_ideas_count': len(initial_ideas), 'final_ideas_count': len(final_ideas), 'ideas': ideas_result, 'message': f'Successfully generated {len(initial_ideas)} ideas'}})}{newline}"
            
            logger.info(f"Idea generation completed: {len(initial_ideas)} initial ideas, {len(final_ideas)} final ideas")
            
        except Exception as e:
            logger.error(f"Idea generation error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'step': 'generate_ideas', 'message': f'Idea generation failed: {str(e)}'}})}{newline}"
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Unexpected error: {str(e)}'}})}{newline}"


def generate_non_streaming_response(background: str) -> Dict[str, Any]:
    """
    Generate non-streaming response for idea generation.
    
    Args:
        background: User's background information
        
    Returns:
        Dict containing all results
    """
    try:
        logger.info(f"Processing background: {background[:100]}...")
        
        # Step 1: Extract entities
        entities_bg = backend.background2entities_callback(background)
        if entities_bg is None:
            entities_bg = []
        
        # Step 2: Expand background
        expanded_background = backend.background2expandedbackground_callback(background, entities_bg)
        if expanded_background is None:
            raise HTTPException(status_code=500, detail="Failed to expand background")
        
        # Step 3: Brainstorming
        brainstorms = backend.background2brainstorm_callback(expanded_background)
        if brainstorms is None:
            raise HTTPException(status_code=500, detail="Failed to generate brainstorm")
        
        # Step 4: Extract entities for literature retrieval
        entities_all = backend.brainstorm2entities_callback(brainstorms, entities_bg)
        if entities_all is None:
            entities_all = []
        
        # Step 5: Retrieve related works
        related_works, related_works_intact = backend.entities2literature_callback(expanded_background, entities_all)
        
        # Step 6: Generate ideas
        initial_ideas, final_ideas = backend.literature2initial_ideas_callback(background, brainstorms, related_works_intact)
        
        # Format ideas
        ideas_result = []
        for i in range(len(initial_ideas)):
            idea_data = {
                "index": i + 1,
                "concise_idea": initial_ideas[i] if i < len(initial_ideas) else None,
                "idea_in_detail": final_ideas[i] if i < len(final_ideas) and final_ideas[i] is not None else None
            }
            ideas_result.append(idea_data)
        
        return {
            "status": "success",
            "entities_bg": entities_bg,
            "expanded_background": expanded_background,
            "brainstorms": brainstorms,
            "entities_all": entities_all,
            "related_works": related_works,
            "related_works_count": len(related_works_intact),
            "initial_ideas_count": len(initial_ideas),
            "final_ideas_count": len(final_ideas),
            "ideas": ideas_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get(HEALTH_ENDPOINT)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "SciPIP API",
        "version": API_VERSION,
        "backend_ready": backend is not None
    }


@app.post(GENERATE_ENDPOINT)
async def generate_ideas(request: GenerateRequest):
    """
    Generate scientific paper ideas.
    
    Args:
        request: GenerateRequest containing the background information
        
    Returns:
        StreamingResponse or JSON response with ideas
    """
    if not request.background.strip():
        raise HTTPException(status_code=400, detail="Empty background provided")
    
    if request.stream:
        return StreamingResponse(
            generate_streaming_response(request.background),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
    else:
        return generate_non_streaming_response(request.background)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "SciPIP API Service",
        "version": API_VERSION,
        "description": API_DESCRIPTION,
        "endpoints": {
            "generate": GENERATE_ENDPOINT,
            "health": HEALTH_ENDPOINT,
            "documentation": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {API_HOST}:{API_PORT}")
    uvicorn.run(
        "api_service:app",
        host=API_HOST,
        port=API_PORT,
        workers=8,
        reload=False,
        log_level=LOG_LEVEL.lower()
    )

