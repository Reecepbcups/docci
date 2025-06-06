#!/usr/bin/env -S python3 -B

import logging
import os
import sys
from logging import basicConfig as logging_basicConfig
from logging import getLogger
from typing import Optional

from src.config import Config
from src.managers.process import process_manager
from src.models import Tags
from src.parsing import parse_markdown_code_blocks

logging_basicConfig(
    format='DOCCI_%(levelname)s: %(message)s',
    force=True,  # Ensure logging is set up even if already configured
    level=logging.INFO  # Set a default level that will be overridden by config
)

logger = getLogger(__name__)

def main():
    """Main entry point for the application."""
    if len(sys.argv) != 2:
        logger.error("Usage: <config_path|config_json_blob> [--tags]")
        sys.exit(1)

    if "--tags" in sys.argv:
        Tags.print_tags_with_aliases()
        sys.exit(0)

    cfg_input = sys.argv[1]

    try:
        config = Config.load_configuration(cfg_input)
    except Exception as e:
        logger.error(f"Configuration: {e}")
        sys.exit(1)

    result = run_documentation_processor(config)
    # Check for any kind of error message, not just those starting with "Error:"
    if result and ("Error:" in result or "`" in result and "is not found in output" in result):
        logger.error(result)
        sys.exit(1)

    logger.debug("Documentation processing completed successfully.")

def run_documentation_processor(config: Config) -> str:
    """
    Execute documentation code blocks according to configuration.

    Args:
        config: The loaded configuration

    Returns:
        Command output or error message
    """
    outputs = []
    
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
                        result = block.run_commands(config=config)
                        # Store non-empty results
                        if result:
                            outputs.append(result)
                        # Treat as error if it starts with "Error:" or contains "Error: `" (for output_contains check)
                        if result and (result.startswith("Error:") or ("Error: `" in result and "` is not found in output" in result)):
                            return f"Error({parent_path_key},{file_paths})[#{i}]: {result}"

            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt: Quitting...")
                return "Interrupted by user"
            except Exception as e:
                return f"Error({parent_path_key},{file_paths}): {e}"

    except Exception as e:
        return f"Setup error: {e}"
    finally:
        # Always clean up resources
        process_manager.cleanup()
        config.run_cleanup_cmds(hide_output=True)

    # Return combined outputs or empty string if no outputs
    return "\n".join(outputs) if outputs else ""


if __name__ == "__main__":
    main()
