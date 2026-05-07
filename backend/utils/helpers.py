"""通用工具函数"""
from datetime import datetime


def parse_date(date_str):
    """安全解析日期字符串"""
    formats = ['%Y-%m-%d', '%Y/%m/%d', '%Y%m%d']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def success_response(data=None, msg='操作成功'):
    """成功响应"""
    resp = {'code': 200, 'msg': msg}
    if data is not None:
        resp['data'] = data
    return resp


def error_response(msg='操作失败', code=400):
    """错误响应"""
    return {'code': code, 'msg': msg}
