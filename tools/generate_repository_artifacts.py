from __future__ import annotations
import argparse,difflib,hashlib,json,sys
from pathlib import Path
from typing import Any
MANIFEST='skills-manifest.json'; README='README.md'; MIRROR_ROOT=Path('.claude/skills'); REGISTRY=Path('.generated/agent-mirrors.json')
SECTIONS=('skill-catalog','installation-inventory','platform-agent-matrix','validation-summary')

def load(root:Path)->dict[str,Any]:
 data=json.loads((root/MANIFEST).read_text(encoding='utf-8'))
 if not isinstance(data.get('skills'),list): raise ValueError('manifest skills must be a list')
 return data

def groups(m): return {g['key']:g for g in m['policy']['catalog_groups']}
def active(m): return [s for s in m['skills'] if s.get('status')!='archived']
def notice(name): return f'<!-- Generated section: {name}. Source: {MANIFEST}. Generator: tools/generate_repository_artifacts.py. Do not edit by hand. -->'
def fmt(xs): return ', '.join(f'`{x}`' for x in xs) if xs else '—'
def source(s):
 x=s.get('source',{}); c=x.get('classification','unspecified').replace('-',' ')
 return f"{c}; `{x['repository']}`" if x.get('repository') else c

def by_group(m):
 out={k:[] for k in groups(m)}
 for s in active(m): out[s['catalog_group']].append(s)
 for v in out.values(): v.sort(key=lambda x:x['name'])
 return out

def catalog(m):
 out=[notice('skill catalog')]; bg=by_group(m)
 for g in m['policy']['catalog_groups']:
  out += ['',f"### {g['title']}",'',g['description'],'','| Skill | Purpose | Provenance |','| --- | --- | --- |']
  for s in bg[g['key']]: out.append(f"| [`{s['name']}`](./{s['path']}) | {s['description']} | {source(s)} |")
 return '\n'.join(out)
def installation(m):
 comps={s['name']:[] for s in active(m)}
 for c in m.get('shared_components',[]):
  for n in c.get('consumers',[]): comps.setdefault(n,[]).append(c['path'])
 out=[notice('installation inventory'),'','Top-level skill directories are canonical. Copy only the skills required by the target agent, plus listed shared components.','','| Skill | Canonical directory | Shared components |','| --- | --- | --- |']
 for s in sorted(active(m),key=lambda x:x['name']): out.append(f"| `{s['name']}` | [`{s['path']}`](./{s['path']}) | {fmt(comps.get(s['name'],[]))} |")
 return '\n'.join(out)
def matrix(m):
 out=[notice('platform and agent matrix'),'','| Skill | Platforms | Agents | Status |','| --- | --- | --- | --- |']
 for s in sorted(active(m),key=lambda x:x['name']): out.append(f"| [`{s['name']}`](./{s['path']}) | {fmt(s.get('platforms',[]))} | {fmt(s.get('agents',[]))} | `{s['status']}` |")
 return '\n'.join(out)
def validations(m):
 out=[notice('validation summary'),'','| Skill | Hosted commands | Environment-dependent commands |','| --- | ---: | ---: |']
 for s in sorted(active(m),key=lambda x:x['name']):
  v=s.get('validation',{}); out.append(f"| `{s['name']}` | {len(v.get('hosted_commands',[]))} | {len(v.get('environment_dependent_commands',[]))} |")
 return '\n'.join(out)
def replace(text,key,body):
 a=f'<!-- BEGIN GENERATED: {key} -->'; b=f'<!-- END GENERATED: {key} -->'
 if a not in text or b not in text: raise ValueError(f'README missing markers for {key}')
 pre,rest=text.split(a,1); _,post=rest.split(b,1); return f'{pre}{a}\n{body}\n{b}{post}'
def render_readme(text,m):
 bodies={'skill-catalog':catalog(m),'installation-inventory':installation(m),'platform-agent-matrix':matrix(m),'validation-summary':validations(m)}
 for k in SECTIONS: text=replace(text,k,bodies[k])
 return text
def mirror_notice(text,src,transform):
 n=f'<!-- GENERATED MIRROR. Source: {src}. Transform: {transform}. Generator: tools/generate_repository_artifacts.py. Do not edit directly. -->'
 lines=text.splitlines()
 if lines and lines[0]=='---':
  i=lines[1:].index('---')+1; lines.insert(i+1,n); return '\n'.join(lines)+('\n' if text.endswith('\n') else '')
 return n+'\n'+text
def expected_mirrors(root,m):
 files={}; rows=[]
 for x in m.get('generated_mirrors',[]):
  src=Path(x['source']); dst=Path(x['destination']); tr=x['transform']
  if dst.is_absolute() or not dst.is_relative_to(MIRROR_ROOT): raise ValueError('mirror destination must be under .claude/skills')
  if tr!='copy-with-generated-notice': raise ValueError(f'unsupported mirror transform: {tr}')
  sb=(root/src).read_bytes(); db=mirror_notice(sb.decode(),src.as_posix(),tr).encode(); files[dst]=db
  rows.append({'source':src.as_posix(),'destination':dst.as_posix(),'transform':tr,'source_sha256':hashlib.sha256(sb).hexdigest(),'destination_sha256':hashlib.sha256(db).hexdigest()})
 reg={'_generated_notice':f'Generated from {MANIFEST}; do not edit by hand.','schema_version':1,'mirrors':sorted(rows,key=lambda x:x['destination'])}
 return files,(json.dumps(reg,indent=2,sort_keys=True)+'\n').encode()
def run(root,check):
 m=load(root); errors=[]; rp=root/README; actual=rp.read_text(encoding='utf-8'); expected=render_readme(actual,m)
 if actual!=expected:
  if check: errors.append('stale generated README sections\n'+''.join(difflib.unified_diff(actual.splitlines(True),expected.splitlines(True),fromfile='README.md',tofile='README.md (generated)')))
  else: rp.write_text(expected,encoding='utf-8')
 files,reg=expected_mirrors(root,m); mr=root/MIRROR_ROOT
 existing={p.relative_to(root) for p in mr.rglob('*') if p.is_file()} if mr.exists() else set(); unexpected=existing-set(files)
 if unexpected:
  if check: errors.append('unexpected files under .claude/skills: '+', '.join(sorted(p.as_posix() for p in unexpected)))
  else:
   for p in unexpected: (root/p).unlink()
 for p,data in files.items():
  q=root/p; old=q.read_bytes() if q.exists() else b''
  if old!=data:
   if check: errors.append(f'stale generated mirror: {p}')
   else: q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(data)
 q=root/REGISTRY; old=q.read_bytes() if q.exists() else b''
 if old!=reg:
  if check: errors.append(f'stale generated registry: {REGISTRY}')
  else: q.parent.mkdir(parents=True,exist_ok=True); q.write_bytes(reg)
 if not check and mr.exists():
  for p in sorted([p for p in mr.rglob('*') if p.is_dir()],reverse=True):
   try:p.rmdir()
   except OSError:pass
 return errors
def main():
 p=argparse.ArgumentParser(); p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1]); p.add_argument('--check',action='store_true'); a=p.parse_args()
 try: errors=run(a.repo_root.resolve(),a.check)
 except Exception as e: print(f'ERROR: {e}',file=sys.stderr); return 1
 if errors:
  for e in errors: print(f'ERROR: {e}',file=sys.stderr)
  return 1
 print(('Validated' if a.check else 'Generated')+' repository artifacts from skills-manifest.json.'); return 0
if __name__=='__main__': raise SystemExit(main())
