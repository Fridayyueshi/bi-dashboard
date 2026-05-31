# BI 看板 API 接口文档

## 基础信息

- **Base URL**: `http://127.0.0.1:5000`
- **数据源**: PostgreSQL (`172.17.80.1:5432/postgres`)
- **时间范围**: 默认近7日

---

## 接口列表

### 1. KPI 核心指标

**GET** `/api/kpi`

近7日核心经营数据 + 上周同比。

| 字段 | 类型 | 说明 |
|------|------|------|
| `payment_amount` | number | 支付金额（元） |
| `payment_items` | number | 支付件数 |
| `buyers` | number | 支付买家数 |
| `refund_amount` | number | 退款金额（元） |
| `amount_trend` | string | 金额环比，如 `"30.3%"` |
| `items_trend` | string | 件数环比 |

---

### 2. 日销售额趋势

**GET** `/api/trend`

近7日每日销售额和件数。

| 字段 | 类型 | 说明 |
|------|------|------|
| `dates` | string[] | 日期数组 `["2026-05-24", ...]` |
| `amounts` | number[] | 每日支付金额 |
| `items` | number[] | 每日支付件数 |

---

### 3. 商品支付TOP5

**GET** `/api/product_top`

近7日支付金额TOP5商品。

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | number | 商品ID |
| `name` | string | 商品名称（截断20字） |
| `amount` | number | 支付金额 |
| `items` | number | 支付件数 |
| `share` | number | 占TOP5总额百分比 |

---

### 4. 竞品监控

**GET** `/api/competitor`

当日竞品监控汇总（竞品每日监控 cron 运行后才有数据）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `item_id` | number | 商品ID |
| `name` | string | 商品名称 |
| `seller` | string | 店铺名 |
| `category` | string | 品类 |
| `total_reviews` | number | 评价数 |
| `total_skus` | number | SKU数 |
| `skus_soldout` | number | 售罄SKU数 |
| `price_range` | string | 价格区间，如 `"¥2443~¥11152"` |
| `has_price_change` | boolean | 是否有调价 |

---

### 5. 竞品SKU预估销售额

**GET** `/api/competitor_sales`

竞品SKU库存日减少量 × 折后价 = 预估日销售额。

| 字段 | 类型 | 说明 |
|------|------|------|
| `total_est_sales` | number | 所有竞品SKU预估总销售额 |
| `items` | object[] | SKU列表（最多5个） |

---

### 6. 评价情感分析

**GET** `/api/sentiment`

竞品评价情感统计（当前固定查询 item_id=663174705065）。

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | number | 总评价数 |
| `good` | number | 好评数 |
| `neutral` | number | 中评数 |
| `bad` | number | 差评数 |
| `good_rate` | number | 好评率百分比 |

---

### 7. 流量来源分布

**GET** `/api/traffic`

无界计划报表的渠道点击量TOP5。

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | string | 渠道/计划名 |
| `clicks` | number | 点击量 |
| `impressions` | number | 展现量 |
| `cost` | number | 花费 |

---

### 8. 关键词上升TOP10

**GET** `/api/keywords`

无界内容报表中黑胡桃/实木/原木相关关键词。

| 字段 | 类型 | 说明 |
|------|------|------|
| `keyword` | string | 关键词（截断15字） |
| `impressions` | number | 展现量 |
| `clicks` | number | 点击量 |

---

### 9. 无界报表概览

**GET** `/api/reports`

各报表近7日记录数。

| 报表名 | 说明 |
|--------|------|
| 商品报表 | `wj_spbb_spandjh` |
| 单元报表 | `wj_dybb_dyandjh` |
| 地域报表 | `wj_diyubb_sfandcs` |
| 计划报表 | `wj_jhbb_jh` |
| 内容报表 | `wj_nrbb_nrandjh` |
| 人群报表 | `wj_rqbb_rqandjh` |
| 营销场景报表 | `wj_yxcjbb_yxcj` |

---

### 10. 完整日报

**GET** `/api/daily_report`

一次性返回所有板块数据，用于全量刷新。

---

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_HOST` | `172.17.80.1` | 数据库主机 |
| `DB_PORT` | `5432` | 数据库端口 |
| `DB_NAME` | `postgres` | 数据库名 |
| `DB_USER` | `postgres` | 用户名 |
| `DB_PASSWORD` | `a123456` | 密码 |
