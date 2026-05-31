#!/usr/bin/env bash
# 导入商品排行Excel到PostgreSQL
source /home/friday/.hermes/hermes-agent/.venv/bin/activate
python /home/friday/.openclaw/skills/input-shangpinpaihang/scripts/import_sycm_sp_all.py /mnt/d/TMNC店铺数据专用文件/店铺-商品排行/ --delete
