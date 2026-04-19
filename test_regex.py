import re
content = """
Some text
```mermaid
graph TD;
A-->B;
```
More text
:::mermaid
graph LR;
C-->D;
:::
Even more text
"""
pattern = re.compile(r'(```|:::)mermaid\s*\n(.*?)\n\1', re.DOTALL)
for match in pattern.finditer(content):
    print("MATCH!")
    print(match.group(2).strip())
