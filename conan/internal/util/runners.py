import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager

from conan.errors import ConanException
from conan.internal.util.files import load


if getattr(sys, "frozen", False) and "LD_LIBRARY_PATH" in os.environ:
    # http://pyinstaller.readthedocs.io/en/stable/runtime-information.html#ld-library-path-libpath-considerations
    pyinstaller_bundle_dir = (
        os.environ["LD_LIBRARY_PATH"]
        .replace(os.environ.get("LD_LIBRARY_PATH_ORIG", ""), "")
        .strip(";:")
    )

    @contextmanager
    def pyinstaller_bundle_env_cleaned():
        """Removes the pyinstaller bundle directory from LD_LIBRARY_PATH"""
        ld_library_path = os.environ["LD_LIBRARY_PATH"]
        os.environ["LD_LIBRARY_PATH"] = ld_library_path.replace(
            pyinstaller_bundle_dir, ""
        ).strip(";:")
        yield
        os.environ["LD_LIBRARY_PATH"] = ld_library_path

else:

    @contextmanager
    def pyinstaller_bundle_env_cleaned():
        yield


def conan_run(command, stdout=None, stderr=None, cwd=None, shell=True):
    """
    @param shell:
    @param stderr:
    @param command: Command to execute
    @param stdout: Instead of print to sys.stdout print to that stream. Could be None
    @param cwd: Move to directory to execute
    """
    # Default stdout should be sys.stdout (not sys.stderr). Keep stderr defaulting to sys.stderr.
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr

    # If the provided stdout/stderr are in-memory streams (like io.StringIO) they don't have
    # a fileno(), so we must use PIPE to capture subprocess output and write it back into
    # the provided stream. Otherwise pass the stream directly to Popen.
    out = (
        subprocess.PIPE
        if (hasattr(stdout, "write") and not hasattr(stdout, "fileno"))
        else stdout
    )
    err = (
        subprocess.PIPE
        if (hasattr(stderr, "write") and not hasattr(stderr, "fileno"))
        else stderr
    )

    with pyinstaller_bundle_env_cleaned():
        try:
            proc = subprocess.Popen(
                command, shell=shell, stdout=out, stderr=err, cwd=cwd
            )
        except Exception as e:
            raise ConanException("Error while running cmd\nError: %s" % (str(e)))

        proc_stdout, proc_stderr = proc.communicate()
        # If the output is piped (we used PIPE), communicate() will return bytes even if empty.
        # Write back the decoded text to the provided stream if we captured it (proc_stdout is not None).
        if proc_stdout is not None:
            try:
                stdout.write(proc_stdout.decode("utf-8", errors="ignore"))
            except Exception:
                # Fallback in case stdout expects bytes-like write
                try:
                    stdout.write(proc_stdout)
                except Exception:
                    pass
        if proc_stderr is not None:
            try:
                stderr.write(proc_stderr.decode("utf-8", errors="ignore"))
            except Exception:
                try:
                    stderr.write(proc_stderr)
                except Exception:
                    pass
        return proc.returncode


def detect_runner(command):
    # Running detect.py automatic detection of profile
    proc = subprocess.Popen(
        command,
        shell=True,
        bufsize=1,
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    output_buffer = []
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        # output.write(line)
        output_buffer.append(str(line))

    proc.communicate()
    return proc.returncode, "".join(output_buffer)


def check_output_runner(cmd, stderr=None, ignore_error=False):
    # Used to run several utilities, like Pacman detect, AIX version, uname, SCM
    assert isinstance(cmd, str)
    d = tempfile.mkdtemp()
    tmp_file = os.path.join(d, "output")
    try:
        # We don't want stderr to print warnings that will mess the pristine outputs
        stderr = stderr or subprocess.PIPE
        command = '{} > "{}"'.format(cmd, tmp_file)
        process = subprocess.Popen(command, shell=True, stderr=stderr)
        stdout_bytes, stderr_bytes = process.communicate()

        # Read the captured stdout from the temp file so we can include it in errors too
        try:
            output = load(tmp_file)
        except Exception:
            output = ""

        if process.returncode and not ignore_error:
            # Only in case of error, include stderr and captured stdout to know what happened
            if stderr_bytes:
                try:
                    stderr_text = stderr_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    stderr_text = str(stderr_bytes)
            else:
                stderr_text = ""
            msg = f"Command '{cmd}' failed with errorcode '{process.returncode}'\n{stderr_text}\n{output}"
            raise ConanException(msg)

        return output
    finally:
        try:
            os.unlink(tmp_file)
        except OSError:
            pass
