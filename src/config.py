import json
import logging
import os
import subprocess
from logging import getLogger
from typing import Dict, List

 # https://github.com/rouge-ruby/rouge/wiki/List-of-supported-languages-and-lexers
ScriptingLanguages = ["shell", "bash", "sh", "zsh", "ksh"] # if it is not in here then it is likely a source ode

class Config:
    config_version = "v0.0.1" # future proofing
    paths: List[str] = [] # this will be loaded with the prefix of the absolute path of the repo
    env_vars: Dict[str, str] = {}
    log_level: str = "INFO"
    pre_cmds: List[str] = []
    cleanup_cmds: List[str] = []
    only_run_bash: bool = True
    ignore_commands: List[str] = []
    supported_file_extensions = ["md", "mdx"]
    followed_languages = ScriptingLanguages
    working_dir: str | None = None

    def __setattr__(self, name, value):
        # Call the parent class's __setattr__ to actually set the attribute
        super().__setattr__(name, value)

        # when the attr is set, it overrides the global config
        if name == "log_level":
            level = value.upper()
            root_logger = logging.getLogger()
            root_logger.setLevel(logging.getLevelName(level))

    def __init__(self, paths: List[str], env_var: Dict[str, str] = {}, cleanup_cmds: List[str] = [], pre_cmds: List[str] = []):
        self.paths = paths
        self.env_vars = env_var
        self.cleanup_cmds = cleanup_cmds
        self.pre_cmds = pre_cmds

    def iterate_paths(self):
        for path in self.paths:
            yield path

    def get_all_possible_paths(self) -> Dict[str, List[str]]:
        collected_files = {} # parent path -> list of files

        for path in self.iterate_paths():
            parent_path = path  # Use the original path as the key
            if parent_path not in collected_files:
                collected_files[parent_path] = []

            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if any(file.endswith(ext) for ext in self.supported_file_extensions):
                            collected_files[parent_path].append(os.path.join(root, file))
            else:
                # For non-directory paths, just add the file directly
                collected_files[parent_path].append(path)

        # sort all collected_files values
        for key in collected_files:
            collected_files[key].sort()

        return collected_files


    def __run_cmd(self, cmd: str, hide_output: bool, cwd: str | None = None):
        subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.DEVNULL if hide_output else None, stderr=subprocess.DEVNULL if hide_output else None)

    def run_pre_cmds(self, hide_output: bool = False):
        for cmd in self.pre_cmds:
            self.__run_cmd(cmd, hide_output)

    def run_cleanup_cmds(self, hide_output: bool = False):
        for cmd in self.cleanup_cmds:
            self.__run_cmd(cmd, hide_output)

    @classmethod
    def from_json(cls, json: Dict) -> "Config":
        c = Config(json['paths'], json.get('env_vars', {}), json.get('cleanup_cmds', []), json.get('pre_cmds', []))
        c.working_dir = json.get('working_dir', None)
        c.log_level = json.get('log_level', "INFO")
        return c

    def to_json(self):
        return {
            'paths': self.paths,
            'env_vars': self.env_vars,
            'cleanup_cmds': self.cleanup_cmds,
            'pre_cmds': self.pre_cmds,
            'working_dir': self.working_dir,
            'log_level': self.log_level,
        }

    @staticmethod
    def load_from_file(absolute_path: str) -> "Config":
        with open(absolute_path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                getLogger(__name__).error(f"Invalid JSON in file: {absolute_path}, make sure you reference the JSON config file & not the README")
                exit(1)

            Config.validate_legacy_options(data)
            return Config.from_json(data)

    @staticmethod
    def validate_legacy_options(_json: str) -> None:
        options: List[str] = []

        if _json.get("debugging") is not None:
            options.append("v0.6: `debugging` is now `log_level`")

        if len(options) > 0:
            getLogger(__name__).warning("Your config contains legacy options. Update to the latest config format.")
            getLogger(__name__).warning("\n".join(options))
            getLogger(__name__).warning("Please refer to the changelogs for more information.")

    @staticmethod
    def load_configuration(cfg_input: str) -> "Config":
        """
        Load configuration from file or JSON string.

        Args:
            cfg_input: Path to config file or JSON string

        Returns:
            Loaded configuration object

        Raises:
            ValueError: If configuration cannot be loaded
        """
        # If input is a directory, look for config.json
        if os.path.isdir(cfg_input):
            cfg_input = os.path.join(cfg_input, 'config.json')
            if not os.path.exists(cfg_input):
                raise ValueError(f"config.json not found in directory: {cfg_input}")

        # Load from file or parse JSON string
        if os.path.isfile(cfg_input):
            return Config.load_from_file(cfg_input)
        else:
            try:
                return Config.from_json(json.loads(cfg_input))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON input: {e}")

