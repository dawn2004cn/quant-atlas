import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'api_service.dart';

typedef QuoteCallback = void Function(Map<String, dynamic> quote);
typedef ProgressCallback = void Function(String runId, int pct, String msg);

class WebSocketService {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  final List<QuoteCallback> _quoteListeners = [];
  final List<ProgressCallback> _progressListeners = [];

  void connect() {
    if (_channel != null) return;
    try {
      _channel = WebSocketChannel.connect(Uri.parse(ApiConfig.wsUrl));
      _subscription = _channel!.stream.listen(_onMessage,
          onError: (e) => print('[ws] error: $e'),
          onDone: () {
            print('[ws] disconnected');
            _channel = null;
          });
    } catch (e) {
      print('[ws] connect failed: $e');
    }
  }

  void onQuote(QuoteCallback cb) => _quoteListeners.add(cb);
  void onProgress(ProgressCallback cb) => _progressListeners.add(cb);

  void _onMessage(dynamic data) {
    try {
      final msg = jsonDecode(data as String) as Map<String, dynamic>;
      final type = msg['type'] as String?;

      if (type == 'quote' || msg.containsKey('symbol')) {
        for (final cb in _quoteListeners) {
          cb(msg);
        }
      } else if (type == 'progress' || msg.containsKey('pct')) {
        final runId = msg['run_id'] as String? ?? '';
        final pct = msg['pct'] as int? ?? 0;
        final message = msg['msg'] as String? ?? '';
        for (final cb in _progressListeners) {
          cb(runId, pct, message);
        }
      }
    } catch (e) {
      print('[ws] parse error: $e');
    }
  }

  void disconnect() {
    _subscription?.cancel();
    _channel?.sink.close();
    _channel = null;
  }

  bool get isConnected => _channel != null;
}