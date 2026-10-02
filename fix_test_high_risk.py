import re
with open("tests/test_policy.py", "r") as f:
    content = f.read()

content = content.replace('engine = PolicyEngine(allowed_file_roots=["~/Projects"], preapproved_rules=rules)', 'from app.core.config import FileRootConfig\n    engine = PolicyEngine(allowed_file_roots=[FileRootConfig(path="~/Projects", delete=True, write=True)], preapproved_rules=rules)')

with open("tests/test_policy.py", "w") as f:
    f.write(content)
