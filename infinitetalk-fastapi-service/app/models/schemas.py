"""Pydantic schemas for request validation."""

from pydantic import BaseModel


class GenerateRequest(BaseModel):
	input_json: str
	save_file: str
