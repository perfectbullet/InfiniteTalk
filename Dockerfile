FROM infinitetalk:v5

ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

RUN pip install aiohttp