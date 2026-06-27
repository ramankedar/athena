"""Trading Engine — application layer.

Use cases:
    ProcessSignal     — receive SignalGenerated, build OrderIntent, run risk gate
    SubmitOrder       — pass validated order to EMS for broker submission
    CancelOrder       — request cancellation of an open order
    ReconcilePositions — compare ledger against broker and detect discrepancies
"""
