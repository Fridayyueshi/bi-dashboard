#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品定价模块 — 独立 Flask Blueprint

职责：
  - 提供定价相关 API（目前为占位）
  - 提供定价前端页面路由

迁移：将此文件 + client/modules/pricing/ 一起拷贝到新项目即可独立部署。
"""

from flask import Blueprint, jsonify, send_from_directory
import os

pricing_bp = Blueprint('pricing', __name__,
                       url_prefix='/modules/pricing')

# 前端文件所在目录
PRICING_CLIENT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'client', 'modules', 'pricing'
)


@ pricing_bp.route('/')
def index():
    """定价功能页面"""
    return send_from_directory(PRICING_CLIENT_DIR, 'index.html')


@ pricing_bp.route('/api/status')
def api_status():
    """健康检查 / 占位 API"""
    return jsonify({
        "module": "pricing",
        "status": "developing",
        "message": "商品定价功能开发中"
    })
