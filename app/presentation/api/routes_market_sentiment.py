"""Market Sentiment API Routes."""











from __future__ import annotations

from flask import Blueprint

from app.application.errors import ExternalServiceError
from app.core.registry import register_routes

from .common import ok_response

sentiment_bp = Blueprint("sentiment", __name__, url_prefix="/sentiment")

















@sentiment_bp.route("/diary", methods=["GET"])





def get_market_diary():





    """Get daily market diary."""





    try:





        from app.modules.market_data.services.sentiment_radar import SentimentRadar











        radar = SentimentRadar()











        market_data = {





            "index_change": 0.85,





            "volume_change": 15,





            "hot_sectors": ["New Energy", "AI", "Semiconductors"],





            "events": ["Central Bank Rate Cut", "CPI Data Release"],





            "sector_sentiment": {"New Energy": "bullish", "Banking": "neutral"},





        }











        diary = radar.generate_market_diary(market_data)











        return ok_response(





            data={





                "date": diary.date.isoformat(),





                "overall_sentiment": diary.overall_sentiment,





                "summary": diary.summary,





                "key_events": diary.key_events,





                "sector_sentiment": diary.sector_sentiment,





            },





        )





    except Exception as exc:





        raise ExternalServiceError(





            "market_diary_failed",





            details={"reason": str(exc)},





        ) from exc

















@sentiment_bp.route("/pulses", methods=["GET"])





def get_sentiment_pulses():





    """Get current sentiment pulses."""





    try:





        from app.modules.market_data.services.sentiment_radar import SentimentRadar











        radar = SentimentRadar()











        stocks = [





            {"symbol": "600519", "name": "Kweichow Moutai", "change_pct": 5.2, "volume_ratio": 2.5},





            {"symbol": "300750", "name": "Contemporary Amperex", "change_pct": -3.5, "volume_ratio": 3.0},





            {"symbol": "000858", "name": "Wuliangye", "change_pct": 3.8, "volume_ratio": 1.8},





            {"symbol": "688111", "name": "Kingsoft Office", "change_pct": 12.5, "volume_ratio": 4.2},





        ]











        pulses = radar.check_for_pulses(stocks, [])











        return ok_response(





            data=[





                {





                    "symbol": p.symbol,





                    "name": p.name,





                    "pulse_type": p.pulse_type,





                    "sentiment_score": p.sentiment_score,





                    "velocity": p.velocity,





                    "trigger_reason": p.trigger_reason,





                    "timestamp": p.timestamp.isoformat(),





                }





                for p in pulses





            ],





        )





    except Exception as exc:





        raise ExternalServiceError(





            "sentiment_pulses_failed",





            details={"reason": str(exc)},





        ) from exc

















@register_routes(name="sentiment", context="market_data", description="Market sentiment diary and pulses")





def register_sentiment_routes(blueprint, ctx=None) -> None:





    """Register sentiment routes."""





    blueprint.register_blueprint(sentiment_bp)
    alias_bp = Blueprint("market_sentiment_alias", __name__, url_prefix="/market/sentiment")
    alias_bp.add_url_rule("/diary", view_func=get_market_diary, methods=["GET"])
    alias_bp.add_url_rule("/pulses", view_func=get_sentiment_pulses, methods=["GET"])
    blueprint.register_blueprint(alias_bp)





