#!/usr/bin/env python3
"""Fix GBK mojibake and common corruption patterns in HTML templates."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "app" / "presentation" / "web/templates"

# UTF-8 text that was mis-decoded as GBK and saved again (typical garbled syllables)
_MOJIBAKE_RE = re.compile(r"[鑲鏌鍔缂璇绠鐜鈥銆鍛涓鍗棰娴鐜鐩鍊鐜鐜杩鎬鐜鐜鐜鐜]")

# Global replacements (order matters for some patterns)
_GLOBAL_REPLACEMENTS: list[tuple[str, str]] = [
    ("%%}", "%}"),
    ("{% endblock %%}", "{% endblock %}"),
    ("鈫?", "→"),
    ("鈫?", "→"),
    ("&#8594;", "&#8594;"),  # noop anchor
    ("銆?", "。"),
    ("銆?", "。"),
    ("' 浜?", "' 亿'"),
    ("' 涓?", "' 万'"),
    ("+ '浜?", "+ '亿'"),
    ("+ '涓?", "+ '万'"),
    ("+ ' 浜?", "+ ' 亿'"),
    ("+ ' 涓?", "+ ' 万'"),
    ("成交棰?", "成交额"),
    ("换手鐜?", "换手率"),
    ("市盈鐜?", "市盈率"),
    ("市净鐜?", "市净率"),
    ("加载涓?..", "加载中..."),
    ("加载涓?..", "加载中..."),
    ("加载中€?", "加载中..."),
    ("加载中?", "加载中..."),
    ("'鈥?", "'—'"),
    ("'鈥?", "'—'"),
    ("|| '鈥?", "|| '—'"),
    ("=== '鈥?", "=== '—'"),
    ("? '鈥?", "? '—'"),
    ("'鈥? :", "'—' :"),
    ("观察鍗?", "观察单"),
    ("收鐩?", "收益"),
    ("回鎾?", "回撤"),
    ("流动鎬?", "流动性"),
    ("走鍔?", "走势"),
    ("白鐩?", "白盒"),
    ("能鍔?", "能力"),
    ("开鏀?", "开仓"),
    ("状鎬?", "状态"),
    ("盈浜?", "盈亏"),
    ("市鍊?", "市值"),
    ("总成鏈?", "总成本"),
    ("持仓鏁?", "持仓数"),
    ("止鎹?", "止损"),
    ("联鍔?", "联动"),
    ("成鍔?", "成功"),
    ("重璇?", "重试"),
    ("跳杩?", "跳过"),
    ("入场浠?", "入场价"),
    ("当前浠?", "当前价"),
    ("止损浠?", "止损价"),
    ("目标浠?", "目标价"),
    ("跟踪涓?", "跟踪中"),
    ("观察涓?", "观察中"),
    ("计算涓?..", "计算中..."),
    ("鐞?", "理"),
    ("淇?", "讯"),
    ("快鐓?", "快照"),
    ("操盘鍙?", "操盘台"),
    ("依璧?", "依赖"),
    ("基金经鐞?", "基金经理"),
    ("请求浣?", "请求体"),
    ("开鍚?", "开启"),
    ("启鍔?", "启动"),
    ("建璁?", "建议"),
    ("投閫?", "投递"),
    ("涔?", "买"),
    ("鍗?", "卖"),
    ("鏍?", "根"),
    ("K 绾?", "K 线"),
    ("出鐜?", "出现"),
    ("元数据锛?", "元数据，"),
    ("引用）銆?", "引用）。"),
    ("回看銆?", "回看。"),
    ("加载该日股票池銆?", "加载该日股票池。"),
    ("加载该日池子銆?", "加载该日池子。"),
    ("'.join('銆?", "'.join('、"),
    ("请先创建銆?", "请先创建。"),
    ("已登录銆?", "已登录。"),
    ("标记涓?", "标记为"),
    ("写鍥?", "写回"),
    ("文件銆?", "文件。"),
    ("生成銆?", "生成。"),
    ("运行对标銆?", "运行对标。"),
    ("peer 代码銆?", "peer 代码。"),
    ("刷新重璇?", "刷新重试"),
    ("加载失败，可刷新重璇?", "加载失败，可刷新重试"),
    ("请稍后重璇?", "请稍后重试"),
    ("分浜?", "分享"),
    ("评鍒?", "评分"),
    ("提示锛?", "提示："),
    ("闈?", "非"),
    ("定心丸锛?", "定心丸："),
    ("走势涓?", "走势与"),
    ("均鍊?", "均值"),
    ("营鏀?", "营收"),
    ("公允鎬?", "公允性"),
    ("股涓?", "股东"),
    ("维鎬?", "维持"),
    ("总资浜?", "总资产"),
    ("现金娴?", "现金流"),
    ("1.2浜?", "1.2亿"),
    ("角色视图锛?", "角色视图："),
    (" 涓?", " 个"),
    ("命中鐜?", "命中率"),
    ("触发率锛?", "触发率："),
    ("均鍊?", "均值"),
    ("分析涓?", "分析中"),
    ("验证銆?", "验证。"),
    ("后再执行銆?", "后再执行。"),
    ("涨股姣?", "涨股比"),
    ("娑?璺?", "涨跌"),
    ("涨跌骞?", "涨跌幅"),
    ("汇鎬?", "汇总"),
    (" 涓?·", " 只 ·"),
    ("请先入库銆?", "请先入库。"),
    ("对照銆?", "对照。"),
    ("环境」銆?", "环境」。"),
    ("复盘銆?", "复盘。"),
    ("坚持理性复盘銆?", "坚持理性复盘。"),
    ("胜率涓?", "胜率为"),
    ("触发鐜?", "触发率"),
    ("批量添加銆?", "批量添加。"),
    ("请确认已登录銆?", "请确认已登录。"),
    ("稍后再试銆?", "稍后再试。"),
    ("加入銆?", "加入。"),
    ("再对照操盘台复盘銆?", "再对照操盘台复盘。"),
    ("只看环境」銆?", "只看环境」。"),
    ("证鏄?", "证明"),
    ("对比收鐩?", "对比收益"),
    ("怎么鍔?", "怎么办"),
    ("机浼?", "机会"),
    ("收鐩?", "收益"),
    ("最大回鎾?", "最大回撤"),
    ("买入鍚?", "买入后"),
    ("收鐩?", "收益"),
]

# Broken closing tags: 管理员?/span> -> 管理员</span>
_BROKEN_CLOSE_TAG = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9%])\?/(span|p|div|th|td|tr|strong|h[1-6]|label|option|button|a)>"
)


def _looks_mojibake(line: str) -> bool:
    return bool(_MOJIBAKE_RE.search(line))


_ARROW_PH = "\uE000"
_ELLIPSIS_PH = "\uE001"
_EM_DASH_PH = "\uE002"


def _fix_line_gbk(line: str) -> str:
    if not _looks_mojibake(line):
        return line
    temp = (
        line.replace("→", _ARROW_PH)
        .replace("…", _ELLIPSIS_PH)
        .replace("—", _EM_DASH_PH)
        .replace("·", "·")
    )
    try:
        fixed = temp.encode("gbk").decode("utf-8")
        return (
            fixed.replace(_ARROW_PH, "→")
            .replace(_ELLIPSIS_PH, "…")
            .replace(_EM_DASH_PH, "—")
        )
    except (UnicodeDecodeError, UnicodeEncodeError):
        return line


_POST_REPLACEMENTS: list[tuple[str, str]] = [
    ("璇曡瘯鏂扮増", "试试新版"),
    ("观察鑲", "观察股"),
    ("成分鑲", "成分股"),
    ('<option value="CN" selected>A鑲</option>', '<option value="CN" selected>A股</option>'),
    (" 鑲</div>", " 股</div>"),
    (" 鑲? +", " 股' +"),
    ("入库中鈥?", "入库中…"),
    ("请稍候鈥?", "请稍候…"),
    ("任务已提浜?", "任务已提交"),
    ("归母净利润(涓?", "归母净利润(万"),
    ("营业总收鍏?涓?", "营业总收入(万"),
    ("总资产涓?", "总资产(万"),
    ("总负鍊?涓?", "总负债(万"),
    ("股东权益(涓?", "股东权益(万"),
    ("经营现金流涓?", "经营现金流(万"),
    ("投资现金流涓?", "投资现金流(万"),
    ("筹资现金流涓?", "筹资现金流(万"),
    ("severity: '涓?", "severity: '中'"),
    ("severity: '楂?", "severity: '高'"),
    ("=== '楂?", "=== '高'"),
    ("=== '涓?", "=== '中'"),
    ("站涓?20", "站上20"),
    ("技术指根,", "技术指标',"),
    ("当鍓?settings", "当前 settings"),
    ("备份涓?.bak", "备份为 .bak"),
    ("还有 ${items.length - 200} 个/span>", "还有 ${items.length - 200} 个</span>"),
    ("成分鑲?·", "成分股 ·"),
]


def fix_content(text: str) -> str:
    text = text.replace("\ufeff", "")
    for old, new in _GLOBAL_REPLACEMENTS:
        text = text.replace(old, new)
    lines = []
    for line in text.splitlines(keepends=True):
        fixed = _fix_line_gbk(line.rstrip("\n\r"))
        if not line.endswith("\n") and not line.endswith("\r"):
            lines.append(fixed)
        else:
            ending = "\n" if line.endswith("\n") else ""
            lines.append(fixed + ending)
    text = "".join(lines)
    text = _BROKEN_CLOSE_TAG.sub(r"\1</\2>", text)
    text = re.sub(r"€\?/(span|p|div|th|td)>", r"</\1>", text)
    text = re.sub(r"€/(span|p|div|th|td)>", r"</\1>", text)
    for old, new in _POST_REPLACEMENTS:
        text = text.replace(old, new)
    # Broken JS object keys from partial mojibake (unclosed quotes)
    text = text.replace("营业收鍏?,", "营业收入',")
    text = text.replace("净资产收益鐜?,", "净资产收益率',")
    text = text.replace("营业利润鐜?,", "营业利润率',")
    text = text.replace("成本费用利润鐜?%)", "成本费用利润率%)")
    text = text.replace("应收帐款周转鐜?,", "应收帐款周转率',")
    text = text.replace("存货周转鐜?,", "存货周转率',")
    text = text.replace("流动资产周转鐜?,", "流动资产周转率',")
    text = text.replace("固定资产周转鐜?,", "固定资产周转率',")
    text = text.replace("股东权益周转鐜?,", "股东权益周转率',")
    text = text.replace("营业收入增长鐜?%)", "营业收入增长率%)")
    text = text.replace("净利润增长鐜?%)", "净利润增长率%)")
    text = text.replace("净资产增长鐜?%)", "净资产增长率%)")
    text = text.replace("营业利润增长鐜?%)", "营业利润增长率%)")
    text = text.replace("经营活动产生的现金流量净棰?,", "经营活动产生的现金流量净额',")
    text = text.replace("投资活动产生的现金流量净棰?,", "投资活动产生的现金流量净额',")
    text = text.replace("筹资活动产生的现金流量净棰?,", "筹资活动产生的现金流量净额',")
    text = text.replace("全部资产现金回收鐜?,", "全部资产现金回收率',")
    text = text.replace("扣除非经常性损益每股收鐩?,", "扣除非经常性损益每股收益',")
    text = text.replace("负债合璁?,", "负债合计',")
    return text


def main() -> int:
    changed: list[str] = []
    for html_file in sorted(TEMPLATES.rglob("*.html")):
        original = html_file.read_text(encoding="utf-8")
        fixed = fix_content(original)
        if fixed != original:
            html_file.write_text(fixed, encoding="utf-8")
            changed.append(str(html_file.relative_to(ROOT)))
    report = ROOT / "scripts" / "html_mojibake_fix_report.txt"
    report.write_text(
        f"Fixed {len(changed)} files\n" + "\n".join(changed),
        encoding="utf-8",
    )
    print(f"Fixed {len(changed)} HTML files. Report: {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
