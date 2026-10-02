import re
with open("tests/test_policy.py", "r") as f:
    content = f.read()

content = content.replace('ApprovalRequest(\n            action_hash="a" * 64, action_id="1", tool="process.run",\n            created_at=math.nan, expires_at=time.time() + 60\n        )', 'dummy = ActionRequest(id="1", tool="process.run", arguments={"argv": ["ls"]})\n        ApprovalRequest(\n            action_hash=hash_action(dummy), action_id="1", tool="process.run",\n            created_at=math.nan, expires_at=time.time() + 60,\n            action_snapshot=dummy.to_canonical_json()\n        )')

content = content.replace('ApprovalRequest(\n            action_hash="a" * 64, action_id="1", tool="process.run",\n            created_at=time.time(), expires_at=math.inf\n        )', 'dummy2 = ActionRequest(id="1", tool="process.run", arguments={"argv": ["ls"]})\n        ApprovalRequest(\n            action_hash=hash_action(dummy2), action_id="1", tool="process.run",\n            created_at=time.time(), expires_at=math.inf,\n            action_snapshot=dummy2.to_canonical_json()\n        )')

with open("tests/test_policy.py", "w") as f:
    f.write(content)
