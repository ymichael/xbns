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
    assert has_revision(from_rev)
    assert has_revision(to_rev)
    output = subprocess.check_output(
        ["git", "format-patch", "--stdout", "-k", "-U1",
            "..".join([from_rev, to_rev])])
    return bz2.compress(output)


def apply_patch(compressed_patch):
    patch = bz2.decompress(compressed_patch)
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(patch)
        temp.flush()
        try:
            output = ""
            output = subprocess.check_output(
                ["git", "am", "--ignore-date",
                    "--committer-date-is-author-date", temp.name])
        except subprocess.CalledProcessError, e:
            output += e.output
            try:
                # Abort the apply patch (am)
                output += subprocess.check_output(["git", "am", "--abort"])
            except subprocess.CalledProcessError, e:
                output += e.output
        return output


def main():
    print get_current_revision()
    print has_revision("696b253")
    # patch = get_patch_for_revision("b529507")
    # subprocess.check_output(["git", "reset", "--hard", "HEAD^"])
    # apply_patch(patch)


if __name__ == '__main__':
    main()
