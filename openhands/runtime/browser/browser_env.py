from __future__ import annotations

import atexit
import contextlib
import json
import multiprocessing
import time
import uuid
from typing import Any

import gymnasium as gym
import html2text
import tenacity
from browsergym.utils.obs import flatten_dom_to_str, overlay_som

from openhands.core.exceptions import BrowserInitException
from openhands.core.logger import openhands_logger as logger
from openhands.runtime.browser.base64 import image_to_png_base64_url
from openhands.utils.shutdown_listener import should_continue, should_exit
from openhands.utils.tenacity_metrics import (
    tenacity_after_factory,
    tenacity_before_sleep_factory,
)
from openhands.utils.tenacity_stop import stop_if_should_exit

BROWSER_EVAL_GET_GOAL_ACTION = "GET_EVAL_GOAL"
BROWSER_EVAL_GET_REWARDS_ACTION = "GET_EVAL_REWARDS"


class BrowserEnv:

    def __init__(self, browsergym_eval_env: str | None = None) -> None:
        self.html_text_converter = self.get_html_text_converter()
        self.eval_mode = False
        self.eval_dir = ""
        self.browsergym_eval_env = browsergym_eval_env
        self.eval_mode = bool(browsergym_eval_env)
        multiprocessing.set_start_method("spawn", force=True)
        self.browser_side, self.agent_side = multiprocessing.Pipe()
        self.init_browser()
        atexit.register(self.close)

    def get_html_text_converter(self) -> html2text.HTML2Text:
        html_text_converter = html2text.HTML2Text()
        html_text_converter.ignore_links = False
        html_text_converter.ignore_images = True
        html_text_converter.images_to_alt = True
        html_text_converter.body_width = 0
        return html_text_converter

    @tenacity.retry(
        wait=tenacity.wait_fixed(1),
        stop=tenacity.stop_after_attempt(5) | stop_if_should_exit(),
        retry=tenacity.retry_if_exception_type(BrowserInitException),
        before_sleep=tenacity_before_sleep_factory("runtime.browser.init_browser"),
        after=tenacity_after_factory("runtime.browser.init_browser"),
    )
    def init_browser(self) -> None:
        logger.debug("Starting browser env...")
        try:
            self.process = multiprocessing.Process(target=self.browser_process)
            self.process.start()
        except Exception as e:
            logger.error("Failed to start browser process: %s", e)
            raise
        if not self.check_alive(timeout=200):
            self.close()
            msg = "Failed to start browser environment."
            raise BrowserInitException(msg)

    def _normalize_eval_env_name(self) -> None:
        """Normalize the browsergym eval environment name."""
        if not self.browsergym_eval_env.startswith("browsergym/"):
            self.browsergym_eval_env = f"browsergym/{self.browsergym_eval_env}"

    def _import_eval_environment(self) -> None:
        """Import the required browsergym evaluation environment."""
        if "visualwebarena" in self.browsergym_eval_env:
            import nltk

            nltk.download("punkt_tab")
        elif "webarena" not in self.browsergym_eval_env and "miniwob" not in self.browsergym_eval_env:
            msg = f"Unsupported browsergym eval env: {self.browsergym_eval_env}"
            raise ValueError(msg)

    def _create_eval_environment(self) -> Any:
        """Create the appropriate evaluation environment."""
        if self.eval_mode:
            self._normalize_eval_env_name()
            self._import_eval_environment()
            return gym.make(self.browsergym_eval_env, tags_to_mark="all", timeout=100000)
        return gym.make(
            "browsergym/openended",
            task_kwargs={"start_url": "about:blank", "goal": "PLACEHOLDER_GOAL"},
            wait_for_user_message=False,
            headless=True,
            disable_env_checker=True,
            tags_to_mark="all",
            timeout=100000,
            pw_context_kwargs={"accept_downloads": True},
            pw_chromium_kwargs={"downloads_path": "/workspace/.downloads/"},
        )

    def _initialize_eval_attributes(self) -> None:
        """Initialize evaluation-related attributes."""
        self.eval_goal = None
        self.goal_image_urls = []
        self.eval_rewards: list[float] = []

    def _process_goal_object(self, obs: dict) -> None:
        """Process goal object from observation."""
        if "goal_object" not in obs:
            return

        obs["goal_object"] = list(obs["goal_object"])
        if len(obs["goal_object"]) > 0:
            self.eval_goal = obs["goal_object"][0]["text"]

        for message in obs["goal_object"]:
            if message["type"] == "image_url":
                image_src = message["image_url"]
                if isinstance(image_src, dict):
                    image_src = image_src["url"]
                self.goal_image_urls.append(image_src)

    def _setup_eval_mode(self, obs: dict) -> None:
        """Setup evaluation mode with goal and image URLs."""
        self.eval_goal = obs["goal"]
        self._process_goal_object(obs)
        logger.debug("Browsing goal: %s", self.eval_goal)

    def _handle_shutdown_request(self, env: Any) -> bool:
        """Handle shutdown request and return True if should shutdown."""
        logger.debug("SHUTDOWN recv, shutting down browser env...")
        env.close()
        return True

    def _handle_alive_request(self) -> None:
        """Handle alive request."""
        self.browser_side.send(("ALIVE", None))

    def _handle_eval_goal_request(self, unique_request_id: str) -> None:
        """Handle evaluation goal request."""
        self.browser_side.send(
            (unique_request_id, {"text_content": self.eval_goal, "image_content": self.goal_image_urls}),
        )

    def _handle_eval_rewards_request(self, unique_request_id: str) -> None:
        """Handle evaluation rewards request."""
        self.browser_side.send((unique_request_id, {"text_content": json.dumps(self.eval_rewards)}))

    def _process_observation(self, obs: dict) -> dict:
        """Process observation data for browser environment."""
        html_str = flatten_dom_to_str(obs["dom_object"])
        obs["text_content"] = self.html_text_converter.handle(html_str)
        obs["set_of_marks"] = image_to_png_base64_url(
            overlay_som(obs["screenshot"], obs.get("extra_element_properties", {})),
            add_data_prefix=True,
        )
        obs["screenshot"] = image_to_png_base64_url(obs["screenshot"], add_data_prefix=True)
        obs["active_page_index"] = obs["active_page_index"].item()
        obs["elapsed_time"] = obs["elapsed_time"].item()
        return obs

    def _handle_browser_action(self, env: Any, action_data: dict, unique_request_id: str) -> None:
        """Handle browser action and send response."""
        action = action_data["action"]

        # Check if this is a goto action to a localhost URL and handle server readiness
        action = self._handle_localhost_server_readiness(action)

        obs, reward, _terminated, _truncated, _info = env.step(action)

        if self.eval_mode:
            self.eval_rewards.append(reward)

        processed_obs = self._process_observation(obs)
        self.browser_side.send((unique_request_id, processed_obs))

    def _handle_localhost_server_readiness(self, action: str) -> str:
        """Handle server readiness for localhost URLs to prevent chrome-error://chromewebdata/.
        
        Uses async non-blocking checks to avoid freezing the browser process.
        """
        import asyncio
        import re

        # Check if this is a goto action to a localhost URL
        goto_match = re.search(r'goto\(["\'](http://(?:localhost|127\.0\.0\.1|0\.0\.0\.0):\d+[^"\']*?)["\']\)', action)
        if not goto_match:
            return action

        url = goto_match.group(1)
        logger.info(f"🔍 Detected localhost navigation to {url}, checking server readiness...")

        # Run async server check
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            server_ready = loop.run_until_complete(self._check_server_ready_async(url))
            loop.close()
            
            if server_ready:
                logger.info(f"✅ Server at {url} is ready and responding!")
            else:
                logger.warning(f"⚠️ Server at {url} not responding, but proceeding with navigation...")
        except Exception as e:
            logger.warning(f"⚠️ Error checking server readiness: {e}, proceeding anyway...")

        return action

    async def _check_server_ready_async(self, url: str, max_wait: int = 30, check_interval: float = 0.5) -> bool:
        """Async non-blocking server readiness check.
        
        Args:
            url: URL to check
            max_wait: Maximum seconds to wait
            check_interval: Seconds between checks
            
        Returns:
            True if server is ready, False otherwise
        """
        import aiohttp
        
        start_time = time.time()
        attempt = 0
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            while time.time() - start_time < max_wait:
                attempt += 1
                try:
                    async with session.head(url, allow_redirects=True) as response:
                        if response.status < 500:
                            logger.debug(f"✅ Server ready after {attempt} attempts ({time.time() - start_time:.1f}s) - Status: {response.status}")
                            return True
                except Exception as e:
                    logger.debug(f"⏳ Attempt {attempt}: Server not ready yet - {type(e).__name__}")
                
                await asyncio.sleep(check_interval)
        
        logger.warning(f"❌ Server not ready after {max_wait}s ({attempt} attempts)")
        return False

    def _handle_browser_requests(self, env: Any) -> bool:
        """Handle browser requests and return True if should continue."""
        if not self.browser_side.poll(timeout=0.01):
            return True

        unique_request_id, action_data = self.browser_side.recv()

        if unique_request_id == "SHUTDOWN":
            return not self._handle_shutdown_request(env)
        if unique_request_id == "IS_ALIVE":
            self._handle_alive_request()
            return True
        if action_data["action"] == BROWSER_EVAL_GET_GOAL_ACTION:
            self._handle_eval_goal_request(unique_request_id)
            return True
        if action_data["action"] == BROWSER_EVAL_GET_REWARDS_ACTION:
            self._handle_eval_rewards_request(unique_request_id)
            return True
        self._handle_browser_action(env, action_data, unique_request_id)
        return True

    def browser_process(self) -> None:
        """Main browser process loop."""
        # Create environment
        env = self._create_eval_environment()

        # Initialize and reset environment
        obs, _info = env.reset()
        logger.info("Successfully called env.reset")

        # Initialize evaluation attributes
        self._initialize_eval_attributes()

        # Setup evaluation mode if needed
        if self.eval_mode:
            self._setup_eval_mode(obs)

        logger.info("Browser env started.")

        # Main processing loop
        while should_continue():
            try:
                if not self._handle_browser_requests(env):
                    return
            except KeyboardInterrupt:
                logger.debug("Browser env process interrupted by user.")
                with contextlib.suppress(Exception):
                    env.close()
                return

    def step(self, action_str: str, timeout: float = 120) -> dict:
        """Execute an action in the browser environment and return the observation."""
        unique_request_id = str(uuid.uuid4())
        self.agent_side.send((unique_request_id, {"action": action_str}))
        start_time = time.time()
        while True:
            if should_exit() or time.time() - start_time > timeout:
                msg = "Browser environment took too long to respond."
                raise TimeoutError(msg)
            if self.agent_side.poll(timeout=0.01):
                response_id, obs = self.agent_side.recv()
                if response_id == unique_request_id:
                    return dict(obs)

    def check_alive(self, timeout: float = 60) -> bool:
        self.agent_side.send(("IS_ALIVE", None))
        if self.agent_side.poll(timeout=timeout):
            response_id, _ = self.agent_side.recv()
            if response_id == "ALIVE":
                return True
            logger.debug("Browser env is not alive. Response ID: %s", response_id)
        return False

    def close(self) -> None:
        if not self.process.is_alive():
            return
        try:
            self.agent_side.send(("SHUTDOWN", None))
            self.process.join(5)
            if self.process.is_alive():
                logger.error("Browser process did not terminate, forcefully terminating...")
                self.process.terminate()
                self.process.join(5)
                if self.process.is_alive():
                    self.process.kill()
                    self.process.join(5)
            self.agent_side.close()
            self.browser_side.close()
        except Exception as e:
            logger.error("Encountered an error when closing browser env: %s", e)
