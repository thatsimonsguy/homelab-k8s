import json
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


class FeedbackDigestChartTest(unittest.TestCase):
    def test_enabled_runs_digest_from_app_image_with_digest_and_alert_credentials_only(self):
        docs = render('feedbackDigest.enabled=true', 'feedbackDigest.suspend=false')
        app = next(d for d in docs if d['kind'] == 'Deployment')['spec']['template']['spec']['containers'][0]
        job = next(d for d in docs if d['kind'] == 'CronJob' and d['metadata']['name'] == 'traceroute-feedback-digest')
        self.assertEqual(job['metadata']['namespace'], 'traceroute')
        self.assertEqual(job['spec']['schedule'], '7 7 * * *')
        self.assertEqual(job['spec']['timeZone'], 'America/Chicago')
        self.assertEqual(job['spec']['concurrencyPolicy'], 'Forbid')
        self.assertIs(job['spec']['suspend'], False)
        self.assertEqual(job['spec']['jobTemplate']['spec']['backoffLimit'], 0)
        pod = job['spec']['jobTemplate']['spec']['template']['spec']
        self.assertIs(pod['automountServiceAccountToken'], False)
        self.assertIs(pod['securityContext']['runAsNonRoot'], True)
        container = pod['containers'][0]
        self.assertEqual(container['image'], app['image'])
        self.assertEqual(container['command'], ['traceroute-feedback-digest'])
        refs = [e['secretRef']['name'] for e in container['envFrom']]
        self.assertEqual(refs, ['traceroute-feedback-digest', 'traceroute-maintenance-alerts'])
        for forbidden in [WRITER, 'traceroute-runtime', 'traceroute-maintenance"', 'traceroute-backup', 'AWS']:
            self.assertNotIn(forbidden, str(container))
        self.assertIs(container['securityContext']['readOnlyRootFilesystem'], True)
        self.assertEqual(container['securityContext']['capabilities'], {'drop': ['ALL']})
        pod_env = [e['name'] for e in container['env']]
        self.assertEqual(pod_env, ['POD_NAME'])
        secret = next(d for d in docs if d['kind'] == 'SealedSecret' and d['metadata']['name'] == 'traceroute-feedback-digest')
        self.assertEqual(secret['metadata']['namespace'], 'traceroute')
        self.assertEqual(list(secret['spec']['encryptedData']), ['TRACEROUTE_FEEDBACK_DATABASE_URL'])

    def test_suspend_pauses_the_schedule_without_removing_it(self):
        docs = render('feedbackDigest.enabled=true', 'feedbackDigest.suspend=true')
        job = next(d for d in docs if d['kind'] == 'CronJob' and d['metadata']['name'] == 'traceroute-feedback-digest')
        self.assertIs(job['spec']['suspend'], True)

    def test_disabled_removes_digest_job_and_credential(self):
        docs = render('feedbackDigest.enabled=false')
        self.assertFalse(any(d['kind'] == 'CronJob' and d['metadata']['name'] == 'traceroute-feedback-digest' for d in docs))
        self.assertFalse(any(d['metadata']['name'] == 'traceroute-feedback-digest' for d in docs))
        self.assertNotIn('TRACEROUTE_FEEDBACK_DATABASE_URL', str(docs))


class ObservabilityChartTest(unittest.TestCase):
    """TRA-4: metrics and probes on their own port, never on the routed one."""

    def test_operations_port_is_scraped_and_probed_but_never_routed(self):
        docs = render('observability.enabled=true')
        app = next(d for d in docs if d['kind'] == 'Deployment')['spec']['template']['spec']['containers'][0]
        args = app['args']
        self.assertEqual(args[:2], ['-listen', '0.0.0.0:8090'])
        self.assertEqual(args[args.index('-ops-listen')+1], '0.0.0.0:9090')
        self.assertEqual([p['containerPort'] for p in app['ports']], [8090, 9090])
        # Startup gates first traffic on the database; readiness and liveness answer for
        # the process, so a dependency outage degrades rather than removing the pod.
        self.assertEqual(app['startupProbe']['httpGet'], {'path': '/readyz', 'port': 'ops'})
        self.assertEqual(app['readinessProbe']['httpGet'], {'path': '/healthz', 'port': 'ops'})
        self.assertEqual(app['livenessProbe']['httpGet'], {'path': '/healthz', 'port': 'ops'})
        service = next(d for d in docs if d['kind'] == 'Service')
        self.assertEqual(service['metadata']['labels'], {'app': 'traceroute'})
        self.assertEqual([p['port'] for p in service['spec']['ports']], [8090, 9090])
        # The tunnel reaches the product port alone.
        route = next(d for d in docs if d['kind'] == 'IngressRoute')
        self.assertEqual([s['port'] for s in route['spec']['routes'][0]['services']], [8090])
        monitor = next(d for d in docs if d['kind'] == 'ServiceMonitor')
        self.assertEqual(monitor['metadata']['labels']['release'], 'kube-prometheus-stack')
        self.assertEqual(monitor['spec']['selector']['matchLabels'], {'app': 'traceroute'})
        self.assertEqual(monitor['spec']['endpoints'][0]['port'], 'ops')
        self.assertEqual(monitor['spec']['endpoints'][0]['path'], '/metrics')

    def test_disabled_leaves_the_listener_exactly_as_it_was(self):
        docs = render('observability.enabled=false', 'observability.rules=false', 'observability.dashboard=false')
        app = next(d for d in docs if d['kind'] == 'Deployment')['spec']['template']['spec']['containers'][0]
        self.assertNotIn('-ops-listen', app['args'])
        self.assertEqual([p['containerPort'] for p in app['ports']], [8090])
        self.assertEqual(app['readinessProbe']['tcpSocket'], {'port': 'http'})
        self.assertFalse(any(d['kind'] in ('ServiceMonitor', 'PrometheusRule') for d in docs))
        self.assertEqual([p['port'] for p in next(d for d in docs if d['kind'] == 'Service')['spec']['ports']], [8090])

    def test_alerts_cover_the_listener_and_every_scheduled_job(self):
        docs = render('observability.rules=true')
        rule = next(d for d in docs if d['kind'] == 'PrometheusRule')
        self.assertEqual(rule['metadata']['labels']['release'], 'kube-prometheus-stack')
        alerts = {r['alert']: r for g in rule['spec']['groups'] for r in g['rules']}
        for name in ['TracerouteListenerDown', 'TracerouteServerErrors', 'TracerouteLatencyHigh',
                     'TracerouteRestarting', 'TracerouteJobFailed', 'TraceroutePurgeStale',
                     'TracerouteBackupStale', 'TracerouteFeedbackDigestStale']:
            self.assertIn(name, alerts)
            self.assertEqual(alerts[name]['labels']['team'], 'traceroute')
        for cronjob in ['traceroute-workspace-purge', 'traceroute-database-backup', 'traceroute-feedback-digest']:
            self.assertIn(cronjob, str(rule))

    def test_dashboard_is_valid_json_the_grafana_sidecar_will_import(self):
        docs = render('observability.dashboard=true')
        board = next(d for d in docs if d['kind'] == 'ConfigMap' and d['metadata']['name'] == 'traceroute-dashboard')
        self.assertEqual(board['metadata']['labels']['grafana_dashboard'], '1')
        dashboard = json.loads(board['data']['traceroute.json'])
        self.assertEqual(dashboard['uid'], 'traceroute')
        queries = [t['expr'] for p in dashboard['panels'] for t in p.get('targets', [])]
        self.assertTrue(any('traceroute_http_requests_total' in q for q in queries))
        self.assertTrue(any('traceroute_mcp_tool_calls_total' in q for q in queries))
        self.assertTrue(any('traceroute_browser_sessions' in q for q in queries))
        self.assertTrue(any('traceroute_db_pool_' in q for q in queries))
