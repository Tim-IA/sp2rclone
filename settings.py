"""Command-line arguments and config.ini loading."""

import argparse
import os
from configparser import ConfigParser
from configparser import Error as ConfigError


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate rclone.conf sections for every document library "
        "on a SharePoint site."
    )
    parser.add_argument(
        "-s",
        "--settings-dir",
        default="~/sharepoint/config",
        help="directory containing config.ini (default: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="rclone.conf file to write "
        "(default: <settings-dir>/rclone/rclone.conf)",
    )
    return parser.parse_args(argv)


def resolve_settings_dir(settings_dir):
    path = os.path.expanduser(settings_dir)
    if os.path.isdir(path) and os.access(path, os.R_OK):
        return path
    raise FileNotFoundError(
        f"SharePoint settings directory does not exist or is not readable: {path}"
    )


def get_sharepoint_settings(settings_path):
    settings_file = os.path.join(settings_path, "config.ini")

    if not os.path.exists(settings_file):
        print(f"Settings file not found or not readable: {settings_file}")
        return None

    config = ConfigParser()
    try:
        if not config.read(settings_file):
            raise OSError("Unable to read config file")
    except (OSError, ConfigError):
        print(f"Failed to read SharePoint settings from {settings_file}")
        return None

    try:
        return {
            "tenant_id": config.get("azure", "tenant_id"),
            "client_id": config.get("azure", "client_id"),
            "client_secret": config.get("azure", "client_secret"),
            "host_name": config.get("sharepoint", "host_name"),
            "site_name": config.get("sharepoint", "site_name"),
        }
    except ConfigError as e:
        print(f"SharePoint config file {settings_file} is missing a required setting: {e}")
        return None
