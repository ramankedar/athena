"""Trading Engine — core layer.

Domain models: Order, Fill, Position, RiskLimit, RiskCheck.
Domain events: OrderIntent, OrderValidated, OrderRejected, OrderFilled, etc.
Domain services: pre-trade risk gate logic (pure, no I/O).
"""
