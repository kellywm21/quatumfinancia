import glob
from pathlib import Path
report=[]
for path in sorted(glob.glob('src/api/*.py')):
    lines = Path(path).read_text(encoding='utf-8').splitlines()
    for idx,line in enumerate(lines):
        if line.strip().startswith('@router.') and idx+1 < len(lines):
            i = idx+1
            fn_line = lines[i].strip()
            if fn_line.startswith('def '):
                signature = fn_line
                while not signature.rstrip().endswith(':') and i+1 < len(lines):
                    i += 1
                    signature += ' ' + lines[i].strip()
                if 'Depends(get_current' not in signature and 'Depends(oauth2_scheme)' not in signature and 'Depends(get_current_user)' not in signature and 'Depends(get_current_active_user)' not in signature and 'Depends(get_current_admin_user)' not in signature:
                    report.append((path, idx+2, fn_line.split('def ')[1].split('(')[0], signature))
print('Total unprotected route handlers:', len(report))
for p,l,f,s in report:
    print(p, l, f)
