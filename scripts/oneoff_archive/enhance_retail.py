import json, sys
PATH = "E:/project/workspace/myrepo/quant-atlas/app/modules/user/services/retail_tier_service.py"

with open(PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

psych_end = None
copy_end = None

for i, l in enumerate(lines):
    if "def _load_events" in l:
        j = i + 1
        while j < len(lines) and (lines[j].startswith((" ", "\t")) or lines[j].strip() == ""):
            j += 1
        psych_end = j
    if "def _save_signal" in l:
        j = i + 1
        while j < len(lines) and (lines[j].startswith((" ", "\t")) or lines[j].strip() == ""):
            j += 1
        copy_end = j

print(f"psych_end={psych_end}, copy_end={copy_end}")

new_psy = [
    "\n",
    "    def get_insights(self, user_id, days=30):\n",
    '        """Analyze trading psychology patterns."""\n',
    "        events = self._load_events(user_id, days)\n",
    "        if not events:\n",
    '            return {"insights": [], "risk_level": "unknown", "suggestions": []}\n',
    "\n",
    "        panic_sells = [e for e in events if e.event_type == 'panic_sell']\n",
    "        revenge_trades = [e for e in events if e.event_type == 'revenge_trade']\n",
    "        over_trades = [e for e in events if e.event_type == 'over_trade']\n",
    "        total = len(events)\n",
    "        panic_pct = len(panic_sells) / max(total, 1)\n",
    "        revenge_pct = len(revenge_trades) / max(total, 1)\n",
    "\n",
    "        if panic_pct > 0.3 or revenge_pct > 0.2:\n",
    '            risk_level = "high"\n',
    "        elif panic_pct > 0.15 or revenge_pct > 0.1:\n",
    '            risk_level = "medium"\n',
    "        else:\n",
    '            risk_level = "low"\n',
    "\n",
    "        insights = []\n",
    "        if panic_pct > 0.3:\n",
    '            insights.append("Frequent panic selling detected")\n',
    "        if revenge_pct > 0.2:\n",
    '            insights.append("Revenge trading pattern detected")\n',
    "        if len(over_trades) > 5:\n",
    '            insights.append("Over-trading pattern detected")\n',
    "\n",
    "        suggestions = []\n",
    '        if risk_level == "high":\n',
    '            suggestions.append("Reduce position size to 50% for 1 week")\n',
    '            suggestions.append("Set daily loss limit to 2% of portfolio")\n',
    '        elif risk_level == "medium":\n',
    '            suggestions.append("Review trade journal before each session")\n',
    "\n",
    "        return {\n",
    '            "total_events": total,\n',
    '            "risk_level": risk_level,\n',
    '            "panic_sell_count": len(panic_sells),\n',
    '            "revenge_trade_count": len(revenge_trades),\n',
    '            "over_trade_count": len(over_trades),\n',
    '            "insights": insights,\n',
    '            "suggestions": suggestions,\n',
    '            "analyzed_period_days": days,\n',
    "        }\n",
]

new_copy = [
    "\n",
    "    def get_provider_rating(self, provider_id):\n",
    '        """Calculate performance rating for a signal provider."""\n',
    "        signals = []\n",
    "        if self._signals_file.exists():\n",
    '            with self._signals_file.open("r", encoding="utf-8") as fh:\n',
    "                for line in fh:\n",
    "                    if not line.strip():\n",
    "                        continue\n",
    "                    sig = json.loads(line)\n",
    "                    if sig.get('provider_id') == provider_id:\n",
    "                        signals.append(sig)\n",
    "\n",
    "        total = len(signals)\n",
    "        if total == 0:\n",
    '            return {"provider_id": provider_id, "total_signals": 0, "rating": "unrated"}\n',
    "\n",
    "        wins = [s for s in signals if s.get('outcome') == 'win']\n",
    "        win_rate = len(wins) / total\n",
    "\n",
    "        recent = signals[-20:]\n",
    "        recent_wins = sum(1 for s in recent if s.get('outcome') == 'win')\n",
    "        recent_win_rate = recent_wins / max(len(recent), 1)\n",
    "\n",
    '        if win_rate >= 0.6 and recent_win_rate >= 0.55: rating = "A"\n',
    '        elif win_rate >= 0.5: rating = "B"\n',
    '        elif win_rate >= 0.4: rating = "C"\n',
    '        else: rating = "D"\n',
    "\n",
    "        return {\n",
    '            "provider_id": provider_id,\n',
    '            "total_signals": total,\n',
    '            "win_rate": round(win_rate, 4),\n',
    '            "recent_win_rate": round(recent_win_rate, 4),\n',
    '            "rating": rating,\n',
    '            "total_wins": len(wins),\n',
    '            "total_losses": total - len(wins),\n',
    "        }\n",
]

lines[psych_end:psych_end] = new_psy
lines[copy_end:copy_end] = new_copy

with open(PATH, "w", encoding="utf-8") as f:
    f.writelines(lines)

import py_compile
py_compile.compile(PATH, doraise=True)
print(f"Written {len(lines)} lines, compiles OK!")
