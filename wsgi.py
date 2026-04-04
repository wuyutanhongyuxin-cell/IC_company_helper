"""
WSGI 入口 — Gunicorn / Flask CLI 启动点
用法:
  开发: flask run
  生产: gunicorn -w 2 "wsgi:app"
"""
from app import create_app

app = create_app()
