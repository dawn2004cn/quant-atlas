"""Page routes: admin domain. Split from pages.py."""

from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    abort,
    render_template,
    request,
)
from flask_login import current_user, login_required
from werkzeug.utils import safe_join

from app.config import BASE_DIR, get_settings
from app.presentation.strategic_sunset_hooks import require_strategic_feature
from app.presentation.web.decorators import admin_required
from app.presentation.web.page_shell import ux_env_hints as _ux_env_hints

def register_pages(blueprint: Blueprint) -> None:
    @blueprint.route("/collaboration")
    @login_required
    @admin_required()
    def collaboration_workspace():
        return render_template("collaboration_workspace.html")

    @blueprint.route("/task-center")
    @login_required
    @admin_required()
    def task_center():
        return render_template("task_center.html")

    @blueprint.route("/alert-center")
    @login_required
    @admin_required()
    def alert_center():
        return render_template("alert_center.html")

    @blueprint.route("/shadow-account")
    @login_required
    @admin_required()
    def shadow_account():
        return render_template("shadow_account.html")

    @blueprint.route("/expert-teams")
    @login_required
    @admin_required()
    def expert_teams():
        return render_template("expert_teams.html")

    @blueprint.route("/run-history")
    @login_required
    @admin_required()
    def run_history():
        return render_template("run_history.html")

    @blueprint.route("/quant-lab")
    @login_required
    @admin_required()
    def quant_lab():
        return render_template("quant_lab.html")

    @blueprint.route("/agent-center")
    @login_required
    @admin_required()
    def agent_center():
        return render_template("agent_center.html")

    @blueprint.route("/swarm-dashboard")
    @login_required
    @admin_required()
    @require_strategic_feature("swarm_topology")
    def swarm_dashboard():
        return render_template("swarm_dashboard.html")

    @blueprint.route("/swarm-designer")
    @login_required
    @admin_required()
    @require_strategic_feature("swarm_topology")
    def swarm_designer():
        return render_template("swarm_designer.html")

    @blueprint.route("/swarm-designer/flow")
    @login_required
    @admin_required()
    @require_strategic_feature("swarm_topology")
    def swarm_designer_flow():
        return render_template("swarm_designer.html")

    @blueprint.route("/research-canvas")
    @login_required
    @admin_required()
    def research_canvas():
        return render_template("research_canvas.html")

    @blueprint.route("/war-room")
    @login_required
    @admin_required()
    @require_strategic_feature("war_room")
    def war_room():
        return render_template("war_room.html")

    @blueprint.route("/voice-briefing")
    @login_required
    def voice_briefing():
        return render_template("voice_briefing.html")

    @blueprint.route("/decision-replay")
    @login_required
    @admin_required()
    @require_strategic_feature("decision_theater")
    def decision_replay_space():
        return render_template("decision_replay_space.html")

    @blueprint.route("/experiment-reporter")
    @login_required
    @admin_required()
    def experiment_reporter():
        return render_template("experiment_reporter.html")

    @blueprint.route("/optimize")
    @login_required
    @admin_required()
    def optimize():
        return render_template("optimize.html")

    @blueprint.route("/stocks-manage")
    @login_required
    @admin_required()
    def stocks_manage():
        if not current_user.can_manage_users():
            abort(403)
        return render_template("stocks_manage.html")

    @blueprint.route("/users-manage")
    @login_required
    @admin_required()
    def users_manage():
        if not current_user.can_manage_users():
            abort(403)
        return render_template("users_manage.html")

    @blueprint.route("/profile")
    @login_required
    def profile():
        settings = get_settings()
        return render_template(
            "profile.html",
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/moments")
    @login_required
    def moments():
        return render_template("moments.html")

    @blueprint.route("/uploads/<path:filename>")
    @login_required
    def uploads(filename: str):
        # 仅用于本项目 instance/uploads 下的用户内容; 避免穿越路径
        from flask import abort as _abort
        from flask import send_from_directory

        root = (get_settings().sqlite_path.parent / "uploads").resolve()
        # 兼容历史错误 URL: /uploads/uploads/moments/...(多一层 uploads)
        fn = (filename or "").lstrip("/").replace("\\", "/")
        if fn.startswith("uploads/"):
            fn = fn[len("uploads/") :]
        # safe_join returns None if unsafe
        safe = safe_join(str(root), fn)
        if not safe:
            _abort(404)
        return send_from_directory(str(root), fn, as_attachment=False)

    @blueprint.route("/retail-assistant")
    @login_required
    def retail_assistant():
        settings = get_settings()
        return render_template(
            "retail_assistant.html",
            ux_env_hints=_ux_env_hints(settings),
        )

    @blueprint.route("/longhu-bang")
    @login_required
    def longhu_bang():
        settings = get_settings()
        return render_template("longhu_bang.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/yanbao-hub")
    @login_required
    def yanbao_hub():
        settings = get_settings()
        return render_template("yanbao_hub.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/message-center")
    @login_required
    def message_center():
        settings = get_settings()
        return render_template("message_center.html", ux_env_hints=_ux_env_hints(settings))

    @blueprint.route("/task/<task_id>")
    @login_required
    def task_detail(task_id: str):
        return render_template("task_detail.html", task_id=task_id)

    @blueprint.route("/avatars/pm/<manager_id>")
    @login_required
    def avatar_pm(manager_id: str):
        from app.core.avatar_svg import build_round_avatar_svg
        from app.infrastructure.repositories.factory import RepositoryType, create_repository

        s = get_settings()
        if s.use_mysql:
            repo = create_repository(RepositoryType.MYSQL, "investment_manager", mysql=s.mysql)
        else:
            repo = create_repository(RepositoryType.SQLITE, "investment_manager", db_path=(BASE_DIR / "instance" / "investment_managers.db").resolve())
        row = repo.get_manager(manager_id)
        label = (row.get("name") if row else "") or manager_id
        svg = build_round_avatar_svg(seed=manager_id, label=str(label))
        return Response(svg, mimetype="image/svg+xml")

    @blueprint.route("/avatars/user")
    @login_required
    def avatar_user():
        from app.core.avatar_svg import build_round_avatar_svg

        uid = str(request.args.get("id") or current_user.id)
        if uid != str(current_user.id):
            abort(403)
        label = current_user.username or uid
        svg = build_round_avatar_svg(seed=f"user:{uid}", label=label)
        return Response(svg, mimetype="image/svg+xml")

