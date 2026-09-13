import os
import pathlib
import subprocess
import unittest
import yaml

CHART = pathlib.Path(__file__).resolve().parents[1]
WRITER = 'traceroute-aws-journal-writer'


def render(*settings):
    command = [os.environ.get('HELM', 'helm'), 'template', str(CHART)]
    for setting in settings: command += ['--set', setting]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode: raise ValueError('Helm render failed')
    return [d for d in yaml.safe_load_all(result.stdout) if d]


class PublicationChartTest(unittest.TestCase):
    def test_enabled_wires_only_service_and_uses_matching_maintenance_image(self):
        docs = render('publication.enabled=true', 'maintenance.suspend=false')
        deployment = next(d for d in docs if d['kind'] == 'Deployment')
        app = deployment['spec']['template']['spec']['containers'][0]
        refs = [e['secretRef']['name'] for e in app['envFrom']]
        self.assertEqual(refs, ['traceroute-runtime', WRITER])
        args = app['args']
        self.assertEqual(args[:2], ['-listen', '0.0.0.0:8090'])
        for flag in ['-publication-journal-bucket', '-publication-journal-account', '-publication-journal-id']:
            self.assertTrue(args[args.index(flag)+1])
        secret = next(d for d in docs if d['kind'] == 'SealedSecret' and d['metadata']['name'] == WRITER)
        self.assertEqual(secret['metadata']['namespace'], 'traceroute')
        for job in [d for d in docs if d['kind'] == 'CronJob']:
            container = job['spec']['jobTemplate']['spec']['template']['spec']['containers'][0]
            self.assertNotIn(WRITER, str(container))
            if job['metadata']['name'] == 'traceroute-workspace-purge':
                self.assertEqual(container['image'], app['image'])
                self.assertIs(job['spec']['suspend'], False)

    def test_disabled_removes_credentials_and_publication_arguments(self):
        docs = render('publication.enabled=false', 'maintenance.suspend=true')
        self.assertFalse(any(d['metadata']['name'] == WRITER for d in docs))
        app = next(d for d in docs if d['kind'] == 'Deployment')['spec']['template']['spec']['containers'][0]
        self.assertNotIn(WRITER, str(app))
        self.assertNotIn('publication-journal', str(app))
        purge = next(d for d in docs if d['kind'] == 'CronJob' and d['metadata']['name'] == 'traceroute-workspace-purge')
        self.assertIs(purge['spec']['suspend'], True)

    def test_missing_journal_settings_fail_render(self):
        for field in ['publication.bucket', 'backup.expectedAccount', 'backup.journalID']:
            with self.subTest(field=field), self.assertRaises(ValueError):
                render('publication.enabled=true', field + '=')
