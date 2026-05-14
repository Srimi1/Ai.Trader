"""
Flush pending email notifications via Gmail MCP.

Run this from within Claude Code (where Gmail MCP is authenticated):
  python scripts/send_pending_emails.py

Or invoke directly: "send pending trading emails"
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.notifications.email import list_pending, ALERT_EMAIL

pending = list_pending()
if not pending:
    print("No pending notifications.")
    sys.exit(0)

print(f"{len(pending)} pending notification(s) to send to {ALERT_EMAIL}:\n")
for n in pending:
    print(f"  Subject: {n['subject']}")
    print(f"  Created: {n.get('created_at', 'unknown')}")
    print(f"  File: {n['file']}")
    print()

print("To send, Claude Code should call Gmail MCP create_draft or send for each pending file.")
print("Pending files are in: data/notifications/")
