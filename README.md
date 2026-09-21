# 课堂行为智能检测系统（YOLO + DeepSeek）

基于改进 YOLO（PyTorch）与大模型（DeepSeek / Qwen）的课堂行为检测与智能分析系统。
支持**单图 / 图片文件夹批量 / 视频 / 实时摄像头**四类输入，含完整前后端源码与一键部署脚本。

技术栈：**Vue3 + Element Plus + Pinia + Axios** ・ **Spring Boot 3 + JPA** ・ **Flask + PyTorch/YOLO** ・ **MySQL（H2 可替换）** ・ **FFmpeg** ・ **JSZip** ・ **SocketIO（可选）**

默认识别 6 类课堂行为：**低头写字、低头看书、抬头听课、转头、举手、站立**。

---

## 一、环境准备

| 组件 | 版本要求 | 本机实测 |
|---|---|---|
| Python | 3.9+（建议 3.10~3.13） | 3.13.14 |
| JDK | 17+ | 25.0.2 |
| Maven | 3.8+ | 3.9.15 |
| Node.js | 18+ | 22.22.2（npm 10.9.7） |
| MySQL | 8.0（可选，可换 H2） | 8.0.40（服务未启动时用 H2） |
| FFmpeg | 任意较新版本（可选） | N-125752 |

> 若机器上没有 Python 虚拟环境要求，全部依赖会安装到指定解释器中；
> 建议为 AI 服务单独使用虚拟环境，见下节。

---

## 二、安装步骤

### 1) AI 推理服务（`ai-service`，端口 5000）

```bash
cd ai-service

# ① 安装基础依赖
python -m pip install -r requirements.txt

# ② 安装 PyTorch（Windows CPU 版，约 200MB；避免默认拉取 2GB+ 的 CUDA 包）
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# ③ 安装 YOLO
python -m pip install ultralytics
```

> 说明：
> - 未安装 torch / ultralytics 时，服务会自动降级为**内置演示引擎**，其余功能（视频流、记录、AI 建议、PDF）全部可用。
> - 首次启动会自动下载官方通用权重 `yolov8n.pt`（约 6MB）。
> - 复制 `.env.example` 为 `.env` 可配置 DeepSeek / Qwen 的 API Key（不配置也能跑，建议由本地规则引擎生成）。

### 2) 后端（`backend`，端口 8080）

```bash
cd backend
mvn -s ../mvn/settings.xml -B package -DskipTests     # 产出 target/classroom-backend.jar
```

数据库二选一：
- **MySQL**：先执行 `db/schema.sql` 建库，或修改 `src/main/resources/application.yml` 的连接信息；
- **H2（零配置兜底）**：启动时加 `--spring.profiles.active=h2`，数据落在 `backend/data/` 目录。

### 3) 前端（`frontend`，端口 5173）

```bash
cd frontend
npm install --registry=https://registry.npmmirror.com   # 国内加速
npm run dev
```

---

## 三、启动方式

### 方式一：一键脚本（Windows PowerShell，推荐）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1          # MySQL 模式
powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1 -H2      # 无 MySQL 时用 H2
powershell -ExecutionPolicy Bypass -File scripts\start-all.ps1 -SkipFrontend
```

停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop-all.ps1
```

### 方式二：分别启动

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start-ai.ps1
powershell -ExecutionPolicy Bypass -File scripts\start-backend.ps1 -H2
powershell -ExecutionPolicy Bypass -File scripts\start-frontend.ps1
```

### 方式三：命令行直接启动

```bash
# 1. AI 服务
cd ai-service && python app.py

# 2. 后端
cd backend && java -jar target/classroom-backend.jar --spring.profiles.active=h2 --server.port=8080

# 3. 前端
cd frontend && npm run dev -- --port 5173
```

访问地址：

| 服务 | 地址 |
|---|---|
| 前端界面 | http://127.0.0.1:5173 |
| 后端接口 | http://127.0.0.1:8080/api/system/status |
| AI 服务 | http://127.0.0.1:5000/health |

---

## 四、验证是否运行成功

### 1) 一键验证脚本（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

覆盖 10 项：AI 健康、模型状态、单图检测、批量检测、后端状态、落库、记录列表、AI 建议、PDF 导出、视频全流程。

### 2) 手工验证（Linux/macOS/Git Bash）

```bash
# ① 服务健康
curl --noproxy '*' http://127.0.0.1:5000/health
curl --noproxy '*' http://127.0.0.1:8080/api/system/status

# ② 单图检测（AI 服务直连）
cd ai-service
curl --noproxy '*' -F "file=@demo_data/classroom_01.jpg" http://127.0.0.1:5000/api/detect/image

# ③ 经后端检测并落库
curl --noproxy '*' -F "file=@demo_data/classroom_01.jpg" http://127.0.0.1:8080/api/detect/image

# ④ 批量（zip）
curl --noproxy '*' -F "zip=@demo_data/classroom_batch.zip" http://127.0.0.1:8080/api/detect/batch

# ⑤ AI 建议
curl --noproxy '*' -X POST -H "Content-Type: application/json" -d '{"provider":"deepseek"}' \
     http://127.0.0.1:8080/api/records/1/advice

# ⑥ PDF 报告
curl --noproxy '*' -o report.pdf http://127.0.0.1:8080/api/records/1/report

# ⑦ 视频（先创建任务，再轮询状态）
curl --noproxy '*' -F "file=@demo_data/classroom_demo.mp4" http://127.0.0.1:8080/api/detect/video
curl --noproxy '*' http://127.0.0.1:8080/api/detect/task/<taskId>
```

成功判据：
- `/health` 返回 `{"status":"ok"}`，且 `engine` 为 `ultralytics` 或 `demo`；
- `/api/system/status` 中 `aiServiceOnline=true`；
- 检测接口返回 `ok=true` 且 `labels` 中含 6 类行为之一；
- PDF 文件以 `%PDF` 开头且大小 > 1KB；
- 视频任务 `status` 由 `running` 变为 `finished`，并产生 `outputs/*.mp4`。

### 3) 演示素材一键生成

```bash
cd ai-service && python tools/make_demo_data.py --n 6
```

生成 `demo_data/classroom_*.jpg`、`classroom_batch.zip`、`classroom_demo.mp4`。

---

## 五、切换为真实课堂行为模型

当前默认使用官方通用权重 `yolov8n.pt`（COCO 80 类）。要获得真正的 6 类行为检测：

```bash
# 1) 按 YOLO 格式准备数据：datasets/classroom/{images,labels}/{train,val}
# 2) 类别顺序必须与 ai-service/data/classroom.yaml 一致
cd ai-service
python train.py --data data/classroom.yaml --weights yolov8n.pt --epochs 100 --imgsz 640
```

训练结束后脚本会把 `best.pt` 复制到 `ai-service/models/best.pt`，**重启 AI 服务**即自动加载，
此时 `/api/model/status` 中 `demo_mode=false` 且 `weights=models/best.pt`，输出即为真实行为类别。

---

## 六、常见问题

| 现象 | 原因与处理 |
|---|---|
| 后端提示「AI 推理服务未启动或不可达」 | 先启动 `ai-service`；确认 5000 端口未被占用 |
| `Port 18789 was already in use` | 环境变量覆盖了 `server.port`，启动时显式加 `--server.port=8080` |
| 检测结果为 0 个目标 | 通用权重对示意图/非真实照片不敏感；换真实课堂照片，或训练 6 类权重 |
| 视频无输出文件 | 检查 FFmpeg 是否在 PATH；无 FFmpeg 时会回退 mp4v 编码 |
| 摄像头打不开 | 需 localhost/HTTPS 环境并授予浏览器摄像头权限；确认 `CBD_CAMERA_INDEX` |
| AI 建议返回「本地规则引擎兜底」 | 未配置 `DEEPSEEK_API_KEY` / `DASHSCOPE_API_KEY`，属预期行为 |
| Maven 下载慢 | 使用 `-s ../mvn/settings.xml`（阿里云镜像） |
| npm 安装慢/失败 | 使用 `--registry=https://registry.npmmirror.com` |
