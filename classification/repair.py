"""Repair omissions from otherwise valid partial model outputs; keep provenance.

Only missing IDs are sent again. Invalid/extra/duplicate IDs are not repaired by
guessing; those failures need inspection. Never overwrite a successful batch.
"""
from datetime import datetime, timezone
import json
import subprocess
from classify import ROOT, SOURCE, MODEL, read, save, digest
import csv


def main():
    work = ROOT / 'work'
    manifest = read(work / 'manifest.json')
    assert manifest['source_sha256'] == digest(SOURCE)
    sources = {r['provider'] + ':' + r['native_id']: r for r in csv.DictReader(SOURCE.open())}
    for batch in manifest['batches']:
        path = work / f'{batch["id"]}.receipt.json'
        if not path.exists() or read(path)['exit_code'] == 0:
            continue
        previous = read(path)
        response = read(work / f'{batch["id"]}.stdout.json')
        labels = response['structured_output']['records']
        by_id = {r['id']: r for r in labels}
        assert len(labels) == len(by_id) and set(by_id) <= set(batch['ids'])
        missing = [uid for uid in batch['ids'] if uid not in by_id]
        if not missing:
            save(work / f'{batch["id"]}.failed-receipt.json', previous)
            save(work / f'{batch["id"]}.labels.json', [by_id[uid] for uid in batch['ids']])
            save(path, dict(batch=batch['id'], model_requested=MODEL,
                started_at=previous['started_at'], ended_at=datetime.now(timezone.utc).isoformat(), exit_code=0,
                prompt_sha256=batch['prompt_sha256'], response_sha256=digest(work / f'{batch["id"]}.stdout.json'),
                model_usage=response.get('modelUsage') or {}, usage=response.get('usage') or {},
                repair=dict(type='order-only', model_call=False)))
            print('Restored source order for', batch['id'], flush=True)
            continue
        print('Repair', batch['id'], 'missing', len(missing), flush=True)
        prompt = (ROOT / 'instructions.txt').read_text() + '\nTAXONOMY\n' + (ROOT / 'taxonomy.json').read_text()
        prompt += '\nReturn ALL ' + str(len(missing)) + ' records below, exactly once.\nPAPERS\n'
        prompt += json.dumps([dict(id=uid, title=sources[uid]['title'], abstract=sources[uid]['abstract']) for uid in missing], ensure_ascii=False)
        prompt_path = work / f'{batch["id"]}.repair.prompt.txt'
        prompt_path.write_text(prompt)
        command = ['claude', '--print', '--model', MODEL, '--tools', '', '--effort', 'medium',
                   '--settings', '{"disableAllHooks":true}', '--no-session-persistence',
                   '--output-format', 'json', '--json-schema', (ROOT / 'schema.json').read_text()]
        started = datetime.now(timezone.utc).isoformat()
        result = subprocess.run(command, input=prompt, text=True, capture_output=True, timeout=600)
        raw_path = work / f'{batch["id"]}.repair.response.json'
        raw_path.write_text(result.stdout)
        assert result.returncode == 0, result.stderr
        repaired = json.loads(result.stdout)
        assert not repaired.get('is_error')
        new = repaired['structured_output']['records']
        assert [r['id'] for r in new] == missing
        by_id.update({r['id']: r for r in new})
        assert set(by_id) == set(batch['ids'])
        save(work / f'{batch["id"]}.failed-receipt.json', previous)
        save(work / f'{batch["id"]}.labels.json', [by_id[uid] for uid in batch['ids']])
        save(path, dict(batch=batch['id'], model_requested=MODEL,
            started_at=previous['started_at'], ended_at=datetime.now(timezone.utc).isoformat(), exit_code=0,
            prompt_sha256=batch['prompt_sha256'],
            response_sha256=digest(work / f'{batch["id"]}.stdout.json'),
            model_usage=response.get('modelUsage') or {}, usage=response.get('usage') or {},
            repair=dict(missing_ids=missing, prompt_sha256=digest(prompt_path), response_sha256=digest(raw_path),
                        started_at=started, model_usage=repaired.get('modelUsage') or {}, usage=repaired.get('usage') or {})))
        print('Repaired', batch['id'], flush=True)


if __name__ == '__main__':
    main()
