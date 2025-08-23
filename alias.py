#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Optional

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
def chatmodes_copy_cmd(folder_name: str = typer.Argument(..., help="Target GitHub folder name (under ~/GitHub)") ) -> None:
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
        target.mkdir(parents=True, exist_ok=True)

        md_files = list(source.glob("*.md")) if source.exists() else []
        if not md_files:
            typer.secho(f"⚠️ No .md files found in source: {source}", fg=typer.colors.YELLOW)
            raise typer.Exit(1)

        for f in md_files:
            dest = target / f.name
            # copy content reliably
            dest.write_bytes(f.read_bytes())

        typer.secho(f"✅ Copied chatmodes to {target}", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to copy chatmodes: {exc}", fg=typer.colors.RED)
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

if __name__ == "__main__":
    app()
