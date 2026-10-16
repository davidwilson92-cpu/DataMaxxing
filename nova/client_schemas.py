"""Shared request schemas for HTTP and durable workers."""
from pydantic import BaseModel,Field,field_validator


class GenerateRequest(BaseModel):
    revision: int | None = Field(default=None, ge=0)
    media_asset_ids:list[int]=Field(default_factory=list,max_length=10)
    brief:str=Field(min_length=1,max_length=12000); instruction:str=Field(default="",max_length=5000); platforms:list[str]; thread_length:int=1; link_url:str=""; draft_id:int|None=None
    @field_validator("thread_length")
    @classmethod
    def valid_thread(cls,v:int): return v if v in {1,3,5} else 1
