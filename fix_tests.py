import re
with open("tests/test_policy.py", "r") as f:
    content = f.read()

content = content.replace('req = ApprovalRequest(\n        action_hash="a" * 64,\n        action_id="act-1",\n        tool="process.run",\n        created_at=now,\n        expires_at=now + 60.0,\n        reason="testing",\n        request_id="req-1",\n    )', 'dummy_req = ActionRequest(id="act-1", tool="process.run", arguments={"argv": ["ls"]}, reason="testing", request_id="req-1")\n    req = ApprovalRequest.from_action(dummy_req)')

content = content.replace('req = ApprovalRequest(\n        action_hash=digest,\n        action_id="benign",\n        tool="browser.read",\n        created_at=time.time(),\n        expires_at=time.time() + 60,\n    )', '')

content = content.replace('with pytest.raises(ValidationError):\n        # extra="forbid" rejects unknown field\n        ApprovalRequest(\n            action_hash="a" * 64,\n            action_id="act-1",\n            tool="process.run",\n            created_at=now,\n            expires_at=now + 60.0,\n            unauthorized_extra="bypass",\n        )', 'with pytest.raises(ValidationError):\n        # extra="forbid" rejects unknown field\n        dummy_req2 = ActionRequest(id="act-1", tool="process.run", arguments={"argv": ["ls"]})\n        ApprovalRequest(\n            action_hash=hash_action(dummy_req2),\n            action_id="act-1",\n            tool="process.run",\n            created_at=now,\n            expires_at=now + 60.0,\n            action_snapshot=dummy_req2.to_canonical_json(),\n            unauthorized_extra="bypass",\n        )')
content = content.replace('with pytest.raises(ValidationError):\n        ApprovalRequest(\n            action_hash="a" * 64,\n            action_id="act-1",\n            tool="process.run",\n            created_at=now,\n            expires_at=now - 1.0,\n        )', 'with pytest.raises(ValidationError):\n        dummy_req3 = ActionRequest(id="act-1", tool="process.run", arguments={"argv": ["ls"]})\n        ApprovalRequest(\n            action_hash=hash_action(dummy_req3),\n            action_id="act-1",\n            tool="process.run",\n            created_at=now,\n            expires_at=now - 1.0,\n            action_snapshot=dummy_req3.to_canonical_json()\n        )')
with open("tests/test_policy.py", "w") as f:
    f.write(content)
