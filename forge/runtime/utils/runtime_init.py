"""Initialization helpers for setting up runtime users and workspaces."""

from __future__ import annotations

import os
import subprocess
import sys

from forge.core.logger import forge_logger as logger


def init_user_and_working_directory(username: str, user_id: int, initial_cwd: str) -> int | None:
    """Create working directory and user if not exists.

    It performs the following steps effectively:
    * Creates the Working Directory:
        - Uses mkdir -p to create the directory.
        - Sets ownership to username:root.
        - Adjusts permissions to be readable and writable by group and others.
    * User Verification and Creation:
        - Checks if the user exists using id -u.
        - If the user exists with the correct UID, it skips creation.
        - If the UID differs, it logs a warning and return an updated user_id.
        - If the user doesn't exist, it proceeds to create the user.
    * Sudo Configuration:
        - Appends %sudo ALL=(ALL) NOPASSWD:ALL to /etc/sudoers to grant
            passwordless sudo access to the sudo group.
        - Adds the user to the sudo group with the useradd command, handling
            UID conflicts by incrementing the UID if necessary.

    Args:
        username (str): The username to create.
        user_id (int): The user ID to assign to the user.
        initial_cwd (str): The initial working directory to create.

    Returns:
        int | None: The user ID if it was updated, None otherwise.

    """
    if sys.platform == "win32":
        logger.debug("Running on Windows, skipping Unix-specific user setup")
        logger.debug("Client working directory: %s", initial_cwd)
        os.makedirs(initial_cwd, exist_ok=True)
        logger.debug("Created working directory: %s", initial_cwd)
        return None
    if username == os.getenv("USER") and username not in ["root", "forge"]:
        return None
    if username != "root":
        logger.debug("Attempting to create user `%s` with UID %s.", username, user_id)
        existing_user_id = -1
        try:
            result = subprocess.run(["id", "-u", username], shell=False, check=True, capture_output=True)
            existing_user_id = int(result.stdout.decode().strip())
            if existing_user_id == user_id:
                logger.debug("User `%s` already has the provided UID %s. Skipping user setup.", username, user_id)
            else:
                logger.warning("User `%s` already exists with UID %s. Skipping user setup.", username, existing_user_id)
                return existing_user_id
            return None
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                logger.debug("User `%s` does not exist. Proceeding with user creation.", username)
            else:
                logger.error("Error checking user `%s`, skipping setup:\n%s\n", username, e)
                raise
        sudoer_line = ["sh", "-c", "echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"]
        output = subprocess.run(sudoer_line, check=False, shell=False, capture_output=True)
        if output.returncode != 0:
            msg = f"Failed to add sudoer: {output.stderr.decode()}"
            raise RuntimeError(msg)
        logger.debug("Added sudoer successfully. Output: [%s]", output.stdout.decode())
        command = [
            "useradd",
            "-rm",
            "-d",
            f"/home/{username}",
            "-s",
            "/bin/bash",
            "-g",
            "root",
            "-G",
            "sudo",
            "-u",
            str(user_id),
            username,
        ]
        output = subprocess.run(command, check=False, shell=False, capture_output=True)
        if output.returncode == 0:
            logger.debug(
                "Added user `%s` successfully with UID %s. Output: [%s]",
                username,
                user_id,
                output.stdout.decode(),
            )
        else:
            msg = f"Failed to create user `{username}` with UID {user_id}. Output: [{
                output.stderr.decode()}]"
            raise RuntimeError(
                msg,
            )
    logger.debug("Client working directory: %s", initial_cwd)
    command = ["sh", "-c", f"umask 002; mkdir -p {initial_cwd}"]
    output = subprocess.run(command, check=False, shell=False, capture_output=True)
    out_str = output.stdout.decode()
    command = ["chown", "-R", f"{username}:root", initial_cwd]
    output = subprocess.run(command, check=False, shell=False, capture_output=True)
    out_str += output.stdout.decode()
    command = ["chmod", "g+rw", initial_cwd]
    output = subprocess.run(command, check=False, shell=False, capture_output=True)
    out_str += output.stdout.decode()
    logger.debug("Created working directory. Output: [%s]", out_str)
    return None
