from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    text: str
    chat_id: Optional[str] = None
    
class SourceCitation(BaseModel):
    file_name: str
    date_added: Optional[str] = None
    
class QueryResponse(BaseModel):
    answer: str
    mode: str # "Recall" or "Elaboration"
    sources: List[SourceCitation] = []
    
class UploadResponse(BaseModel):
    message: str
    chunks_indexed: int

class CreateChatRequest(BaseModel):
    id: str
    title: str