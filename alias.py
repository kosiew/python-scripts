#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Optional, List

import typer

app = typer.Typer(
    name="alias-cli",
    help="Reusable helpers for zsh aliases (GitHub issue notes, templating, git helpers).",
    no_args_is_help=True,
)

# -------------------------
# Utilities
# -------------------------

def _which(name: str) -> bool:
    return any((Path(p) / name).exists() for p in os.environ.get("PATH", "").split(os.pathsep))

def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("check", True)
    kw.setdefault("text", True)
    kw.setdefault("capture_output", True)
    return subprocess.run(cmd, **kw)

def _nowstamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M")

def _extract_id(url: str) -> str:
    return url.rstrip("/").split("/")[-1]

def _llm(flags: list[str], prompt: str, input_text: Optional[str] = None) -> str:
    if not _which("llm"):
        return ""
    try:
        proc = _run(["llm", *flags, prompt], input=input_text)
        return proc.stdout or ""
    except Exception:
        return ""

def _open_in_editor(path: Path, editor: Optional[str]) -> None:
    ed = editor or os.environ.get("EDITOR") or "vi"
    try:
        subprocess.run([ed, str(path)])
    except Exception:
        typer.secho(f"⚠️ Failed to open editor '{ed}'. File saved: {path}", fg=typer.colors.YELLOW)


def _git_main_branch() -> Optional[str]:
    """Try to detect the repository's main branch name.

    Preference order: 'main', 'master', remote origin HEAD, else None.
    """
    try:
        # Prefer local branches if they exist
        for name in ("main", "master"):
            proc = _run(["git", "show-ref", f"refs/heads/{name}"], check=False)
            if proc.returncode == 0:
                return name

        # Try origin/HEAD symbolic-ref
        proc = _run(["git", "rev-parse", "--abbrev-ref", "origin/HEAD"], check=False)
        out = (proc.stdout or "").strip()
        if out and out != "origin/HEAD":
            # rev-parse may return 'origin/main' → pick last segment
            return out.split("/")[-1]

        # Try remote show origin to parse HEAD branch
        proc = _run(["git", "remote", "show", "origin"], check=False)
        text = proc.stdout or ""
        m = re.search(r"HEAD branch: (\S+)", text)
        if m:
            return m.group(1)
    except Exception:
        return None
    return None

# -------------------------
# Filename & summaries
# -------------------------

def _gen_short_title(title_source: str) -> str:
    prompt = (
        "Generate a short, kebab-case filename-style title for this GitHub issue. "
        "Avoid punctuation. No more than 8 words."
    )
    out = _llm(["-u", "-ef", title_source], prompt).strip()
    first = (out.splitlines() or [""])[0]
    cleaned = re.sub(r"[^A-Za-z0-9\-]", "", first)
    return cleaned or "note"

def _gen_summary_from_issue(url: str) -> str:
    prompt = (
        "Summarize this GitHub issue concisely for a senior contributor.\n"
        "- Max ~80 words total.\n"
        "- Focus on the problem, scope, impact, and any constraints.\n"
        "- No code, no headers.\n"
        "- Prefer 3–6 tight bullet points if it helps clarity."
    )
    out = _llm(["-u", "-ef", f"issue:{url}"], prompt)
    lines = [("- " + re.sub(r"^\s*-\s*", "", l).strip())
             for l in out.splitlines() if l.strip()]
    return "\n".join(lines).strip()

def _gen_filename(issue_id: str, title_source: str, prefix: str = "note") -> Path:
    short = _gen_short_title(title_source)
    ts = _nowstamp()
    return Path(os.path.expanduser("~/tmp")) / f"{issue_id}-{prefix}-{short}_{ts}.md"

DEFAULT_TEMPLATE = """**Role:** You are a **senior open-source contributor and software engineer**.

**Task:** Given a GitHub issue and the associated codebase, produce a strategic and actionable review by following these steps:

## Description of issue
${summary}

**Steps:**

1. Review the repository to locate all areas relevant to the issue.
2. Determine whether the solution requires modifying existing code or extending the codebase.
3. Provide a high-level, detailed action plan for resolving the issue.

---

**Guidelines:**

* Do **not** generate code.
* Keep the commentary concise and strategic.
* Focus on problem analysis and solution direction rather than implementation details.
* Ensure the output is actionable for a coding agent without unnecessary narrative.
"""

# -------------------------
# Commands
# -------------------------

@app.command(help="Generate filename like <id>-<prefix>-<slug>_<ts>.md")
def gen_filename(
    id: str = typer.Argument(..., help="Issue/PR numeric id (last URL segment)"),
    title_source: str = typer.Argument(..., help='Title source, e.g. "issue:<url>"'),
    prefix: str = typer.Option("note", "--prefix", "-p", help="Filename prefix"),
):
    path = _gen_filename(id, title_source, prefix)
    typer.echo(str(path))

@app.command(help="Summarize a GitHub issue into concise bullets")
def summary(url: str = typer.Argument(..., help="GitHub issue/PR URL")):
    s = _gen_summary_from_issue(url)
    typer.echo(s or "(Summary could not be auto-generated. Replace with 3–6 concise bullets.)")

@app.command("render-note", help="Render a template with ${summary}, ${url}, ${id}, ${timestamp}")
def render_note(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="Path or '-' for stdin"),
    prefix: str = typer.Option("icask", "--prefix", "-p", help="Filename prefix"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    issue_id = _extract_id(url)
    ts = _nowstamp()

    summary_text = _gen_summary_from_issue(url)
    if not summary_text:
        summary_text = "(Summary could not be auto-generated. Replace with 3–6 concise bullets: problem, scope, impact, constraints.)"

    if template == "-":
        tpl_text = sys.stdin.read()
    elif template:
        tpl_text = Path(template).read_text(encoding="utf-8")
    else:
        tpl_text = DEFAULT_TEMPLATE

    content = Template(tpl_text).safe_substitute(
        summary=summary_text, url=url, id=issue_id, timestamp=ts
    )

    outpath = _gen_filename(issue_id, f"issue:{url}", prefix)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(content, encoding="utf-8")
    typer.secho(f"✅ Wrote: {outpath}", fg=typer.colors.GREEN)

    if not no_open:
        _open_in_editor(outpath, editor)

@app.command("issue-to-file", help="Run LLM over issue context with a prompt → file (like _process_issue)")
def issue_to_file(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    prompt: str = typer.Option(..., "--prompt", "-m", help="LLM prompt"),
    prefix: str = typer.Option("note", "--prefix", "-p", help="Filename prefix"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    if not _which("llm"):
        typer.secho("❌ 'llm' not found in PATH.", fg=typer.colors.RED)
        raise typer.Exit(1)


    

    issue_id = _extract_id(url)
    outpath = _gen_filename(issue_id, f"issue:{url}", prefix)
    outpath.parent.mkdir(parents=True, exist_ok=True)

    try:
        proc = _run(["llm", "-u", "-ef", f"issue:{url}", prompt])
        outpath.write_text(proc.stdout, encoding="utf-8")
    except subprocess.CalledProcessError:
        outpath.unlink(missing_ok=True)
        typer.secho("❌ LLM generation failed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"✅ Wrote: {outpath}", fg=typer.colors.GREEN)
    if not no_open:
        _open_in_editor(outpath, editor)

@app.command("clipboard-to-file", help="Apply prompt to clipboard content → file (like _process_clipboard_issue)")
def clipboard_to_file(
    prompt: str = typer.Option(..., "--prompt", "-m", help="LLM prompt"),
    prefix: str = typer.Option("clip", "--prefix", "-p", help="Filename prefix"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    if sys.platform != "darwin":
        typer.secho("❌ Clipboard mode currently supports macOS (pbpaste).", fg=typer.colors.RED)
        raise typer.Exit(1)
    if not _which("llm"):
        typer.secho("❌ 'llm' not found in PATH.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # derive short title from clipboard
    short = "note"
    try:
        clip = _run(["pbpaste"]).stdout
        gen = _llm(["-s",
                    "Generate a short, kebab-case filename-style title for this GitHub issue. Avoid punctuation. No more than 8 words."],
                   input_text=clip)
        cand = (gen.splitlines() or [""])[0]
        cleaned = re.sub(r"[^A-Za-z0-9\-]", "", cand)
        short = cleaned or "note"
    except Exception:
        pass

    outpath = Path(os.path.expanduser("~/tmp")) / f"{prefix}-{short}_{_nowstamp()}.md"
    outpath.parent.mkdir(parents=True, exist_ok=True)

    try:
        proc = _run(["llm", prompt], input=clip)
        outpath.write_text(proc.stdout, encoding="utf-8")
    except Exception:
        outpath.unlink(missing_ok=True)
        typer.secho("❌ Clipboard + LLM generation failed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"✅ Wrote: {outpath}", fg=typer.colors.GREEN)
    if not no_open:
        _open_in_editor(outpath, editor)

@app.command(help="Print commit hash(es) for PR number by grepping commit messages")
def gprhash(pr: str = typer.Argument(..., help="PR number, e.g. 43197")):
    try:
        out = _run(["git", "log", "--oneline", f"--grep=#{pr}"]).stdout.strip()
    except Exception:
        typer.secho("❌ Not a git repo or git error.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not out:
        typer.echo("No matching commits found.")
        raise typer.Exit(0)

    for line in out.splitlines():
        typer.echo(line.split()[0])


@app.command(help="Show git diff in various modes and copy output to clipboard (gdiff)")
def gdiff(args: List[str] = typer.Argument(None, help="Arguments forwarded to git diff")) -> None:
    """Mimic the shell `gdiff` helper with these modes:
      - gdiff <ref>                # compare working tree with <ref>
      - gdiff <a> <b>              # compare a ↔ b
      - gdiff <commit> <files...>  # compare commit with specific files
      - gdiff                      # compare with repo main branch

    The diff is written to ~/tmp/gdiff-<ts>.patch, copied to clipboard on macOS
    (pbcopy), and opened in $EDITOR (falls back to vi).
    """
    items = args or []

    # Determine default branch if needed
    def_branch = _git_main_branch() or "main"

    # Build git diff command depending on args
    if len(items) == 1:
        typer.secho(f"🔍 Comparing working tree with: {items[0]}", fg=typer.colors.CYAN)
        cmd = ["git", "diff", items[0]]
    elif len(items) == 2:
        typer.secho(f"🔍 Comparing: {items[0]} ↔ {items[1]}", fg=typer.colors.CYAN)
        cmd = ["git", "diff", items[0], items[1]]
    elif len(items) >= 3:
        commit = items[0]
        files = items[1:]
        typer.secho(f"🔍 Comparing: {commit} with specific files: {' '.join(files)}", fg=typer.colors.CYAN)
        cmd = ["git", "diff", commit, "--", *files]
    else:
        typer.secho(f"🔍 No arguments provided. Comparing against default branch: {def_branch}", fg=typer.colors.CYAN)
        cmd = ["git", "diff", def_branch]

    # Run git diff and capture output
    try:
        proc = _run(cmd, check=False)
        diff_text = proc.stdout or ""
    except Exception:
        typer.secho("❌ git diff failed or not a repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Ensure tmp directory exists and write file
    outdir = Path(os.path.expanduser("~/tmp"))
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / f"gdiff-{_nowstamp()}.patch"
    outpath.write_text(diff_text, encoding="utf-8")

    # Copy to clipboard on macOS if pbcopy present
    if sys.platform == "darwin" and _which("pbcopy"):
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(diff_text.encode())
            typer.secho("📋 Diff output copied to clipboard!", fg=typer.colors.GREEN)
        except Exception:
            typer.secho("⚠️ Failed to copy to clipboard.", fg=typer.colors.YELLOW)
    else:
        typer.echo("📋 Diff output saved to: " + str(outpath))

    # Open in editor
    editor = os.environ.get("EDITOR") or "vi"
    _open_in_editor(outpath, editor)


@app.command(help="Show git diff --stat for commits or working tree (gs)")
def gs(args: List[str] = typer.Argument(None, help="Arguments forwarded: [commit_early] [commit_late]")) -> None:
    """Show `git diff --stat` in three modes:
      - gs <commit>           # working tree vs commit
      - gs <a> <b>            # diff stat between a and b
      - gs                    # diff stat vs repo main
    """
    items = args or []
    if len(items) == 1:
        typer.secho(f"📊 Showing diff stat between working tree and: {items[0]}", fg=typer.colors.CYAN)
        cmd = ["git", "diff", "--stat", items[0]]
    elif len(items) == 2:
        typer.secho(f"📊 Showing diff stat between: {items[0]} ↔ {items[1]}", fg=typer.colors.CYAN)
        cmd = ["git", "diff", "--stat", items[0], items[1]]
    elif len(items) == 0:
        default_branch = _git_main_branch() or "main"
        typer.secho(f"📊 No arguments provided. Showing diff stat against default branch: {default_branch}", fg=typer.colors.CYAN)
        cmd = ["git", "diff", "--stat", default_branch]
    else:
        typer.secho("Usage: gs <commit_early> [<commit_late>]", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        proc = _run(cmd, check=False)
        output = proc.stdout or ""
    except Exception:
        typer.secho("❌ git diff --stat failed or not a repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    outdir = Path(os.path.expanduser("~/tmp"))
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / f"gs-{_nowstamp()}.txt"
    outpath.write_text(output, encoding="utf-8")

    editor = os.environ.get("EDITOR") or "vi"
    _open_in_editor(outpath, editor)


@app.command(name="grmuntracked", help="Remove untracked files (asks for confirmation)")
def grmuntracked(dry_run: bool = typer.Option(False, "--dry-run", help="Show files without deleting")) -> None:
    """List untracked files (git ls-files --others --exclude-standard) and delete them after confirmation.

    Use --dry-run to only show the list.
    """
    try:
        proc = _run(["git", "ls-files", "--others", "--exclude-standard"], check=False)
        out = (proc.stdout or "").strip()
    except Exception:
        typer.secho("❌ Not a git repository or git error.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not out:
        typer.secho("✅ No untracked files to remove.", fg=typer.colors.GREEN)
        raise typer.Exit(0)

    files = out.splitlines()

    typer.secho("🚨 The following untracked files will be removed:", fg=typer.colors.YELLOW)
    for f in files:
        typer.echo(f"   {f}")

    if dry_run:
        raise typer.Exit(0)

    if not typer.confirm("Are you sure you want to delete these files? [y/N]", default=False):
        typer.secho("❌ Aborted. No files were deleted.", fg=typer.colors.RED)
        raise typer.Exit(0)

    import shutil

    failed = False
    for f in files:
        p = Path(f)
        try:
            if p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()
        except Exception as exc:
            typer.secho(f"❌ Failed to remove {f}: {exc}", fg=typer.colors.RED)
            failed = True

    if not failed:
        typer.secho("🗑️ Untracked files deleted.", fg=typer.colors.GREEN)
    else:
        typer.secho("⚠️ Some files failed to delete; check errors above.", fg=typer.colors.YELLOW)


@app.command(help="Create a new branch, optionally replacing an existing local branch (gnb)")
def gnb(branch: str = typer.Argument(..., help="New branch name")) -> None:
    """Create a new branch <branch>. If it already exists locally, delete it first.

    Then check out AGENTS.md from dev into the new branch, add and commit it with message
    'UNPICK added AGENTS.md' — mirroring the shell helper.
    """
    if not branch:
        typer.secho("Usage: gnb <new-branch-name>", fg=typer.colors.RED)
        raise typer.Exit(1)

    # If branch exists locally, delete it
    if _run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False).returncode == 0:
        typer.secho(f"🗑️ Deleting existing branch '{branch}'...", fg=typer.colors.YELLOW)
        try:
            _run(["git", "branch", "-D", branch])
        except Exception:
            typer.secho(f"❌ Failed to delete branch '{branch}'.", fg=typer.colors.RED)
            raise typer.Exit(1)

    # Create and switch to new branch
    try:
        _run(["git", "checkout", "-b", branch])
    except Exception:
        typer.secho(f"❌ Failed to create branch '{branch}'.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Checkout AGENTS.md from dev, add and commit
    try:
        _run(["git", "checkout", "dev", "--", "AGENTS.md"]) 
        _run(["git", "add", "AGENTS.md"])
        _run(["git", "commit", "-m", "UNPICK added AGENTS.md"])
    except subprocess.CalledProcessError:
        typer.secho("❌ Failed to checkout or commit AGENTS.md; continue if not applicable.", fg=typer.colors.YELLOW)
    except Exception:
        # non-fatal: some repos may not have AGENTS.md
        pass


@app.command(help="Run repository-specific rust clippy script and open output (rust_clippy)")
def rust_clippy() -> None:
    """Run `ci/scripts/rust_clippy.sh` if present and open the captured output in $EDITOR.

    Mirrors the shell helper which runs the CI script and pipes output to `vi -`.
    """
    script = Path("ci/scripts/rust_clippy.sh")
    if script.exists() and os.access(script, os.X_OK):
        typer.secho("👋 running datafusion rust_clippy", fg=typer.colors.CYAN)
        try:
            proc = _run([str(script)], check=False)
            output = proc.stdout or ""
            outdir = Path(os.path.expanduser("~/tmp"))
            outdir.mkdir(parents=True, exist_ok=True)
            outpath = outdir / f"rust_clippy-{_nowstamp()}.txt"
            outpath.write_text(output, encoding="utf-8")
            editor = os.environ.get("EDITOR") or "vi"
            _open_in_editor(outpath, editor)
        except Exception:
            typer.secho("❌ Failed running rust_clippy script.", fg=typer.colors.RED)
            raise typer.Exit(1)
    else:
        typer.secho("⚠️ ci/scripts/rust_clippy.sh not found or not executable.", fg=typer.colors.YELLOW)


@app.command(help="Run cargo check with optional head/tail and project selection (ccheck)")
def ccheck(
    head: Optional[int] = typer.Option(None, "-h", help="Show only first N lines"),
    tail: Optional[int] = typer.Option(None, "-t", help="Show only last N lines"),
    project: Optional[str] = typer.Option(None, "-p", help="Cargo package (-p)")
) -> None:
    """Run `cargo check` (optionally -p <project>) and show output in $EDITOR.

    Use -h N to show head N lines, -t N to show tail N lines.
    """
    cmd = ["cargo", "check"]
    if project:
        cmd.extend(["-p", project])

    try:
        proc = _run(cmd, check=False)
        out = proc.stdout or ""
    except Exception:
        typer.secho("❌ Failed to run cargo check (is cargo installed?).", fg=typer.colors.RED)
        raise typer.Exit(1)

    lines = out.splitlines()
    if head is not None and head > 0:
        lines = lines[:head]
    if tail is not None and tail > 0:
        lines = lines[-tail:]

    content = "\n".join(lines)
    outdir = Path(os.path.expanduser("~/tmp"))
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / f"ccheck-{_nowstamp()}.txt"
    outpath.write_text(content, encoding="utf-8")

    editor = os.environ.get("EDITOR") or "vi"
    _open_in_editor(outpath, editor)

@app.command(name="encode_and_copy")
def encode_and_copy_cmd(
    text: str = typer.Argument(..., help="Text to base64-encode and copy to clipboard")
):
    """Base64-encode the given text and copy to the macOS clipboard (pbcopy)."""
    import base64
    import subprocess
    import sys

    encoded = base64.b64encode(text.encode()).decode()
    if sys.platform == "darwin":
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(encoded.encode())
            typer.echo("Encoded message copied to clipboard.")
        except Exception:
            typer.echo("Failed to copy to clipboard; printing encoded text:")
            typer.echo(encoded)
    else:
        # Non-macOS fallback: print encoded value
        typer.echo(encoded)


@app.command(name="prettier_toggle")
def prettier_toggle_cmd() -> None:
    """Toggle ~/prettier-sql/.prettierrc by moving it to ~/tmp/.prettierrc and back.

    Mirrors the existing shell helper: if the file exists, move it to ~/tmp/.prettierrc;
    if the tmp exists, restore it back. Prints a short status message.
    """
    import shutil
    from pathlib import Path

    home = Path.home()
    file_path = home / "prettier-sql" / ".prettierrc"
    tmp_path = home / "tmp" / ".prettierrc"

    # Ensure tmp dir exists when moving to it
    try:
        if file_path.exists():
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(tmp_path))
            typer.echo("👋 Hiding .prettierrc → ~/tmp/")
            return

        if tmp_path.exists():
            # restore to original location
            (file_path.parent).mkdir(parents=True, exist_ok=True)
            shutil.move(str(tmp_path), str(file_path))
            typer.echo("🔄 Restoring .prettierrc → ~/")
            return

        typer.echo("⚠️ No .prettierrc found to hide or restore.")
    except Exception as exc:
        typer.echo(f"❌ Error toggling .prettierrc: {exc}")


@app.command(name="chatmodes_copy")
def chatmodes_copy_cmd(
    folder_name: str = typer.Argument(..., help="Target GitHub folder name (under ~/GitHub)"),
    preserve: bool = typer.Option(False, "--preserve", help="Preserve timestamps/permissions (uses shutil.copy2)"),
) -> None:
    """Copy chatmodes markdown files from chezmoi to the target repo's .github/chatmodes folder.

    Mirrors the existing shell helper:
      - source: ~/.local/share/chezmoi/GitHub/datafusion/dot_github/chatmodes
      - target: ~/GitHub/<folder_name>/.github/chatmodes
    Prints success or usage message on error.
    """
    if not folder_name:
        typer.secho("❗ Usage: chatmodes_copy <folder_name>", fg=typer.colors.RED)
        raise typer.Exit(1)

    home = Path.home()
    target = home / "GitHub" / folder_name / ".github" / "chatmodes"
    source = home / ".local" / "share" / "chezmoi" / "GitHub" / "datafusion" / "dot_github" / "chatmodes"

    try:
        import shutil

        target.mkdir(parents=True, exist_ok=True)

        md_files = list(source.glob("*.md")) if source.exists() else []
        if not md_files:
            typer.secho(f"⚠️ No .md files found in source: {source}", fg=typer.colors.YELLOW)
            raise typer.Exit(1)

        for f in md_files:
            dest = target / f.name
            if preserve:
                shutil.copy2(str(f), str(dest))
            else:
                # previous behavior: copy content
                dest.write_bytes(f.read_bytes())

        msg = f"✅ Copied chatmodes to {target}"
        if preserve:
            msg += " (preserved timestamps/permissions)"
        typer.secho(msg, fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to copy chatmodes: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command(help="Switch to main, sync, and return to the previous branch (gsm)")
def gsm() -> None:
    """Save current branch, run `gcom` to switch to main, run `gsync`, then return to the saved branch.

    Mirrors the shell helper: prints progress and exits with non-zero on failures.
    """
    try:
        # determine current branch
        proc = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        cur_branch = proc.stdout.strip()
    except Exception:
        typer.secho("❌ Not a git repo or cannot determine current branch.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("📌 Saving current branch...")

    typer.echo("🔁 Switching to main branch using gcom...")
    try:
        gcom()
    except Exception:
        typer.secho("❌ Failed to switch to main branch.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("🔄 Syncing with upstream...")
    try:
        gsync()
    except Exception:
        typer.secho("❌ Failed to sync with upstream.", fg=typer.colors.RED)
        # attempt to return to original branch
        try:
            _run(["git", "checkout", cur_branch])
        except Exception:
            pass
        raise typer.Exit(1)

    typer.echo(f"↩️ Returning to previous branch: {cur_branch}")
    try:
        _run(["git", "checkout", cur_branch])
    except Exception:
        typer.secho(f"❌ Failed to return to {cur_branch}.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("✅ Done!", fg=typer.colors.GREEN)


@app.command(help="Delete a git branch locally and on origin after confirmation (gdb)")
def gdb(branch: str = typer.Argument(..., help="Branch name to delete")) -> None:
    """Delete a local branch and remove it from origin after explicit confirmation.

    Mirrors the shell `gdb` helper: prompts the user with a clear warning and proceeds
    only if the user types 'y' or 'Y'. Uses `git branch -d` and `git push origin --delete`.
    """
    if not branch:
        typer.echo("Usage: gdb <branch-name>")
        raise typer.Exit(1)

    typer.secho(f"⚠️  WARNING: This will delete the branch '{branch}' locally and remotely (origin).", fg=typer.colors.YELLOW)
    confirm = typer.prompt("Are you sure? (y/N)")

    if confirm.lower() != "y":
        typer.secho(f"❌ Aborted: Branch '{branch}' was not deleted.", fg=typer.colors.RED)
        raise typer.Exit(0)

    try:
        _run(["git", "branch", "-d", branch])
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ Failed to delete local branch '{branch}': {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        _run(["git", "push", "origin", "--delete", branch])
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ Failed to delete remote branch 'origin/{branch}': {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"✅ Deleted branch '{branch}' locally and on origin.", fg=typer.colors.GREEN)


@app.command(help="Show files changed compared to a branch (gdn)")
def gdn(branch: Optional[str] = typer.Argument(None, help="Branch to compare against (defaults to repo main)")) -> None:
    """Run `git diff --name-only <branch>` and open the list in $EDITOR (falls back to vi).

    If branch is omitted, attempt to detect the repo's main branch.
    """
    b = branch
    if not b:
        b = _git_main_branch() or "main"

    typer.secho(f"🔍 Comparing against branch: {b}", fg=typer.colors.CYAN)

    try:
        proc = _run(["git", "diff", "--name-only", b])
        output = proc.stdout or ""
    except Exception as exc:
        typer.secho(f"❌ git diff failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Write to a temporary file and open in editor
    tmp = Path(os.path.expanduser("~/tmp"))
    tmp.mkdir(parents=True, exist_ok=True)
    outpath = tmp / f"gdn-{b}-{_nowstamp()}.txt"
    outpath.write_text(output, encoding="utf-8")
    editor = os.environ.get("EDITOR") or "vi"
    _open_in_editor(outpath, editor)


@app.command(help="Checkout the repository's main branch (gcom)")
def gcom() -> None:
    """Checkout the repository's main branch determined by `_git_main_branch()`.

    Prints progress and exits non-zero on failure.
    """
    branch = _git_main_branch() or "main"
    typer.secho(f"🔁 Switching to main branch: {branch}", fg=typer.colors.CYAN)
    try:
        _run(["git", "checkout", branch])
    except Exception as exc:
        typer.secho(f"❌ Failed to switch to {branch}: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)
    typer.secho(f"✅ Checked out {branch}", fg=typer.colors.GREEN)


@app.command(help="Sync local main branch with upstream (gsync)")
def gsync() -> None:
    """Fetch from 'upstream', checkout the main branch, and hard-reset to upstream/<branch>.

    Mirrors the shell `gsync` helper: determines the main branch then runs:
      git fetch upstream
      git checkout <branch>
      git reset --hard upstream/<branch>
    """
    branch = _git_main_branch()
    if not branch:
        typer.secho("❌ Could not determine upstream main branch.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"🌀 Syncing with upstream/{branch}...", fg=typer.colors.CYAN)

    try:
        _run(["git", "fetch", "upstream"])
        _run(["git", "checkout", branch])
        _run(["git", "reset", "--hard", f"upstream/{branch}"])
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ gsync failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"✅ Synced with upstream/{branch}", fg=typer.colors.GREEN)


@app.command(help="Squash a range of commits into one and apply to a target branch (gsquash)")
def gsquash(
    c1: str = typer.Argument(..., help="Oldest commit in range (ancestor)"),
    c2: str = typer.Argument(..., help="Newest commit in range (descendent)"),
    to: Optional[str] = typer.Option(None, "-t", "--to", help="Target branch to update (default: current branch)"),
    force_push: bool = typer.Option(False, "-F", "--force-push", help="Force-push target branch to its upstream after rewrite"),
    keep_temp: bool = typer.Option(False, "-k", "--keep-temp", help="Keep the temporary squash branch"),
    message: Optional[str] = typer.Option(None, "-m", "--message", help="Commit message for the squashed commit"),
) -> None:
    """Squash commits in the range c1^..c2 into one commit and apply back to a target branch.

    Mirrors the shell `gsquash` helper. Be careful: this rewrites history.
    """
    # Basic validations
    try:
        _run(["git", "rev-parse", "--git-dir"])
    except Exception:
        typer.secho("❌ Not a git repo.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # verify commits exist
    if _run(["git", "rev-parse", "--verify", c1], check=False).returncode != 0:
        typer.secho(f"❌ Commit {c1} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
    if _run(["git", "rev-parse", "--verify", c2], check=False).returncode != 0:
        typer.secho(f"❌ Commit {c2} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # ensure c1 is ancestor of c2
    if _run(["git", "merge-base", "--is-ancestor", c1, c2], check=False).returncode != 0:
        typer.secho(f"❌ {c1} is not an ancestor of {c2}.", fg=typer.colors.RED)
        raise typer.Exit(1)

    orig_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    target_branch = to or orig_branch

    # Require clean state
    if _run(["git", "diff", "--quiet"], check=False).returncode != 0 or _run(["git", "diff", "--cached", "--quiet"], check=False).returncode != 0:
        typer.secho("❌ Working tree or index not clean. Commit/stash first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    sha_head = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    sha_c2 = _run(["git", "rev-parse", c2]).stdout.strip()
    if sha_head != sha_c2:
        short = _run(["git", "rev-parse", "--short", c2]).stdout.strip()
        tmp_branch = f"squash-{short}"
        typer.secho(f"ℹ️  Creating temp branch {tmp_branch} at {c2}…", fg=typer.colors.CYAN)
        try:
            _run(["git", "switch", "-c", tmp_branch, c2])
        except Exception:
            typer.secho("❌ Failed to switch to temp branch.", fg=typer.colors.RED)
            raise typer.Exit(1)
    else:
        tmp_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()

    # Count commits
    proc = _run(["git", "rev-list", "--count", f"{c1}^..{c2}"], check=False)
    count = int((proc.stdout or "0").strip() or 0)
    if count < 1:
        typer.secho(f"⚠️ Nothing to squash in {c1}^..{c2}.", fg=typer.colors.YELLOW)
        if tmp_branch != orig_branch:
            _run(["git", "switch", orig_branch], check=False)
        raise typer.Exit(1)

    typer.secho(f"🔄 Squashing {count} commit(s) in {c1}^..{c2} into one on {tmp_branch}.", fg=typer.colors.CYAN)
    if not typer.confirm("👉 History will be rewritten. Continue?", default=False):
        typer.secho("❌ Cancelled.", fg=typer.colors.RED)
        _run(["git", "switch", orig_branch], check=False)
        raise typer.Exit(1)

    # Stage the exact range as index content, then commit once
    try:
        _run(["git", "reset", "--soft", f"{c1}^"])
    except Exception:
        typer.secho("❌ reset --soft failed.", fg=typer.colors.RED)
        _run(["git", "switch", orig_branch], check=False)
        raise typer.Exit(1)

    # Commit
    commit_msg = message or f"chore: squash {c1}..{c2}"
    try:
        _run(["git", "commit", "-m", commit_msg])
    except Exception:
        typer.secho("❌ Commit failed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    squashed_sha = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    typer.secho(f"✅ Created squashed commit: {squashed_sha}", fg=typer.colors.GREEN)

    # apply back to target branch
    if _run(["git", "show-ref", "--verify", f"refs/heads/{target_branch}"], check=False).returncode != 0:
        typer.secho(f"❌ Target branch '{target_branch}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Does target contain c2?
    if _run(["git", "merge-base", "--is-ancestor", c2, f"refs/heads/{target_branch}"], check=False).returncode == 0:
        # Target contains c2
        if _run(["git", "rev-parse", target_branch]).stdout.strip() == sha_c2:
            typer.secho(f"🔁 Moving {target_branch} to squashed commit (replacing {c2})…", fg=typer.colors.CYAN)
            _run(["git", "switch", target_branch])
            _run(["git", "reset", "--hard", squashed_sha])
        else:
            typer.secho("🪄 Rebasing commits after {c2} on top of squashed commit…", fg=typer.colors.CYAN)
            _run(["git", "switch", target_branch])
            try:
                _run(["git", "rebase", "--onto", squashed_sha, c2])
            except Exception:
                typer.secho("❌ Rebase failed.", fg=typer.colors.RED)
                raise typer.Exit(1)
    else:
        # Target doesn't contain c2 → cherry-pick the squashed change
        typer.secho(f"ℹ️  {target_branch} doesn’t contain {c2}; cherry-picking squashed commit…", fg=typer.colors.CYAN)
        _run(["git", "switch", target_branch])
        try:
            _run(["git", "cherry-pick", squashed_sha])
        except Exception:
            # If cherry-pick produces no changes, create empty commit with same message
            if _run(["git", "diff", "--cached", "--quiet"], check=False).returncode == 0 and _run(["git", "diff", "--quiet"], check=False).returncode == 0:
                typer.secho("⚠️ Cherry-pick produced no changes. Creating an empty commit to preserve history.", fg=typer.colors.YELLOW)
                # Get original message
                orig_msg = _run(["git", "log", "-1", "--pretty=%B", squashed_sha]).stdout.strip()
                _run(["git", "commit", "--allow-empty", "-m", orig_msg])
            else:
                typer.secho("❌ Cherry-pick failed with conflicts. Resolve and run: git cherry-pick --continue", fg=typer.colors.RED)
                raise typer.Exit(1)

    # Optional force-push
    if force_push:
        # Only attempt if upstream exists
        if _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False).returncode == 0:
            typer.secho(f"⤴️  Force-pushing {target_branch} to its upstream…", fg=typer.colors.CYAN)
            try:
                _run(["git", "push", "-f"])
            except Exception:
                typer.secho("❌ Push failed.", fg=typer.colors.RED)
                raise typer.Exit(1)
        else:
            typer.secho(f"⚠️ No upstream set for {target_branch}. Skipping push.", fg=typer.colors.YELLOW)

    # Cleanup temp branch
    if not keep_temp and tmp_branch != target_branch and tmp_branch != orig_branch:
        _run(["git", "branch", "-D", tmp_branch], check=False)
        typer.secho(f"🧹 Deleted temp branch {tmp_branch}.", fg=typer.colors.GREEN)

    # Return user to target (or original if same)
    cur = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if target_branch != cur:
        _run(["git", "switch", target_branch], check=False)

    typer.secho(f"🎯 Done on {target_branch}. (If previously pushed, consider: git push -f)", fg=typer.colors.GREEN)


@app.command(help="Interactive rebase with optional signoff (gggrbi)")
def gggrbi(args: List[str] = typer.Argument(None)) -> None:
    """Run `git rebase -i -r [--signoff] <args>` depending on git config or env.

    Mirrors shell helper `gggrbi`: adds --signoff if git config commit.gcommitSigned is set
    or environment variable `GCOMMIT_SIGNED` is present.
    """
    signoff_flag = []
    try:
        proc = _run(["git", "config", "--get", "commit.gcommitSigned"], check=False)
        cfg = (proc.stdout or "").strip()
        if cfg:
            signoff_flag = ["--signoff"]
    except Exception:
        pass

    if os.environ.get("GCOMMIT_SIGNED"):
        signoff_flag = ["--signoff"]

    cmd = ["git", "rebase", "-i", "-r", *signoff_flag, *args]
    try:
        _run(cmd)
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ git rebase failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command(name="gcommit", help="Commit staged changes with an optional AI-generated message")
def gcommit_cmd(message: Optional[str] = typer.Argument(None, help="Commit message; if omitted, generate via llm")) -> None:
    """Commit staged changes. If message is omitted, generate one using `llm` from staged diff.

    Prompts user to confirm the commit. Signs off if repo config `commit.gcommitSigned` or
    environment `GCOMMIT_SIGNED` is set.
    """
    # If message not provided, generate one
    msg = message
    if not msg:
        typer.echo("🧠 Generating commit message from staged changes...")
        try:
            staged = _run(["git", "diff", "--staged"]).stdout
        except Exception:
            staged = ""

        if staged.strip():
            generated = _llm(["-s", "Generate a clear, conventional commit message for these staged changes"], staged)
            msg = generated.strip()

        if not msg:
            fallback = f"chore: commit at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            typer.secho("⚠️ No commit message generated. Using fallback message:", fg=typer.colors.YELLOW)
            msg = fallback
        else:
            typer.secho("💬 AI-generated commit message:", fg=typer.colors.CYAN)

    typer.echo("----------------------------")
    typer.echo(msg)
    typer.echo("----------------------------")

    if not typer.confirm("👉 Proceed with commit?", default=False):
        typer.secho("❌ Commit cancelled.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Determine signoff
    signoff = False
    try:
        proc = _run(["git", "config", "--get", "commit.gcommitSigned"], check=False)
        if (proc.stdout or "").strip():
            signoff = True
    except Exception:
        pass
    if os.environ.get("GCOMMIT_SIGNED"):
        signoff = True

    try:
        if signoff:
            _run(["git", "commit", "-s", "-m", msg])
            typer.secho("✅ Commit (signed-off) completed!", fg=typer.colors.GREEN)
        else:
            _run(["git", "commit", "-m", msg])
            typer.secho("✅ Commit completed!", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ Commit failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command(help="Stage all changes and run gcommit (gacommit)")
def gacommit(args: List[str] = typer.Argument(None)) -> None:
    """Stage all changes (git add .) and invoke the `gcommit` workflow.
    Any arguments passed are forwarded to `gcommit`.
    """
    typer.echo("➕ Staging all changes...")
    try:
        _run(["git", "add", "."])
    except Exception:
        typer.secho("❌ Failed to stage changes.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("🚀 Running gcommit...")
    # Forward args to gcommit command handler: construct a message arg if provided
    if args:
        # join args as a single message
        _run([sys.executable, __file__, "gcommit", " ".join(args)])
    else:
        _run([sys.executable, __file__, "gcommit"])


@app.command(help="Recreate 'test' branch from a commit point (gtest)")
def gtest(commit_point: Optional[str] = typer.Argument(None, help="Commit point (default: HEAD)")) -> None:
    """Recreate a 'test' branch from the given commit point (defaults to HEAD).

    If currently on 'test', attempt to switch back to the previous branch before recreating.
    """
    cp = commit_point or "HEAD"

    try:
        current_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    except Exception:
        typer.secho("❌ Not a git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if current_branch == "test":
        typer.secho("🔄 Currently on 'test' branch. Trying to checkout previous branch...", fg=typer.colors.YELLOW)
        # Attempt to get previous branch from reflog or @{-1}
        try:
            prev = _run(["git", "rev-parse", "--abbrev-ref", "@{-1}"], check=False).stdout.strip()
            if prev:
                _run(["git", "checkout", prev])
        except Exception:
            pass

    typer.secho(f"🔥 Recreating 'test' branch from: {cp}", fg=typer.colors.CYAN)
    # Delete existing test branch if present
    _run(["git", "branch", "-D", "test"], check=False)
    try:
        _run(["git", "checkout", "-b", "test", cp])
    except Exception as exc:
        typer.secho(f"❌ Failed to create test branch: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("✅ 'test' branch recreated.", fg=typer.colors.GREEN)


@app.command(help="Copy short HEAD commit hash to clipboard (gcopyhash)")
def gcopyhash() -> None:
    """Copy the short HEAD commit hash to the macOS clipboard (pbcopy) or print it.
    """
    try:
        short_hash = _run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    except Exception:
        typer.secho("❌ Not a git repo or failed to get HEAD hash.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if sys.platform == "darwin" and _which("pbcopy"):
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(short_hash.encode())
            typer.secho(f"📋 Short commit hash copied to clipboard: {short_hash}", fg=typer.colors.GREEN)
            return
        except Exception:
            pass

    # fallback: print to stdout
    typer.echo(short_hash)


@app.command(help="Copy current branch name to clipboard (gcopybranch)")
def gcopybranch() -> None:
    """Copy the current branch name to macOS clipboard (pbcopy) or print it.
    """
    try:
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    except Exception:
        typer.secho("❌ Not a git repo or failed to get branch name.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if sys.platform == "darwin" and _which("pbcopy"):
        try:
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(branch.encode())
            typer.secho(f"🌿 Current branch name copied to clipboard: {branch}", fg=typer.colors.GREEN)
            return
        except Exception:
            pass

    typer.echo(branch)


@app.command(help="Apply a patch from the clipboard (handles fenced code blocks) (gappdiff)")
def gappdiff(dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Check whether patch would apply without applying")) -> None:
    """Read clipboard (macOS pbpaste), strip code fences and non-patch text, save to a temp file,
    and apply with `git apply --3way --index`. Use --dry-run to only check with --3way --check.
    """
    if sys.platform != "darwin":
        typer.secho("❌ gappdiff currently supports macOS (pbpaste).", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not _which("pbpaste"):
        typer.secho("❌ pbpaste not found in PATH.", fg=typer.colors.RED)
        raise typer.Exit(1)

    import tempfile

    tmpdir = Path(tempfile.mkdtemp(prefix="gappdiff."))
    patch_path = tmpdir / "clip.patch"

    # Read clipboard and filter: drop fenced blocks and everything before first 'diff --git'
    try:
        proc = _run(["pbpaste"], check=False)
        clip = proc.stdout or ""
    except Exception:
        clip = ""

    if not clip:
        typer.secho("❌ Clipboard empty or pbpaste failed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Filter similar to shell awk: skip fenced code blocks and start printing at first 'diff --git'
    lines = clip.splitlines()
    out_lines = []
    in_fence = False
    started = False
    for ln in lines:
        if ln.startswith("```") or ln.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not started and ln.startswith("diff --git "):
            started = True
        if started:
            out_lines.append(ln)

    patch_text = "\n".join(out_lines)
    # Normalize CRLF
    patch_text = patch_text.replace("\r\n", "\n").replace("\r", "\n")

    if not patch_text.strip():
        typer.secho("❌ Clipboard doesn’t contain a valid patch (no 'diff --git').", fg=typer.colors.RED)
        raise typer.Exit(1)

    patch_path.write_text(patch_text, encoding="utf-8")

    # Determine repo root
    try:
        root = _run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    except Exception:
        typer.secho("❌ Repo root not found; ensure you're inside a git repo.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("📋 Patch preview (first 20 lines):", fg=typer.colors.CYAN)
    for ln in patch_text.splitlines()[:20]:
        typer.echo(ln)

    if dry_run:
        typer.secho("🧪 Dry-run: checking with --3way…", fg=typer.colors.CYAN)
        try:
            _run(["git", "apply", "--3way", "--index", "--check", str(patch_path)], check=False)
            typer.secho("✅ Patch would apply cleanly.", fg=typer.colors.GREEN)
            raise typer.Exit(0)
        except Exception:
            typer.secho("❌ Patch check failed.", fg=typer.colors.RED)
            typer.secho(f"   Try: (cd \"{root}\" && git apply --3way --reject \"{patch_path}\")", fg=typer.colors.YELLOW)
            raise typer.Exit(1)

    typer.secho("📥 Applying with --3way…", fg=typer.colors.CYAN)
    try:
        _run(["git", "apply", "--3way", "--index", str(patch_path)])
        typer.secho("🎉 Applied. Changes are staged.", fg=typer.colors.GREEN)
        raise typer.Exit(0)
    except Exception:
        typer.secho("❌ Apply failed.", fg=typer.colors.RED)
        typer.secho(f"   Try: (cd \"{root}\" && git apply --3way --reject \"{patch_path}\")", fg=typer.colors.YELLOW)
        raise typer.Exit(1)


@app.command(help="Reverse-apply a patch saved in the clipboard to revert changes (grevdiff)")
def grevdiff() -> None:
    """Save clipboard to rev.patch, run `git apply -R rev.patch`, then remove the file.

    Mirrors the shell `grevdiff` helper. Requires macOS pbpaste.
    """
    if sys.platform != "darwin":
        typer.secho("❌ grevdiff currently supports macOS (pbpaste).", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not _which("pbpaste"):
        typer.secho("❌ pbpaste not found in PATH.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("📋 Saving clipboard contents to rev.patch...", fg=typer.colors.CYAN)
    try:
        proc = _run(["pbpaste"], check=False)
        content = proc.stdout or ""
    except Exception:
        content = ""

    if not content:
        typer.secho("❌ Failed to read clipboard or clipboard empty.", fg=typer.colors.RED)
        raise typer.Exit(1)

    rev_path = Path.cwd() / "rev.patch"
    try:
        rev_path.write_text(content, encoding="utf-8")
    except Exception:
        typer.secho("❌ Failed to write rev.patch", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("↩️ Reversing patch...", fg=typer.colors.CYAN)
    try:
        _run(["git", "apply", "-R", str(rev_path)])
    except Exception:
        typer.secho("❌ Failed to apply reverse patch", fg=typer.colors.RED)
        try:
            rev_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise typer.Exit(1)

    typer.secho("🧹 Cleaning up rev.patch...", fg=typer.colors.CYAN)
    try:
        rev_path.unlink(missing_ok=True)
    except Exception:
        pass

    typer.secho("✅ Patch reverted!", fg=typer.colors.GREEN)


@app.command(help="Stage a single file and commit with an AI-generated message (gfilecommit)")
def gfilecommit(file: str = typer.Argument(..., help="File path to stage and commit")) -> None:
    """Stage the given file, generate a commit message from the staged diff using `llm`, and commit.

    Mirrors the shell `gfilecommit` helper. Exits non-zero on failure.
    """
    p = Path(file).expanduser()
    if not p.exists() or not p.is_file():
        typer.secho(f"❌ File '{file}' does not exist.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"➕ Staging {file}...", fg=typer.colors.CYAN)
    try:
        _run(["git", "add", str(p)])
    except subprocess.CalledProcessError:
        typer.secho(f"❌ Failed to stage {file}.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("🧠 Generating commit message for {file}...", fg=typer.colors.CYAN)
    # Generate message from staged diff for the specific file
    try:
        proc = _run(["git", "diff", "--staged", str(p)], check=False)
        staged_diff = proc.stdout or ""
    except Exception:
        staged_diff = ""

    if not staged_diff.strip():
        typer.secho("⚠️ No staged diff found for file; aborting.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    msg = _llm(["-s", "Generate an appropriate commit message"], staged_diff)
    msg = (msg or "").strip()

    if not msg:
        typer.secho("⚠️ No commit message generated. Aborting commit.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    typer.secho(f"💬 Commit message: {msg}", fg=typer.colors.CYAN)
    try:
        _run(["git", "commit", "-m", msg])
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ Commit failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"✅ Committed {file} successfully!", fg=typer.colors.GREEN)


@app.command(help="Commit each changed file individually using gfilecommit (gfcommit)")
def gfcommit() -> None:
    """Iterate over git status --porcelain changed files and run gfilecommit for each.

    Mirrors the shell helper `gfcommit`. Skips and reports errors per-file.
    """
    try:
        proc = _run(["git", "status", "--porcelain"], check=False)
        out = (proc.stdout or "").strip()
    except Exception:
        typer.secho("❌ Not a git repository or git error.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not out:
        typer.secho("ℹ️ No changed files detected.", fg=typer.colors.YELLOW)
        raise typer.Exit(0)

    # Parse second column (filename) from porcelain output; handle renamed entries
    files = []
    for line in out.splitlines():
        # porcelain format: XY <file> or 'R100 from -> to'
        parts = line.split()
        if len(parts) >= 2:
            # For rename, last token is destination
            if '->' in line:
                # take last token
                fname = parts[-1]
            else:
                fname = parts[1]
            files.append(fname)

    for f in files:
        typer.echo(f"📄 Processing: {f}")
        try:
            gfilecommit(f)
        except SystemExit as se:
            # gfilecommit uses raise typer.Exit; mimic shell behavior and continue
            typer.secho(f"⚠️ Skipped {f} due to error", fg=typer.colors.YELLOW)
            continue
        except Exception:
            typer.secho(f"⚠️ Skipped {f} due to error", fg=typer.colors.YELLOW)
            continue

    typer.secho("✅ Done! All files processed.", fg=typer.colors.GREEN)


@app.command(help="Split last commit into individual file commits (gsplit)")
def gsplit() -> None:
    """Reset last commit (soft), unstage files, then run `gfcommit` to commit files individually.

    Mirrors the shell `gsplit` helper. This rewrites history: use with care.
    """
    typer.secho("🧨 Splitting last commit into individual file commits with AI-powered messages...", fg=typer.colors.CYAN)

    try:
        _run(["git", "reset", "--soft", "HEAD~1"])
    except Exception:
        typer.secho("❌ Failed to reset HEAD~1", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        _run(["git", "reset"])
    except Exception:
        typer.secho("❌ Failed to unstage files", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Delegate to gfcommit which handles per-file processing
    try:
        gfcommit()
    except Exception:
        typer.secho("⚠️ gfcommit encountered errors; some files may be skipped.", fg=typer.colors.YELLOW)

    typer.secho("✅ Done! All files have been committed individually.", fg=typer.colors.GREEN)


@app.command(help="Show added and deleted files compared to a branch (gadded)")
def gadded(branch: str = typer.Argument(..., help="Branch to compare against")) -> None:
    """Show files added and deleted compared to <branch>...HEAD and open the list in $EDITOR.

    Mirrors the existing shell helper: prints 'Added files:' then 'Deleted files:' and
    opens the result in the user's editor (falls back to vi).
    """
    try:
        proc = _run(["git", "diff", "--name-status", f"{branch}...HEAD"], check=False)
        out = proc.stdout or ""
    except Exception:
        typer.secho("❌ Not a git repo or git error.", fg=typer.colors.RED)
        raise typer.Exit(1)

    added: List[str] = []
    deleted: List[str] = []

    for ln in out.splitlines():
        parts = ln.split()
        if len(parts) >= 2:
            status = parts[0]
            path = parts[1]
            if status == "A":
                added.append(path)
            elif status == "D":
                deleted.append(path)

    lines: List[str] = []
    lines.append("📂 Added files:")
    if added:
        lines.extend(added)
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("🗑️ Deleted files:")
    if deleted:
        lines.extend(deleted)
    else:
        lines.append("(none)")

    content = "\n".join(lines)

    outpath = Path(os.path.expanduser("~/tmp")) / f"gadded-{_nowstamp()}.txt"
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(content, encoding="utf-8")

    editor = os.environ.get("EDITOR") or "vi"
    _open_in_editor(outpath, editor)


@app.command(help="Rebase a range and add Signed-off-by to each commit (gsign)")
def gsign(args: List[str] = typer.Argument(None, help="Range or upstream and optional flags")) -> None:
    """Run `git rebase --signoff [--autosquash] [--rebase-merges] <upstream> <branch>`.

    Usage examples (same as shell):
      gsign main
      gsign main..HEAD
      gsign abc123..def456 --autosquash --rebase-merges
    """
    autosquash_flag = ""
    rebase_merges_flag = ""
    arg = ""

    # normalize args list
    items = args or []
    for a in items:
        if a == "--autosquash":
            autosquash_flag = "--autosquash"
        elif a == "--rebase-merges":
            rebase_merges_flag = "--rebase-merges"
        elif a.startswith("-"):
            typer.secho(f"⚠️ Unknown option: {a}", fg=typer.colors.YELLOW)
            raise typer.Exit(2)
        else:
            if not arg:
                arg = a
            else:
                typer.secho("Usage: gsign <upstream|range> [--autosquash] [--rebase-merges]", fg=typer.colors.RED)
                raise typer.Exit(2)

    if not arg:
        typer.secho("Usage: gsign <upstream|range> [--autosquash] [--rebase-merges]", fg=typer.colors.RED)
        raise typer.Exit(2)

    # Ensure we're in a git repo
    if _run(["git", "rev-parse", "--git-dir"], check=False).returncode != 0:
        typer.secho("❌ Not a git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Refuse to start if rebase/merge in progress
    try:
        git_dir = _run(["git", "rev-parse", "--git-dir"]).stdout.strip()
    except Exception:
        git_dir = ""

    if git_dir:
        if (Path(git_dir) / "rebase-merge").exists() or (Path(git_dir) / "rebase-apply").exists():
            typer.secho("❌ A rebase is already in progress. Resolve/abort it first.", fg=typer.colors.RED)
            raise typer.Exit(1)

    # Ensure working tree/index clean
    if _run(["git", "diff", "--quiet"], check=False).returncode != 0 or _run(["git", "diff", "--cached", "--quiet"], check=False).returncode != 0:
        typer.secho("❌ Working tree or index not clean. Commit or stash changes first.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Determine upstream and branch from arg
    upstream = ""
    branch = ""
    if ".." in arg:
        upstream, branch = arg.split("..", 1)
        if not branch:
            branch = "HEAD"
    else:
        upstream = arg
        branch = "HEAD"

    try:
        cur_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    except Exception:
        cur_branch = "HEAD"

    typer.secho(f"🔧 Rebase {branch} onto {upstream} with --signoff {('and --autosquash' if autosquash_flag else '')}{(' and --rebase-merges' if rebase_merges_flag else '')}...", fg=typer.colors.CYAN)
    typer.secho(f"   Current branch: {cur_branch}", fg=typer.colors.CYAN)

    # Build command
    cmd = ["git", "rebase", "--signoff"]
    if autosquash_flag:
        cmd.append(autosquash_flag)
    if rebase_merges_flag:
        cmd.append(rebase_merges_flag)
    cmd.extend([upstream, branch])

    try:
        _run(cmd)
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ git rebase failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

@app.command(name="chezcrypt")
def chezcrypt_cmd(dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be encrypted without running chezmoi"),
                 targets: list[str] = typer.Argument(..., help="One or more target directories to encrypt")) -> None:
    """Encrypt all files in the given directories using `chezmoi add --encrypt`.

    For each provided directory, runs `find <dir> -type f -exec chezmoi add --encrypt {} \;`.
    Use --dry-run to only print the commands that would run.
    """
    if not targets:
        typer.secho("Usage: chezcrypt <relative_path_in_chezmoi_dir> [more_dirs...]", fg=typer.colors.RED)
        raise typer.Exit(1)

    for target_dir in targets:
        p = Path(target_dir).expanduser()
        if not p.exists() or not p.is_dir():
            typer.secho(f"❌ Directory not found: {target_dir}", fg=typer.colors.RED)
            continue

        typer.secho(f"🔒 Encrypting all files in {target_dir}", fg=typer.colors.CYAN)

        # Build the find + chezmoi command
        find_cmd = ["find", str(p), "-type", "f", "-print0"]

        try:
            # Gather files safely using NUL separator
            proc = _run(find_cmd, check=True)
            raw = proc.stdout
            if not raw:
                typer.secho(f"⚠️ No files found in {target_dir}", fg=typer.colors.YELLOW)
                continue

            # split by NUL; fallback to lines if necessary
            files = [x for x in raw.split("\x00") if x]

            if dry_run:
                for f in files:
                    typer.echo(f"chezmoi add --encrypt {f}")
                continue

            # Run chezmoi add --encrypt on each file
            for f in files:
                try:
                    _run(["chezmoi", "add", "--encrypt", f])
                except subprocess.CalledProcessError as exc:
                    typer.secho(f"❌ chezmoi failed for {f}: {exc}", fg=typer.colors.RED)
        except Exception as exc:
            typer.secho(f"❌ Error processing {target_dir}: {exc}", fg=typer.colors.RED)
            continue


@app.command(name="chezupdate")
def chezupdate_cmd(dry_run: bool = typer.Option(False, "--dry-run", help="Show the chezmoi update command without running it")) -> None:
    """Run `chezmoi update` to refresh local dotfiles. Use --dry-run to print the command instead of executing."""
    cmd = ["chezmoi", "update"]
    if dry_run:
        typer.echo("Would run: " + " ".join(cmd))
        raise typer.Exit(0)

    try:
        typer.secho("chezmoi update in progress ....", fg=typer.colors.CYAN)
        _run(cmd)
        typer.secho("chezmoi update done", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError:
        typer.secho("❌ chezmoi update failed.", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command(name="chezadd")
def chezadd_cmd(dry_run: bool = typer.Option(False, "--dry-run", help="Show the chezmoi add commands without running them"),
               targets: list[str] = typer.Argument(..., help="One or more target directories to add")) -> None:
    """Add all files in the given directories to chezmoi (runs `chezmoi add <file>` for each file).

    Use --dry-run to only print the commands.
    """
    if not targets:
        typer.secho("Usage: chezadd <relative_path_to_directory> [more_dirs...]", fg=typer.colors.RED)
        raise typer.Exit(1)

    for target_dir in targets:
        p = Path(target_dir).expanduser()
        if not p.exists() or not p.is_dir():
            typer.secho(f"❌ Directory not found: {target_dir}", fg=typer.colors.RED)
            continue

        typer.secho(f"➕ Adding all files in {target_dir} to chezmoi", fg=typer.colors.CYAN)

        find_cmd = ["find", str(p), "-type", "f", "-print0"]
        try:
            proc = _run(find_cmd, check=True)
            raw = proc.stdout
            if not raw:
                typer.secho(f"⚠️ No files found in {target_dir}", fg=typer.colors.YELLOW)
                continue

            files = [x for x in raw.split("\x00") if x]

            if dry_run:
                for f in files:
                    typer.echo(f"chezmoi add {f}")
                continue

            for f in files:
                try:
                    _run(["chezmoi", "add", f])
                except subprocess.CalledProcessError as exc:
                    typer.secho(f"❌ chezmoi add failed for {f}: {exc}", fg=typer.colors.RED)
        except Exception as exc:
            typer.secho(f"❌ Error processing {target_dir}: {exc}", fg=typer.colors.RED)
            continue


@app.command(name="chezsync")
def chezsync_cmd(dry_run: bool = typer.Option(False, "--dry-run", help="Show actions without executing them")) -> None:
    """Sync tracked dotfiles with chezmoi: re-add, commit, and push changes in the chezmoi repo."""
    home = Path.home()
    chez_repo = home / ".local" / "share" / "chezmoi"

    if dry_run:
        typer.echo("Would run: chezmoi re-add")
        typer.echo(f"Would cd to: {chez_repo}")
        typer.echo("Would run: git add . && git commit -m 'chezmoi: re-add' && git push (if changes present)")
        raise typer.Exit(0)

    try:
        _run(["chezmoi", "re-add"])
    except subprocess.CalledProcessError:
        typer.secho("❌ chezmoi re-add failed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not chez_repo.exists():
        typer.secho(f"❌ Failed to access chezmoi repo: {chez_repo}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # change working dir to chez_repo
    cwd = Path.cwd()
    try:
        os.chdir(chez_repo)

        # check for changes (untracked/modified or staged)
        diff_ret = subprocess.run(["git", "diff", "--quiet"]).returncode
        staged_ret = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode

        if diff_ret == 0 and staged_ret == 0:
            typer.secho("🔍 No changes to commit.", fg=typer.colors.YELLOW)
            return

        _run(["git", "add", "."])
        # simple commit with message
        msg = f"chezmoi: re-add {datetime.now().strftime('%Y-%m-%d_%H:%M')}"
        try:
            _run(["git", "commit", "-m", msg])
        except subprocess.CalledProcessError:
            # commit may fail if nothing to commit
            typer.secho("❌ git commit failed.", fg=typer.colors.RED)
            raise typer.Exit(1)

        _run(["git", "push"])
        typer.secho("✅ Dotfiles synced and pushed!", fg=typer.colors.GREEN)

    finally:
        os.chdir(cwd)


@app.command(name="cdiff")
def cdiff_cmd() -> None:
    """Prompt to paste two clipboard contents and show a unified diff in $EDITOR.

    Mirrors the shell helper which reads two pasted blocks and opens the diff in an editor.
    """
    import tempfile

    editor = os.environ.get("EDITOR") or "vi"

    # Try to use the macOS clipboard (pbpaste) when available for non-interactive use.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as f1, tempfile.NamedTemporaryFile(delete=False) as f2:
            if sys.platform == "darwin" and _which("pbpaste"):
                # Use pbpaste to populate both files sequentially (user may have split content manually)
                # First read current clipboard once into f1, then prompt for a second paste into f2.
                proc = subprocess.run(["pbpaste"], capture_output=True, text=True)
                f1.write(proc.stdout.encode())

                # interactive second paste for convenience
                with open("/dev/tty", "w") as tty_out, open("/dev/tty", "r") as tty_in:
                    tty_out.write("📋 Paste second clipboard content (press Ctrl+D when done):\n")
                    tty_out.flush()
                    while True:
                        line = tty_in.readline()
                        if not line:
                            break
                        f2.write(line.encode())
            else:
                # Fallback: interactive paste for both blocks
                with open("/dev/tty", "r") as tty_in, open("/dev/tty", "w") as tty_out:
                    tty_out.write("📋 Paste first clipboard content (press Ctrl+D when done):\n")
                    tty_out.flush()
                    while True:
                        line = tty_in.readline()
                        if not line:
                            break
                        f1.write(line.encode())

                    tty_out.write("📋 Paste second clipboard content (press Ctrl+D when done):\n")
                    tty_out.flush()
                    while True:
                        line = tty_in.readline()
                        if not line:
                            break
                        f2.write(line.encode())

            f1.flush(); f2.flush()

            # produce diff
            proc = subprocess.run(["diff", "-u", f1.name, f2.name], capture_output=True, text=True)
            diff_out = proc.stdout or ""

            # open diff in editor (via stdin)
            subprocess.run([editor, "-"], input=diff_out, text=True)

    finally:
        # Very small cleanup: try to remove temp files if they exist
        try:
            Path(f1.name).unlink(missing_ok=True)
            Path(f2.name).unlink(missing_ok=True)
        except Exception:
            pass


@app.command(name="copyfromurl")
def copyfromurl_cmd(url: str = typer.Argument(..., help="URL to fetch"), selectors: list[str] = typer.Argument(..., help="One or more selectors to pass to strip-tags -m")) -> None:
    """Fetch a URL, extract content using `strip-tags -m <selectors...>`, and copy to the macOS clipboard.

    If not on macOS or pbcopy not available, prints the extracted content to stdout.
    """
    from shutil import which

    if not url or not selectors:
        typer.secho("⚠️ Usage: copyfromurl <url> <selector1> [selector2 ...]", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"🌐 Fetching: {url}", fg=typer.colors.CYAN)
    typer.secho(f"🔍 Extracting with selectors: {' '.join(selectors)}", fg=typer.colors.CYAN)

    try:
        proc_curl = _run(["curl", "-s", url])
        strip = which("strip-tags")
        if not strip:
            typer.secho("❌ 'strip-tags' not found in PATH.", fg=typer.colors.RED)
            typer.echo(proc_curl.stdout)
            raise typer.Exit(1)

        # run strip-tags -m <selectors...>
        proc_strip = _run([strip, "-m", *selectors], input=proc_curl.stdout)
        out = proc_strip.stdout or ""

        if sys.platform == "darwin" and which("pbcopy"):
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE, text=True)
            p.communicate(out)
            typer.secho("📋 Extracted content copied to clipboard!", fg=typer.colors.GREEN)
        else:
            typer.echo(out)
    except Exception as exc:
        typer.secho(f"❌ Failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)
    # end of cdiff_cmd

if __name__ == "__main__":
    app()


@app.command(name="clean_old_zcompdump")
def clean_old_zcompdump_cmd() -> None:
    """Remove old ~/.zcompdump* files, keeping the current ~/.zcompdump.

    Mirrors the shell helper: finds files matching ~/.zcompdump* and removes any that are not
    the current ~/.zcompdump file, then prints a summary.
    """
    home = Path.home()
    current_dump = home / ".zcompdump"
    files = list(home.glob('.zcompdump*'))
    count = 0

    for f in files:
        try:
            if f != current_dump:
                f.unlink(missing_ok=True)
                count += 1
        except Exception:
            # ignore individual unlink errors
            continue

    if count > 0:
        typer.secho(f"🗑️  Cleaned up {count} old zcompdump file(s)!", fg=typer.colors.GREEN)
