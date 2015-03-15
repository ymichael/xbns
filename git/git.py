import subprocess


def get_current_revision():
    output = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"])
    rev = output.strip()
    assert len(rev) == 7
    return rev


def main():
    print get_current_revision()

if __name__ == '__main__':
    main()