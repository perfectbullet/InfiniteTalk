#!/usr/bin/env python3
"""
测试绿色背景去除服务 API

测试以下功能:
1. 健康检查接口
2. /convert 接口的参数验证
3. /logs 接口的错误处理
"""

import sys
import time
import tempfile
import subprocess
import requests
from pathlib import Path


def test_api():
    """测试 API 端点"""
    base_url = "http://localhost:8000"
    
    print("等待服务启动...")
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{base_url}/health", timeout=1)
            if response.status_code == 200:
                print("✓ 服务已启动")
                break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    else:
        print("✗ 服务启动失败")
        return False
    
    print("\n测试 1: 健康检查接口")
    response = requests.get(f"{base_url}/health")
    if response.status_code == 200 and response.json()["status"] == "ok":
        print("✓ 健康检查通过")
    else:
        print("✗ 健康检查失败")
        return False
    
    print("\n测试 2: 参数验证 - 输入文件不存在")
    response = requests.post(
        f"{base_url}/convert",
        json={
            "input": "/nonexistent/file.mp4",
            "output_format": "mov"
        }
    )
    if response.status_code == 404:
        print("✓ 正确返回 404 错误")
    else:
        print(f"✗ 期望 404，实际返回 {response.status_code}")
        return False
    
    print("\n测试 3: 参数验证 - 输出格式与输入格式相同")
    # 使用临时文件
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        test_file = Path(tmp.name)
    
    try:
        response = requests.post(
            f"{base_url}/convert",
            json={
                "input": str(test_file),
                "output_format": ".mp4"
            }
        )
        if response.status_code == 400:
            print("✓ 正确返回 400 错误")
        else:
            print(f"✗ 期望 400，实际返回 {response.status_code}")
            return False
    finally:
        test_file.unlink(missing_ok=True)
    
    print("\n测试 4: 日志文件不存在")
    response = requests.get(f"{base_url}/logs/nonexistent.log")
    if response.status_code == 404:
        print("✓ 正确返回 404 错误")
    else:
        print(f"✗ 期望 404，实际返回 {response.status_code}")
        return False
    
    print("\n测试 5: 自动添加点号到输出格式")
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        test_file = Path(tmp.name)
    
    try:
        response = requests.post(
            f"{base_url}/convert",
            json={
                "input": str(test_file),
                "output_format": "mov"  # 不带点号
            }
        )
        # 不管是否成功启动命令，只要不报参数错误即可
        if response.status_code in [200, 500]:
            print("✓ 输出格式自动添加点号")
        else:
            print(f"✗ 意外的状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
    finally:
        test_file.unlink(missing_ok=True)
    
    print("\n✓ 所有测试通过!")
    return True


if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
