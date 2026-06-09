"""
Shared SSE stream sentinels.

The worker publishes one of these as the final message on a job's pub/sub channel;
the API forwards it and the frontend ends the stream on either. Kept in a tiny
shared module so the API never has to import the heavy worker module (tasks.py)
just to know the protocol.
"""

SUCCESS_SENTINEL = "DONE"   # job completed → client fetches the result
FAILURE_SENTINEL = "ERROR"  # job failed/timed out → client shows the error
