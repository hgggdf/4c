"""兼容旧脚本路径，转发到 crawler.scripts.import_research_reports。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from crawler.scripts.import_research_reports import *  # noqa: F401,F403

if __name__ == "__main__":
    main()