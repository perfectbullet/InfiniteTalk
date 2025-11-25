# Python 客户端使用示例

这个文档展示如何使用 Python 调用绿色背景去除服务 API。

## 安装依赖

```bash
pip install requests
```

## 基础使用

### 1. 转换单个视频

```python
import requests
import time

def convert_video(input_path: str, output_format: str = "mov"):
    """
    转换视频并去除绿色背景
    
    Args:
        input_path: 输入视频文件路径
        output_format: 输出格式（不带点号），如 "mov", "webm"
    
    Returns:
        转换结果字典
    """
    url = "http://localhost:8000/convert"
    payload = {
        "input": input_path,
        "output_format": output_format
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()


# 使用示例
result = convert_video("/path/to/video.mp4", "mov")
print(f"状态: {result['status']}")
print(f"输出路径: {result['output_path']}")
print(f"日志路径: {result['log_path']}")
```

### 2. 查看转换日志

```python
import requests
from pathlib import Path

def get_log_content(log_filename: str):
    """
    获取日志文件内容
    
    Args:
        log_filename: 日志文件名
    
    Returns:
        日志内容字符串
    """
    url = f"http://localhost:8000/logs/{log_filename}"
    response = requests.get(url)
    
    if response.status_code == 404:
        return None
    
    response.raise_for_status()
    return response.text


# 使用示例
log_content = get_log_content("video.log")
if log_content:
    print(log_content)
else:
    print("日志文件不存在")
```

### 3. 完整的转换流程（包含进度监控）

```python
import requests
import time
from pathlib import Path

class VideoConverter:
    """视频转换客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def convert(self, input_path: str, output_format: str = "mov"):
        """开始转换任务"""
        url = f"{self.base_url}/convert"
        payload = {
            "input": input_path,
            "output_format": output_format
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if result['status'] == 'success':
            print(f"✓ 输出文件已存在: {result['output_path']}")
            return result
        
        print(f"✓ 转换任务已启动，PID: {result['message'].split(': ')[-1]}")
        return result
    
    def get_log(self, log_filename: str):
        """获取日志内容"""
        url = f"{self.base_url}/logs/{log_filename}"
        response = requests.get(url)
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        return response.text
    
    def wait_for_completion(self, log_path: str, check_interval: int = 5, timeout: int = 600):
        """
        等待转换完成
        
        Args:
            log_path: 日志文件路径
            check_interval: 检查间隔（秒）
            timeout: 超时时间（秒）
        
        Returns:
            是否成功完成
        """
        log_filename = Path(log_path).name
        start_time = time.time()
        
        print("等待转换完成...")
        
        while True:
            # 检查超时
            if time.time() - start_time > timeout:
                print("✗ 转换超时")
                return False
            
            # 获取日志内容
            log_content = self.get_log(log_filename)
            
            if log_content is None:
                print("⏳ 等待日志文件生成...")
                time.sleep(check_interval)
                continue
            
            # 检查是否完成
            if "✓ 处理完成" in log_content:
                print("✓ 转换成功完成!")
                return True
            elif "✗ 处理失败" in log_content or "错误" in log_content:
                print("✗ 转换失败，查看日志获取详情")
                print(log_content)
                return False
            
            print("⏳ 转换进行中...")
            time.sleep(check_interval)


# 使用示例
def main():
    converter = VideoConverter()
    
    # 开始转换
    result = converter.convert("/path/to/video.mp4", "mov")
    
    if result['status'] == 'started':
        # 等待完成
        success = converter.wait_for_completion(result['log_path'])
        
        if success:
            print(f"输出文件: {result['output_path']}")
        else:
            print("转换失败")
    else:
        print("文件已存在，无需转换")


if __name__ == "__main__":
    main()
```

### 4. 批量转换多个视频

```python
import requests
from pathlib import Path
from typing import List, Dict
import time

class BatchConverter:
    """批量视频转换客户端"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def convert_batch(self, video_files: List[str], output_format: str = "mov"):
        """
        批量转换视频
        
        Args:
            video_files: 视频文件路径列表
            output_format: 输出格式
        
        Returns:
            转换结果列表
        """
        results = []
        
        for video_file in video_files:
            try:
                print(f"\n正在处理: {video_file}")
                result = self._convert_single(video_file, output_format)
                results.append({
                    "input": video_file,
                    "status": "success" if result else "failed",
                    "result": result
                })
            except Exception as e:
                print(f"✗ 处理失败: {e}")
                results.append({
                    "input": video_file,
                    "status": "error",
                    "error": str(e)
                })
        
        return results
    
    def _convert_single(self, input_path: str, output_format: str):
        """转换单个视频"""
        url = f"{self.base_url}/convert"
        payload = {
            "input": input_path,
            "output_format": output_format
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        if result['status'] == 'success':
            print(f"✓ 文件已存在，跳过")
        else:
            print(f"✓ 转换任务已启动")
        
        return result


# 使用示例
def batch_convert_example():
    converter = BatchConverter()
    
    video_files = [
        "/path/to/video1.mp4",
        "/path/to/video2.mp4",
        "/path/to/video3.mp4"
    ]
    
    results = converter.convert_batch(video_files, "mov")
    
    # 统计结果
    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n总计: {len(results)} 个文件")
    print(f"成功: {success_count} 个")
    print(f"失败: {len(results) - success_count} 个")


if __name__ == "__main__":
    batch_convert_example()
```

### 5. 错误处理示例

```python
import requests
from requests.exceptions import RequestException

def convert_with_error_handling(input_path: str, output_format: str = "mov"):
    """带完整错误处理的转换函数"""
    try:
        url = "http://localhost:8000/convert"
        payload = {
            "input": input_path,
            "output_format": output_format
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        # 处理不同的 HTTP 状态码
        if response.status_code == 404:
            print(f"✗ 错误: 输入文件不存在 - {input_path}")
            return None
        elif response.status_code == 400:
            print(f"✗ 错误: 参数错误 - {response.json()['detail']}")
            return None
        elif response.status_code == 500:
            print(f"✗ 错误: 服务器内部错误 - {response.json()['detail']}")
            return None
        
        response.raise_for_status()
        result = response.json()
        
        print(f"✓ 请求成功")
        return result
        
    except requests.exceptions.Timeout:
        print("✗ 错误: 请求超时")
        return None
    except requests.exceptions.ConnectionError:
        print("✗ 错误: 无法连接到服务器，请确认服务是否启动")
        return None
    except RequestException as e:
        print(f"✗ 错误: 网络请求失败 - {e}")
        return None
    except Exception as e:
        print(f"✗ 错误: 未知错误 - {e}")
        return None


# 使用示例
result = convert_with_error_handling("/path/to/video.mp4", "mov")
if result:
    print(f"输出路径: {result['output_path']}")
```

## 环境变量配置

创建配置文件来管理 API 地址：

```python
import os
from typing import Optional

class Config:
    """配置类"""
    
    def __init__(self):
        self.api_base_url = os.getenv(
            'GREEN_BG_API_URL',
            'http://localhost:8000'
        )
        self.timeout = int(os.getenv('API_TIMEOUT', '60'))
    
    @property
    def convert_url(self):
        return f"{self.api_base_url}/convert"
    
    @property
    def logs_url(self):
        return f"{self.api_base_url}/logs"


# 使用示例
config = Config()
response = requests.post(config.convert_url, json={...})
```

## 测试建议

在实际使用前，建议先测试 API 连接：

```python
import requests

def test_connection(base_url: str = "http://localhost:8000"):
    """测试服务是否可用"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✓ 服务连接正常")
            return True
        else:
            print(f"✗ 服务返回异常状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接到服务: {e}")
        return False


if __name__ == "__main__":
    test_connection()
```
