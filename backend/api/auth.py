"""
认证API - 登录、注册、用户管理
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from backend.models import db, User, OperationLog
from backend.utils.auth import generate_token, login_required, admin_required

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'})

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify({'code': 401, 'message': '用户名或密码错误'})

    if user.status == 0:
        return jsonify({'code': 403, 'message': '账户已禁用，请联系管理员'})

    # 更新登录时间
    user.last_login = datetime.now()
    db.session.commit()

    # 生成Token
    token = generate_token(user.id, user.username, user.role)

    # 记录日志
    log = OperationLog(username=username, action='登录', detail='用户登录系统',
                       ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()

    return jsonify({
        'code': 200,
        'message': '登录成功',
        'data': {
            'token': token,
            'user': user.to_dict()
        }
    })


@auth_bp.route('/info', methods=['GET'])
@login_required
def get_user_info():
    """获取当前用户信息"""
    from flask import request as req
    username = req.current_user.get('username')
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({'code': 404, 'message': '用户不存在'})
    return jsonify({'code': 200, 'data': user.to_dict()})


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    from flask import request as req
    data = req.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return jsonify({'code': 400, 'message': '密码不能为空'})

    if len(new_password) < 6:
        return jsonify({'code': 400, 'message': '新密码长度不能少于6位'})

    username = req.current_user.get('username')
    user = User.query.filter_by(username=username).first()

    if not user.check_password(old_password):
        return jsonify({'code': 401, 'message': '原密码错误'})

    user.set_password(new_password)
    db.session.commit()

    return jsonify({'code': 200, 'message': '密码修改成功'})


@auth_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """获取用户列表（管理员）"""
    users = User.query.order_by(User.id.desc()).all()
    return jsonify({
        'code': 200,
        'data': [u.to_dict() for u in users]
    })


@auth_bp.route('/users', methods=['POST'])
@admin_required
def create_user():
    """创建用户（管理员）"""
    from flask import request as req
    data = req.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    real_name = data.get('real_name', '')
    role = data.get('role', 'operator')

    if not username or not password:
        return jsonify({'code': 400, 'message': '用户名和密码不能为空'})

    if len(password) < 6:
        return jsonify({'code': 400, 'message': '密码长度不能少于6位'})

    if User.query.filter_by(username=username).first():
        return jsonify({'code': 400, 'message': '用户名已存在'})

    user = User(username=username, real_name=real_name, role=role)
    user.set_password(password)
    db.session.add(user)

    # 日志
    log = OperationLog(
        username=req.current_user.get('username'),
        action='创建用户',
        detail=f'创建用户: {username}',
        ip_address=req.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'code': 200, 'message': '用户创建成功', 'data': user.to_dict()})


@auth_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """更新用户信息（管理员）"""
    from flask import request as req
    user = User.query.get(user_id)
    if user is None:
        return jsonify({'code': 404, 'message': '用户不存在'})

    data = req.get_json()
    if 'real_name' in data:
        user.real_name = data['real_name']
    if 'role' in data:
        user.role = data['role']
    if 'status' in data:
        user.status = data['status']
    if 'password' in data and data['password']:
        user.set_password(data['password'])

    db.session.commit()
    return jsonify({'code': 200, 'message': '更新成功', 'data': user.to_dict()})


@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户（管理员）"""
    from flask import request as req
    user = User.query.get(user_id)
    if user is None:
        return jsonify({'code': 404, 'message': '用户不存在'})

    if user.username == 'admin':
        return jsonify({'code': 400, 'message': '不能删除管理员账户'})

    db.session.delete(user)
    log = OperationLog(
        username=req.current_user.get('username'),
        action='删除用户',
        detail=f'删除用户: {user.username}',
        ip_address=req.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'code': 200, 'message': '删除成功'})
