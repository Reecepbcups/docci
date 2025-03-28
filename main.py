#!/usr/bin/env -S python3 -B

import os
import sys
from typing import Optional

from src.config import Config
from src.models import Tags
from src.parsing import parse_markdown_code_blocks
from src.processes_manager import process_manager


def main():
    """Main entry point for the application."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <config_path|config_json_blob> [--tags]")
        sys.exit(1)

    if "--tags" in sys.argv:
        Tags.print_tags_with_aliases()
        sys.exit(0)

    cfg_input = sys.argv[1]

    try:
        config = Config.load_configuration(cfg_input)
    except Exception as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    error = run_documentation_processor(config)
    if error:
        print(f"Error: {error}")
        sys.exit(1)

    print("Documentation processing completed successfully.")

def run_documentation_processor(config: Config) -> Optional[str]:
    """
    Execute documentation code blocks according to configuration.

    Args:
        config: The loaded configuration

    Returns:
        Error message or None if successful
    """
    try:
        # Set up environment
        config.run_pre_cmds(hide_output=True)
        for key, value in config.env_vars.items():
            os.environ[key] = value

        # Process all content paths
        for parent_path_key, file_paths in config.get_all_possible_paths().items():
            try:
                for file_path in file_paths:
                    # Read and parse file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Extract and process code blocks
                    code_blocks = parse_markdown_code_blocks(config, content)

                    # Execute commands for each code block
                    for i, block in enumerate(code_blocks):
                        error = block.run_commands(config=config)
                        if error:
                            return f"Error({parent_path_key},{file_paths})[#{i}]: {error}"

            except KeyboardInterrupt:
                print("\nKeyboardInterrupt: Quitting...")
                return "Interrupted by user"
            except Exception as e:
                return f"Error({parent_path_key},{file_paths}): {e}"

    except Exception as e:
        return f"Setup error: {e}"
    finally:
        # Always clean up resources
        process_manager.cleanup()
        config.run_cleanup_cmds(hide_output=True)

    return None


if __name__ == "__main__":
    main()
