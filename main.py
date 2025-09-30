from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from envi_translator.translator import ENVITranslator

app = FastAPI(title="ENVI Translator", version="1.0.0")

# Enable CORS for local dev and extensions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TranslateRequest(BaseModel):
    text: str = Field(..., description="Input text to translate")
    source: str = Field("auto", description="Source language code or 'auto'")
    target: str = Field("vi", description="Target language code")
    preserve_format: bool = Field(True, description="Preserve line breaks and spacing")
    max_chars: int = Field(4500, ge=100, le=5000, description="Max chars per chunk")
    retries: int = Field(3, ge=0, le=10, description="Retries per chunk")
    retry_backoff_sec: float = Field(1.0, ge=0.0, le=10.0, description="Backoff seconds")


class TranslateResponse(BaseModel):
    translated: str
    source: str
    target: str


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index() -> Dict[str, str]:
    return {
        "name": "ENVI Translator",
        "version": "1.0.0",
        "docs": "/docs",
        "translate": "POST /translate",
        "translate_batch": "POST /translate_batch",
        "languages": "GET /languages",
    }


@app.get("/languages")
async def languages(as_dict: bool = True):
    try:
        return ENVITranslator.get_supported_languages(as_dict=as_dict)
    except Exception as e:
        # Fallback minimal set so the extension UI can still work
        fallback = {
            "Afrikaans": "af",
            "Arabic": "ar",
            "Bulgarian": "bg",
            "Chinese (Simplified)": "zh-CN",
            "Chinese (Traditional)": "zh-TW",
            "Czech": "cs",
            "Dutch": "nl",
            "English": "en",
            "French": "fr",
            "German": "de",
            "Hindi": "hi",
            "Indonesian": "id",
            "Italian": "it",
            "Japanese": "ja",
            "Korean": "ko",
            "Polish": "pl",
            "Portuguese": "pt",
            "Russian": "ru",
            "Spanish": "es",
            "Thai": "th",
            "Turkish": "tr",
            "Ukrainian": "uk",
            "Vietnamese": "vi",
        }
        if as_dict:
            return fallback
        else:
            return list(fallback.keys())


@app.get("/translate", response_model=TranslateResponse)
async def translate_get(
    text: str = Query(..., description="Text to translate"),
    source: str = Query("auto"),
    target: str = Query("vi"),
    preserve_format: bool = Query(True),
    max_chars: int = Query(4500, ge=100, le=5000),
    retries: int = Query(3, ge=0, le=10),
    retry_backoff_sec: float = Query(1.0, ge=0.0, le=10.0),
) -> TranslateResponse:
    try:
        tr = ENVITranslator(source=source, target=target)
        out = tr.translate_text(
            text,
            preserve_format=preserve_format,
            max_chars=max_chars,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )
        return TranslateResponse(translated=out, source=source, target=target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BatchTranslateItem(BaseModel):
    text: str
    source: str = Field("auto")
    target: str = Field("vi")


class BatchTranslateRequest(BaseModel):
    items: List[BatchTranslateItem]
    preserve_format: bool = True
    max_chars: int = 4500
    retries: int = 3
    retry_backoff_sec: float = 1.0


class BatchTranslateResponse(BaseModel):
    translated: List[str]


@app.post("/translate_batch", response_model=BatchTranslateResponse)
async def translate_batch(req: BatchTranslateRequest) -> BatchTranslateResponse:
    try:
        outputs: List[str] = []
        for it in req.items:
            tr = ENVITranslator(source=it.source, target=it.target)
            out = tr.translate_text(
                it.text,
                preserve_format=req.preserve_format,
                max_chars=req.max_chars,
                retries=req.retries,
                retry_backoff_sec=req.retry_backoff_sec,
            )
            outputs.append(out)
        return BatchTranslateResponse(translated=outputs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest) -> TranslateResponse:
    try:
        tr = ENVITranslator(source=req.source, target=req.target)
        out = tr.translate_text(
            req.text,
            preserve_format=req.preserve_format,
            max_chars=req.max_chars,
            retries=req.retries,
            retry_backoff_sec=req.retry_backoff_sec,
        )
        return TranslateResponse(translated=out, source=req.source, target=req.target)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Run with: uvicorn main:app --reload --host 127.0.0.1 --port 8000

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
