import subprocess
import logger

cli_logger = logger.get_logger("utils.cli")

def call(args, on_error=None):
    """Wrapper around `subprocess.check_output` to catch exceptions.

    callutes on_error if provided if an error occurs.
    """
    try:
        output = subprocess.check_output(args)
        cli_logger.debug(output.strip())
    except subprocess.CalledProcessError, e:
        output = e.output
        cli_logger.error(output.strip())
        if on_error is not None: call(on_error)
    return output.strip()

