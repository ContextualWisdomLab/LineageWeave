from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_frontend_container_copies_the_single_build_script_policy() -> None:
    """Each image install must receive the fail-closed pnpm allowlist first."""
    workspace = (ROOT / "frontend" / "pnpm-workspace.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8").splitlines()

    assert workspace == "allowBuilds:\n  esbuild: true\n"
    stage = -1
    policy_copies: list[tuple[int, int]] = []
    installs: list[tuple[int, int]] = []
    for line_number, line in enumerate(dockerfile, start=1):
        command = line.strip()
        if command.upper().startswith("FROM "):
            stage += 1
        if command == "COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./":
            policy_copies.append((line_number, stage))
        if command.startswith("RUN ") and "pnpm install" in command:
            installs.append((line_number, stage))

    assert installs
    assert all(
        any(copy_stage == install_stage and copy_line < install_line for copy_line, copy_stage in policy_copies)
        for install_line, install_stage in installs
    )
