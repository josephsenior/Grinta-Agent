"""Async client utilities for interacting with a Jupyter kernel gateway."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from uuid import uuid4

import tornado
import tornado.websocket
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed
from tornado.escape import json_decode, json_encode, url_escape
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.ioloop import PeriodicCallback
from tornado.websocket import websocket_connect

from forge.utils.tenacity_metrics import (
    tenacity_after_factory,
    tenacity_before_sleep_factory,
)

logging.basicConfig(level=logging.INFO)


def strip_ansi(o: str) -> str:
    r"""Removes ANSI escape sequences from `o`, as defined by ECMA-048 in.

    http://www.ecma-international.org/publications/files/ECMA-ST/Ecma-048.pdf.

    # https://github.com/ewen-lbh/python-strip-ansi/blob/master/strip_ansi/__init__.py

    >>> strip_ansi("\\\\033[33mLorem ipsum\\\\033[0m")
    'Lorem ipsum'

    >>> strip_ansi("Lorem \\\\033[38;25mIpsum\\\\033[0m sit\\\\namet.")
    'Lorem Ipsum sit\\\\namet.'

    >>> strip_ansi("")
    ''

    >>> strip_ansi("\\\\x1b[0m")
    ''

    >>> strip_ansi("Lorem")
    'Lorem'

    >>> strip_ansi('\\\\x1b[38;5;32mLorem ipsum\\\\x1b[0m')
    'Lorem ipsum'

    >>> strip_ansi('\\\\x1b[1m\\\\x1b[46m\\\\x1b[31mLorem dolor sit ipsum\\\\x1b[0m')
    'Lorem dolor sit ipsum'
    """
    pattern = re.compile("\\x1B\\[\\d+(;\\d+){0,2}m")
    return pattern.sub("", o)


class JupyterKernel:
    """Lightweight client wrapper around Jupyter Gateway for code execution."""

    def __init__(self, url_suffix: str, convid: str, lang: str = "python") -> None:
        """Configure base HTTP/WebSocket endpoints for the remote kernel session."""
        self.base_url = f"http://{url_suffix}"
        self.base_ws_url = f"ws://{url_suffix}"
        self.lang = lang
        self.kernel_id: str | None = None
        self.ws: tornado.websocket.WebSocketClientConnection | None = None
        self.convid = convid
        logging.info(
            f"Jupyter kernel created for conversation {convid} at {url_suffix}"
        )
        self.heartbeat_interval = 10000
        self.heartbeat_callback: PeriodicCallback | None = None
        self.initialized = False
        self.tools_to_run: list[str] = []

    async def initialize(self) -> None:
        """Initialize Jupyter execute server.

        Sets up color scheme and prepares tools for execution.
        """
        await self.execute("%colors nocolor")
        for tool in self.tools_to_run:
            res = await self.execute(tool)
            logging.info(f"Tool [{tool}] initialized:\n{res}")
        self.initialized = True

    async def _send_heartbeat(self) -> None:
        if not self.ws:
            return
        try:
            self.ws.ping()
        except tornado.iostream.StreamClosedError:
            try:
                await self._connect()
            except ConnectionRefusedError:
                logging.info(
                    "ConnectionRefusedError: Failed to reconnect to kernel websocket - Is the kernel still running?",
                )

    async def _connect(self) -> None:
        if self.ws:
            self.ws.close()
            self.ws = None
        client = AsyncHTTPClient()
        if not self.kernel_id:
            n_tries = 5
            while n_tries > 0:
                try:
                    response = await client.fetch(
                        f"{self.base_url}/api/kernels",
                        method="POST",
                        body=json_encode({"name": self.lang}),
                    )
                    kernel = json_decode(response.body)
                    self.kernel_id = kernel["id"]
                    break
                except Exception:
                    n_tries -= 1
                    await asyncio.sleep(1)
            if n_tries == 0:
                msg = "Failed to connect to kernel"
                raise ConnectionRefusedError(msg)
        kernel_id = self.kernel_id
        if kernel_id is None:
            msg = "Kernel ID not initialized"
            raise ConnectionRefusedError(msg)
        ws_req = HTTPRequest(
            url=f"{self.base_ws_url}/api/kernels/{url_escape(kernel_id)}/channels"
        )
        self.ws = await websocket_connect(ws_req)
        logging.info("Connected to kernel websocket")
        if self.heartbeat_callback:
            self.heartbeat_callback.stop()
        self.heartbeat_callback = PeriodicCallback(
            self._send_heartbeat, self.heartbeat_interval
        )
        self.heartbeat_callback.start()

    def _create_execute_request(self, code: str, msg_id: str) -> dict:
        """Create the execute request message for the Jupyter kernel.

        Args:
            code: The code to execute.
            msg_id: The message ID for tracking.

        Returns:
            dict: The formatted execute request message.

        """
        return {
            "header": {
                "username": "",
                "version": "5.0",
                "session": "",
                "msg_id": msg_id,
                "msg_type": "execute_request",
            },
            "parent_header": {},
            "channel": "shell",
            "content": {
                "code": code,
                "silent": False,
                "store_history": False,
                "user_expressions": {},
                "allow_stdin": False,
            },
            "metadata": {},
            "buffers": {},
        }

    def _process_message_output(self, msg_dict: dict, outputs: list[dict]) -> bool:
        """Process a message from the Jupyter kernel and update outputs.

        Args:
            msg_dict: The decoded message dictionary.
            outputs: List to append processed outputs to.

        Returns:
            bool: True if execution is complete, False otherwise.

        """
        msg_type = msg_dict["msg_type"]

        if os.environ.get("DEBUG"):
            logging.info(
                f"MSG TYPE: {msg_type.upper()}\nCONTENT: {msg_dict['content']}"
            )

        if msg_type == "error":
            traceback = "\n".join(msg_dict["content"]["traceback"])
            outputs.append({"type": "text", "content": traceback})
            return True
        if msg_type == "stream":
            outputs.append({"type": "text", "content": msg_dict["content"]["text"]})
        elif msg_type in ["execute_result", "display_data"]:
            outputs.append(
                {"type": "text", "content": msg_dict["content"]["data"]["text/plain"]}
            )
            if "image/png" in msg_dict["content"]["data"]:
                image_url = (
                    f"data:image/png;base64,{msg_dict['content']['data']['image/png']}"
                )
                outputs.append({"type": "image", "content": image_url})
        elif msg_type == "execute_reply":
            return True

        return False

    async def _wait_for_messages(self, msg_id: str, outputs: list[dict]) -> bool:
        """Wait for messages from the Jupyter kernel until execution is complete.

        Args:
            msg_id: The message ID to filter responses.
            outputs: List to collect outputs.

        Returns:
            bool: True if execution completed successfully.

        """
        execution_done = False
        while not execution_done:
            assert self.ws is not None
            msg = await self.ws.read_message()
            if msg is None:
                continue

            msg_dict = json_decode(msg)
            parent_msg_id = msg_dict["parent_header"].get("msg_id", None)
            if parent_msg_id != msg_id:
                continue

            execution_done = self._process_message_output(msg_dict, outputs)

        return execution_done

    async def _interrupt_kernel(self) -> None:
        """Interrupt the Jupyter kernel execution.

        Sends an interrupt request to the kernel to stop execution.
        """
        client = AsyncHTTPClient()
        if self.kernel_id is None:
            return

        interrupt_response = await client.fetch(
            f"{self.base_url}/api/kernels/{self.kernel_id}/interrupt",
            method="POST",
            body=json_encode({"kernel_id": self.kernel_id}),
        )
        logging.info(f"Kernel interrupted: {interrupt_response}")

    def _format_outputs(
        self, outputs: list[dict], execution_done: bool
    ) -> dict[str, list[str] | str]:
        """Format the collected outputs into the final result.

        Args:
            outputs: List of output dictionaries.
            execution_done: Whether execution completed successfully.

        Returns:
            dict: Formatted result with text and images.

        """
        text_outputs = []
        image_outputs = []

        for output in outputs:
            if output["type"] == "text":
                text_outputs.append(output["content"])
            elif output["type"] == "image":
                image_outputs.append(output["content"])

        if not text_outputs and execution_done:
            text_content = "[Code executed successfully with no output]"
        else:
            text_content = "".join(text_outputs)

        text_content = strip_ansi(text_content)
        return {"text": text_content, "images": image_outputs}

    @retry(
        retry=retry_if_exception_type(ConnectionRefusedError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        before_sleep=tenacity_before_sleep_factory("runtime.jupyter.execute"),
        after=tenacity_after_factory("runtime.jupyter.execute"),
    )
    async def execute(
        self, code: str, timeout: int = 120
    ) -> dict[str, list[str] | str]:
        """Execute code in the Jupyter kernel.

        Args:
            code: The Python code to execute.
            timeout: Maximum execution time in seconds.

        Returns:
            dict: Result containing text output and any images.

        """
        if not self.ws or self.ws.stream.closed():
            await self._connect()

        msg_id = uuid4().hex
        assert self.ws is not None

        # Send execute request
        execute_request = self._create_execute_request(code, msg_id)
        await self.ws.write_message(json_encode(execute_request))
        logging.info("Executed code in jupyter kernel")

        outputs: list[dict] = []

        try:
            execution_done = await asyncio.wait_for(
                self._wait_for_messages(msg_id, outputs),
                timeout,
            )
        except asyncio.TimeoutError:
            await self._interrupt_kernel()
            return {"text": f"[Execution timed out ({timeout} seconds).]", "images": []}

        return self._format_outputs(outputs, execution_done)

    async def shutdown_async(self) -> None:
        """Asynchronously shutdown Jupyter kernel and cleanup resources."""
        if self.kernel_id:
            client = AsyncHTTPClient()
            await client.fetch(
                f"{self.base_url}/api/kernels/{self.kernel_id}", method="DELETE"
            )
            self.kernel_id = None
            if self.ws:
                self.ws.close()
                self.ws = None


class ExecuteHandler(tornado.web.RequestHandler):
    """HTTP handler that proxies execute requests to the conversation kernel."""

    def initialize(self, jupyter_kernel: JupyterKernel) -> None:
        """Initialize Jupyter execute server with kernel reference.

        Args:
            jupyter_kernel: Jupyter kernel instance to use

        """
        self.jupyter_kernel = jupyter_kernel

    async def post(self) -> None:
        """Handle POST request to execute Jupyter code.

        Executes code in Jupyter kernel and returns output.
        """
        data = json_decode(self.request.body)
        code = data.get("code")
        if not code:
            self.set_status(400)
            self.write("Missing code")
            return
        output = await self.jupyter_kernel.execute(code)
        self.set_header("Content-Type", "application/json")
        self.write(json_encode(output))


def make_app() -> tornado.web.Application:
    """Create Tornado web application for Jupyter execution server.

    Initializes Jupyter kernel and sets up execute endpoint handler.

    Returns:
        Configured Tornado application

    """
    jupyter_kernel = JupyterKernel(
        f"localhost:{os.environ.get('JUPYTER_GATEWAY_PORT', '8888')}",
        os.environ.get("JUPYTER_GATEWAY_KERNEL_ID", "default"),
    )
    asyncio.get_event_loop().run_until_complete(jupyter_kernel.initialize())
    return tornado.web.Application(
        [("/execute", ExecuteHandler, {"jupyter_kernel": jupyter_kernel})]
    )


if __name__ == "__main__":
    app = make_app()
    port_str = os.environ.get("JUPYTER_EXEC_SERVER_PORT", "8890")
    try:
        port = int(port_str)
    except ValueError:
        port = 8890
    app.listen(port)
    tornado.ioloop.IOLoop.current().start()
