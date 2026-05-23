from pathlib import Path
import re

files = [Path('README.md'), Path('QUICK_START.md')]
for path in files:
    lines = path.read_text(encoding='utf-8').splitlines()
    out = []
    in_code = False
    code_fence = None
    fence_re = re.compile(r'^(?P<fence>`{3,})(?P<lang>\w+)?\s*$')
    for i, line in enumerate(lines):
        m = fence_re.match(line)
        if m:
            if not in_code:
                if not m.group('lang'):
                    line = m.group('fence') + 'bash'
                in_code = True
                code_fence = m.group('fence')
            else:
                in_code = False
                code_fence = None
            out.append(line)
            continue

        if not in_code and re.match(r'^(#{2,6})\s+', line):
            if out and out[-1].strip() != '':
                out.append('')
            out.append(line)
            next_line = lines[i+1] if i+1 < len(lines) else ''
            if next_line.strip() != '':
                out.append('')
            continue

        if not in_code:
            line = line.replace('http://localhost:8000/docs', '[http://localhost:8000/docs](http://localhost:8000/docs)')
            line = line.replace('http://localhost:8000', '[http://localhost:8000](http://localhost:8000)')
        out.append(line)
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')

ignore_path = Path('.markdownlintignore')
ignore_path.write_text('venv/**\nremote_test_clone/**\n', encoding='utf-8')
print('Updated docs and .markdownlintignore')
