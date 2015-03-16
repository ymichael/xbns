import subprocess


def call(args, on_error=None):
    """Wrapper around `subprocess.check_output` to catch exceptions.

    callutes on_error if provided if an error occurs.
    """
    try:
        output = subprocess.check_output(args)
    except subprocess.CalledProcessError, e:
        output = e.output
        if on_error is not None: call(on_error)
    return output

