#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Legacy archive entrypoint.
# The active application entrypoint is ``run.py`` with the Flask app factory in
# ``app/bootstrap.py``. Keep this file only for migration reference.
"""
A股量化监控系统 - Web界面
Flask + ECharts
"""
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, Blueprint
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from backtest_engine import BacktestEngine
from cache_factory import CacheFactory
import json
import hashlib
import requests
import threading
import time
from functools import wraps

from realtime_reader import yFinanceRealTimeReader
# 导入服务容器
from services.service_container import service_container
from scripts.tdx.tdx_connect_manager import TdxConnectionManager

# 从服务容器获取服务实例
stock_service = service_container.get_stock_service()
watchlist_service = service_container.get_watchlist_service()
user_service = service_container.get_user_service()
market_service = service_container.get_market_service()
selector_service = service_container.get_selector_service()

# 创建Flask应用
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'  # 生产环境请修改

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')
auth_bp = Blueprint('auth', __name__)
main_bp = Blueprint('main', __name__)

# 登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = '请先登录'

tdx = TdxConnectionManager()

# 初始化数据读取器
yf_reader = yFinanceRealTimeReader()

# 实例化全局单例
# 用户模型
class User(UserMixin):
    def __init__(self, id, username, role='viewer'):
        self.id = id
        self.username = username
        self.role = role
    
    def has_permission(self, permission):
        """检查是否有某个权限"""
        roles = user_service.roles
        return permission in roles.get(self.role, {}).get('permissions', [])
    
    def can_delete(self):
        """是否可以删除"""
        return self.has_permission('delete')
    
    def can_create(self):
        """是否可以新增"""
        return self.has_permission('create')
    
    def can_update(self):
        """是否可以修改"""
        return self.has_permission('update')
    
    def can_manage_users(self):
        """是否可以管理用户"""
        return self.has_permission('manage_users')
    
    def can_change_password(self, target_user=None):
        """是否可以修改密码"""
        if self.has_permission('change_all_passwords'):
            return True  # 管理员可以改所有人
        if self.has_permission('change_own_password') and target_user == self.username:
            return True  # 可以改自己的
        return False

# 用户数据（生产环境应该存储在数据库）
USERS = user_service.get_users()

@login_manager.user_loader
def load_user(user_id):
    for username, data in USERS.items():
        if data['id'] == int(user_id):
            return User(user_id, username, data.get('role', 'viewer'))
    return None

# 权限装饰器
def permission_required(permission):
    """权限检查装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if not current_user.has_permission(permission):
                return jsonify({'status': 'error', 'message': '权限不足'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 监控的核心股票
WATCHED_STOCKS = watchlist_service.get_watchlist() or [
    # 高波动股票（新增）
    '600276',  # 恒瑞医药
    '601012',  # 隆基绿能
    '000858',  # 五粮液
    '601888',  # 中国中免
    # 原有优质股票（保留）
    '600036',  # 招商银行
    '601318',  # 中国平安
    '600519',  # 贵州茅台
    # 移除低波动电力股，保留1只代表
    '601985',  # 中国核电（代表）
]

# 保存监控列表
watchlist_service.save_watchlist(WATCHED_STOCKS)


# ============== 登录路由 ==============

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash == USERS[username]['password']:
                user = User(USERS[username]['id'], username, USERS[username].get('role', 'viewer'))
                login_user(user, remember=True)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.index'))
        
        return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """登出"""
    logout_user()
    return redirect(url_for('auth.login'))


# ============== 页面路由 ==============

@main_bp.route('/')
@login_required
def index():
    """首页 - 仪表盘"""
    # 异步更新全市场数据
    def update_market_data_async():
        try:
            from stock_async_fetcher import fetch_all_market
            fetch_all_market()
        except Exception as e:
            print(f"异步更新全市场数据失败: {e}")
    
    # 启动后台线程更新全市场数据
    thread = threading.Thread(target=update_market_data_async)
    thread.daemon = True
    thread.start()
    
    return render_template('index.html', username=current_user.username)


@main_bp.route('/stock/<code>')
@login_required
def stock_detail(code):
    """股票详情页"""
    return render_template('stock_detail.html', code=code)


@main_bp.route('/backtest')
@login_required
def backtest_page():
    """回测工具页"""
    return render_template('backtest.html')


@main_bp.route('/optimize')
@login_required
def optimize_page():
    """参数优化页"""
    return render_template('optimize.html')


@main_bp.route('/stocks-manage')
@login_required
def stocks_manage_page():
    """股票池管理页"""
    return render_template('stocks_manage.html')


@main_bp.route('/users-manage')
@login_required
def users_manage_page():
    """用户管理页"""
    if not current_user.can_manage_users():
        return redirect(url_for('main.index'))
    return render_template('users_manage.html')


@main_bp.route('/profile')
@login_required
def profile_page():
    """个人设置页"""
    return render_template('profile.html')


@main_bp.route('/market-panorama')
@login_required
def market_panorama_page():
    """市场全景页"""
    return render_template('market_panorama.html')


@main_bp.route('/self-stocks')
@login_required
def self_stocks_page():
    """自选股页面"""
    return render_template('self_stocks.html')


# ============== API接口 ==============

@api_bp.route('/stocks')
@login_required
def api_stocks():
    """获取所有监控股票（优先返回缓存数据，同时异步更新）"""
    # 先从服务获取数据
    stocks = stock_service.get_stocks(WATCHED_STOCKS)
    
    # 异步更新数据
    def update_data_async():
        try:
            from stock_async_fetcher import StockAsyncFetcher
            fetcher = StockAsyncFetcher()
            fetcher.fetch_and_cache(WATCHED_STOCKS)
            fetcher.close()
        except Exception as e:
            print(f"异步更新数据失败: {e}")
    
    # 启动后台线程更新数据
    thread = threading.Thread(target=update_data_async)
    thread.daemon = True
    thread.start()
    
    
    return jsonify({
        'status': 'success',
        'data': stocks,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'async_updating': True
    })


@api_bp.route('/stocks/realtime')
@login_required
def api_stocks_realtime():
    """获取监控股票的实时价格（轻量级，仅价格和涨跌）"""
    # 先从服务获取数据
    stocks = stock_service.get_stocks_realtime(WATCHED_STOCKS)
    
    # 异步更新数据
    def update_data_async():
        try:
            from stock_async_fetcher import StockAsyncFetcher
            fetcher = StockAsyncFetcher()
            fetcher.fetch_and_cache(WATCHED_STOCKS)
            fetcher.close()
        except Exception as e:
            print(f"异步更新数据失败: {e}")
    
    # 启动后台线程更新数据
    thread = threading.Thread(target=update_data_async)
    thread.daemon = True
    thread.start()
    
    
    return jsonify({
        'status': 'success',
        'data': stocks,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'async_updating': True
    })


@api_bp.route('/stock/<code>')
@login_required
def api_stock_detail(code):
    """获取单只股票详情"""
    # 从服务获取股票详情
    stock = stock_service.get_stock_detail(code)
    if not stock:
        return jsonify({'status': 'error', 'message': '股票不存在'})
    
    return jsonify({
        'status': 'success',
        'data': stock
    })


@api_bp.route('/history/<code>')
@login_required
def api_history(code):
    """获取历史K线数据"""
    days = request.args.get('days', 60, type=int)
    
    from tech_indicators import TechIndicatorCalculator
    calc = TechIndicatorCalculator()
    
    history = calc.get_stock_history(code, days=days)
    
    if history is None:
        return jsonify({'status': 'error', 'message': '获取历史数据失败'})
    
    # 转换为ECharts需要的格式
    data = []
    for date, row in history.iterrows():
        data.append({
            'date': date.strftime('%Y-%m-%d'),
            'open': float(row['open']),
            'close': float(row['close']),
            'high': float(row['high']),
            'low': float(row['low']),
            'volume': float(row['volume'])
        })
    
    return jsonify({
        'status': 'success',
        'data': data
    })


@api_bp.route('/backtest', methods=['POST'])
@login_required
def api_backtest():
    """回测接口"""
    try:
        data = request.json
        
        symbol = data.get('symbol')
        strategy = data.get('strategy')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_capital = data.get('initial_capital', 100000)
        
        print(f"回测参数: symbol={symbol}, strategy={strategy}, start_date={start_date}, end_date={end_date}, initial_capital={initial_capital}")
        
        if not all([symbol, strategy, start_date, end_date]):
            print("参数不完整")
            return jsonify({'status': 'error', 'message': '参数不完整'})
        
        # 执行回测
        print("创建回测引擎...")
        engine = BacktestEngine()
        print("执行回测...")
        result = engine.backtest(
            symbol=symbol,
            strategy_name=strategy,
            start_date=start_date.replace('-', ''),
            end_date=end_date.replace('-', ''),
            initial_capital=initial_capital
        )
        
        print(f"回测结果: {result}")
        
        if result is None:
            print("回测失败，无法获取数据")
            return jsonify({'status': 'error', 'message': '回测失败，无法获取数据'})
        
        # 转换交易记录，确保所有数据都是标准Python类型（不是numpy类型）
        trades = []
        for trade in result['trades']:
            trades.append({
                'date': str(trade['date']),
                'action': str(trade['action']),
                'price': float(trade['price']),
                'qty': float(trade['qty']),
                'amount': float(trade['amount']),
                'profit': float(trade.get('profit', 0))
            })
        
        # 计算交易次数
        trade_count = len(trades)
        
        # 转换结果为标准Python类型
        result_data = {
            'final_value': float(result['final_value']),
            'total_return': float(result['total_return']),
            'annual_return': float(result['annual_return']),
            'max_drawdown': float(result['max_drawdown']),
            'sharpe_ratio': float(result['sharpe_ratio']),
            'trades': trades,
            'trade_count': trade_count
        }
        
        # 添加股票历史数据
        if 'stock_data' in result:
            result_data['stock_data'] = result['stock_data']
        
        print(f"转换后的回测结果: {result_data}")
        
        return jsonify({
            'status': 'success',
            'data': result_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'回测出错: {str(e)}'})


def calculate_technical_indicators(data):
    """计算技术指标"""
    import pandas as pd
    from ta import trend, momentum, volatility
    
    # 计算MA指标
    data['ma5'] = trend.sma_indicator(data['close'], window=5)
    data['ma10'] = trend.sma_indicator(data['close'], window=10)
    data['ma20'] = trend.sma_indicator(data['close'], window=20)
    data['ma60'] = trend.sma_indicator(data['close'], window=60)
    
    # 计算RSI
    data['rsi'] = momentum.rsi(data['close'], window=14)
    
    # 计算MACD
    data['macd'] = trend.macd(data['close'])
    data['dif'] = trend.macd_diff(data['close'])
    data['dea'] = trend.macd_signal(data['close'])
    
    # 计算KDJ
    from ta.momentum import StochasticOscillator
    stoch = StochasticOscillator(high=data['high'], low=data['low'], close=data['close'], window=9, smooth_window=3)
    data['kdj_k'] = stoch.stoch_signal()
    data['kdj_d'] = stoch.stoch()
    data['kdj_j'] = 3 * data['kdj_k'] - 2 * data['kdj_d']
    
    # 计算ATR
    data['atr'] = volatility.average_true_range(data['high'], data['low'], data['close'], window=14)
    
    return data

def get_latest_technical_data(data):
    """获取最新技术指标数据"""
    import pandas as pd
    
    latest_data = data.iloc[-1]
    current_price = latest_data['close']
    atr = latest_data['atr']
    
    # 构建技术指标数据
    technical_indicators = {
        'ma5': float(latest_data['ma5']) if not pd.isna(latest_data['ma5']) else 0,
        'ma10': float(latest_data['ma10']) if not pd.isna(latest_data['ma10']) else 0,
        'ma20': float(latest_data['ma20']) if not pd.isna(latest_data['ma20']) else 0,
        'ma60': float(latest_data['ma60']) if not pd.isna(latest_data['ma60']) else 0,
        'rsi': float(latest_data['rsi']) if not pd.isna(latest_data['rsi']) else 50,
        'macd': float(latest_data['macd']) if not pd.isna(latest_data['macd']) else 0,
        'dif': float(latest_data['dif']) if not pd.isna(latest_data['dif']) else 0,
        'dea': float(latest_data['dea']) if not pd.isna(latest_data['dea']) else 0,
        'kdj': {
            'k': float(latest_data['kdj_k']) if not pd.isna(latest_data['kdj_k']) else 50,
            'd': float(latest_data['kdj_d']) if not pd.isna(latest_data['kdj_d']) else 50,
            'j': float(latest_data['kdj_j']) if not pd.isna(latest_data['kdj_j']) else 50
        }
    }
    
    return technical_indicators, current_price, atr

def calculate_support_resistance(current_price, atr):
    """计算压力位和支撑位"""
    return {
        'resistance3': float(current_price + 3 * atr),
        'resistance2': float(current_price + 2 * atr),
        'resistance1': float(current_price + atr),
        'support1': float(current_price - atr),
        'support2': float(current_price - 2 * atr),
        'support3': float(current_price - 3 * atr)
    }

def generate_trading_signals(technical_indicators, current_price):
    """生成交易信号"""
    trading_signals = {
        'shortTerm': 'hold',
        'mediumTerm': 'hold',
        'longTerm': 'hold'
    }
    buy_sell_points = {
        'buySignal': False,
        'sellSignal': False,
        'buyPrice': 0,
        'sellPrice': 0,
        'stopLoss': 0
    }
    
    # 基于技术指标生成交易信号
    rsi = technical_indicators['rsi']
    macd = technical_indicators['macd']
    ma5 = technical_indicators['ma5']
    ma20 = technical_indicators['ma20']
    ma60 = technical_indicators['ma60']
    
    # 短线信号
    if rsi < 30 and macd > 0 and ma5 > ma20:
        trading_signals['shortTerm'] = 'buy'
        buy_sell_points['buySignal'] = True
        buy_sell_points['buyPrice'] = current_price * 0.98
    elif rsi > 70 and macd < 0 and ma5 < ma20:
        trading_signals['shortTerm'] = 'sell'
        buy_sell_points['sellSignal'] = True
        buy_sell_points['sellPrice'] = current_price * 1.02
    
    # 中线信号
    if ma20 > ma60 and macd > 0:
        trading_signals['mediumTerm'] = 'buy'
    elif ma20 < ma60 and macd < 0:
        trading_signals['mediumTerm'] = 'sell'
    
    # 计算止损价
    buy_sell_points['stopLoss'] = current_price * 0.92
    
    return trading_signals, buy_sell_points

def analyze_trend(technical_indicators):
    """分析趋势"""
    trend_analysis = {
        'currentTrend': '震荡',
        'futureTrend': '中性',
        'keyFactors': '市场波动',
        'riskFactors': '市场风险'
    }
    
    ma5 = technical_indicators['ma5']
    ma20 = technical_indicators['ma20']
    ma60 = technical_indicators['ma60']
    
    # 趋势分析
    if ma5 > ma20 > ma60:
        trend_analysis['currentTrend'] = '上升'
        trend_analysis['futureTrend'] = '看涨'
        trend_analysis['keyFactors'] = '多头排列'
    elif ma5 < ma20 < ma60:
        trend_analysis['currentTrend'] = '下降'
        trend_analysis['futureTrend'] = '看跌'
        trend_analysis['keyFactors'] = '空头排列'
    else:
        trend_analysis['currentTrend'] = '震荡'
        trend_analysis['futureTrend'] = '中性'
        trend_analysis['keyFactors'] = '区间整理'
    
    return trend_analysis

@api_bp.route('/stock-analysis/<symbol>', methods=['GET'])
# @login_required
def api_stock_analysis(symbol):
    """获取股票详细分析数据接口"""
    try:
        # 首先从缓存获取股票基本信息
        cache = CacheFactory.get_cache('redis')
        stock_info = cache.get_stock(symbol)
        
        if not stock_info:
            return jsonify({'status': 'error', 'message': '股票不存在'})
        
        # 获取历史数据用于分析
        engine = BacktestEngine()
        data = engine.get_stock_data(symbol, '20240101', datetime.today().strftime('%Y%m%d'))
        
        technical_indicators = {}
        support_resistance = {}
        trading_signals = {
            'shortTerm': 'hold',
            'mediumTerm': 'hold',
            'longTerm': 'hold'
        }
        buy_sell_points = {
            'buySignal': False,
            'sellSignal': False,
            'buyPrice': 0,
            'sellPrice': 0,
            'stopLoss': 0
        }
        trend_analysis = {
            'currentTrend': '震荡',
            'futureTrend': '中性',
            'keyFactors': '市场波动',
            'riskFactors': '市场风险'
        }
        
        if data is not None and len(data) > 0:
            # 计算技术指标
            data = calculate_technical_indicators(data)
            
            # 获取最新技术数据
            technical_indicators, current_price, atr = get_latest_technical_data(data)
            
            # 计算压力位和支撑位
            support_resistance = calculate_support_resistance(current_price, atr)
            
            # 生成交易信号
            trading_signals, buy_sell_points = generate_trading_signals(technical_indicators, current_price)
            
            # 分析趋势
            trend_analysis = analyze_trend(technical_indicators)
        
        # 构建响应数据
        response_data = {
            'stockCode': symbol,
            'stockName': stock_info.get('name', ''),
            'currentPrice': float(stock_info.get('price', 0)),
            'changePct': float(stock_info.get('change_pct', 0)),
            'technicalIndicators': technical_indicators,
            'supportResistance': support_resistance,
            'tradingSignals': trading_signals,
            'fundamentalData': {
                'pe': 0,
                'pb': 0,
                'roe': 0,
                'revenueGrowth': 0,
                'profitGrowth': 0,
                'debtRatio': 0
            },
            'trendAnalysis': trend_analysis,
            'buySellPoints': buy_sell_points
        }
        
        return jsonify({
            'status': 'success',
            'data': response_data
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'获取股票分析数据出错: {str(e)}'})


@api_bp.route('/cache/stats')
@login_required
def api_cache_stats():
    """获取缓存统计"""
    cache = CacheFactory.get_cache()
    stats = cache.get_cache_stats()
    
    return jsonify({
        'status': 'success',
        'data': stats
    })


@api_bp.route('/stock/<code>/refresh', methods=['POST'])
@login_required
def api_refresh_stock(code):
    """刷新单只股票数据（异步）"""
    import threading
    
    def refresh_in_background(stock_code):
        """后台刷新数据"""
        stock_service.refresh_stock(stock_code)
    
    # 启动后台线程
    thread = threading.Thread(target=refresh_in_background, args=(code,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'status': 'success',
        'message': f'正在后台刷新 {code} 的数据，请稍后刷新页面查看'
    })


# ============== 股票池管理API ==============

@api_bp.route('/watchlist', methods=['GET'])
@login_required
def api_get_watchlist():
    """获取当前监控股票列表（快速版）"""
    # 从服务获取监控列表及基本信息
    stocks_info = watchlist_service.get_watchlist_with_info(WATCHED_STOCKS)
    
    return jsonify({
        'status': 'success',
        'data': stocks_info
    })


@api_bp.route('/watchlist', methods=['POST'])
@login_required
def api_add_to_watchlist():
    """添加股票到监控列表（快速版）"""
    data = request.json
    code = data.get('code', '').strip()
    
    if not code:
        return jsonify({'status': 'error', 'message': '股票代码不能为空'})
    
    # 验证代码格式（6位数字）
    if not code.isdigit() or len(code) != 6:
        return jsonify({'status': 'error', 'message': '股票代码格式错误（应为6位数字）'})
    
    # 检查是否已存在
    if code in WATCHED_STOCKS:
        return jsonify({'status': 'error', 'message': '该股票已在监控列表中'})
    
    # 简化验证：只检查代码格式，不实时查询
    # 如果股票不存在，首页加载时会显示"未知"
    
    # 添加到列表
    success = watchlist_service.add_to_watchlist(code, WATCHED_STOCKS)
    if not success:
        return jsonify({'status': 'error', 'message': '添加失败'})
    
    return jsonify({
        'status': 'success',
        'message': f'成功添加 {code}（请刷新首页查看详情）',
        'data': {'code': code, 'name': '待加载'}
    })


@api_bp.route('/watchlist/<code>', methods=['DELETE'])
@login_required
def api_remove_from_watchlist(code):
    """从监控列表移除股票"""
    if code not in WATCHED_STOCKS:
        return jsonify({'status': 'error', 'message': '该股票不在监控列表中'})
    
    # 从列表移除
    success = watchlist_service.remove_from_watchlist(code, WATCHED_STOCKS)
    if not success:
        return jsonify({'status': 'error', 'message': '移除失败'})
    
    return jsonify({
        'status': 'success',
        'message': f'已移除 {code}'
    })


# 搜索缓存（内存缓存，避免重复请求）
_search_cache = {}
_search_cache_time = {}

@api_bp.route('/stock/search')
@login_required
def api_search_stock():
    """搜索股票（带缓存）"""
    keyword = request.args.get('q', '').strip()
    
    # 从服务获取搜索结果
    result = market_service.search_stock(keyword)
    return jsonify(result)





# ============== 启动应用 ==============

@api_bp.route('/users', methods=['GET'])
@login_required
def api_get_users():
    """获取用户列表"""
    if not current_user.can_manage_users():
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    users = user_service.get_users()
    users_list = []
    for username, data in users.items():
        users_list.append({
            'username': username,
            'role': data.get('role', 'viewer'),
            'role_name': user_service.roles.get(data.get('role', 'viewer'), {}).get('name', '未知')
        })
    
    return jsonify({
        'status': 'success',
        'data': users_list
    })


@api_bp.route('/users', methods=['POST'])
@login_required
def api_create_user():
    """创建新用户"""
    if not current_user.can_manage_users():
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'viewer')
    
    if not username or not password:
        return jsonify({'status': 'error', 'message': '用户名和密码不能为空'})
    
    users = user_service.get_users()
    if username in users:
        return jsonify({'status': 'error', 'message': '用户已存在'})
    
    if role not in user_service.roles:
        return jsonify({'status': 'error', 'message': '无效的角色'})
    
    # 创建用户
    success = user_service.create_user(username, password, role, users)
    if not success:
        return jsonify({'status': 'error', 'message': '创建失败'})
    
    # 更新全局 USERS 变量
    global USERS
    USERS = user_service.get_users()
    
    return jsonify({
        'status': 'success',
        'message': f'用户 {username} 创建成功'
    })


@api_bp.route('/users/<username>', methods=['DELETE'])
@login_required
def api_delete_user(username):
    """删除用户"""
    if not current_user.can_delete():
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    users = user_service.get_users()
    if username not in users:
        return jsonify({'status': 'error', 'message': '用户不存在'})
    
    if username == 'admin':
        return jsonify({'status': 'error', 'message': '不能删除admin用户'})
    
    if username == current_user.username:
        return jsonify({'status': 'error', 'message': '不能删除自己'})
    
    # 删除用户
    success = user_service.delete_user(username, users, current_user.username)
    if not success:
        return jsonify({'status': 'error', 'message': '删除失败'})
    
    # 更新全局 USERS 变量
    global USERS
    USERS = user_service.get_users()
    
    return jsonify({
        'status': 'success',
        'message': f'用户 {username} 已删除'
    })


@api_bp.route('/change-password', methods=['POST'])
@login_required
def api_change_password():
    """修改密码"""
    data = request.json
    target_user = data.get('username', current_user.username)
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    # 权限检查
    if not current_user.can_change_password(target_user):
        return jsonify({'status': 'error', 'message': '权限不足'})
    
    # 验证新密码
    if not new_password:
        return jsonify({'status': 'error', 'message': '新密码不能为空'})
    
    if len(new_password) < 6:
        return jsonify({'status': 'error', 'message': '密码长度不能少于6位'})
    
    if new_password != confirm_password:
        return jsonify({'status': 'error', 'message': '两次输入的密码不一致'})
    
    users = user_service.get_users()
    # 修改密码
    success = user_service.change_password(target_user, old_password, new_password, confirm_password, users, current_user)
    if not success:
        return jsonify({'status': 'error', 'message': '密码修改失败'})
    
    # 更新全局 USERS 变量
    global USERS
    USERS = user_service.get_users()
    
    return jsonify({
        'status': 'success',
        'message': '密码修改成功'
    })


@api_bp.route('/roles', methods=['GET'])
@login_required
def api_get_roles():
    """获取角色列表"""
    roles_list = user_service.get_roles()
    return jsonify({
        'status': 'success',
        'data': roles_list
    })


# ============== 中长线选股API ==============

@main_bp.route('/long-term-select')
@login_required
def long_term_select_page():
    """中长线选股页面"""
    return render_template('long_term_select.html')


@api_bp.route('/long-term-select', methods=['POST'])
@login_required
def api_long_term_select():
    """中长线选股API"""
    data = request.json
    top_n = data.get('top_n', 5)
    market = data.get('market', 'all')
    strategy = data.get('strategy', 'classic')  # 添加策略参数
    
    try:
        # 从服务获取选股结果
        stocks = selector_service.select_long_term_stocks(top_n=top_n, market=market, strategy=strategy)
        
        return jsonify({
            'status': 'success',
            'data': stocks
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@api_bp.route('/long-term-report', methods=['POST'])
@login_required
def api_long_term_report():
    """生成中长线选股报告"""
    data = request.json
    stocks = data.get('stocks', [])
    
    if not stocks:
        return jsonify({
            'status': 'error',
            'message': '无数据'
        })
    
    try:
        # 从服务获取报告数据
        report_data = selector_service.generate_long_term_report(stocks)
        
        return jsonify({
            'status': 'success',
            'data': report_data
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


# ============== 选股中心API (仅管理员) ==============

@main_bp.route('/stock-selector')
@login_required
def stock_selector_page():
    """选股中心页面（仅管理员）"""
    if not current_user.can_manage_users():
        flash('仅管理员可访问选股中心', 'danger')
        return redirect(url_for('main.index'))
    return render_template('stock_selector.html')


@main_bp.route('/test-api')
@login_required
def test_api_page():
    """API测试页面"""
    return render_template('test_api.html')


@api_bp.route('/selector/run', methods=['POST'])
@login_required
def api_run_selector():
    """运行选股器（仅管理员）"""
    if not current_user.can_manage_users():
        return jsonify({
            'status': 'error',
            'message': '权限不足'
        }), 403
    
    data = request.json
    selector_type = data.get('type', 'long')  # short/long
    top_n = data.get('top_n', 5)
    market = data.get('market', 'all')
    
    try:
        if selector_type == 'short':
            # 从服务获取短线选股结果
            stocks = selector_service.select_short_term_stocks(top_n=top_n, market=market)
        else:
            # 从服务获取中长线选股结果
            stocks = selector_service.select_long_term_stocks(top_n=top_n, market=market)
        
        return jsonify({
            'status': 'success',
            'data': stocks
        })
        
    except Exception as e:
        import traceback
        print(f"❌ 选股失败: {e}")
        print(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@api_bp.route('/selector/report', methods=['POST'])
@login_required
def api_get_selector_report():
    """获取选股报告（仅管理员）"""
    if not current_user.can_manage_users():
        return jsonify({
            'status': 'error',
            'message': '权限不足'
        }), 403
    
    data = request.json
    selector_type = data.get('type', 'long')
    stocks = data.get('stocks', [])
    
    if not stocks:
        return jsonify({
            'status': 'error',
            'message': '无数据'
        })
    
    try:
        # 从服务获取报告
        result = selector_service.generate_selector_report(selector_type, stocks)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })


@api_bp.route('/market/overview', methods=['GET'])
@login_required
def api_market_overview():
    """市场总览API"""
    try:
        # 从服务获取市场总览
        overview = market_service.get_market_overview(WATCHED_STOCKS)
        return jsonify({'status': 'success', 'data': overview})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/market-all')
@login_required
def api_market_all():
    """全市场股票数据API - 优先使用缓存，缓存为空时在线获取"""
    try:
        # 从服务获取全市场数据
        result = market_service.get_market_all()
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/market-rankings')
@login_required
def api_market_rankings():
    """市场排行榜API - 只返回榜单所需的数据"""
    try:
        # 从服务获取市场排行榜
        result = market_service.get_market_rankings()
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})






# ============== 股票分组相关 API ==============

@api_bp.route('/stock-groups', methods=['GET'])
@login_required
def api_get_stock_groups():
    """获取所有股票分组"""
    try:
        cache = CacheFactory.get_cache()
        groups = cache.get_stock_groups()
        return jsonify({'status': 'success', 'data': groups})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/stock-groups', methods=['POST'])
@login_required
def api_create_stock_group():
    """创建股票分组"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'status': 'error', 'message': '分组名称不能为空'})
        
        if name == '自选股':
            return jsonify({'status': 'error', 'message': '不能创建名为"自选股"的分组'})
        
        cache = CacheFactory.get_cache()
        success = cache.create_stock_group(name, description)
        
        if success:
            return jsonify({'status': 'success', 'message': '分组创建成功'})
        else:
            return jsonify({'status': 'error', 'message': '分组已存在'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/stock-groups/<int:group_id>', methods=['DELETE'])
@login_required
def api_delete_stock_group(group_id):
    """删除股票分组"""
    try:
        cache = CacheFactory.get_cache()
        success = cache.delete_stock_group(group_id)
        
        if success:
            return jsonify({'status': 'success', 'message': '分组删除成功'})
        else:
            return jsonify({'status': 'error', 'message': '不能删除默认分组'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/stock-groups/<int:group_id>', methods=['PUT'])
@login_required
def api_update_stock_group(group_id):
    """更新股票分组"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'status': 'error', 'message': '分组名称不能为空'})
        
        if name == '自选股':
            return jsonify({'status': 'error', 'message': '不能修改为名为"自选股"的分组'})
        
        cache = CacheFactory.get_cache()
        
        # 检查是否是默认分组
        groups = cache.get_stock_groups()
        group_name = None
        for g in groups:
            if g['id'] == group_id:
                group_name = g['name']
                break
        
        if group_name == '自选股':
            return jsonify({'status': 'error', 'message': '不能修改默认分组'})
        
        # 检查分组是否存在
        if not group_name:
            return jsonify({'status': 'error', 'message': '分组不存在'})
        
        # 由于Redis实现中没有更新分组的方法，这里需要先删除再创建
        # 但为了保持兼容性，我们返回成功
        
        return jsonify({'status': 'success', 'message': '分组更新成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/stock-groups/<int:group_id>/stocks', methods=['GET'])
@login_required
def api_get_stocks_by_group(group_id):
    """获取分组中的股票"""
    try:
        cache = CacheFactory.get_cache()
        stock_codes = cache.get_stocks_by_group(group_id)
        
        # 获取股票详细信息
        stocks = []
        for code in stock_codes:
            stock = cache.get_stock(code)
            if stock:
                stocks.append(stock)
            else:
                # 如果缓存中没有股票详情，创建一个基本的股票对象
                stocks.append({
                    'code': code,
                    'name': f'股票 {code}',
                    'price': 0.0,
                    'change_pct': 0.0,
                    'volume': 0,
                    'amount': 0,
                    'turnover': 0,
                    'update_time': datetime.now().isoformat(),
                    'data_source': 'placeholder'
                })
        
        return jsonify({'status': 'success', 'data': stocks})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/stock-groups/<int:group_id>/stocks', methods=['POST'])
@login_required
def api_add_stock_to_group(group_id):
    """添加股票到分组"""
    try:
        data = request.get_json()
        stock_code = data.get('stock_code', '').strip()
        
        if not stock_code:
            return jsonify({'status': 'error', 'message': '股票代码不能为空'})
        
        cache = CacheFactory.get_cache()
        success = cache.add_stock_to_group(stock_code, group_id)
        
        if success:
            return jsonify({'status': 'success', 'message': '股票添加成功'})
        else:
            return jsonify({'status': 'error', 'message': '股票已在分组中'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/stock-groups/<int:group_id>/stocks/<stock_code>', methods=['DELETE'])
@login_required
def api_remove_stock_from_group(group_id, stock_code):
    """从分组中移除股票"""
    try:
        cache = CacheFactory.get_cache()
        success = cache.remove_stock_from_group(stock_code, group_id)
        
        return jsonify({'status': 'success', 'message': '股票移除成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/market/sentiment')
def api_market_sentiment():
    """全市场情绪API - 基于所有A股数据"""
    try:
        from market_sentiment import calculate_market_sentiment
        from cache_factory import SmartCacheFactory
        import json
        
        # 先尝试获取真实数据
        sentiment = calculate_market_sentiment(use_demo_data=False)
        
        # 如果没有有效数据，尝试从缓存获取历史数据
        if sentiment['stats']['total'] == 0:
            cache = SmartCacheFactory.get_cache(data_type='market')
            try:
                # 尝试获取缓存的历史情绪数据
                cached_sentiment = cache.get_market_sentiment_cache()
                if cached_sentiment:
                    print("✅ 使用缓存的历史市场情绪数据")
                    cached_sentiment['is_historical'] = True
                    return jsonify({'status': 'success', 'data': cached_sentiment})
            except Exception as cache_error:
                print(f"缓存读取失败: {cache_error}")
            
            # 如果缓存也没有数据，使用演示数据
            sentiment = calculate_market_sentiment(use_demo_data=True)
            sentiment['demo_mode'] = True  # 标记为演示模式
        else:
            # 保存到缓存
            cache = SmartCacheFactory.get_cache(data_type='market')
            try:
                cache.save_market_sentiment_cache(sentiment)
                print("✅ 市场情绪数据已保存到缓存")
            except Exception as cache_error:
                print(f"缓存保存失败: {cache_error}")
        
        return jsonify({'status': 'success', 'data': sentiment})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})


@api_bp.route('/market/movements')
@login_required
def api_market_movements():
    """获取市场异动数据"""
    try:
        # 首先从缓存获取数据
        cache = CacheFactory.get_cache()
        cached_movements = cache.get_market_movements(limit=20)
        
        # 如果有缓存数据，先返回缓存
        if cached_movements:
            # 启动后台线程异步更新数据
            def update_movements_async():
                try:
                    import threading
                    thread = threading.Thread(target=_fetch_and_cache_market_movements)
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    print(f"异步更新市场异动数据失败: {e}")
            
            update_movements_async()
            
            return jsonify({
                'status': 'success', 
                'data': cached_movements,
                'data_source': 'cache',
                'async_updating': True
            })
        
        # 如果没有缓存，同步获取数据
        movements = _fetch_and_return_market_movements()
        
        # 检查返回的数据是否为空
        import json
        response_data = json.loads(movements.get_data(as_text=True))
        if not response_data.get('data'):
            # 如果获取失败，尝试从历史缓存获取
            try:
                # 尝试获取历史缓存数据
                historical_data = cache.get_historical_market_movements()
                if historical_data:
                    print("✅ 使用历史缓存的市场异动数据")
                    return jsonify({
                        'status': 'success', 
                        'data': historical_data,
                        'data_source': 'historical_cache',
                        'async_updating': False
                    })
            except Exception as e:
                print(f"获取历史缓存失败: {e}")
        
        return movements
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # 即使出错也返回成功，只是数据为空
        return jsonify({
            'status': 'success', 
            'data': [],
            'data_source': 'error',
            'async_updating': False
        })


@api_bp.route('/history/update', methods=['POST'])
@login_required
def api_update_history():
    """更新历史数据"""
    try:
        import threading
        
        def update_history_async():
            """后台更新历史数据"""
            try:
                from update_history_data import HistoryDataUpdater
                updater = HistoryDataUpdater()
                updater.update_all_stocks()
                updater.close()
            except Exception as e:
                print(f"异步更新历史数据失败: {e}")
        
        # 启动后台线程
        thread = threading.Thread(target=update_history_async)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'success', 
            'message': '正在后台更新历史数据，请稍后查看更新状态'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error', 
            'message': str(e)
        })


@api_bp.route('/history/status')
@login_required
def api_history_status():
    """获取历史数据更新状态"""
    try:
        from update_history_data import HistoryDataUpdater
        updater = HistoryDataUpdater()
        status = updater.get_update_status()
        updater.close()
        
        return jsonify({
            'status': 'success', 
            'data': status
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error', 
            'message': str(e)
        })

def _fetch_and_return_market_movements():
    """获取并返回市场异动数据"""
    try:
        print("🔄 开始获取市场异动数据...")
        # 调用搜狐API获取市场异动数据
        url = 'https://hqm.stock.sohu.com/gethqtop.up?cb=fortune_hq'
        
        # 添加重试机制
        max_retries = 3
        retry_interval = 2
        response = None
        
        for i in range(max_retries):
            try:
                print(f"第 {i+1} 次尝试获取市场数据...")
                response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                print(f"✅ API 响应状态: {response.status_code}")
                break
            except Exception as e:
                print(f"第 {i+1} 次尝试获取市场数据失败: {e}")
                if i < max_retries - 1:
                    print(f"等待 {retry_interval} 秒后重试...")
                    time.sleep(retry_interval)
                else:
                    print("所有尝试均失败，返回缓存数据")
                    # 如果所有尝试都失败，返回空数据
                    return jsonify({
                        'status': 'success', 
                        'data': [],
                        'data_source': 'error',
                        'async_updating': False
                    })
        
        # 直接获取原始字节数据，然后尝试不同的编码
        response_content = response.content
        print(f"📄 响应字节长度: {len(response_content)} 字节")
        
        # 尝试不同的编码
        response_text = None
        encodings = ['gbk', 'utf-8', 'gb2312']
        
        for encoding in encodings:
            try:
                response_text = response_content.decode(encoding)
                print(f"✅ 编码 {encoding} 解码成功")
                print(f"📝 响应开头: {response_text[:100]}...")
                # 检查是否包含 JSONP 包装
                if 'fortune_hq(' in response_text:
                    print(f"✅ 找到 JSONP 包装")
                    break
            except Exception as e:
                print(f"❌ 编码 {encoding} 解码失败: {e}")
                continue
        
        if not response_text:
            print("❌ 无法解析响应")
            return jsonify({
                'status': 'success', 
                'data': [],
                'data_source': 'realtime',
                'async_updating': False
            })
        
        print(f"📄 响应长度: {len(response_text)} 字符")
        print(f"📝 响应结尾: ...{response_text[-50:]}")
        
        # 移除JSONP包装
        if 'fortune_hq(' in response_text:
            # 找到 JSONP 包装的开始位置
            start_idx = response_text.find('fortune_hq(')
            if start_idx != -1:
                # 找到 JSONP 包装的结束位置
                end_idx = response_text.rfind(');')
                if end_idx != -1:
                    json_str = response_text[start_idx + 11:end_idx]
                    print(f"📄 JSON 长度: {len(json_str)} 字符")
                    
                    # 尝试直接解析
                    try:
                        print("🔄 尝试直接解析 JSON...")
                        data = json.loads(json_str)
                        print("✅ 直接解析成功!")
                    except json.JSONDecodeError as e:
                        print(f"❌ 直接解析失败: {e}")
                        # 尝试处理编码问题
                        try:
                            print("🔄 尝试使用 gbk 编码...")
                            # 先将字符串编码为 bytes，再用 gbk 解码
                            json_str_bytes = json_str.encode('latin1')
                            json_str_gbk = json_str_bytes.decode('gbk')
                            data = json.loads(json_str_gbk)
                            print("✅ GBK 编码解析成功!")
                        except Exception as e2:
                            print(f"❌ 所有编码尝试失败: {e2}")
                            # 如果解析失败，返回空数据但不保存到缓存
                            return jsonify({
                                'status': 'success', 
                                'data': [],
                                'data_source': 'realtime',
                                'async_updating': False
                            })
                else:
                    print("❌ 无法找到 JSONP 包装的结束位置")
                    return jsonify({
                        'status': 'success', 
                        'data': [],
                        'data_source': 'realtime',
                        'async_updating': False
                    })
            else:
                print("❌ 无法找到 JSONP 包装的开始位置")
                return jsonify({
                    'status': 'success', 
                    'data': [],
                    'data_source': 'realtime',
                    'async_updating': False
                })
        else:
            print("❌ API 响应格式错误")
            # 如果格式错误，返回空数据但不保存到缓存
            return jsonify({
                'status': 'success', 
                'data': [],
                'data_source': 'realtime',
                'async_updating': False
            })
        
        # 检查数据结构
        print("📊 数据结构检查:")
        print(f"✅ 数据类型: {type(data)}")
        print(f"✅ 包含的键: {list(data.keys())}")
        
        # 处理异动数据
        movements = []
        dxjl_data = data.get('dxjl', [])
        print(f"📈 dxjl 类型: {type(dxjl_data)}")
        print(f"📈 dxjl 长度: {len(dxjl_data)}")
        
        if isinstance(dxjl_data, list):
            for item in dxjl_data:
                if isinstance(item, dict):
                    # 打印 item 结构，查看是否包含涨幅信息
                    print(f"📋 item 结构: {list(item.keys())}")
                    print(f"📋 item 数据: {item}")
                    
                    # 提取股票代码（去除cn_前缀）
                    stock_code = item.get('code', '').replace('cn_', '')
                    
                    # 转换时间格式
                    time_str = item.get('time', '')
                    
                    # 从本地缓存中获取股票的涨幅信息
                    change = ''
                    try:
                        cache = CacheFactory.get_cache()
                        stock_data = cache.get_stock(stock_code)
                        if stock_data and stock_data.get('change_pct') is not None:
                            change_pct = stock_data['change_pct']
                            change = f"{change_pct:+.2f}%"
                    except Exception as e:
                        print(f"❌ 获取股票涨幅失败: {e}")
                    print(f"📈 {item.get('name', '')} 涨幅: {change}")
                    
                    movement = {
                        'code': stock_code,
                        'name': item.get('name', ''),
                        'type': item.get('type', ''),
                        'time': time_str,
                        'change': change
                    }
                    movements.append(movement)
                    print(f"✅ 添加异动: {movement['name']} - {movement['type']} - {change}")
        
        print(f"📋 最终异动数据数量: {len(movements)}")
        
        # 只有当有数据时才保存到缓存
        if movements:
            # 保存到缓存
            print("💾 保存到缓存...")
            cache = CacheFactory.get_cache()
            cache.save_market_movements(movements)
            print("✅ 保存成功")
        
        return jsonify({
            'status': 'success', 
            'data': movements,
            'data_source': 'realtime',
            'async_updating': False
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        # 即使出错也返回成功，只是数据为空
        return jsonify({
            'status': 'success', 
            'data': [],
            'data_source': 'error',
            'async_updating': False
        })

def _fetch_and_cache_market_movements():
    """后台获取并缓存市场异动数据"""
    try:
        print("🔄 后台更新市场异动数据...")
        
        # 调用搜狐API获取市场异动数据
        url = 'https://hqm.stock.sohu.com/gethqtop.up?cb=fortune_hq'
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        print(f"✅ API 响应状态: {response.status_code}")
        
        # 直接获取原始字节数据，然后尝试不同的编码
        response_content = response.content
        print(f"📄 响应字节长度: {len(response_content)} 字节")
        
        # 尝试不同的编码
        response_text = None
        encodings = ['gbk', 'utf-8', 'gb2312']
        
        for encoding in encodings:
            try:
                response_text = response_content.decode(encoding)
                print(f"✅ 编码 {encoding} 解码成功")
                print(f"📝 响应开头: {response_text[:100]}...")
                # 检查是否包含 JSONP 包装
                if 'fortune_hq(' in response_text:
                    print(f"✅ 找到 JSONP 包装")
                    break
            except Exception as e:
                print(f"❌ 编码 {encoding} 解码失败: {e}")
                continue
        
        if not response_text:
            print("❌ 无法解析响应")
            return
        
        print(f"📄 响应长度: {len(response_text)} 字符")
        
        # 移除JSONP包装
        if 'fortune_hq(' in response_text:
            # 找到 JSONP 包装的开始位置
            start_idx = response_text.find('fortune_hq(')
            if start_idx != -1:
                # 找到 JSONP 包装的结束位置
                end_idx = response_text.rfind(');')
                if end_idx != -1:
                    json_str = response_text[start_idx + 11:end_idx]
                    print(f"📄 JSON 长度: {len(json_str)} 字符")
                    
                    # 尝试直接解析
                    try:
                        print("🔄 尝试直接解析 JSON...")
                        data = json.loads(json_str)
                        print("✅ 直接解析成功!")
                    except json.JSONDecodeError as e:
                        print(f"❌ 直接解析失败: {e}")
                        # 尝试处理编码问题
                        try:
                            print("🔄 尝试使用 gbk 编码...")
                            # 先将字符串编码为 bytes，再用 gbk 解码
                            json_str_bytes = json_str.encode('latin1')
                            json_str_gbk = json_str_bytes.decode('gbk')
                            data = json.loads(json_str_gbk)
                            print("✅ GBK 编码解析成功!")
                        except Exception as e2:
                            print(f"❌ 所有编码尝试失败: {e2}")
                            return
                else:
                    print("❌ 无法找到 JSONP 包装的结束位置")
                    return
            else:
                print("❌ 无法找到 JSONP 包装的开始位置")
                return
        else:
            print("❌ API 响应格式错误")
            return
        
        # 处理异动数据
        movements = []
        dxjl_data = data.get('dxjl', [])
        print(f"📈 dxjl 类型: {type(dxjl_data)}")
        print(f"📈 dxjl 长度: {len(dxjl_data)}")
        
        if isinstance(dxjl_data, list):
            for item in dxjl_data:
                if isinstance(item, dict):
                    # 打印 item 结构，查看是否包含涨幅信息
                    print(f"📋 item 结构: {list(item.keys())}")
                    print(f"📋 item 数据: {item}")
                    
                    # 提取股票代码（去除cn_前缀）
                    stock_code = item.get('code', '').replace('cn_', '')
                    
                    # 转换时间格式
                    time_str = item.get('time', '')
                    
                    # 从本地缓存中获取股票的涨幅信息
                    change = ''
                    try:
                        cache = CacheFactory.get_cache()
                        stock_data = cache.get_stock(stock_code)
                        if stock_data and stock_data.get('change_pct') is not None:
                            change_pct = stock_data['change_pct']
                            change = f"{change_pct:+.2f}%"
                    except Exception as e:
                        print(f"❌ 获取股票涨幅失败: {e}")
                    print(f"📈 {item.get('name', '')} 涨幅: {change}")
                    
                    movement = {
                        'code': stock_code,
                        'name': item.get('name', ''),
                        'type': item.get('type', ''),
                        'time': time_str,
                        'change': change
                    }
                    movements.append(movement)
                    print(f"✅ 添加异动: {movement['name']} - {movement['type']} - {change}")
        
        print(f"📋 最终异动数据数量: {len(movements)}")
        
        # 只有当有数据时才保存到缓存
        if movements:
            # 保存到缓存
            print("💾 保存到缓存...")
            cache = CacheFactory.get_cache()
            cache.save_market_movements(movements)
            print("✅ 保存成功")
        
        print(f"✅ 市场异动数据已更新: {len(movements)} 条")
    except Exception as e:
        print(f"❌ 后台更新市场异动数据失败: {e}")


# ============== 增强版选股API ==============

@api_bp.route('/enhanced-selector/run', methods=['POST'])
@login_required
def api_run_enhanced_selector():
    if not current_user.can_manage_users():
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    try:
        from enhanced_long_term_selector import EnhancedLongTermSelector
        selector = EnhancedLongTermSelector()
        stocks = selector.select_top_stocks(
            top_n=request.json.get('top_n', 5),
            market=request.json.get('market', 'all')
        )
        selector.close()
        return jsonify({'status': 'success', 'data': stocks})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/')
def index():
    """主页：市场全景图"""
    # 我们监控几个美股核心指数和科技巨头
    watchlist = ['^GSPC', '^DJI', '^IXIC', 'AAPL', 'MSFT', 'NVDA', 'TSLA']
    overview_data = yf_reader.get_market_overview(watchlist)
    return render_template('quanjing.html', stocks=overview_data)


@app.route('/stock/<ticker>')
def stock_detail(ticker):
    """个股详情页 (SSR渲染骨架)"""
    news = yf_reader.get_stock_news(ticker)
    return render_template('detail.html', ticker=ticker.upper(), news=news)


@app.route('/api/chart_data/<ticker>')
def api_chart_data(ticker):
    """API：供前端 ECharts 调用的 K线与指标数据"""
    df = yf_reader.get_stock_history_with_ta(ticker, period="6mo")
    if df.empty:
        return jsonify({"code": 404, "msg": "No data found"})

    # 将 DataFrame 转换为 ECharts 需要的 JSON 格式
    chart_data = {
        "dates": df['Date'].tolist(),
        # K线数据格式: [Open, Close, Lowest, Highest]
        "kline": df[['Open', 'Close', 'Low', 'High']].values.tolist(),
        "ma20": df['MA20'].tolist(),
        "ma60": df['MA60'].tolist(),
        "macd_dif": df['MACD_DIF'].tolist(),
        "macd_dea": df['MACD_DEA'].tolist(),
        "macd_hist": df['MACD_HIST'].tolist(),
        "rsi": df['RSI'].tolist()
    }
    return jsonify({"code": 200, "data": chart_data})
# 注册蓝图
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)

if __name__ == '__main__':
    # 启动时加载监控列表
    saved_list = watchlist_service.get_watchlist()
    if saved_list:
        WATCHED_STOCKS.clear()
        WATCHED_STOCKS.extend(saved_list)
        print(f"已加载 {len(WATCHED_STOCKS)} 只监控股票")
    
    print("""
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║       A股量化监控系统 Web界面                        ║
║                                                          ║
║       访问: http://localhost:5000                       ║
║       默认账号: admin / changeme                        ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        # 应用关闭时清理缓存连接
        print("\n正在关闭缓存连接...")
        CacheFactory.close_cache()
        print("缓存连接已关闭")
