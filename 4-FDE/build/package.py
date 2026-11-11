"""Synchronize canonical documents and rebuild the companion ZIP deterministically."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import shutil
import zipfile

BUILD = Path(__file__).resolve().parent
FDE = BUILD.parent
REPO = FDE.parent
DEFAULT_RESOURCES = FDE / "resources_10.06.4"
CANONICAL = {
    "inputs/开发计划.md": "4-FDE/开发计划.md",
    "inputs/调研报告（对内）.md": "2-项目经理/④调研/调研报告（对内）.md",
    "00-fde-flow/FDE_流程图_内部执行版.html": "1-FDE交付流程/FDE_流程图_内部执行版.html",
}
OLD_INPUTS = {"inputs/开发计划模板_10.08.md", "inputs/通用调研输入文档_10.06.md"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sync(resources):
    for name in OLD_INPUTS:
        (resources / name).unlink(missing_ok=True)
    for target, source in CANONICAL.items():
        destination = resources / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / source, destination)


def update_manifest(files):
    manifest = json.loads(files["manifest.json"])
    manifest.update(version="11.11.0", date="2026-11-11", publication_revision="11.11.0")
    for key, target, source in (
        ("development_plan_template", "inputs/开发计划.md", "4-FDE/开发计划.md"),
        ("research_input", "inputs/调研报告（对内）.md", "2-项目经理/④调研/调研报告（对内）.md"),
        ("workflow", "00-fde-flow/FDE_流程图_内部执行版.html", "1-FDE交付流程/FDE_流程图_内部执行版.html"),
    ):
        data = files[target]
        entry = {
            "version": "11.11.0",
            "status": "available" if key != "workflow" else "revised-nine-node-workflow",
            "repository_path": source,
            "archive_path": target,
            "sha256": sha(data),
            "bytes": len(data),
        }
        if key == "development_plan_template":
            entry["included_in_this_companion_archive"] = True
        if key == "workflow":
            entry["source_sha256"] = entry["sha256"]
            entry["archive_sha256"] = entry["sha256"]
            entry["link_adaptation"] = "Nine-node internal execution edition; canonical HTML copied byte-for-byte."
        manifest[key] = entry
    catalog_path = REPO / "tools/catalog.json"
    if catalog_path.exists():
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        meta = next(p for p in catalog["packages"] if p.get("slug") == "meta-spec")
        for item in manifest.get("separate_downloads", []):
            if item.get("tool") == "meta-spec":
                item.update(
                    sha256=meta["sha256"], bytes=meta["bytes"],
                    members=meta["member_count"], version=meta["version"],
                )
    files["manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resources", type=Path, default=DEFAULT_RESOURCES)
    parser.add_argument("--output", type=Path, default=FDE / "FDE开发配套资源包_10.06.zip")
    args = parser.parse_args()
    resources = args.resources.resolve()
    if resources == DEFAULT_RESOURCES:
        sync(resources)
    files = {}
    for file in sorted(resources.rglob("*")):
        if file.is_symlink():
            raise ValueError("Symlink: " + str(file))
        if file.is_file() and file.name not in {".DS_Store", "SHA256SUMS.txt"}:
            name = file.relative_to(resources).as_posix()
            assert ".." not in PurePosixPath(name).parts
            files[name] = file.read_bytes()
    update_manifest(files)
    (resources / "manifest.json").write_bytes(files["manifest.json"])
    for package in json.loads(files["manifest.json"])["packages"]:
        assert sha(files[package["file"]]) == package["sha256"], package["file"]
    files["SHA256SUMS.txt"] = "".join(
        f"{sha(data)}  {name}\n" for name, data in sorted(files.items())
    ).encode()
    (resources / "SHA256SUMS.txt").write_bytes(files["SHA256SUMS.txt"])
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(name, (2026, 11, 11, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o100644 << 16
            archive.writestr(item, data)
    print(json.dumps({
        "file": args.output.name,
        "sha256": sha(args.output.read_bytes()),
        "packages": len(json.loads(files["manifest.json"])["packages"]),
        "files": len(files),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
