from __future__ import annotations
"""UseCase Router Adapter - Gradual integration with existing routes."""


from flask import jsonify



class UseCaseRouter:
    """Adapter to integrate UseCases with Flask routes smoothly."""

    def __init__(self, use_case_factory):
        self._factory = use_case_factory

    def create_handler(self, use_case_method, *use_case_args, **use_case_kwargs):
        """Create a route handler that wraps a use case."""
        def handler(*args, **kwargs):
            use_case = getattr(self._factory, use_case_method)()
            result = use_case.execute(*use_case_args, **use_case_kwargs)

            if result.success:
                return jsonify({
                    "data": result.data,
                    "status": "ok"
                })
            else:
                return jsonify({
                    "error": result.error,
                    "status": "error"
                }), 400

        return handler

    def create_market_handler(self, use_case_method, market_default="CN"):
        """Create a route handler that extracts market from request."""
        from flask import request

        def handler():

            market = request.args.get("market", market_default).strip().upper()
            use_case = getattr(self._factory, use_case_method)()
            result = use_case.execute(market=market)

            if result.success:
                return jsonify({"data": result.data})
            else:
                return jsonify({"error": result.error}), 400

        return handler

    def create_quote_handler(self, use_case_method):
        """Create a route handler for stock quotes."""
        from flask import request

        def handler():
            symbols = request.args.getlist("symbol")
            limit = request.args.get("limit", "12000")
            market = request.args.get("market", "CN").strip().upper()

            try:
                limit = int(limit)
            except ValueError:
                limit = 12000

            use_case = getattr(self._factory, use_case_method)()
            result = use_case.execute(
                symbols=symbols if symbols else None,
                market=market,
                limit=limit
            )

            if result.success:
                return jsonify(result.data)
            else:
                return jsonify({"error": result.error}), 400

        return handler
