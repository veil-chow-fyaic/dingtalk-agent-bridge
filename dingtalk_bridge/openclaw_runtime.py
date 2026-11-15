"""Restricted local OpenClaw host contract, reviewed against 41f2b981.

The operator supplies a dedicated, immutable JSON config. We reference it, never
copy credentials or merge an ambient OpenClaw installation. This is not a sandbox.
"""
import hashlib
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from .agent_runtime import RuntimeFailure, RuntimeResultError, checked_pi_session

WORKSPACE = '${DAB_OPENCLAW_WORKSPACE}'


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:raise ValueError('duplicate key')
            result[key] = value
        return result
    def invalid(_):raise ValueError('nonfinite constant')
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def host_identity(settings):
    spec = settings.get('openclaw')
    if not isinstance(spec, dict) or set(spec) != {'configPath', 'configSha256'}:
        raise ValueError('openclaw_host_config_required')
    path, digest = spec['configPath'], spec['configSha256']
    if (not isinstance(path, str) or not Path(path).is_absolute() or
        any(ord(c) < 32 for c in path) or not isinstance(digest, str) or
        not re.fullmatch('[0-9a-f]{64}', digest)):
        raise ValueError('openclaw_host_identity_invalid')
    return {'contract': 'openclaw-local-v1', 'configPath': str(Path(path).resolve()),
            'configSha256': digest, 'agentId': 'main'}


def expected_agents(model):
    return {'defaults': {'systemAgent': {'agentId': 'main'}, 'workspace': WORKSPACE,
            'cwd': WORKSPACE, 'repoRoot': WORKSPACE, 'skipBootstrap': True, 'skills': [],
            'model': {'primary': model}, 'models': {model: {'agentRuntime': {'id': 'openclaw'}}}},
            'entries': {'main': {}}}


def validate_host_config(settings):
    identity = host_identity(settings)
    try:
        path = Path(identity['configPath'])
        if path.stat().st_size > 1024 * 1024:raise ValueError('oversized')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != identity['configSha256']:
            raise ValueError('digest changed')
        config = strict_json(raw)
        def reject_includes(value):
            if isinstance(value, dict):
                if '$include' in value:raise ValueError('external include')
                for child in value.values():reject_includes(child)
            elif isinstance(value, list):
                for child in value:reject_includes(child)
        reject_includes(config)
        model = settings.get('model')
        if not isinstance(model, str) or '/' not in model:raise ValueError('model required')
        provider, model_id = model.split('/', 1)
        # A small explicit host surface: no alternate agents, remote ACP,
        # include files, channel delivery, shell env injection or plugin discovery.
        if (set(config) != {'agents', 'models', 'plugins', 'env', 'tools'} or
            config['agents'] != expected_agents(model) or
            config['plugins'] != {'enabled': False} or
            config['env'] != {'shellEnv': {'enabled': False}} or
            config['tools'] != {'allow': ['exec', 'process'], 'codeMode': False, 'swarm': False,
                'exec': {'host': 'gateway', 'security': 'full', 'ask': 'off'},
                'fs': {'workspaceOnly': True}}):raise ValueError('host shape')
        models = config['models']
        if set(models) != {'mode', 'providers'} or models['mode'] != 'replace':raise ValueError('models')
        if set(models['providers']) != {provider}:raise ValueError('provider')
        declared = models['providers'][provider]
        if (not isinstance(declared, dict) or declared.get('api') != 'openai-completions' or
            not isinstance(declared.get('apiKey'), str) or not declared['apiKey'].strip() or
            '$' in declared['apiKey'] or set(declared) - {'api', 'apiKey', 'baseUrl', 'models', 'request'}):
            raise ValueError('explicit provider required')
        url = urlsplit(declared.get('baseUrl', ''))
        if url.scheme not in {'http', 'https'} or not url.hostname:
            raise ValueError('explicit provider endpoint required')
        entries = declared['models']
        if not isinstance(entries, list) or len(entries) != 1 or entries[0].get('id') != model_id:
            raise ValueError('model entry')
        # Only these three exact substitutions are needed. Do not let provider
        # metadata or an included configuration redirect the bound host.
        remaining = dict(config);remaining.pop('agents')
        if '${' in json.dumps(remaining):raise ValueError('ambient substitution')
    except (OSError, ValueError, TypeError, KeyError, AttributeError, UnicodeError) as exc:
        raise RuntimeFailure('openclaw_host_config_invalid', 'configuration') from exc
    return identity


class OpenClawHost:
    def __init__(self, settings):
        self.settings = settings
        self.identity = validate_host_config(settings)

    def command(self, session_id, timeout):
        return [self.settings['binary'], 'agent', '--local', '--agent', 'main',
                '--session-id', checked_pi_session(session_id), '--json',
                '--timeout', str(math.ceil(timeout)), '--message-file', '-']

    def environment(self, workspace, inherited):
        # Revalidate before each turn; a changed config is not silently resumed.
        if validate_host_config(self.settings) != self.identity:
            raise RuntimeFailure('openclaw_host_config_changed', 'configuration')
        workspace = Path(workspace).resolve()
        if Path(self.identity['configPath']).is_relative_to(workspace):
            raise RuntimeFailure('openclaw_config_inside_workspace', 'configuration')
        root = workspace / '.openclaw-host'
        profile = 'dab-host-' + hashlib.sha256(str(workspace).encode()).hexdigest()[:24]
        if (Path.home() / ('.openclaw-' + profile)).exists():
            raise RuntimeFailure('openclaw_ambient_profile_exists', 'configuration')
        for name in ('home', 'state', 'cache', 'tmp'):
            directory = root / name
            if directory.resolve() != directory:
                raise RuntimeFailure('openclaw_host_path_escaped', 'configuration')
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        # No inherited provider keys, OPENCLAW_*, NODE_OPTIONS, shell hooks or
        # default profile. HOME/CODEX_HOME are not repurposed. Native OS home
        # access is still possible; this is an environment boundary, not a jail.
        allowed = {'PATH', 'LANG', 'LC_ALL', 'TZ', 'HTTP_PROXY', 'HTTPS_PROXY',
                   'ALL_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy'}
        env = {k: v for k, v in inherited.items() if k in allowed}
        env.update({'SHELL': '/bin/sh', 'OPENCLAW_NO_RESPAWN': '1',
            'OPENCLAW_LOAD_SHELL_ENV': '0', 'OPENCLAW_DEFER_SHELL_ENV_FALLBACK': '1',
            'OPENCLAW_CONFIG_READONLY': '1', 'OPENCLAW_CONFIG_PATH': self.identity['configPath'],
            'OPENCLAW_HOME': str(root / 'home'), 'OPENCLAW_STATE_DIR': str(root / 'state'),
            'XDG_CACHE_HOME': str(root / 'cache'), 'TMPDIR': str(root / 'tmp'),
            'DAB_OPENCLAW_WORKSPACE': str(workspace), 'NO_COLOR': '1',
            'OPENCLAW_PROFILE': profile})
        return env


def terminal_text(raw, session_id, exit_code):
    """Whole local-agent JSON only; neither exit zero nor payload text is enough."""
    if exit_code != 0:raise RuntimeFailure('runtime_exit_nonzero')
    try:
        result = strict_json(raw)
        if not isinstance(result, dict) or not isinstance(result.get('meta'), dict):raise ValueError('meta')
        meta = result['meta']
        agent = meta.get('agentMeta')
        if not isinstance(agent, dict):raise ValueError('agentMeta')
        checked_pi_session(agent.get('sessionId'), session_id)
        completion = meta.get('completion')
        if (meta.get('stopReason') != 'stop' or meta.get('aborted') is not False or
            meta.get('error') is not None or meta.get('timeoutPhase') is not None or
            ('replayInvalid' in meta and type(meta['replayInvalid']) is not bool) or
            not isinstance(completion, dict) or completion.get('stopReason') != 'stop' or
            completion.get('finishReason', 'stop') != 'stop'):
            raise RuntimeFailure('runtime_turn_failed', 'unknown')
        # replayInvalid=true also marks successful side-effecting tools. It
        # forbids replay, not delivery of a settled successful result. The
        # gateway already never automatically replays an attempted turn.
        if 'toolSummary' in meta:
            summary = meta['toolSummary']
            if (not isinstance(summary, dict) or type(summary.get('failures')) is not int or
                summary['failures'] != 0 or summary.get('unresolvedError') is not None):
                raise RuntimeFailure('runtime_turn_failed', 'unknown')
        text = meta.get('finalAssistantVisibleText')
        if not isinstance(text, str) or not text.strip():raise RuntimeResultError('runtime_result_missing')
        return text
    except (ValueError, TypeError, UnicodeError) as exc:
        if isinstance(exc, RuntimeFailure):raise
        raise RuntimeFailure('runtime_protocol_invalid') from exc
