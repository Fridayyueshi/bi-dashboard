#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nanchao BI dashboard backend server

Dependencies: pip install flask flask-cors psycopg2-binary
Run: python bi_dashboard_server.py
Visit: http://127.0.0.1:5000

Environment:
  DB_HOST     database host (default: 172.17.80.1)
  DB_PORT     database port (default: 5432)
  DB_NAME     database name (default: postgres)
  DB_USER     database user (default: postgres)
  DB_PASSWORD database password (default: a123456)
  SECRET_KEY  Flask session key (default: nanchao-bi-secret-2026)
"""

import os
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, session, send_from_directory
from flask_cors import CORS
import requests
import psycopg2
import psycopg2.extras

app = Flask(__name__, static_folder='.', template_folder='.')
app.secret_key = os.environ.get("SECRET_KEY", "nanchao-bi-secret-2026")
app.permanent_session_lifetime = timedelta(hours=8)
CORS(app, supports_credentials=True)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "172.17.80.1"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "database": os.environ.get("DB_NAME", "postgres"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "a123456"),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

# ── 工具函数 ──
def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_user(username, password):
    """验证用户名密码"""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, username, display_name, role, is_active FROM bi_users WHERE username = %s AND password = %s",
        (username, hash_pwd(password))
    )
    user = cur.fetchone()
    if user:
        # 更新最后登录时间
        cur.execute("UPDATE bi_users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user['id'],))
        conn.commit()
    cur.close(); conn.close()
    return user

# ── 登录验证装饰器 ──
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "未登录", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated

# ── 页面入口 ──
@app.route('/')
def index():
    return send_from_directory('../client', 'bi-dashboard.html')

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

# ── API: 登录/登出/会话检查 ──
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '')
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"error": "请输入用户名和密码"}), 400

    # 验证用户
    user = verify_user(username, password)
    if not user:
        return jsonify({"error": "用户名或密码错误"}), 401

    session.permanent = True
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['display_name'] = user['display_name']
    session['role'] = user['role']
    return jsonify({
        "ok": True,
        "user": {
            "username": user['username'],
            "display_name": user['display_name'],
            "role": user['role'],
        }
    })

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"ok": True})

@app.route('/api/check_session')
def api_check_session():
    if 'user_id' in session:
        return jsonify({
            "ok": True,
            "user": {
                "username": session.get('username'),
                "display_name": session.get('display_name'),
                "role": session.get('role'),
            }
        })
    return jsonify({"ok": False, "error": "未登录"}), 401

# ── API: 店铺数据概况 ──
@app.route('/api/shop_overview')
@login_required
def api_shop_overview():
    from flask import request
    days_param = request.args.get('days', '7')
    if days_param == 'yesterday':
        date_filter = f"{S['stat_date']} = CURRENT_DATE - INTERVAL '1 day'"
    else:
        days = int(days_param)
        date_filter = f"{S['stat_date']} >= CURRENT_DATE - INTERVAL '{days} days'"
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
        WHERE {date_filter}
    """)
    s = cur.fetchone()

    # 无界 — 推广花费（按场景分类）
    if days_param == 'yesterday':
        w_filter = f"{W['date']} = CURRENT_DATE - INTERVAL '1 day'"
    else:
        w_filter = f"{W['date']} >= CURRENT_DATE - INTERVAL '{days} days'"
    cur.execute(f"""
        SELECT
            COALESCE(SUM({W['cost']}), 0) AS total_cost,
            COALESCE(SUM(CASE WHEN {W['scene']} = '关键词推广' THEN {W['cost']} ELSE 0 END), 0) AS keyword_cost,
            COALESCE(SUM(CASE WHEN {W['scene']} = '人群推广' THEN {W['cost']} ELSE 0 END), 0) AS audience_cost,
            COALESCE(SUM(CASE WHEN {W['scene']} = '货品全站推广' THEN {W['cost']} ELSE 0 END), 0) AS "全站推广成本",
            COALESCE(SUM(CASE WHEN {W['scene']} = '超级短视频' THEN {W['cost']} ELSE 0 END), 0) AS video_cost,
            COALESCE(SUM(CASE WHEN {W['scene']} = '店铺直达' THEN {W['cost']} ELSE 0 END), 0) AS direct_cost
        FROM wj_jhbb_jh
        WHERE {w_filter}
    """)
    w = cur.fetchone()
    cur.close()
    conn.close()

    pay_amt = float(s['pay_amount'])
    refund_amt = float(s['refund_amount'])
    net_amt = pay_amt - refund_amt
    total_cost = float(w['total_cost'])

    return jsonify({
        "pay_amount": round(pay_amt, 2),
        "refund_amount": round(refund_amt, 2),
        "net_amount": round(net_amt, 2),
        "visitors": int(s['visitors']),
        "pay_buyers": int(s['pay_buyers']),
        "cart_users": int(s['cart_users']),
        "cart_items": int(s['cart_items']),
        "total_cost": round(total_cost, 2),
        "keyword_cost": round(float(w['keyword_cost']), 2),
        "audience_cost": round(float(w['audience_cost']), 2),
        "全站推广成本": round(float(w['全站推广成本']), 2),
        "net_profit": round(net_amt - total_cost, 2),
        "cost_ratio": round(total_cost / net_amt * 100, 1) if net_amt > 0 else 0,
        "roi": round(net_amt / total_cost, 2) if total_cost > 0 else 0,
        "avg_order_value": round(pay_amt / int(s['pay_buyers']), 2) if int(s['pay_buyers']) > 0 else 0,
        "cart_rate": round(int(s['cart_users']) / int(s['visitors']) * 100, 2) if int(s['visitors']) > 0 else 0,
        "pay_rate": round(int(s['pay_buyers']) / int(s['visitors']) * 100, 2) if int(s['visitors']) > 0 else 0,
    })

# ── API: KPI（旧版，保留兼容） ──
@app.route('/api/kpi')
@login_required
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
@login_required
def api_trend():
    from flask import request
    days_param = request.args.get('days', '7')
    if days_param == 'yesterday':
        date_filter = f"{S['stat_date']} = CURRENT_DATE - INTERVAL '1 day'"
    else:
        days = int(days_param)
        date_filter = f"{S['stat_date']} >= CURRENT_DATE - INTERVAL '{days} days'"
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"""
        SELECT {S['stat_date']},
               COALESCE(SUM({S['pay_amt']}), 0) AS pay_amount,
               COALESCE(SUM({S['refund_amt']}), 0) AS refund_amount
        FROM sycm_sp_all WHERE {date_filter}
        GROUP BY {S['stat_date']} ORDER BY {S['stat_date']}
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return jsonify({
        "dates": [str(r[S_KEY['stat_date']]) for r in rows],
        "net_amounts": [round(float(r['pay_amount']) - float(r['refund_amount']), 2) for r in rows],
        "days": days_param,
    })

# ── API: 推广花费趋势 ──
@app.route('/api/ad_trend')
@login_required
def api_ad_trend():
    from flask import request
    days_param = request.args.get('days', '7')
    if days_param == 'yesterday':
        date_filter = f"{W['date']} = CURRENT_DATE - INTERVAL '1 day'"
    else:
        days = int(days_param)
        date_filter = f"{W['date']} >= CURRENT_DATE - INTERVAL '{days} days'"
    filter_scene = request.args.get('scene', '')
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if filter_scene:
        cur.execute(f"""
            SELECT {W['date']}, COALESCE(SUM({W['cost']}), 0) AS cost
            FROM wj_jhbb_jh
            WHERE {W['date']} >= CURRENT_DATE - INTERVAL '{days} days'
              AND {W['scene']} = %s
            GROUP BY {W['date']} ORDER BY {W['date']}
        """, (filter_scene,))
    else:
        cur.execute(f"""
            SELECT {W['date']},
                   COALESCE(SUM(CASE WHEN {W['scene']} = '关键词推广' THEN {W['cost']} ELSE 0 END), 0) AS keyword_cost,
                   COALESCE(SUM(CASE WHEN {W['scene']} = '人群推广' THEN {W['cost']} ELSE 0 END), 0) AS audience_cost,
                   COALESCE(SUM(CASE WHEN {W['scene']} = '货品全站推广' THEN {W['cost']} ELSE 0 END), 0) AS zhanquan_cost,
                   COALESCE(SUM({W['cost']}), 0) AS total_cost
            FROM wj_jhbb_jh
            WHERE {date_filter}
            GROUP BY {W['date']} ORDER BY {W['date']}
        """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    if filter_scene:
        scene_map = {'关键词推广': 'keyword_cost', '人群推广': 'audience_cost', '货品全站推广': '全站推广成本'}
        return jsonify({
            "dates": [str(r[W_KEY['date']]) for r in rows],
            "costs": [round(float(r['cost']), 2) for r in rows],
            "scene": filter_scene,
            "days": days_param,
        })
    return jsonify({
        "dates": [str(r[W_KEY['date']]) for r in rows],
        "keyword_cost": [round(float(r['keyword_cost']), 2) for r in rows],
        "audience_cost": [round(float(r['audience_cost']), 2) for r in rows],
        "全站推广成本": [round(float(r['zhanquan_cost']), 2) for r in rows],
        "total_cost": [round(float(r['total_cost']), 2) for r in rows],
        "days": days_param,
    })

# ── API: 商品支付TOP5 ──
@app.route('/api/product_top')
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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
@login_required
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

# ── API: 商品数据（独立模块，不影响其他页面） ──
@app.route('/api/product_data')
@login_required
def api_product_data():
    days_param = request.args.get('days', '7')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # 自定义日期区间优先
    if date_from and date_to:
        date_filter_o = f"\"订单付款时间\" >= '{date_from}'::date AND \"订单付款时间\" < ('{date_to}'::date + INTERVAL '1 day')"
        date_filter_a = f"\"日期\" >= '{date_from}'::date AND \"日期\" < ('{date_to}'::date + INTERVAL '1 day')"
    elif days_param == 'yesterday':
        date_filter_o = "\"订单付款时间\" >= (CURRENT_DATE - INTERVAL '1 day')::date AND \"订单付款时间\" < CURRENT_DATE::date"
        date_filter_a = "\"日期\" = CURRENT_DATE - INTERVAL '1 day'"
    else:
        days = int(days_param)
        date_filter_o = f"\"订单付款时间\" >= (CURRENT_DATE - INTERVAL '{days} days')::date"
        date_filter_a = f"\"日期\" >= CURRENT_DATE - INTERVAL '{days} days'"

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. 所有商品基础信息
    cur.execute('''
        SELECT DISTINCT "商品ID", "商品状态", "商品名称", "商家编码", "商品图片"
        FROM products ORDER BY "商品ID"
    ''')
    products = cur.fetchall()
    if not products:
        cur.close(); conn.close()
        return jsonify([])

    # 2. 订单聚合（总GMV、退款金额、种菜订单数）
    cur.execute(f'''
        SELECT "商品ID",
               COALESCE(SUM(CASE WHEN "买家实付金额" > 1000 THEN "买家实付金额" ELSE 0 END), 0) AS total_gmv,
               COALESCE(SUM(CASE WHEN "退款状态" = \'退款成功\' THEN CAST("退款金额" AS NUMERIC) ELSE 0 END), 0) AS total_refund,
               COALESCE(COUNT(CASE WHEN "买家实付金额" > 0 AND "买家实付金额" <= 1000 THEN 1 END), 0) AS seed_count
        FROM orders
        WHERE {date_filter_o}
        GROUP BY "商品ID"
    ''')
    order_map = {r['商品ID']: r for r in cur.fetchall()}

    # 3. 广告花费聚合
    cur.execute(f'''
        SELECT "主体id",
               COALESCE(SUM("花费"), 0) AS total_ad
        FROM wj_spbb_spandjh
        WHERE {date_filter_a}
        GROUP BY "主体id"
    ''')
    ad_map = {str(r['主体id']): r for r in cur.fetchall()}

    cur.close(); conn.close()

    result = []
    for p in products:
        pid = p['商品ID']
        oa = order_map.get(pid, {})
        aa = ad_map.get(pid, {})

        gmv = float(oa.get('total_gmv', 0) or 0)
        refund = float(oa.get('total_refund', 0) or 0)
        net_gmv = gmv - refund
        seed_count = int(oa.get('seed_count', 0) or 0)
        seed_cost = seed_count * 8
        ad_cost = float(aa.get('total_ad', 0) or 0)
        total_cost = ad_cost + seed_cost
        cost_ratio = round(total_cost / (net_gmv if net_gmv > 0 else 1) * 100, 2)

        result.append({
            "prod_id": pid,
            "status": p['商品状态'],
            "title": p['商品名称'],
            "model": p['商家编码'],
            "image": p['商品图片'],
            "gmv": round(gmv, 2),
            "refund": round(refund, 2),
            "net_gmv": round(net_gmv, 2),
            "ad_cost": round(ad_cost, 2),
            "seed_count": seed_count,
            "seed_cost": seed_cost,
            "total_cost": round(total_cost, 2),
            "cost_ratio": cost_ratio,
        })

    return jsonify(result)


# ── AI 分析 ──
AI_API_KEY = "sk-cxXAvs9pZLYXBWQj3dHkHtmKSqxwxac4"
AI_API_URL = "https://token.sensenova.cn/v1/chat/completions"
AI_MODEL = "deepseek-v4-flash"

@app.route('/api/ai_analyze', methods=['POST'])
@login_required
def ai_analyze():
    """AI分析商品数据"""
    data = request.get_json(silent=True) or {}
    products = data.get('products', [])
    time_label = data.get('time_label', '当前周期')

    if not products:
        return jsonify({"error": "无数据可分析"}), 400

    # 构建分析提示词
    prod_lines = []
    for p in products:
        prod_lines.append(
            f"商品ID:{p.get('prod_id','-')} | 标题:{p.get('title','-')} | "
            f"型号:{p.get('model','-')} | 状态:{p.get('status','-')} | "
            f"总GMV:¥{p.get('gmv',0):.2f} | 退款:¥{p.get('refund',0):.2f} | "
            f"去退GMV:¥{p.get('net_gmv',0):.2f} | 广告:¥{p.get('ad_cost',0):.2f} | "
            f"种菜投入:¥{p.get('seed_cost',0):.2f} | 总投入:¥{p.get('total_cost',0):.2f} | "
            f"费比:{p.get('cost_ratio',0):.2f}%"
        )

    prompt = f"""你是一名天猫店铺运营数据分析专家。以下是 {time_label} 的商品数据表格，请进行专业分析。

商品数据（共{len(products)}条）：
{chr(10).join(prod_lines)}

请从以下几个角度进行分析（使用中文，markdown格式）：
1. **整体概况**：总体GMV、去退GMV、总投入、平均费比的概况
2. **盈利/亏损商品**：哪些商品费比过高（>15%），哪些商品表现优秀
3. **广告投放效率**：广告投入与GMV的比例分析
4. **种菜投入分析**：种菜成本是否合理
5. **改进建议**：针对异常商品的具体优化方向

请保持分析简洁精炼，控制在500字以内。"""

    try:
        resp = requests.post(
            AI_API_URL,
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个专业的天猫店铺运营数据分析助手，回复简洁精炼，使用中文。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1500,
            },
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        content = result['choices'][0]['message']['content']
        return jsonify({"analysis": content})
    except Exception as e:
        return jsonify({"error": f"AI分析请求失败: {str(e)}"}), 500


# ── 启动 ──
if __name__ == '__main__':
    print("=" * 50)
    print("  南巢店铺 BI 看板")
    print(f"  数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print("  访问: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
