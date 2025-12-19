"""
测试视频任务取消功能

演示如何：
1. 创建视频生成任务
2. 查询任务状态
3. 取消正在运行的任务
"""

import requests
import time


API_BASE_URL = "http://localhost:50002"


def create_test_task():
    """创建一个测试任务"""
    url = f"{API_BASE_URL}/video_task/create"
    
    # 使用较长的音频文本，确保任务运行足够长时间以便测试取消
    data = {
        "prompt": "一位年轻而充满活力的女教师正在讲解PPT演示文稿。她穿着天蓝色的衣服，长长的棕发自然垂落。"
                  "她用富有表现力的手势强调重点内容。她的脸上洋溢着热情和温暖。",
        "image_path": "/workspace/InfiniteTalk/upload_image/img_20251125_061050_4bce0a3b.png",
        "audio_text": "欢迎同学们选修制造工程体验课程。今天我们将学习关于现代制造技术的基础知识。",
        "spk_name": "胡桃",
        "use_green_background": False  # 跳过绿幕处理，加快测试
    }
    
    print("📤 创建任务...")
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        task_info = response.json()
        task_id = task_info['id']
        print(f"✅ 任务创建成功: {task_id}")
        print(f"   状态: {task_info['status']}")
        return task_id
    else:
        print(f"❌ 创建任务失败: {response.status_code}")
        print(f"   错误: {response.text}")
        return None


def get_task_status(task_id):
    """查询任务状态"""
    url = f"{API_BASE_URL}/video_task/status/{task_id}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        task_info = response.json()
        print(f"📊 任务状态: {task_info['status']}")
        if task_info.get('pid'):
            print(f"   进程 PID: {task_info['pid']}")
        if task_info.get('uptime'):
            print(f"   运行时长: {task_info['uptime']}s")
        return task_info
    else:
        print(f"❌ 查询失败: {response.status_code}")
        print(f"   错误: {response.text}")
        return None


def cancel_task(task_id):
    """取消任务"""
    url = f"{API_BASE_URL}/video_task/cancel/{task_id}"
    
    print(f"\n🛑 取消任务: {task_id}")
    response = requests.post(url)
    
    if response.status_code == 200:
        result = response.json()
        if result['success']:
            print(f"✅ {result['message']}")
            print(f"   之前状态: {result.get('previous_status')}")
            print(f"   当前状态: {result.get('current_status')}")
        else:
            print(f"⚠️  {result['message']}")
        return result
    else:
        print(f"❌ 取消失败: {response.status_code}")
        print(f"   错误: {response.text}")
        return None


def main():
    """主测试流程"""
    print("=" * 60)
    print("视频任务取消功能测试")
    print("=" * 60)
    
    # 1. 创建任务
    task_id = create_test_task()
    if not task_id:
        return
    
    # 2. 等待任务开始运行
    print("\n⏳ 等待任务开始运行（10秒）...")
    time.sleep(10)
    
    # 3. 查询任务状态
    print("\n" + "=" * 60)
    get_task_status(task_id)
    
    # 4. 取消任务
    print("=" * 60)
    cancel_result = cancel_task(task_id)
    
    # 5. 再次查询状态确认
    if cancel_result:
        print("\n⏳ 等待 3 秒后再次确认...")
        time.sleep(3)
        
        print("\n" + "=" * 60)
        print("📊 最终状态确认:")
        get_task_status(task_id)
    
    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)


def test_cancel_completed_task():
    """测试取消已完成的任务（应该失败）"""
    print("\n" + "=" * 60)
    print("测试取消已完成的任务")
    print("=" * 60)
    
    # 使用一个假设已完成的任务 ID（实际使用时替换为真实的已完成任务 ID）
    completed_task_id = "video_20231219_120000_abcd1234"
    
    result = cancel_task(completed_task_id)
    if result and not result['success']:
        print("✅ 预期行为：无法取消已完成的任务")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "cancel":
            # 直接取消指定任务
            if len(sys.argv) > 2:
                task_id = sys.argv[2]
                cancel_task(task_id)
            else:
                print("用法: python test_cancel_task.py cancel <task_id>")
        elif sys.argv[1] == "status":
            # 查询任务状态
            if len(sys.argv) > 2:
                task_id = sys.argv[2]
                get_task_status(task_id)
            else:
                print("用法: python test_cancel_task.py status <task_id>")
        else:
            print("未知命令。支持的命令: cancel, status")
    else:
        # 运行完整测试
        main()
