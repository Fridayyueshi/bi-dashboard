# 南巢店铺 BI 看板

> 天猫店铺"南巢"（黑胡桃木/真皮床）的数据可视化看板，长期开发项目。

## 📦 项目结构

```
nanchao-bi-dashboard/
├── server/              # 后端服务
│   ├── bi_dashboard_server.py   # Flask API + 页面入口
│   ├── requirements.txt         # Python 依赖
│   └── config.example.env       # 环境变量示例
├── client/              # 前端页面
│   └── bi-dashboard.html        # 单文件 SPA（深色主题卡片式布局）
├── docs/                # 文档
│   └── API.md                   # API 接口文档
├── scripts/             # 辅助脚本
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

## 📅 开发计划

- [ ] 竞品每日监控 cron 任务（待创建）
- [ ] 竞品SKU预估销售额板块
- [ ] 竞品情感分析趋势图
- [ ] 无界报表数据深度分析
- [ ] 多店铺支持
- [ ] 数据导出（CSV/PDF）
- [ ] 移动端适配优化
