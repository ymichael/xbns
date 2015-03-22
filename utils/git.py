import bz2
import cli
import datetime
import logger
import subprocess
import tempfile


git_logger = logger.get_logger("utils.git")


def get_current_revision():
    rev = cli.call(["git", "rev-parse", "--short", "HEAD"])
    assert len(rev) == 7
    return rev


def has_revision(rev):
    return cli.call(["git", "cat-file", "-t", rev]) == "commit"

def reset_hard(rev="HEAD"):
    return cli.call(["git", "reset", "--hard", rev])


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
    git_logger.debug("Setting git user and email.")
    email = "wrong92@gmail.com"
    name = "Michael Yong"
    cli.call(["git", "config", "user.email", email])
    cli.call(["git", "config", "user.name", name])


def try_apply_patch(from_rev, to_rev, compressed_patch):
    # The time is updated for the commits to have the same hash.
    output = cli.call(['date'])
    if "2014" in output or "UTC" in output:
        git_logger.error("Time is not up-to-date.")
        return
    set_user_and_email()
    if not has_revision(from_rev):
        return
    # Store original revision to rollback (in case).
    git_logger.debug("Trying to apply patch.")
    original_rev = get_current_revision()
    # 1. reset --hard to from_rev
    reset_hard(from_rev)
    # 2. Apply patch
    patch = bz2.decompress(compressed_patch)
    with tempfile.NamedTemporaryFile() as temp:
        temp.write(patch)
        temp.flush()
        args = ["git", "am", "--reject", "--committer-date-is-author-date", temp.name]
        # Fail safe
        counter = 100
        while counter:
            try:
                output = subprocess.check_output(args)
                break
            except subprocess.CalledProcessError, e:
                ["git", "am", "--committer-date-is-author-date", "--skip"]
                counter -= 1
    # Check patch application.
    if get_current_revision() == to_rev:
        # 3. reset --hard to to_rev
        reset_hard()
        git_logger.debug("Patch succeeded, current revision %s" % get_current_revision())
    else:
        git_logger.debug("Patch failed, expected %s, got %s" % (to_rev, get_current_revision()))
        reset_hard(original_rev)
    return


def main():
    print get_current_revision()
    print has_revision("50033fe")
    print get_revision_date("50033fe")
    cur_rev = get_current_revision()
    try_apply_patch("d9e421a", cur_rev, get_patch_for_revision("d9e421a", cur_rev))


if __name__ == '__main__':
    main()
