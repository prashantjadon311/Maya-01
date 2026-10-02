import re
with open("tests/test_policy.py", "r") as f:
    content = f.read()

content = content.replace('{"tool": "process.run", "executable": "env", "risk": "low"},', '{"tool": "process.run", "executable": "env", "argv_prefix": [], "risk": "low"},')
content = content.replace('{"tool": "process.run", "executable": "pkexec", "risk": "low"},', '{"tool": "process.run", "executable": "pkexec", "argv_prefix": [], "risk": "low"},')
content = content.replace('{"tool": "process.run", "executable": "su", "risk": "low"},', '{"tool": "process.run", "executable": "su", "argv_prefix": [], "risk": "low"},')
content = content.replace('{"tool": "process.run", "executable": "doas", "risk": "low"}', '{"tool": "process.run", "executable": "doas", "argv_prefix": [], "risk": "low"}')

content = content.replace('{"tool": "process.run", "executable": "ls", "working_roots": ["/allowed/root"]}', '{"tool": "process.run", "executable": "ls", "argv_prefix": [], "working_roots": ["/allowed/root"]}')

with open("tests/test_policy.py", "w") as f:
    f.write(content)
