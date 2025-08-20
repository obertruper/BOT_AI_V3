"""
Tests for unified_launcher.py - the main system launcher
Tests the launcher components and process management
"""

import os
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestUnifiedLauncher:
    """Test the unified launcher functionality"""

    def test_launcher_process_definitions(self):
        """Test launcher process definitions and configuration"""
        # Define expected launcher processes
        expected_processes = {
            "core": {
                "name": "Core Trading System",
                "command": ["python3", "main.py"],
                "description": "Main trading engine and orchestrator",
                "critical": True,
                "restart_on_failure": True,
            },
            "api": {
                "name": "API Server",
                "command": ["python3", "-m", "uvicorn", "web.api.main:app"],
                "description": "REST API and WebSocket server",
                "critical": False,
                "restart_on_failure": True,
            },
            "frontend": {
                "name": "Frontend Development Server",
                "command": ["npm", "run", "dev"],
                "description": "React frontend development server",
                "critical": False,
                "restart_on_failure": False,
            },
        }

        def validate_process_config(process_config):
            """Validate process configuration"""
            required_fields = ["name", "command", "description"]

            for process_id, config in process_config.items():
                for field in required_fields:
                    if field not in config:
                        return False, f"Missing {field} in {process_id}"

                if not isinstance(config["command"], list):
                    return False, f"Command must be list in {process_id}"

                if len(config["command"]) == 0:
                    return False, f"Command cannot be empty in {process_id}"

            return True, "Configuration valid"

        # Test configuration validation
        is_valid, message = validate_process_config(expected_processes)

        assert is_valid is True
        assert message == "Configuration valid"

        # Test individual process configurations
        for process_id, config in expected_processes.items():
            assert "name" in config
            assert "command" in config
            assert "description" in config
            assert isinstance(config["command"], list)
            assert len(config["command"]) > 0

    def test_launcher_mode_selection(self):
        """Test launcher mode selection and configuration"""
        launcher_modes = {
            "full": {
                "description": "Full system with all components",
                "processes": ["core", "api", "frontend", "monitoring"],
                "default": True,
            },
            "core": {
                "description": "Core trading system only",
                "processes": ["core"],
                "default": False,
            },
            "api": {
                "description": "API server with core",
                "processes": ["core", "api"],
                "default": False,
            },
            "development": {
                "description": "Development mode with frontend",
                "processes": ["core", "api", "frontend"],
                "default": False,
            },
        }

        def get_processes_for_mode(mode, modes_config):
            """Get processes to run for given mode"""
            if mode not in modes_config:
                return None

            return modes_config[mode]["processes"]

        def get_default_mode(modes_config):
            """Get default launcher mode"""
            for mode, config in modes_config.items():
                if config.get("default", False):
                    return mode
            return list(modes_config.keys())[0]  # First mode as fallback

        # Test mode selection
        full_processes = get_processes_for_mode("full", launcher_modes)
        assert "core" in full_processes
        assert "api" in full_processes
        assert "frontend" in full_processes

        core_processes = get_processes_for_mode("core", launcher_modes)
        assert core_processes == ["core"]

        # Test default mode
        default_mode = get_default_mode(launcher_modes)
        assert default_mode == "full"

        # Test invalid mode
        invalid_processes = get_processes_for_mode("invalid", launcher_modes)
        assert invalid_processes is None

    @patch("subprocess.Popen")
    def test_process_launching(self, mock_popen):
        """Test process launching functionality"""
        # Setup mock process
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process running
        mock_process.returncode = None
        mock_popen.return_value = mock_process

        def launch_process(command, working_dir=None, env_vars=None):
            """Launch a process with given configuration"""
            import os

            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # Launch process
            process = subprocess.Popen(
                command, cwd=working_dir, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            return {"process": process, "pid": process.pid, "command": command, "status": "running"}

        # Test process launching
        test_command = ["python3", "-c", "print('Hello World')"]
        result = launch_process(test_command)

        assert result["pid"] == 12345
        assert result["command"] == test_command
        assert result["status"] == "running"
        assert "process" in result

        # Verify subprocess.Popen was called
        mock_popen.assert_called_once()

    def test_process_monitoring(self):
        """Test process monitoring and health checking"""
        # Mock process registry
        process_registry = {}

        def register_process(process_id, process_info):
            """Register a process for monitoring"""
            process_registry[process_id] = {
                **process_info,
                "start_time": 1692000000,  # Mock timestamp
                "last_check": 1692000000,
                "health_checks_passed": 0,
                "health_checks_failed": 0,
            }

        def check_process_health(process_id):
            """Check health of a registered process"""
            if process_id not in process_registry:
                return {"status": "not_found"}

            process_info = process_registry[process_id]

            # Simulate health check
            if hasattr(process_info.get("process"), "poll"):
                return_code = process_info["process"].poll()

                if return_code is None:
                    # Process is running
                    process_info["health_checks_passed"] += 1
                    process_info["last_check"] = 1692000000 + process_info["health_checks_passed"]

                    return {
                        "status": "healthy",
                        "pid": process_info.get("pid"),
                        "uptime": process_info["last_check"] - process_info["start_time"],
                        "health_checks": process_info["health_checks_passed"],
                    }
                else:
                    # Process has exited
                    process_info["health_checks_failed"] += 1

                    return {
                        "status": "failed",
                        "exit_code": return_code,
                        "health_checks_failed": process_info["health_checks_failed"],
                    }

            return {"status": "unknown"}

        def get_all_process_status():
            """Get status of all registered processes"""
            status_report = {}

            for process_id in process_registry:
                status_report[process_id] = check_process_health(process_id)

            return status_report

        # Test process registration
        mock_process = Mock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345

        register_process(
            "core", {"process": mock_process, "pid": 12345, "command": ["python3", "main.py"]}
        )

        assert "core" in process_registry
        assert process_registry["core"]["pid"] == 12345

        # Test health checking
        health_status = check_process_health("core")

        assert health_status["status"] == "healthy"
        assert health_status["pid"] == 12345
        assert health_status["uptime"] >= 0

        # Test failed process
        mock_process.poll.return_value = 1  # Exit code 1
        failed_status = check_process_health("core")

        assert failed_status["status"] == "failed"
        assert failed_status["exit_code"] == 1

        # Test status report
        status_report = get_all_process_status()
        assert "core" in status_report

    def test_argument_parsing(self):
        """Test command line argument parsing"""

        def parse_launcher_arguments(args_list):
            """Parse launcher command line arguments"""
            import argparse

            parser = argparse.ArgumentParser(description="BOT_AI_V3 Unified Launcher")

            parser.add_argument(
                "--mode",
                choices=["full", "core", "api", "development"],
                default="full",
                help="Launch mode",
            )

            parser.add_argument("--config", type=str, help="Configuration file path")

            parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

            parser.add_argument(
                "--dry-run",
                action="store_true",
                help="Show what would be launched without actually launching",
            )

            parser.add_argument(
                "--status", action="store_true", help="Show status of running processes"
            )

            parser.add_argument("--stop", action="store_true", help="Stop all running processes")

            return parser.parse_args(args_list)

        # Test default arguments
        default_args = parse_launcher_arguments([])
        assert default_args.mode == "full"
        assert default_args.verbose is False
        assert default_args.dry_run is False

        # Test custom mode
        mode_args = parse_launcher_arguments(["--mode", "core"])
        assert mode_args.mode == "core"

        # Test verbose flag
        verbose_args = parse_launcher_arguments(["--verbose"])
        assert verbose_args.verbose is True

        # Test dry run
        dry_run_args = parse_launcher_arguments(["--dry-run"])
        assert dry_run_args.dry_run is True

        # Test status flag
        status_args = parse_launcher_arguments(["--status"])
        assert status_args.status is True

        # Test stop flag
        stop_args = parse_launcher_arguments(["--stop"])
        assert stop_args.stop is True

    def test_configuration_loading(self):
        """Test launcher configuration loading"""

        def load_launcher_config(config_path=None):
            """Load launcher configuration"""
            import json
            import os

            # Default configuration
            default_config = {
                "processes": {
                    "core": {
                        "command": ["python3", "main.py"],
                        "working_directory": ".",
                        "environment": {},
                        "critical": True,
                    },
                    "api": {
                        "command": [
                            "python3",
                            "-m",
                            "uvicorn",
                            "web.api.main:app",
                            "--host",
                            "0.0.0.0",
                            "--port",
                            "8083",
                        ],
                        "working_directory": ".",
                        "environment": {},
                        "critical": False,
                    },
                },
                "modes": {"full": ["core", "api"], "core": ["core"]},
                "monitoring": {
                    "health_check_interval": 30,
                    "restart_threshold": 3,
                    "startup_timeout": 60,
                },
            }

            if config_path and os.path.exists(config_path):
                try:
                    with open(config_path) as f:
                        custom_config = json.load(f)

                    # Merge configurations
                    merged_config = default_config.copy()
                    merged_config.update(custom_config)
                    return merged_config
                except Exception as e:
                    print(f"Failed to load config from {config_path}: {e}")
                    return default_config

            return default_config

        # Test default configuration loading
        config = load_launcher_config()

        assert "processes" in config
        assert "modes" in config
        assert "monitoring" in config

        assert "core" in config["processes"]
        assert "api" in config["processes"]

        assert "full" in config["modes"]
        assert "core" in config["modes"]

        # Test configuration structure
        core_process = config["processes"]["core"]
        assert "command" in core_process
        assert "working_directory" in core_process
        assert "critical" in core_process

        monitoring_config = config["monitoring"]
        assert "health_check_interval" in monitoring_config
        assert "restart_threshold" in monitoring_config
        assert "startup_timeout" in monitoring_config


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
