# 南巢店铺 BI 看板

> 天猫店铺"南巢"（黑胡桃木/真皮床）的数据可视化看板，长期开发项目。

📋 **项目架构设计**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 完整模块划分、依赖关系、开发优先级

📖 **API 接口文档**: [docs/API.md](docs/API.md)

## 📦 项目结构

```
nanchao-bi-dashboard/
├── server/                    # 后端服务
│   ├── bi_dashboard_server.py # Flask API + 页面入口
│   └── requirements.txt       # Python 依赖
├── client/                    # 前端页面
│   └── bi-dashboard.html      # 单文件 SPA（深色卡片式布局）
├── docs/                      # 文档
│   ├── ARCHITECTURE.md        # 项目架构设计（模块划分+依赖+优先级）
│   └── API.md                 # API 接口文档
├── scripts/                   # 辅助脚本
├── README.md
└── .gitignore
```

## 🚀 快速启动

```bash
cd server
pip install -r requirements.txt
python bi_dashboard_server.py
# 访问 http://127.0.0.1:5000
```

## 📊 数据源

| 数据模块 | 数据库表 | 说明 |
|----------|----------|------|
| KPI / 趋势 / 商品排行 | `sycm_sp_all` | 生意参谋商品排行（近7日） |
| 流量来源 | `wj_jhbb_jh` | 无界计划报表 |
| 关键词上升 | `wj_nrbb_nrandjh` | 无界内容报表 |
| 报表概览 | 7张无界报表 | 商品/单元/地域/计划/内容/人群/营销场景 |
| 竞品监控 | `competitor_*` | 竞品 SKU/评价（可选） |

## 🔧 配置

```bash
export DB_HOST=172.17.80.1
export DB_PORT=5432
export DB_NAME=postgres
export DB_USER=postgres
export DB_PASSWORD=a123456
```

## 📅 开发阶段

| 阶段 | 模块 | 状态 |
|------|------|------|
| **Phase 1** — 核心看板 | M1~M6 | ✅ 已完成 |
| **Phase 2** — 竞品监控 | M7 + M11 | ⏳ 待开发 |
| **Phase 3** — 数据导出 | M8 + M9 | ⏳ 待开发 |
| **Phase 4** — 多店铺 | M10 | ⏳ 待开发 |

详见: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
