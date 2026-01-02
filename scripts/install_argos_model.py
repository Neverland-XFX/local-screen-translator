import argparse

import argostranslate.package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="from_code", default="ja")
    parser.add_argument("--to", dest="to_code", default="zh")
    args = parser.parse_args()

    from_code = args.from_code
    to_code = args.to_code
    print("Updating Argos package index...")
    argostranslate.package.update_package_index()
    packages = argostranslate.package.get_available_packages()
    match = next(
        (pkg for pkg in packages if pkg.from_code == from_code and pkg.to_code == to_code),
        None,
    )
    if not match:
        print(f"Model not found for {from_code} -> {to_code}.")
        return 1

    print("Downloading model...")
    path = match.download()
    print(f"Installing from {path}...")
    argostranslate.package.install_from_path(path)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
