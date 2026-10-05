import sys

from regression_framework.executor import build_command, command_to_string, run_command


def test_build_command_splits_string():
    assert build_command('echo "hello world"') == ["echo", "hello world"]


def test_build_command_uses_current_python():
    assert build_command("python script.py")[0] == sys.executable
    assert build_command(["python3", "-V"])[0] == sys.executable


def test_command_to_string():
    assert command_to_string(["echo", "hello world"]) == "echo 'hello world'"
    assert command_to_string("echo hi") == "echo hi"


def test_run_command_captures_output_and_exit_code():
    result = run_command(["python", "-c", "import sys; print('hi'); sys.exit(3)"])

    assert result.stdout.strip() == "hi"
    assert result.exit_code == 3
    assert result.timed_out is False
    assert result.duration >= 0


def test_run_command_captures_stderr():
    result = run_command(["python", "-c", "import sys; sys.stderr.write('oops')"])
    assert result.stderr == "oops"


def test_run_command_sends_stdin():
    result = run_command(["python", "-c", "import sys; print(sys.stdin.read().upper())"], stdin="abc")
    assert result.stdout.strip() == "ABC"


def test_run_command_passes_environment_variables():
    result = run_command(["python", "-c", "import os; print(os.environ['GREETING'])"], env={"GREETING": "hello"})
    assert result.stdout.strip() == "hello"


def test_run_command_timeout():
    result = run_command(["python", "-c", "import time; time.sleep(5)"], timeout=0.5)

    assert result.timed_out is True
    assert result.exit_code == -1


def test_run_command_missing_program():
    result = run_command("this_program_does_not_exist_123")

    assert result.exit_code == -1
    assert "Command not found" in result.stderr


def test_run_command_not_executable(tmp_path):
    result = run_command([str(tmp_path)])  # a folder can't be executed
    assert result.exit_code == -1
    assert result.stderr
