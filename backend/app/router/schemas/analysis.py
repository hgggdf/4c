"""分析路由正式 schema。"""

from pydantic import BaseModel


class DimensionOut(BaseModel):
	"""单个诊断维度的响应结构。"""

	name: str
	score: float
	comment: str
	metrics: dict


class DiagnoseOut(BaseModel):
	"""企业运营诊断接口的标准响应结构。"""

	stock_code: str
	stock_name: str
	year: int
	total_score: float
	level: str
	dimensions: list[DimensionOut]
	strengths: list[str]
	weaknesses: list[str]
	suggestion: str


__all__ = ["DiagnoseOut", "DimensionOut"]