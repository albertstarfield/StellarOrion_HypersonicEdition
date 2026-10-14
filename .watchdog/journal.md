# Overnight watchdog journal (resume point)
Last heartbeat is in heartbeat.json. If stale > 20 min, work stalled.
## Resume instructions
1. Read heartbeat.json for `step`.
2. Verify last claimed step's artifact on disk (figure PNG mtime, build log, commits).
3. Continue from NEXT step in the todo list; do not trust claimed state without re-verification.
