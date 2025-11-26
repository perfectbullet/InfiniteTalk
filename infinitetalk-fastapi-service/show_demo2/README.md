# 📚 PPT + 视频在线课程演示系统

一个教育培训风格的 PPT 展示网页，支持视频解说画中画功能。

## 🚀 快速启动

### 使用 Docker Compose（推荐）

1. **确保已安装 Docker 和 Docker Compose**
   ```bash
   docker --version
   docker-compose --version
   ```

2. **启动项目**
   ```bash
   docker-compose up -d
   ```

3. **访问应用**
   
   打开浏览器访问：http://localhost:8080

4. **查看日志**
   ```bash
   docker-compose logs -f
   ```

5. **停止服务**
   ```bash
   docker-compose down
   ```

### 使用 Docker（不使用 Compose）

```bash
# 构建镜像
docker build -t ppt-video-demo .

# 运行容器
docker run -d -p 8080:80 --name ppt-demo ppt-video-demo

# 停止容器
docker stop ppt-demo

# 删除容器
docker rm ppt-demo
```

### 本地直接运行

如果您有本地 Web 服务器：

```bash
# 使用 Python
python3 -m http.server 8080

# 使用 Node.js (需要安装 http-server)
npx http-server -p 8080

# 使用 PHP
php -S localhost:8080
```

## 📁 项目结构

```
.
├── index.html              # 主页面
├── style.css               # 样式文件
├── script.js               # 交互逻辑
├── docker-compose.yml      # Docker Compose 配置
├── Dockerfile              # Docker 镜像构建文件
├── nginx.conf              # Nginx 配置
└── README.md               # 项目说明
```

## ✨ 功能特点

- ✅ PPT 全屏展示
- ✅ 视频画中画（右下角浮窗）
- ✅ 视频可拖动、可调整大小
- ✅ 课程进度追踪
- ✅ 学习笔记功能
- ✅ 键盘快捷键支持
- ✅ 自动保存进度

## ⌨️ 快捷键

- `←` / `→` - 切换幻灯片
- `空格` - 播放/暂停视频

## 🔧 自定义配置

### 修改端口

编辑 `docker-compose.yml`：

```yaml
ports:
  - "您的端口:80"  # 例如："3000:80"
```

### 添加自己的内容

编辑 `script.js` 中的 `courseData` 数组：

```javascript
const courseData = [
    {
        id: 1,
        title: "您的课程标题",
        slideContent: `
            <h2>您的 PPT 内容</h2>
            <p>内容描述...</p>
        `,
        videoUrl: "您的视频URL",
        duration: "视频时长"
    },
    // 添加更多课程...
];
```

## 🌐 生产环境部署

### 使用反向代理

如果您使用 Nginx 作为反向代理：

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 使用 HTTPS

建议使用 Let's Encrypt 免费证书：

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d yourdomain.com
```

## 📝 注意事项

1. 视频文件建议使用 CDN 托管
2. 大型 PPT 建议使用图片格式
3. 生产环境建议启用 HTTPS
4. 定期备份用户笔记数据（存储在浏览器 localStorage）

## 🐛 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs web

# 检查端口占用
sudo lsof -i :8080
```

### 视频无法播放

- 检查视频 URL 是否可访问
- 检查浏览器控制台错误信息
- 确认视频格式为 MP4（H.264 编码）

## 📄 License

MIT License

## 👤 作者

perfectbullet

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！