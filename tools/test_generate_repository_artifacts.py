from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from generate_repository_artifacts import run
class TestGenerator(unittest.TestCase):
 def repo(self,r:Path,mirror=False):
  (r/'sample/agents').mkdir(parents=True); (r/'sample/SKILL.md').write_text('---\nname: sample\ndescription: Sample.\n---\n'); (r/'sample/agents/openai.yaml').write_text('x')
  m={'schema_version':1,'policy':{'catalog_groups':[{'key':'repository-owned','title':'Repository owned','description':'Original.'}]},'shared_components':[],'generated_mirrors':([{'source':'sample/SKILL.md','destination':'.claude/skills/sample/SKILL.md','transform':'copy-with-generated-notice'}] if mirror else []),'skills':[{'name':'sample','path':'sample','catalog_group':'repository-owned','status':'supported','description':'Sample.','platforms':['linux'],'agents':['codex'],'source':{'classification':'repo-owned-original'},'validation':{'hosted_commands':[],'environment_dependent_commands':[]}}]}
  (r/'skills-manifest.json').write_text(json.dumps(m)); (r/'README.md').write_text('\n'.join(f'<!-- BEGIN GENERATED: {k} -->\nstale\n<!-- END GENERATED: {k} -->' for k in ('skill-catalog','installation-inventory','platform-agent-matrix','validation-summary')))
 def test_write_then_check(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t); self.repo(r); self.assertEqual(run(r,False),[]); self.assertEqual(run(r,True),[]); self.assertIn('Repository owned',(r/'README.md').read_text())
 def test_stale_fails(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t); self.repo(r); self.assertTrue(run(r,True))
 def test_mirror_hashes_and_notice(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t); self.repo(r,True); run(r,False); self.assertIn('GENERATED MIRROR',(r/'.claude/skills/sample/SKILL.md').read_text()); reg=json.loads((r/'.generated/agent-mirrors.json').read_text()); self.assertEqual(len(reg['mirrors'][0]['source_sha256']),64); self.assertEqual(run(r,True),[])
 def test_legacy_mirror_fails(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t); self.repo(r); p=r/'.claude/skills/old/SKILL.md'; p.parent.mkdir(parents=True); p.write_text('old'); self.assertTrue(any('unexpected files' in e for e in run(r,True)))
if __name__=='__main__': unittest.main(verbosity=2)
