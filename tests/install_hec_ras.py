import argparse
import sys
import subprocess


def main(argv):
    parser = argparse.ArgumentParser(add_help=False)

    req_args = parser.add_argument_group("Required")

    req_args.add_argument("--version", type=str, help="Version of HEC-RAS as string e.g. 50 for 5.0.0")

    args = parser.parse_args(argv)

    version = getattr(args, "version")

    if version in ("400", "500"):
        version = version[:-1]

    if version[0] == "4":
        base_url = "https://www.hec.usace.army.mil/software/hec-ras/downloads/HEC-RAS_{}_Setup.exe"
    else:
        # For versions >= 5, does not work on Github Actions
        base_url = "https://www.hec.usace.army.mil/software/hec-ras/downloads/HEC-RAS_{}_Setup_Without_Examples.exe"

    download_args = ["curl.exe", "--output", "hec.exe", "--url", base_url.format(version)]

    p = subprocess.Popen(download_args)
    p.wait()
    p.terminate()

    install_args = ["hec.exe", "/S", "/v/qn"]

    p = subprocess.Popen(install_args)
    p.wait()
    p.communicate(input="")
    p.terminate()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
