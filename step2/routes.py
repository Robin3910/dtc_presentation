# -*- coding: utf-8 -*-
"""
Web 路由模块：处理所有 HTTP 请求
"""

import os
import logging
import mimetypes
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from functools import wraps

from flask import (
    Blueprint, request, jsonify, render_template, 
    send_from_directory, redirect, url_for, session, flash, Response
)
from werkzeug.utils import secure_filename

from config import (
    UPLOADS_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, MAX_FILES_PER_UPLOAD,
    ADMIN_USERNAME, ADMIN_PASSWORD, DEBUG_MODE,
    HOST, PORT,
)
from database import Database
from cloud_storage import get_storage_instance
from review_scheduler import ReviewScheduler

logger = logging.getLogger(__name__)

# 创建 Flask Blueprint
main_bp = Blueprint("main", __name__)
api_bp = Blueprint("api", __name__, url_prefix="/api")

# 全局实例
db = Database()
storage = get_storage_instance()
scheduler: Optional[ReviewScheduler] = None


def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("logged_in"):
            return f(*args, **kwargs)
        return redirect(url_for("main.login_page"))
    return decorated_function


# ── 页面路由 ─────────────────────────────────────────────

@main_bp.route("/")
def index():
    """首页 / 上传页面"""
    return render_template("upload.html")


@main_bp.route("/login")
def login_page():
    """登录页面"""
    if session.get("logged_in"):
        return redirect(url_for("main.admin_dashboard"))
    return render_template("login.html")


@main_bp.route("/admin")
@login_required
def admin_dashboard():
    """管理后台首页"""
    stats = db.get_statistics()
    recent_reviews = db.get_reviews(limit=10)
    recent_materials = db.get_materials(limit=10)
    
    return render_template(
        "dashboard.html",
        stats=stats,
        recent_reviews=recent_reviews,
        recent_materials=recent_materials,
    )


@main_bp.route("/admin/materials")
@login_required
def admin_materials():
    """素材管理页面"""
    status_filter = request.args.get("status", "")
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page
    
    materials = db.get_materials(status=status_filter if status_filter else None, 
                                  limit=per_page, offset=offset)
    total = db.get_material_count(status=status_filter if status_filter else None)
    total_pages = (total + per_page - 1) // per_page
    
    return render_template(
        "materials.html",
        materials=materials,
        status_filter=status_filter,
        page=page,
        total_pages=total_pages,
        total=total,
    )


@main_bp.route("/admin/reviews")
@login_required
def admin_reviews():
    """审核记录页面"""
    result_filter = request.args.get("result", "")
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page
    
    reviews = db.get_reviews(result=result_filter if result_filter else None,
                               limit=per_page, offset=offset)
    
    return render_template(
        "reviews.html",
        reviews=reviews,
        result_filter=result_filter,
        page=page,
    )


@main_bp.route("/admin/material/<int:material_id>")
@login_required
def admin_material_detail(material_id: int):
    """素材详情页面"""
    material = db.get_material(material_id)
    if not material:
        return "素材不存在", 404
    
    review = db.get_review(material_id)
    
    # 获取文件 URL
    if material.get("cloud_path"):
        file_url = storage.get_file_url(material["cloud_path"])
    else:
        file_url = f"/uploads/{material['filename']}"
    
    return render_template(
        "material_detail.html",
        material=material,
        review=review,
        file_url=file_url,
    )


# ── 认证 API ─────────────────────────────────────────────

@api_bp.route("/auth/login", methods=["POST"])
def api_login():
    """登录接口"""
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["logged_in"] = True
        session["username"] = username
        db.add_log("login", username, details="用户登录", ip_address="")
        return jsonify({"success": True, "message": "登录成功"})
    
    return jsonify({"success": False, "message": "用户名或密码错误"}), 401


@api_bp.route("/auth/logout", methods=["POST"])
def api_logout():
    """登出接口"""
    username = session.get("username", "unknown")
    session.clear()
    db.add_log("logout", username, details="用户登出", ip_address="")
    return jsonify({"success": True, "message": "已退出登录"})


@api_bp.route("/auth/status", methods=["GET"])
def api_auth_status():
    """检查登录状态"""
    return jsonify({"logged_in": session.get("logged_in", False)})


# ── 素材上传 API ─────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.route("/upload", methods=["POST"])
def api_upload():
    """素材上传接口"""
    try:
        # 获取上传者信息
        uploader_email = request.form.get("email", "")
        uploader_name = request.form.get("name", "")
        description = request.form.get("description", "")
        
        # 检查是否有文件
        if "files" not in request.files:
            return jsonify({"success": False, "message": "没有上传文件"}), 400
        
        files = request.files.getlist("files")
        
        if not files or all(f.filename == "" for f in files):
            return jsonify({"success": False, "message": "没有选择文件"}), 400
        
        # 检查文件数量
        if len(files) > MAX_FILES_PER_UPLOAD:
            return jsonify({
                "success": False, 
                "message": f"一次最多上传 {MAX_FILES_PER_UPLOAD} 个文件"
            }), 400
        
        uploaded_materials = []
        errors = []
        
        for file in files:
            if file.filename == "":
                continue
            
            if not allowed_file(file.filename):
                errors.append(f"{file.filename}: 不支持的文件类型")
                continue
            
            # 检查文件大小
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            max_size = MAX_FILE_SIZE_MB * 1024 * 1024
            if file_size > max_size:
                errors.append(f"{file.filename}: 文件大小超过 {MAX_FILE_SIZE_MB}MB 限制")
                continue
            
            # 保存文件
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{timestamp}_{original_filename}"
            
            file_path = UPLOADS_DIR / unique_filename
            file.save(str(file_path))
            
            # 获取 MIME 类型
            mime_type = mimetypes.guess_type(original_filename)[0] or "application/octet-stream"
            
            # 保存到数据库
            material_id = db.add_material(
                filename=unique_filename,
                original_filename=original_filename,
                file_path=str(file_path),
                file_size=file_size,
                mime_type=mime_type,
                uploader_email=uploader_email,
                uploader_name=uploader_name,
            )
            
            # 尝试上传到云存储
            cloud_path = f"materials/{unique_filename}"
            if storage.upload_file(file_path, cloud_path):
                db.update_material_status(material_id, "uploaded", cloud_path=cloud_path)
            else:
                db.update_material_status(material_id, "uploaded")
            
            uploaded_materials.append({
                "id": material_id,
                "filename": original_filename,
                "size": file_size,
            })
            
            # 记录操作日志
            db.add_log(
                "upload", 
                operator=uploader_email or "anonymous",
                target_id=material_id,
                target_type="material",
                details=f"上传文件: {original_filename}",
                ip_address=request.remote_addr or "",
            )
            
            logger.info(f"✅ 文件上传成功：{original_filename} -> ID: {material_id}")
        
        # 触发审核（如果启用自动审核）
        if uploaded_materials and scheduler and scheduler._running:
            scheduler.trigger_review(uploaded_materials[0]["id"])
        


        response = {
            "success": True,
            "message": f"成功上传 {len(uploaded_materials)} 个文件",
            "uploaded": uploaded_materials,
        }
        
        if errors:
            response["errors"] = errors
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"上传失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@api_bp.route("/materials", methods=["GET"])
@login_required
def api_get_materials():
    """获取素材列表（API）"""
    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    offset = (page - 1) * per_page
    
    materials = db.get_materials(status=status, limit=per_page, offset=offset)
    total = db.get_material_count(status=status)
    
    # 补充文件 URL
    for m in materials:
        if m.get("cloud_path"):
            m["file_url"] = storage.get_file_url(m["cloud_path"])
        else:
            m["file_url"] = f"/uploads/{m['filename']}"
    
    return jsonify({
        "success": True,
        "materials": materials,
        "total": total,
        "page": page,
        "per_page": per_page,
    })


@api_bp.route("/materials/<int:material_id>", methods=["GET"])
@login_required
def api_get_material(material_id: int):
    """获取单个素材详情"""
    material = db.get_material(material_id)
    if not material:
        return jsonify({"success": False, "message": "素材不存在"}), 404
    
    # 获取审核结果
    review = db.get_review(material_id)
    
    # 获取文件 URL
    if material.get("cloud_path"):
        file_url = storage.get_file_url(material["cloud_path"])
    else:
        file_url = f"/uploads/{material['filename']}"
    
    return jsonify({
        "success": True,
        "material": material,
        "review": review,
        "file_url": file_url,
    })


@api_bp.route("/materials/<int:material_id>", methods=["DELETE"])
@login_required
def api_delete_material(material_id: int):
    """删除素材"""
    material = db.get_material(material_id)
    if not material:
        return jsonify({"success": False, "message": "素材不存在"}), 404
    
    # 删除云端文件
    if material.get("cloud_path"):
        storage.delete_file(material["cloud_path"])
    
    # 删除本地文件
    file_path = Path(material["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    # 删除数据库记录（硬删除）
    db.delete_material(material_id)
    
    # 记录操作日志
    db.add_log(
        "delete",
        operator=session.get("username", "unknown"),
        target_id=material_id,
        target_type="material",
        details=f"删除素材: {material['filename']}",
        ip_address=request.remote_addr or "",
    )
    
    return jsonify({"success": True, "message": "素材已删除"})


@api_bp.route("/materials/<int:material_id>/review", methods=["POST"])
@login_required
def api_trigger_review(material_id: int):
    """手动触发素材审核"""
    if not scheduler:
        return jsonify({"success": False, "message": "审核服务未启动"}), 500
    
    try:
        scheduler.trigger_review(material_id)
        return jsonify({"success": True, "message": "审核任务已触发"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── 审核 API ─────────────────────────────────────────────

@api_bp.route("/reviews", methods=["GET"])
@login_required
def api_get_reviews():
    """获取审核记录列表"""
    result = request.args.get("result")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    offset = (page - 1) * per_page
    
    reviews = db.get_reviews(result=result, limit=per_page, offset=offset)
    
    return jsonify({
        "success": True,
        "reviews": reviews,
        "page": page,
        "per_page": per_page,
    })


@api_bp.route("/reviews/<int:material_id>", methods=["GET"])
@login_required
def api_get_review(material_id: int):
    """获取素材的审核结果"""
    review = db.get_review(material_id)
    if not review:
        return jsonify({"success": False, "message": "暂无审核结果"}), 404
    
    return jsonify({
        "success": True,
        "review": review,
    })


# ── 统计 API ─────────────────────────────────────────────

@api_bp.route("/statistics", methods=["GET"])
@login_required
def api_get_statistics():
    """获取统计数据"""
    stats = db.get_statistics()
    return jsonify({
        "success": True,
        "statistics": stats,
    })


# ── 调度器 API ─────────────────────────────────────────────

@api_bp.route("/scheduler/status", methods=["GET"])
@login_required
def api_scheduler_status():
    """获取调度器状态"""
    if not scheduler:
        return jsonify({
            "success": True,
            "running": False,
            "message": "调度器未初始化",
        })
    
    return jsonify({
        "success": True,
        "running": scheduler._running,
        "pending_count": len(db.get_pending_materials()),
    })


@api_bp.route("/scheduler/start", methods=["POST"])
@login_required
def api_scheduler_start():
    """启动调度器"""
    if not scheduler:
        return jsonify({"success": False, "message": "调度器未初始化"}), 500
    
    if scheduler._running:
        return jsonify({"success": True, "message": "调度器已在运行中"})
    
    scheduler.start()
    return jsonify({"success": True, "message": "调度器已启动"})


@api_bp.route("/scheduler/stop", methods=["POST"])
@login_required
def api_scheduler_stop():
    """停止调度器"""
    if not scheduler:
        return jsonify({"success": False, "message": "调度器未初始化"}), 500
    
    scheduler.stop()
    return jsonify({"success": True, "message": "调度器已停止"})


@api_bp.route("/scheduler/trigger", methods=["POST"])
@login_required
def api_scheduler_trigger():
    """手动触发所有待审核素材的审核"""
    if not scheduler:
        return jsonify({"success": False, "message": "调度器未初始化"}), 500
    
    try:
        scheduler.trigger_review_all()
        return jsonify({"success": True, "message": "审核任务已触发"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ── 文件服务 ─────────────────────────────────────────────

@main_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    """提供上传文件的访问"""
    return send_from_directory(UPLOADS_DIR, filename)


@main_bp.route("/reports/<path:filename>")
@login_required
def serve_report(filename):
    """提供报告文件的访问"""
    from config import REPORTS_DIR
    return send_from_directory(REPORTS_DIR, filename)


def init_scheduler(s: ReviewScheduler):
    """初始化调度器实例"""
    global scheduler
    scheduler = s
