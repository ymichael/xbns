import bz2
import subprocess
import tempfile


def get_current_revision():
    output = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"])
    rev = output.strip()
    assert len(rev) == 7
    return rev


def has_revision(rev):
    try:
        output = subprocess.check_output(
            ["git", "cat-file", "-t", rev])
        return output.strip() == "commit"
    except subprocess.CalledProcessError:
        return False


def get_patch_for_revision(from_rev, to_rev="HEAD"):
    output = subprocess.check_output(
        ["git", "format-patch", "..".join([from_rev, to_rev]),
            "--stdout", "-k", "-U0", "--shortstat"])
    return bz2.compress(output)


def apply_patch(compressed_patch):
    patch = bz2.decompress(compressed_patch)
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(patch)
        try:
            output = subprocess.check_output(["git", "am", temp.name])
        except subprocess.CalledProcessError:
            # Abort the apply patch (am)
            subprocess.check_output(["git", "am", "--abort"])
        return output


def main():
    print get_current_revision()
    print has_revision("696b253")
    print apply_patch(get_patch_for_revision("696b253"))


if __name__ == '__main__':
    main()
