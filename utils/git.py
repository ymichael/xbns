import bz2
import cli
import datetime
import subprocess
import tempfile

def get_current_revision():
    rev = cli.call(["git", "rev-parse", "--short", "HEAD"])
    assert len(rev) == 7
    return rev


def has_revision(rev):
    return cli.call(["git", "cat-file", "-t", rev]) == "commit"

def reset_hard_head():
    return cli.call(["git", "reset", "--hard", "HEAD"])


def get_revision_date(rev):
    date = cli.call(["git", "show", "-s", '--format=%ad', rev])
    format = "%a %b %d %H:%M:%S %Y"
    return datetime.datetime.strptime(date[:-6], format)


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
    # The time is updated for the commits to have the same hash.
    output = cli.call(['date'])
    if "2014" in output or "UTC" in output:
        return
    set_user_and_email()

    patch = bz2.decompress(compressed_patch)
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(patch)
        temp.flush()

        # Reset hard HEAD.
        # TODO: Figure out a way to get this value.
        counter = 100
        output = reset_hard_head()
        args = ["git", "am", "--reject", "--committer-date-is-author-date", temp.name]
        while counter:
            try:
                output = subprocess.check_output(args)
                break
            except subprocess.CalledProcessError, e:
                ["git", "am", "--committer-date-is-author-date", "--skip"]
                counter -= 1
        reset_hard_head()
        return output




def main():
    print get_current_revision()
    print has_revision("50033fe")
    print get_revision_date("50033fe")
    # patch = get_patch_for_revision("b529507")
    # cli.call(["git", "reset", "--hard", "HEAD^"])
    # apply_patch(patch)


if __name__ == '__main__':
    main()
