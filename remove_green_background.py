"""
去除视频绿色背景，输出透明背景视频

使用 FFmpeg 的 colorkey 滤镜去除绿色背景，支持自定义阈值参数
输出为支持透明通道的 MOV 或 WebM 格式

用法:
    python remove_green_background.py --input input.mp4 --output output.mov
    python remove_green_background.py --input input.mp4 --output output.webm --similarity 0.4 --blend 0.1
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Tuple


class BlackBackgroundRemover:
    """绿色背景去除工具"""
    
    def __init__(
        self, 
        input_path: str, 
        output_path: str,
        similarity: float = 0.35,
        blend: float = 0.1
    ):
        """
        初始化绿色背景去除工具
        
        Args:
            input_path: 输入视频路径
            output_path: 输出视频路径（建议使用 .mov 或 .webm）
            similarity: 绿色相似度阈值 (0.0-1.0)，值越大去除范围越广
            blend: 边缘混合程度 (0.0-1.0)，用于平滑边缘
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.similarity = similarity
        self.blend = blend
    
    def check_ffmpeg(self) -> bool:
        """检查 FFmpeg 是否安装"""
        try:
            subprocess.run(
                ['ffmpeg', '-version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_codec_settings(self) -> Tuple[str, str, list]:
        """
        根据输出格式获取编码器设置
        
        Returns:
            (codec, pixel_format, extra_args)
        """
        ext = self.output_path.suffix.lower()
        
        if ext == '.mov':
            # ProRes 4444 支持透明通道，质量最好
            return 'prores_ks', 'yuva444p10le', ['-c:a', 'pcm_s16le']
        elif ext == '.webm':
            # VP9 支持透明通道，文件较小
            return 'libvpx-vp9', 'yuva420p', [
                '-c:a', 'libopus',
                '-auto-alt-ref', '0',
                '-b:v', '2M'  # 设置码率
            ]
        else:
            print(f"警告: 输出格式 {ext} 可能不支持透明通道")
            print("建议使用 .mov 或 .webm 格式")
            return 'png', 'rgba', []

    def process(self) -> bool:
        """
        处理视频,去除绿色背景和边缘色溢

        Returns:
            处理是否成功
        """
        if not self.check_ffmpeg():
            print("错误: 未找到 FFmpeg,请先安装 FFmpeg")
            print("Ubuntu/Debian: sudo apt-get install ffmpeg")
            print("macOS: brew install ffmpeg")
            print("Windows: 从 https://ffmpeg.org/download.html 下载")
            return False

        if not self.input_path.exists():
            print(f"错误: 输入视频文件不存在: {self.input_path}")
            return False

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        codec, pixel_format, extra_args = self.get_codec_settings()

        # 使用 colorkey + despill 组合滤镜
        filter_chain = (
            f"colorkey=0x00FF00:{self.similarity}:{self.blend},"
            "despill=type=green:mix=0.9:expand=0.05"
        )

        cmd = [
            'ffmpeg',
            '-i', str(self.input_path),
            '-vf', filter_chain,
            '-c:v', codec,
            '-pix_fmt', pixel_format,
            *extra_args,
            '-y',
            str(self.output_path)
        ]

        print("开始处理视频...")
        print(f"输入文件: {self.input_path}")
        print(f"输出文件: {self.output_path}")
        print(f"滤镜链: colorkey + despill (去除绿色色溢)")
        print(f"相似度阈值: {self.similarity}")
        print(f"边缘混合: {self.blend}")
        print(f"编码器: {codec}")
        print(f"像素格式: {pixel_format}")
        print()

        try:
            subprocess.run(cmd, check=True)
            print(f"\n✓ 处理完成!输出文件: {self.output_path}")
            size_mb = self.output_path.stat().st_size / (1024 * 1024)
            print(f"✓ 文件大小: {size_mb:.2f} MB")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n✗ 处理失败: {e}")
            return False


def validate_threshold(value: float, name: str) -> None:
    """验证阈值参数范围"""
    if not (0.0 <= value <= 1.0):
        raise argparse.ArgumentTypeError(
            f"{name} 参数必须在 0.0 到 1.0 之间，当前值: {value}"
        )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='去除视频绿色背景，输出透明背景视频',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法，输出 MOV 格式（推荐，质量最好）
  python remove_green_background.py --input input.mp4 --output output.mov
  
  # 输出 WebM 格式（文件较小）
  python remove_green_background.py --input input.mp4 --output output.webm
  
  # 调整相似度阈值（背景不是纯黑时使用）
  python remove_green_background.py --input input.mp4 --output output.mov --similarity 0.2
  
  # 调整边缘混合度（使边缘更平滑）
  python remove_green_background.py --input input.mp4 --output output.mov --blend 0.1

参数说明:
  --similarity: 绿色相似度阈值，值越大去除的颜色范围越广
                如果背景不是纯绿色，可以适当增大此值（例如 0.15-0.3）
  --blend:      边缘混合程度，值越大边缘越平滑
                建议保持较小值（0.05-0.1）以避免主体边缘过度透明
        """
    )
    
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='输入视频文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='输出视频文件路径（建议使用 .mov 或 .webm 格式）'
    )
    parser.add_argument(
        '-s', '--similarity',
        type=float,
        default=0.1,
        help='绿色相似度阈值 0.0-1.0（默认: 0.1）'
    )
    parser.add_argument(
        '-b', '--blend',
        type=float,
        default=0.05,
        help='边缘混合程度 0.0-1.0（默认: 0.05）'
    )
    
    args = parser.parse_args()
    
    # 验证参数
    try:
        validate_threshold(args.similarity, 'similarity')
        validate_threshold(args.blend, 'blend')
    except argparse.ArgumentTypeError as e:
        print(f"错误: {e}")
        sys.exit(1)
    
    # 处理视频
    remover = BlackBackgroundRemover(
        input_path=args.input,
        output_path=args.output,
        similarity=args.similarity,
        blend=args.blend
    )
    
    success = remover.process()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()