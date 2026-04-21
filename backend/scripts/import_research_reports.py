"""兼容旧脚本路径，转发到 crawler.scripts.import_research_reports。"""

from crawler.scripts.import_research_reports import *  # noqa: F401,F403

if __name__ == "__main__":
    import_reports_to_knowledge_store()