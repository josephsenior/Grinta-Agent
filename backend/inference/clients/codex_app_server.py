"""Official local bridge to ``codex app-server``.

The app-server manages ChatGPT OAuth itself.  This adapter intentionally never
reads, accepts, or exports OAuth tokens; it only speaks the documented JSON-RPC
protocol over a child process' stdin/stdout.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from backend.inference.clients.base import DirectLLMClient, LLMResponse


class CodexAppServerError(RuntimeError):
    """Raised when the local Codex app-server cannot complete a request."""


class CodexAppServerClient(DirectLLMClient):
    """Adapt a Codex agent turn to Grinta's direct-client response contract.

    Codex has its own tool executor, so this provider deliberately does not
    expose native function calls to Grinta.  Each completion is an ephemeral
    Codex thread rooted in the current workspace.
    """

    def __init__(self, model_name: str = 'default', *, timeout: float | int | None = None) -> None:
        self._model_name = model_name
        self._timeout = float(timeout) if timeout else None
        self._process: subprocess.Popen[str] | None = None
        self._next_id = 1
        self._lock = threading.Lock()

    def completion(self, messages: list[dict[str, Any]], **kwargs: Any) -> LLMResponse:
        with self._lock:
            self._ensure_started()
            prompt = self._messages_to_prompt(messages)
            thread = self._request(
                'thread/start',
                self._thread_params(kwargs.get('reasoning_effort')),
            )
            thread_id = str((thread.get('thread') or thread).get('id') or '')
            if not thread_id:
                raise CodexAppServerError('Codex app-server did not return a thread id.')
            turn = self._request(
                'turn/start',
                {'threadId': thread_id, 'input': [{'type': 'text', 'text': prompt}]},
            )
            turn_id = str((turn.get('turn') or turn).get('id') or '')
            content, usage = self._wait_for_turn(turn_id)
            if not content:
                raise CodexAppServerError('Codex completed without an agent message.')
            return LLMResponse(
                content=content,
                model=self._model_name,
                usage=usage,
                response_id=turn_id,
            )

    async def acompletion(self, messages: list[dict[str, Any]], **kwargs: Any) -> LLMResponse:
        return await asyncio.to_thread(self.completion, messages, **kwargs)

    async def astream(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        """Forward Codex's text and reasoning deltas as they arrive.

        The app-server is blocking JSONL, so its reader runs in a worker
        thread and hands each protocol delta back to this async generator.
        """
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, Any] | BaseException | None] = asyncio.Queue()

        def emit(delta: dict[str, Any]) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, delta)

        def run() -> None:
            try:
                self._stream_turn(messages, kwargs.get('reasoning_effort'), emit)
            except BaseException as exc:
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        worker = asyncio.create_task(asyncio.to_thread(run))
        try:
            while True:
                item = await queue.get()
                if item is None:
                    await worker
                    return
                if isinstance(item, BaseException):
                    raise item
                yield {'choices': [{'delta': item}]}
        finally:
            if worker.done():
                await worker

    def close(self) -> None:
        process = self._process
        self._process = None
        if process and process.poll() is None:
            process.terminate()

    def ensure_authenticated(self) -> None:
        """Start Codex and complete managed ChatGPT login when required."""
        with self._lock:
            self._ensure_started()

    def list_available_models(self) -> list[str]:
        """Return this signed-in account's picker-visible Codex model ids."""
        with self._lock:
            self._ensure_started()
            cursor: str | None = None
            models: list[str] = []
            while True:
                result = self._request(
                    'model/list', {'cursor': cursor, 'includeHidden': False}
                )
                for item in result.get('data') or []:
                    if not isinstance(item, dict):
                        continue
                    model = str(item.get('model') or item.get('id') or '').strip()
                    if model and model not in models:
                        models.append(model)
                cursor_value = result.get('nextCursor')
                cursor = str(cursor_value).strip() if cursor_value else None
                if not cursor:
                    return models

    def _ensure_started(self) -> None:
        if self._process and self._process.poll() is None:
            return
        # npm places a PowerShell shim first on PATH on Windows.  Popen cannot
        # execute that .ps1 file directly, whereas the adjacent .cmd shim is
        # designed for child-process invocation.
        executable = (
            shutil.which('codex.cmd')
            if sys.platform == 'win32'
            else shutil.which('codex')
        )
        if not executable:
            raise CodexAppServerError(
                'Codex CLI is required. Install it, then run `codex login` to sign in with ChatGPT.'
            )
        self._process = subprocess.Popen(
            [executable, 'app-server', '--stdio'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            bufsize=1,
            cwd=os.getcwd(),
        )
        self._request(
            'initialize',
            {'clientInfo': {'name': 'grinta', 'title': 'Grinta', 'version': '1.0'}},
        )
        self._notify('initialized', {})
        account = self._request('account/read', {'refreshToken': True})
        if not (account.get('account') or {}).get('type') == 'chatgpt':
            self._start_chatgpt_login()

    def _start_chatgpt_login(self) -> None:
        """Use Codex's documented managed-OAuth browser flow.

        The URL is generated by Codex and completes on its localhost callback;
        Grinta only opens it and waits for the app-server notification.
        """
        login = self._request(
            'account/login/start',
            {
                'type': 'chatgpt',
                'useHostedLoginSuccessPage': True,
                'appBrand': 'codex',
            },
        )
        auth_url = str(login.get('authUrl') or '')
        login_id = str(login.get('loginId') or '')
        if not auth_url or not login_id:
            raise CodexAppServerError('Codex did not provide a ChatGPT login URL.')
        if not webbrowser.open(auth_url, new=2):
            raise CodexAppServerError(
                f'Open this URL to sign in with ChatGPT, then retry: {auth_url}'
            )
        while True:
            message = self._read()
            if message.get('method') != 'account/login/completed':
                continue
            params = message.get('params') or {}
            if str(params.get('loginId') or '') != login_id:
                continue
            if not params.get('success'):
                raise CodexAppServerError(
                    f"ChatGPT sign-in did not complete: {params.get('error') or 'cancelled'}"
                )
            account = self._request('account/read', {'refreshToken': True})
            if (account.get('account') or {}).get('type') == 'chatgpt':
                return
            raise CodexAppServerError('ChatGPT sign-in completed, but Codex has no active ChatGPT account.')

    def _thread_params(self, reasoning_effort: Any = None) -> dict[str, Any]:
        params: dict[str, Any] = {
            'cwd': str(Path.cwd()),
            'ephemeral': True,
            # Codex is responsible for its own tools; constrain those tools
            # to the active workspace and avoid an approval protocol Grinta
            # cannot render inside its chat-completions abstraction.
            'sandbox': 'workspace-write',
            'approvalPolicy': 'never',
        }
        if self._model_name and self._model_name != 'default':
            params['model'] = self._model_name
        # Ask Codex for a transcript-safe summary stream.  The app-server
        # emits it through item/reasoning/summaryTextDelta.
        config: dict[str, Any] = {'model_reasoning_summary': 'detailed'}
        tier = str(reasoning_effort or '').strip().lower()
        if tier:
            # The Codex app-server consumes the per-thread model setting here.
            # Valid values are advertised by `model/list` for the signed-in
            # account and invalid tiers are rejected by Codex rather than
            # silently falling back.
            config['model_reasoning_effort'] = tier
        params['config'] = config
        return params

    def _stream_turn(
        self,
        messages: list[dict[str, Any]],
        reasoning_effort: Any,
        emit: Any,
    ) -> None:
        """Read one Codex turn and forward transcript deltas to *emit*."""
        with self._lock:
            self._ensure_started()
            thread = self._request('thread/start', self._thread_params(reasoning_effort))
            thread_id = str((thread.get('thread') or thread).get('id') or '')
            if not thread_id:
                raise CodexAppServerError('Codex app-server did not return a thread id.')
            turn = self._request(
                'turn/start',
                {
                    'threadId': thread_id,
                    'input': [
                        {'type': 'text', 'text': self._messages_to_prompt(messages)}
                    ],
                },
            )
            turn_id = str((turn.get('turn') or turn).get('id') or '')
            while True:
                message = self._read()
                method = message.get('method')
                params = message.get('params') or {}
                if str(params.get('turnId') or '') not in {'', turn_id}:
                    continue
                if method == 'item/agentMessage/delta':
                    delta = str(params.get('delta') or '')
                    if delta:
                        emit({'content': delta})
                    continue
                if method in {
                    'item/reasoning/textDelta',
                    'item/reasoning/summaryTextDelta',
                }:
                    delta = str(params.get('delta') or '')
                    if delta:
                        emit({'reasoning_content': delta})
                    continue
                if method != 'turn/completed':
                    continue
                completed_turn = params.get('turn') or {}
                if str(completed_turn.get('id') or params.get('turnId') or '') != turn_id:
                    continue
                if completed_turn.get('error'):
                    raise CodexAppServerError(str(completed_turn['error']))
                return

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._write({'method': method, 'id': request_id, 'params': params})
        while True:
            message = self._read()
            if message.get('id') != request_id:
                continue
            if 'error' in message:
                raise CodexAppServerError(str(message['error'].get('message', message['error'])))
            return message.get('result') or {}

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._write({'method': method, 'params': params})

    def _wait_for_turn(self, turn_id: str) -> tuple[str, dict[str, int]]:
        parts: list[str] = []
        latest_usage: dict[str, Any] = {}
        while True:
            message = self._read()
            if message.get('method') == 'thread/tokenUsage/updated':
                params = message.get('params') or {}
                if str(params.get('turnId') or '') == turn_id:
                    token_usage = params.get('tokenUsage') or {}
                    latest_usage = token_usage.get('total') or token_usage.get('last') or {}
            if message.get('method') == 'item/agentMessage/delta':
                params = message.get('params') or {}
                parts.append(str(params.get('delta') or ''))
            if message.get('method') != 'turn/completed':
                continue
            params = message.get('params') or {}
            turn = params.get('turn') or {}
            if turn_id and str(turn.get('id') or params.get('turnId') or '') != turn_id:
                continue
            if turn.get('error'):
                raise CodexAppServerError(str(turn['error']))
            usage_raw = turn.get('usage') or params.get('usage') or latest_usage
            usage = {
                'prompt_tokens': int(usage_raw.get('inputTokens') or 0),
                'completion_tokens': int(usage_raw.get('outputTokens') or 0),
                'reasoning_tokens': int(usage_raw.get('reasoningOutputTokens') or 0),
                'total_tokens': int(usage_raw.get('totalTokens') or 0),
            }
            return ''.join(parts).strip(), usage

    def _write(self, payload: dict[str, Any]) -> None:
        if not self._process or not self._process.stdin:
            raise CodexAppServerError('Codex app-server is not running.')
        self._process.stdin.write(json.dumps(payload, separators=(',', ':')) + '\n')
        self._process.stdin.flush()

    def _read(self) -> dict[str, Any]:
        if not self._process or not self._process.stdout:
            raise CodexAppServerError('Codex app-server is not running.')
        line = self._process.stdout.readline()
        if not line:
            detail = ''
            if self._process.stderr:
                detail = self._process.stderr.read().strip()
            raise CodexAppServerError(f'Codex app-server exited unexpectedly. {detail}'.strip())
        try:
            return json.loads(line)
        except json.JSONDecodeError as exc:
            raise CodexAppServerError(f'Invalid Codex app-server response: {line!r}') from exc

    @staticmethod
    def _messages_to_prompt(messages: list[dict[str, Any]]) -> str:
        rendered = []
        for message in messages:
            role = str(message.get('role') or 'user').upper()
            content = message.get('content')
            if isinstance(content, list):
                content = '\n'.join(str(part.get('text') or '') for part in content if isinstance(part, dict))
            if content:
                rendered.append(f'[{role}]\n{content}')
        return '\n\n'.join(rendered)
