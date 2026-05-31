"""
南巢店铺 BI 看板 — 后端服务

依赖: pip install flask flask-cors psycopg2-binary
启动: python bi_dashboard_server.py
访问: http://127.0.0.1:5000

环境变量:
  DB_HOST     数据库主机 (默认: 172.17.80.1)
  DB_PORT     数据库端口 (默认: 5432)
  DB_NAME     数据库名 (默认: postgres)
  DB_USER     用户名 (默认: postgres)
  DB_PASSWORD 密码 (默认: a123456)
"""

import os
from datetime import datetime
from flask import Flask, jsonify, render_template
from flask_cors import CORS
import psycopg2
import psycopg2.extras

app = Flask(__name__, static_folder='.', template_folder='.')
CORS(app)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "172.17.80.1"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "postgres"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "a123456"),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# ── 列名(双引号保留大小写) ──
S = dict(
    stat_date='"统计日期"', prod_id='"商品ID"', prod_name='"商品名称"',
    pay_amt='"支付金额"', pay_items='"支付件数"', pay_buyers='"支付买家数"',
    refund_amt='"成功退款金额"', visitor='"商品访客数"',
    cart_users='"商品加购人数"', cart_items='"商品加购件数"',
)
W = dict(
    date='"日期"', scene='"场景名字"', channel='"计划名字"', keyword='"主体名称"',
    impressions='"展现量"', clicks='"点击量"', cost='"花费"',
    content_type='"主体类型"',
)
W_KEY = dict(
    date='日期', scene='场景名字', channel='计划名字', keyword='主体名称',
    impressions='展现量', clicks='点击量', cost='花费',
    content_type='主体类型',
)
S_KEY = dict(
    stat_date='统计日期', prod_id='商品ID', prod_name='商品名称',
    pay_amt='支付金额', pay_items='支付件数', pay_buyers='支付买家数',
    refund_amt='成功退款金额', visitor='商品访客数',
    cart_users='商品加购人数', cart_items='商品加购件数',
)

# ── 页面入口 ──
@app.route('/')
def index():
    return render_template('bi-dashboard.html')

# ── API: 店铺数据概况 ──
@app.route('/api/shop_overview')
def api_shop_overview():
    """店铺维度核心指标汇总（近7日）"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 生意参谋 — 成交与流量指标
    cur.execute(f"""
        SELECT
            COALESCE(SUM({S['pay_amt']}), 0) AS pay_amount,
            COALESCE(SUM({S['refund_amt']}), 0) AS refund_amount,
            COALESCE(SUM({S['visitor']}), 0) AS visitors,
            COALESCE(SUM({S['pay_buyers']}), 0) AS pay_buyers,
            COALESCE(SUM({S['cart_users']}), 0) AS cart_users,
            COALESCE(SUM({S['cart_items']}), 0) AS cart_items
        FROM sycm_sp_all
        WHERE {S['stat_date']} >= CURRENT_DATE - INTERVAL '7 days'
    """)
    s = cur.fetchone()

    # 无界 — 推广花费（按场景分类）
    cur.execute(f"""
        SELECT
            COALESCE(SUM({W['cost']}), 0) AS total_cost,
            COALESCE(SUM(CASE WHEN {W['scene']} = '关键词推广' THEN {W['cost']} ELSE 0 END), 0) AS keyword_cost,
            COALESCE(SUM(CASE WHEN {W['scene']} = '人群推广' THEN {W['cost']} ELSE 0 END), 0) AS audience_cost,
            COALESCE(SUM(CASE WHEN {W['scene']} = '货品全站推广' THEN {W['cost']} ELSE 0 END), 0) AS "全站推广成本",
            COALESCE(SUM(CASE WHEN {W['scene']} = '超级短视频' THEN {W['cost']} ELSE 0 END), 0) AS video_cost,
            COALESCE(SUM(CASE WHEN {W['scene']} = '店铺直达' THEN {W['cost']} ELSE 0 END), 0) AS direct_cost
        FROM wj_jhbb_jh
        WHERE {W['date']} >= CURRENT_DATE - INTERVAL '7 days'
    """)
    w = cur.fetchone()
    cur.close()
    conn.close()

    pay_amt = float(s['pay_amount'])
    refund_amt = float(s['refund_amount'])
    net_amt = pay_amt - refund_amt
    total_cost = float(w['total_cost'])

    return jsonify({
        # 成交指标
        "pay_amount": round(pay_amt, 2),
        "refund_amount": round(refund_amt, 2),
        "net_amount": round(net_amt, 2),
        # 流量指标
        "visitors": int(s['visitors']),
        "pay_buyers": int(s['pay_buyers']),
        "cart_users": int(s['cart_users']),
        "cart_items": int(s['cart_items']),
        # 推广花费
        "total_cost": round(total_cost, 2),
        "keyword_cost": round(float(w['keyword_cost']), 2),
        "audience_cost": round(float(w['audience_cost']), 2),
        "全站推广成本": round(float(w['全站推广成本']), 2),
        # 衍生指标
        "net_profit": round(net_amt - total_cost, 2),
        "cost_ratio": round(total_cost / pay_amt * 100, 1) if pay_amt > 0 else 0,
        "roi": round(pay_amt / total_cost, 2) if total_cost > 0 else 0,
        "avg_order_value": round(pay_amt / int(s['pay_buyers']), 2) if int(s['pay_buyers']) > 0 else 0,
        "cart_rate": round(int(s['cart_users']) / int(s['visitors']) * 100, 2) if int(s['visitors']) > 0 else 0,
        "pay_rate": round(int(s['pay_buyers']) / int(s['visitors']) * 100, 2) if int(s['visitors']) > 0 else 0,
    })

# ── API: KPI（旧版，保留兼容） ──
@app.route('/api/kpi')
def api_kpi():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"""
        SELECT COALESCE(SUM({S['pay_amt']}), 0) AS ta,
               COALESCE(SUM({S['pay_items']}), 0) AS ti,
               COALESCE(SUM({S['pay_buyers']}), 0) AS tb
        FROM sycm_sp_all WHERE {S['stat_date']} >= CURRENT_DATE - INTERVAL '7 days'
    """)
    w = cur.fetchone()
    cur.execute(f"""
        SELECT COALESCE(SUM({S['pay_amt']}), 0) AS ta,
               COALESCE(SUM({S['pay_items']}), 0) AS ti
        FROM sycm_sp_all
        WHERE {S['stat_date']} >= CURRENT_DATE - INTERVAL '14 days'
          AND {S['stat_date']} < CURRENT_DATE - INTERVAL '7 days'
    """)
    lw = cur.fetchone()
    cur.execute(f"""
        SELECT COALESCE(SUM({S['refund_amt']}), 0) AS ra
        FROM sycm_sp_all WHERE {S['stat_date']} >= CURRENT_DATE - INTERVAL '7 days'
    """)
    rf = cur.fetchone()
    cur.close(); conn.close()

    def pct(c, p):
        return round((c - p) / p * 100, 1) if p else 0

    return jsonify({
        "payment_amount": round(float(w['ta']), 2) if w else 0,
        "payment_items": int(w['ti']) if w else 0,
        "buyers": int(w['tb']) if w else 0,
        "refund_amount": round(float(rf['ra']), 2) if rf else 0,
        "amount_trend": f"{pct(float(w['ta']), float(lw['ta']))}%" if w and lw else "0%",
        "items_trend": f"{pct(float(w['ti']), float(lw['ti']))}%" if w and lw else "0%",
    })

# ── API: 日销售额趋势 ──
@app.route('/api/trend')
def api_trend():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"""
        SELECT {S['stat_date']},
               COALESCE(SUM({S['pay_amt']}), 0) AS amount,
               COALESCE(SUM({S['pay_items']}), 0) AS items
        FROM sycm_sp_all WHERE {S['stat_date']} >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY {S['stat_date']} ORDER BY {S['stat_date']}
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify({
        "dates": [str(r[S_KEY['stat_date']]) for r in rows],
        "amounts": [round(float(r['amount']), 2) for r in rows],
        "items": [int(r['items']) for r in rows],
    })

# ── API: 商品支付TOP5 ──
@app.route('/api/product_top')
def api_product_top():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"""
        SELECT {S['prod_id']}, {S['prod_name']},
               COALESCE(SUM({S['pay_amt']}), 0) AS amount,
               COALESCE(SUM({S['pay_items']}), 0) AS items
        FROM sycm_sp_all WHERE {S['stat_date']} >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY {S['prod_id']}, {S['prod_name']} ORDER BY amount DESC LIMIT 5
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    total = sum(float(r['amount']) for r in rows)
    return jsonify([
        {"id": r[S_KEY['prod_id']], "name": (r[S_KEY['prod_name']] or '')[:20],
         "amount": round(float(r['amount']), 2), "items": int(r['items']),
         "share": round(float(r['amount']) / total * 100, 1) if total > 0 else 0}
        for r in rows
    ])

# ── API: 竞品监控 ──
@app.route('/api/competitor')
def api_competitor():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT p.item_id, p.title, p.seller, p.category,
               s.total_reviews, s.total_skus, s.skus_soldout,
               s.min_price, s.max_price, s.has_discount_change
        FROM competitor_daily_summary s
        JOIN competitor_products p ON s.item_id = p.item_id
        WHERE s.summary_date = CURRENT_DATE ORDER BY s.total_reviews DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify([
        {"item_id": r['item_id'], "name": (r['title'] or '')[:25],
         "seller": r['seller'], "category": r['category'],
         "total_reviews": int(r['total_reviews']), "total_skus": int(r['total_skus']),
         "skus_soldout": int(r['skus_soldout']),
         "price_range": f"¥{r['min_price']:.0f}~¥{r['max_price']:.0f}" if r['min_price'] else '-',
         "has_price_change": r['has_discount_change']}
        for r in rows
    ])

# ── API: 竞品SKU预估销售额 ──
@app.route('/api/competitor_sales')
def api_competitor_sales():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT t.item_id, p.title, t.sku_name,
               y.stock AS ystock, t.stock AS tstock,
               y.stock - t.stock AS decr, t.discount_price,
               (y.stock - t.stock) * t.discount_price AS est
        FROM competitor_sku_snapshots t
        JOIN competitor_sku_snapshots y
          ON t.item_id = y.item_id AND t.sku_id = y.sku_id
         AND y.snapshot_date = t.snapshot_date - INTERVAL '1 day'
        JOIN competitor_products p ON t.item_id = p.item_id
        WHERE t.snapshot_date = CURRENT_DATE AND y.stock > t.stock
        ORDER BY est DESC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify({
        "total_est_sales": round(sum(float(r['est']) for r in rows), 2),
        "items": [{"sku_name": r['sku_name'][:25], "decrease": int(r['decr']),
                   "price": round(float(r['discount_price']), 2),
                   "est_sales": round(float(r['est']), 2)} for r in rows[:5]]
    })

# ── API: 流量来源 ──
@app.route('/api/traffic')
def api_traffic():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"""
        SELECT {W['channel']},
               COALESCE(SUM({W['impressions']}), 0) AS imp,
               COALESCE(SUM({W['clicks']}), 0) AS clk,
               COALESCE(SUM({W['cost']}), 0) AS cst
        FROM wj_jhbb_jh WHERE {W['date']} >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY {W['channel']} ORDER BY clk DESC LIMIT 5
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify([
        {"source": r[W_KEY['channel']], "clicks": int(r['clk']),
         "impressions": int(r['imp']), "cost": round(float(r['cst']), 2)}
        for r in rows
    ])

# ── API: 关键词 ──
@app.route('/api/keywords')
def api_keywords():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"""
        SELECT {W['keyword']},
               COALESCE(SUM({W['impressions']}), 0) AS imp,
               COALESCE(SUM({W['clicks']}), 0) AS clk
        FROM wj_nrbb_nrandjh
        WHERE {W['date']} >= CURRENT_DATE - INTERVAL '7 days'
          AND ({W['keyword']} LIKE '%黑胡桃%' OR {W['keyword']} LIKE '%实木%' OR {W['keyword']} LIKE '%原木%')
        GROUP BY {W['keyword']} ORDER BY clk DESC LIMIT 10
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify([
        {"keyword": r[W_KEY['keyword']][:15], "impressions": int(r['imp']), "clicks": int(r['clk'])}
        for r in rows
    ])

# ── API: 报表概览 ──
@app.route('/api/reports')
def api_reports():
    conn = get_conn()
    cur = conn.cursor()
    tables = {
        "商品报表": "wj_spbb_spandjh", "单元报表": "wj_dybb_dyandjh",
        "地域报表": "wj_diyubb_sfandcs", "计划报表": "wj_jhbb_jh",
        "内容报表": "wj_nrbb_nrandjh", "人群报表": "wj_rqbb_rqandjh",
        "营销场景报表": "wj_yxcjbb_yxcj",
    }
    result = {}
    for name, table in tables.items():
        cur.execute(f'SELECT COUNT(*) FROM {table} WHERE {W["date"]} >= CURRENT_DATE - INTERVAL \'7 days\'')
        result[name] = int(cur.fetchone()[0])
    cur.close(); conn.close()
    return jsonify(result)

# ── API: 完整日报 ──
@app.route('/api/daily_report')
def api_daily_report():
    from flask import current_app
    with current_app.test_client() as client:
        overview = client.get('/api/shop_overview').get_json()
        kpi = client.get('/api/kpi').get_json()
        trend = client.get('/api/trend').get_json()
        top5 = client.get('/api/product_top').get_json()
        competitor = client.get('/api/competitor').get_json()
        comp_sales = client.get('/api/competitor_sales').get_json()
        traffic = client.get('/api/traffic').get_json()
        keywords = client.get('/api/keywords').get_json()
        reports = client.get('/api/reports').get_json()

    return jsonify({
        "overview": overview,
        "kpi": kpi,
        "trend": trend,
        "product_top": top5,
        "competitor": competitor,
        "competitor_sales": comp_sales,
        "traffic": traffic,
        "keywords": keywords,
        "reports": reports,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

# ── 启动 ──
if __name__ == '__main__':
    print("=" * 50)
    print("  南巢店铺 BI 看板")
    print(f"  数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("  访问: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
