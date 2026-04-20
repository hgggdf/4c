"""医药公司注册表，维护观察池公司名单、别名和代码转换工具。"""

from __future__ import annotations

from copy import deepcopy


PHARMA_COMPANIES = [
    {"symbol": "600276", "name": "恒瑞医药", "exchange": "SH", "aliases": ["恒瑞医药", "恒瑞"]},
    {"symbol": "603259", "name": "药明康德", "exchange": "SH", "aliases": ["药明康德", "药明"]},
    {"symbol": "600436", "name": "片仔癀", "exchange": "SH", "aliases": ["片仔癀"]},
    {"symbol": "600085", "name": "同仁堂", "exchange": "SH", "aliases": ["同仁堂"]},
    {"symbol": "601607", "name": "上海医药", "exchange": "SH", "aliases": ["上海医药", "上药"]},
    {"symbol": "600332", "name": "白云山", "exchange": "SH", "aliases": ["白云山", "广药白云山"]},
    {"symbol": "600196", "name": "复星医药", "exchange": "SH", "aliases": ["复星医药", "复星"]},
    {"symbol": "300760", "name": "迈瑞医疗", "exchange": "SZ", "aliases": ["迈瑞医疗", "迈瑞"]},
    {"symbol": "300015", "name": "爱尔眼科", "exchange": "SZ", "aliases": ["爱尔眼科", "爱尔"]},
    {"symbol": "300347", "name": "泰格医药", "exchange": "SZ", "aliases": ["泰格医药", "泰格"]},
    {"symbol": "300759", "name": "康龙化成", "exchange": "SZ", "aliases": ["康龙化成", "康龙"]},
    {"symbol": "300896", "name": "爱美客", "exchange": "SZ", "aliases": ["爱美客"]},
    {"symbol": "000538", "name": "云南白药", "exchange": "SZ", "aliases": ["云南白药"]},
    {"symbol": "000999", "name": "华润三九", "exchange": "SZ", "aliases": ["华润三九", "三九医药", "999"]},
    {"symbol": "688137", "name": "近岸蛋白", "exchange": "SH", "aliases": ["近岸蛋白"]},
    {"symbol": "002821", "name": "凯莱英", "exchange": "SZ", "aliases": ["凯莱英"]},
    {"symbol": "000963", "name": "华东医药", "exchange": "SZ", "aliases": ["华东医药"]},
    {"symbol": "688271", "name": "联影医疗", "exchange": "SH", "aliases": ["联影医疗", "联影"]},
    {"symbol": "688235", "name": "百济神州", "exchange": "SH", "aliases": ["百济神州", "百济"]},
    {"symbol": "688180", "name": "君实生物", "exchange": "SH", "aliases": ["君实生物", "君实"]},
]


COMPANY_BY_SYMBOL = {item["symbol"]: item for item in PHARMA_COMPANIES}

NAME_TO_SYMBOL: dict[str, str] = {}
for company in PHARMA_COMPANIES:
    NAME_TO_SYMBOL[company["name"]] = company["symbol"]
    for alias in company.get("aliases", []):
        NAME_TO_SYMBOL[alias] = company["symbol"]


def list_pharma_companies() -> list[dict]:
    """返回医药观察池公司的深拷贝列表，避免调用方误改全局注册表。"""
    return [deepcopy(item) for item in PHARMA_COMPANIES]


def get_company(symbol: str) -> dict | None:
    """按股票代码读取单家公司的注册信息。"""
    item = COMPANY_BY_SYMBOL.get(symbol)
    return deepcopy(item) if item else None


def resolve_company_symbol(query: str) -> str | None:
    """根据 6 位代码、公司全名或别名解析标准股票代码。"""
    if not query:
        return None

    if query.isdigit() and len(query) == 6:
        return query if query in COMPANY_BY_SYMBOL else None

    for name, symbol in NAME_TO_SYMBOL.items():
        if name in query:
            return symbol
    return None


def to_market_prefix(symbol: str) -> str:
    """根据股票代码前缀推断交易所市场简称。"""
    if symbol.startswith(("0", "3")):
        return "SZ"
    if symbol.startswith(("4", "8")):
        return "BJ"
    return "SH"


def to_tushare_code(symbol: str) -> str:
    """把纯数字股票代码转换为 Tushare 使用的代码格式。"""
    return f"{symbol}.{to_market_prefix(symbol)}"