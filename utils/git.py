import bz2
import cli
import tempfile


def get_current_revision():
    rev = cli.call(["git", "rev-parse", "--short", "HEAD"])
    assert len(rev) == 7
    return rev


def has_revision(rev):
    return cli.call(["git", "cat-file", "-t", rev]) == "commit"


def get_patch_for_revision(from_rev, to_rev="HEAD"):
    assert has_revision(from_rev)
    assert has_revision(to_rev)
    rev_range = "..".join([from_rev, to_rev])
    output = cli.call(["git", "format-patch", "--stdout", "-k", "-U1", rev_range])
    return bz2.compress(output)


def set_user_and_email():
    # TODO: extract this somehow.
    email = "wrong92@gmail.com"
    name = "Michael Yong"
    cli.call(["git", "config", "user.email", email])
    cli.call(["git", "config", "user.name", name])


def apply_patch(compressed_patch):
    # Assert that the time is updated.
    output = cli.call(['date'])
    assert "2014" not in output
    assert "UTC" not in output
    set_user_and_email()

    patch = bz2.decompress(compressed_patch)
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(patch)
        temp.flush()
        output = cli.call(
            ["git", "am", "--committer-date-is-author-date", temp.name],
            on_error=["git", "am", "--abort"])
        return output


def main():
    print get_current_revision()
    print has_revision("696b253")
    # patch = get_patch_for_revision("b529507")
    # cli.call(["git", "reset", "--hard", "HEAD^"])
    # apply_patch(patch)


if __name__ == '__main__':
    main()
