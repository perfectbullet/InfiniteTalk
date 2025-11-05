#!/usr/bin/env python
"""
InfiniteTalk API Server 启动脚本
启动命令： python api_server/api_server.py 有路径导入问题，还未搞定
"""

if __name__ == "__main__":
    from api_server.api_server import main
    main()