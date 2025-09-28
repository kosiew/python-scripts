#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from string import Template
from typing import Optional, List, Callable, NamedTuple

import typer

ICTRIAGE_MD = "ictriage04.md"
ICASK_MD = "icask04.md"
IDEEP_MD = "icdeep02.md"
SHORT_HASH_LENGTH = 9

app = typer.Typer(
    name="alias-cli",
    help="Reusable helpers for zsh aliases (GitHub issue notes, templating, git helpers).",
    no_args_is_help=True,
)


class CommitResult(NamedTuple):
    """Result type for commit lookups.

    Attributes:
        sha: The full commit SHA as a string, or None when not found.
        message: The commit subject/message, or None when not found.
    """
    sha: Optional[str]
    message: Optional[str]

# -------------------------
# Utilities
# -------------------------

def _get_output_dir(filename: str) -> Path:
    """Get the appropriate output directory based on file prefix.
    
    Files starting with issue IDs (ic prefix files) go to ~/tmp.
    All other files go to ~/tmp/tools for better organization.
    
    Args:
        filename: The filename to check for ic prefix patterns
        
    Returns:
        Path object for the appropriate output directory
    """
    base_tmp = Path(os.path.expanduser("~/tmp"))
    
    # Check if this is an issue-related file (starts with issue ID pattern)
    # Issue files typically have pattern: {issue_id}-{prefix}-{title}_{timestamp}.md
    # They can have prefixes like: note, triage, ask, codex, comment, ictriage, icask, icodex, etc.
    if re.match(r'^\d+-(ic?[a-z]*|note|triage|ask|codex|comment)', filename):
        return base_tmp
    
    # All other files go to tools subdirectory
    tools_dir = base_tmp / "tools"
    return tools_dir

def _which(name: str) -> bool:
    return any((Path(p) / name).exists() for p in os.environ.get("PATH", "").split(os.pathsep))

def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    kw.setdefault("check", True)
    kw.setdefault("text", True)
    kw.setdefault("capture_output", True)
    return subprocess.run(cmd, **kw)

def _nowstamp() -> str:
    # include seconds for finer-grained timestamps
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def _extract_id(url: str) -> str:
    try:
        typer.secho(f"🔍 Extracting issue id from: {url}", fg=typer.colors.CYAN)
    except Exception:
        # avoid raising if typer isn't available in some contexts
        pass
    return url.rstrip("/").split("/")[-1]




def _llm(flags: list[str], prompt: str, input_text: Optional[str] = None) -> str:
    if not _which("llm"):
        return ""
    try:
        typer.secho(f"🔍 Running LLM with flags: {flags}", fg=typer.colors.CYAN)
        proc = _run(["llm", *flags, prompt], input=input_text)
        return proc.stdout or ""
    except Exception:
        return ""


def _unwrap_fenced(text: str) -> str:
    """Remove surrounding fenced code block markers (``` or ~~~) from LLM output.

    If the text begins and ends with matching fence markers, strip them and any
    leading/trailing blank lines. Otherwise return text unchanged.
    """
    if not text:
        return text
    lines = text.splitlines()
    if len(lines) >= 3:
        first = lines[0].strip()
        last = lines[-1].strip()
        if (first.startswith("```") and last.startswith("```")) or (first.startswith("~~~") and last.startswith("~~~")):
            # remove first and last lines, then trim surrounding blank lines
            inner = lines[1:-1]
            # strip leading/trailing blank lines
            while inner and not inner[0].strip():
                inner.pop(0)
            while inner and not inner[-1].strip():
                inner.pop()
            return "\n".join(inner)
    return text


def _ensure_macos() -> None:
    """Ensure we're running on macOS, exit with error message if not."""
    if sys.platform != "darwin":
        typer.secho("❌ This feature currently supports macOS only.", fg=typer.colors.RED)
        raise typer.Exit(1)


def _ensure_macos_with_pbpaste() -> None:
    """Ensure we're running on macOS with pbpaste available."""
    _ensure_macos()
    
    if not _which("pbpaste"):
        typer.secho("❌ pbpaste not found in PATH.", fg=typer.colors.RED)
        raise typer.Exit(1)


def _is_macos_with_pbcopy() -> bool:
    """Check if we're on macOS with pbcopy available."""
    return sys.platform == "darwin" and _which("pbcopy")


def _copy_to_clipboard(text: str, success_msg: str = "📋 Copied to clipboard!", error_msg: str = "⚠️ Failed to copy to clipboard.") -> bool:
    """Copy text to clipboard on macOS using pbcopy.
    
    Args:
        text: Text to copy to clipboard
        success_msg: Message to show on successful copy
        error_msg: Message to show on copy failure
        
    Returns:
        True if successfully copied, False otherwise
    """
    if not _is_macos_with_pbcopy():
        return False
    
    try:
        p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        p.communicate(text.encode())
        if success_msg:
            typer.secho(success_msg, fg=typer.colors.GREEN)
        return True
    except Exception:
        if error_msg:
            typer.secho(error_msg, fg=typer.colors.YELLOW)
        return False


def _read_from_clipboard() -> str:
    """Read text from clipboard using pbpaste.
    
    Returns:
        Clipboard content as string, or empty string if reading fails
    """
    try:
        return _run(["pbpaste"]).stdout or ""
    except Exception:
        return ""


def find_and_remove_old_files(rel_dir: str, *, days: int = 30, pattern: Optional[str] = None, recurse: bool = True) -> int:
    """Find files under Path.home()/rel_dir matching `pattern` older than `days` and remove them.

    Args:
        rel_dir: directory path relative to the user's home directory (e.g., 'tmp')
        days: delete files older than this many days
    pattern: optional regex to match filenames (applied to Path.name)
    recurse: whether to recurse into subdirectories (default True)

    Returns:
        Number of files removed (int)
    """
    
    import time
    import re

    base = Path.home() / rel_dir
    if not base.exists():
        return 0

    cutoff_time = time.time() - (days * 24 * 60 * 60)
    filename_re = re.compile(pattern) if pattern else None

    removed = 0
    iterator = base.rglob("*") if recurse else base.iterdir()
    for p in iterator:
        if p.is_file():
            try:
                if p.stat().st_mtime < cutoff_time:
                    if filename_re is not None and not filename_re.search(p.name):
                        continue
                    try:
                        p.unlink()
                    except Exception:
                        # best-effort delete; skip on failure
                        continue
                    removed += 1
            except (OSError, PermissionError):
                continue

    return removed

def _open_in_editor(path: Path, editor: Optional[str] = None, syntax_on: bool = False) -> None:
    """Open `path` in the user's editor.

    If the editor is a vim-family editor (mvim, vim, nvim, gvim) we pass a -c command to
    turn syntax on or off depending on `syntax_on`. Other editors are invoked as-is.
    """
    ed = editor or os.environ.get("EDITOR") or "mvim"
    try:
        # Detect vim-like editors and pass a -c command to control syntax highlighting
        ed_base = os.path.basename(ed)
        if ed_base in ("mvim", "vim", "nvim", "gvim"):
            syntax_cmd = "syntax on" if syntax_on else "syntax off"
            subprocess.run([ed, "-c", syntax_cmd, str(path)])
        else:
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

def _git_merge_base(branch: Optional[str] = None) -> Optional[str]:
    """Get merge-base between HEAD and the specified branch.
    
    Args:
        branch: Branch to find merge-base with. If None, uses main branch.
        
    Returns:
        Merge-base commit hash, or None if not found or on error
    """
    target_branch = branch or _git_main_branch() or "main"
    try:
        proc = _run(["git", "merge-base", "HEAD", target_branch], check=False)
        mb = (proc.stdout or "").strip()
        typer.secho(f"🧭 Detected merge-base: {mb}", fg=typer.colors.CYAN)
        return mb if mb else None
    except Exception:
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
        "- Max ~500 words total.\n"
        "- Focus on the problem, scope, impact, and any constraints.\n"
        "- No code, no headers.\n"
        "- Prefer 3–6 tight bullet points if it helps clarity."
    )
    try:
        typer.secho(f"🧭 Generating concise summary for issue: {url}", fg=typer.colors.CYAN)
    except Exception:
        pass
    out = _llm(["-u", "-ef", f"issue:{url}"], prompt)
    lines = [("- " + re.sub(r"^\s*-\s*", "", l).strip())
             for l in out.splitlines() if l.strip()]
    if not lines:
        try:
            typer.secho("⚠️ Summary could not be auto-generated by LLM; using fallback placeholder.", fg=typer.colors.YELLOW)
        except Exception:
            pass
    return "\n".join(lines).strip()

def _gen_filename(issue_id: str, title_source: str, prefix: str = "note") -> Path:
    short = _gen_short_title(title_source)
    ts = _nowstamp()
    filename = f"{issue_id}-{prefix}-{short}_{ts}.md"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir / filename

# -------------------------
# Template helpers
# -------------------------

def _read_local_template(filename: str) -> Optional[str]:
    """Read a template file located next to this source file.

    Returns the file contents if present, otherwise None.
    """
    try:
        p = Path(__file__).with_name(filename)
        if p.exists():
            return p.read_text(encoding="utf-8")
    except Exception:
        pass
    return None


def _get_first_commit(start_hash: str, pattern: str, match: bool) -> CommitResult:
    """Find the first commit in range `start_hash^..HEAD` that matches (or does not match) `pattern`.

    Scans commits from oldest to newest and returns a tuple of (commit_hash, commit_message).
    If no matching commit is found or on error, returns (None, None).

    Args:
        start_hash: The starting commit hash (the search range is `start_hash^..HEAD`).
        pattern: A regular expression to test against the commit message.
        match: If True, return the first commit whose message matches the pattern.
               If False, return the first commit whose message does NOT match the pattern.
    """
    try:
        rng = f"{start_hash}^..HEAD"
        # Use NUL-separated output to safely split subject lines
        proc = _run(["git", "log", "--reverse", "--pretty=format:%H%x00%s", rng], check=False)
        out = (proc.stdout or "").strip()
        if not out:
            return CommitResult(None, None)

        for line in out.splitlines():
            if not line:
                continue
            if "\x00" in line:
                sha, msg = line.split("\x00", 1)
            else:
                parts = line.split(None, 1)
                sha = parts[0]
                msg = parts[1] if len(parts) > 1 else ""

            try:
                matched = bool(re.search(pattern, msg))
            except re.error:
                # If the provided pattern is not a valid regex, fall back to substring check
                matched = pattern in msg

            if (match and matched) or (not match and not matched):
                return CommitResult(sha, msg)
    except Exception:
        # Best-effort: return None on any error
        return CommitResult(None, None)

    return CommitResult(None, None)


def _resolve_start_short(short_hash: str, pattern: str = "UNPICK", match: bool = False, repo: Optional[str] = None) -> str:
    """Resolve the `{START}` placeholder to a truncated commit sha.

    Finds the merge-base between HEAD and main (via `_git_merge_base`), then
    locates the first commit in `merge-base^..HEAD` whose message does NOT
    contain 'UNPICK'. Returns the truncated sha (to the length of `short_hash`
    or `SHORT_HASH_LENGTH` if `short_hash` is empty). Returns empty string on
    any failure or if no commit found.
    """
    try:
        # If a repo path is given, run git commands within that directory so
        # callers can resolve START against a different repository than the
        # current working directory.
        if repo:
            # Determine main branch name in the target repo (prefer local main/master)
            target_branch = None
            for name in ("main", "master"):
                proc = _run(["git", "show-ref", f"refs/heads/{name}"], check=False, cwd=repo)
                if proc.returncode == 0:
                    target_branch = name
                    break
            if not target_branch:
                proc = _run(["git", "rev-parse", "--abbrev-ref", "origin/HEAD"], check=False, cwd=repo)
                out = (proc.stdout or "").strip()
                if out and out != "origin/HEAD":
                    target_branch = out.split("/")[-1]
                else:
                    proc = _run(["git", "remote", "show", "origin"], check=False, cwd=repo)
                    m = re.search(r"HEAD branch: (\S+)", proc.stdout or "")
                    if m:
                        target_branch = m.group(1)

            target_branch = target_branch or "main"
            proc = _run(["git", "merge-base", "HEAD", target_branch], check=False, cwd=repo)
            mb = (proc.stdout or "").strip()
        else:
            mb = _git_merge_base()

        if not mb:
            return ""

        # Get the full ordered list of commits in the range mb^..HEAD
        rng = f"{mb}^..HEAD"
        if repo:
            proc = _run(["git", "log", "--reverse", "--pretty=format:%H%x00%s", rng], check=False, cwd=repo)
        else:
            proc = _run(["git", "log", "--reverse", "--pretty=format:%H%x00%s", rng], check=False)
        out = (proc.stdout or "").strip()
        if not out:
            return ""

        commits: List[tuple[str, str]] = []
        for line in out.splitlines():
            if not line:
                continue
            if "\x00" in line:
                sha, msg = line.split("\x00", 1)
            else:
                parts = line.split(None, 1)
                sha = parts[0]
                msg = parts[1] if len(parts) > 1 else ""
            commits.append((sha, msg))

        # Helper to test match (regex with fallback)
        def _matches(msg: str) -> bool:
            try:
                return bool(re.search(pattern, msg))
            except re.error:
                return pattern in msg

        if match:
            # If caller asked to match, return the first matching commit
            for sha, msg in commits:
                if _matches(msg):
                    start_sha = sha
                    trunc_len = len(short_hash) if short_hash else SHORT_HASH_LENGTH
                    return start_sha[:trunc_len]
            return ""

        # match == False: prefer the first non-matching commit AFTER the last match
        last_match_idx = -1
        for i, (_sha, msg) in enumerate(commits):
            if _matches(msg):
                last_match_idx = i

        # If there was at least one match, pick the commit immediately after it
        if last_match_idx != -1:
            after_idx = last_match_idx + 1
            if after_idx < len(commits):
                start_sha = commits[after_idx][0]
                trunc_len = len(short_hash) if short_hash else SHORT_HASH_LENGTH
                return start_sha[:trunc_len]
            # No commit after the last match
            return ""

        # No matches found: return the first non-matching commit (oldest)
        for sha, msg in commits:
            if not _matches(msg):
                trunc_len = len(short_hash) if short_hash else SHORT_HASH_LENGTH
                return sha[:trunc_len]

        return ""
    except Exception:
        return ""


def _render_and_write(issue_id: str, url: str, prefix: str, tpl_text: str, summary_text: str, ts: str, no_open: bool, editor: Optional[str]) -> Path:
    """Substitute variables into tpl_text, write to generated filename, and open editor unless suppressed.

    Returns the output Path.
    """
    content = Template(tpl_text).safe_substitute(summary=summary_text, url=url, id=issue_id, timestamp=ts)

    outpath = _gen_filename(issue_id, f"issue:{url}", prefix)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(content, encoding="utf-8")
    typer.secho(f"✅ Wrote: {outpath}", fg=typer.colors.GREEN)

    if not no_open:
        _open_in_editor(outpath, editor)
    return outpath


def _get_git_branch() -> str:
    """Return the current git branch name or 'unknown' if it cannot be determined."""
    branch = "unknown"
    try:
        proc = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False)
        b = (proc.stdout or "").strip()
        if b:
            branch = b
    except Exception:
        branch = "unknown"
    return re.sub(r"[^A-Za-z0-9\-_]", "-", branch)


def _build_git_diff_cmd_and_msg(items: List[str], exclude_agents: bool = True) -> tuple[list[str], str]:
    """Return a git diff command list and a short info message for the given items.

    Rules mirror the previous `gdiff`/`greview_branch` logic:
      - 0 items: prefer merge-base..HEAD (fallback to default branch)
      - 1 item: diff working tree vs that ref (exclude AGENTS.md)
      - 2 items: diff a vs b (exclude AGENTS.md)
      - >=3 items: first is commit, rest are files; exclude AGENTS.md unless explicitly requested
    """
    def_branch = _git_main_branch() or "main"

    if len(items) == 1:
        msg = f"🔍 Comparing working tree with: {items[0]}"
        if exclude_agents:
            msg += " (excluding AGENTS.md)"
            cmd = ["git", "diff", items[0], "--", ".", ":(exclude)AGENTS.md"]
        else:
            cmd = ["git", "diff", items[0], "--", "."]
    elif len(items) == 2:
        msg = f"🔍 Comparing: {items[0]} ↔ {items[1]}"
        if exclude_agents:
            msg += " (excluding AGENTS.md)"
            cmd = ["git", "diff", items[0], items[1], "--", ".", ":(exclude)AGENTS.md"]
        else:
            cmd = ["git", "diff", items[0], items[1], "--", "."]
    elif len(items) >= 3:
        commit = items[0]
        files = items[1:]
        if "AGENTS.md" not in files and exclude_agents:
            msg = f"🔍 Comparing: {commit} with specific files: {' '.join(files)} (excluding AGENTS.md)"
            cmd = ["git", "diff", commit, "--", *files, ":(exclude)AGENTS.md"]
        else:
            msg = f"🔍 Comparing: {commit} with specific files: {' '.join(files)}"
            cmd = ["git", "diff", commit, "--", *files]
    else:
        # no args: prefer merge-base..HEAD
        mb = _git_merge_base(def_branch)

        if mb:
            msg = f"🔍 No arguments provided. Comparing merge-base {mb}..HEAD"
            if exclude_agents:
                msg += " (excluding AGENTS.md)"
                cmd = ["git", "diff", f"{mb}..HEAD", "--", ".", ":(exclude)AGENTS.md"]
            else:
                cmd = ["git", "diff", f"{mb}..HEAD", "--", "."]
        else:
            msg = f"🔍 No arguments provided. Comparing against default branch: {def_branch}"
            if exclude_agents:
                msg += " (excluding AGENTS.md)"
                cmd = ["git", "diff", def_branch, "--", ".", ":(exclude)AGENTS.md"]
            else:
                cmd = ["git", "diff", def_branch, "--", "."]

    return cmd, msg


def _git_diff_text(items: List[str]) -> str:
    """Run git diff for given items and return stdout text (empty on error).

    This wraps _build_git_diff_cmd_and_msg and _run.
    """
    cmd, _ = _build_git_diff_cmd_and_msg(items)
    try:
        proc = _run(cmd, check=False)
        return proc.stdout or ""
    except Exception:
        return ""

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
    _ensure_macos_with_pbpaste()
    if not _which("llm"):
        typer.secho("❌ 'llm' not found in PATH.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # derive short title from clipboard
    short = "note"
    try:
        clip = _read_from_clipboard()
        gen = _llm(["-s",
                    "Generate a short, kebab-case filename-style title for this GitHub issue. Avoid punctuation. No more than 8 words."],
                   input_text=clip)
        cand = (gen.splitlines() or [""])[0]
        cleaned = re.sub(r"[^A-Za-z0-9\-]", "", cand)
        short = cleaned or "note"
    except Exception:
        pass

    filename = f"{prefix}-{short}_{_nowstamp()}.md"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / filename

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


@app.command(help="Print all commit messages between two commits (inclusive of range), excluding merge commits")
def commits_between(
    commit1: Optional[str] = typer.Argument(None, help="First commit ref (hash, branch, tag). If not provided, uses merge-base with main branch."),
    commit2: Optional[str] = typer.Argument(None, help="Second commit ref (hash, branch, tag). Defaults to HEAD if not provided."),
):
    """Print commit messages between commit1 and commit2, excluding merge commits.

    If commit2 is not specified, defaults to HEAD.
    If neither commit1 nor commit2 are specified, obtains the commit range 
    using the same logic as gdiff (without arguments) - from merge-base with main branch to HEAD.

    Tries the range `commit1..commit2` first. If that yields no results (or errors),
    it will try the reverse `commit2..commit1` so the command is forgiving about
    the order of arguments.

    Merge commits are automatically excluded from the output.
    """
    def _run_log(rng: str) -> List[str]:
        try:
            proc = _run(["git", "log", "--no-merges", "--pretty=format:%s", rng], check=False)
            out = (proc.stdout or "").strip()
            return [l for l in out.splitlines() if l.strip()]
        except Exception:
            return []

    # Handle optional parameters
    if commit1 is None and commit2 is None:
        # Use same logic as gdiff without arguments - get range from merge-base to HEAD
        def_branch = _git_main_branch() or "main"
        mb = _git_merge_base(def_branch)
        if mb:
            commit1 = mb
            commit2 = "HEAD"
            typer.secho(f"🔍 Using merge-base range: {commit1}..{commit2}", fg=typer.colors.CYAN)
        else:
            commit1 = def_branch
            commit2 = "HEAD"
            typer.secho(f"🔍 No merge-base found. Using: {commit1}..{commit2}", fg=typer.colors.CYAN)
    elif commit2 is None:
        # Default commit2 to HEAD if not specified
        commit2 = "HEAD"
        typer.secho(f"🔍 Using range: {commit1}..{commit2}", fg=typer.colors.CYAN)

    # try commit1..commit2 first
    rng = f"{commit1}..{commit2}"
    messages = _run_log(rng)
    if not messages:
        # try reverse range
        rng = f"{commit2}..{commit1}"
        messages = _run_log(rng)

    if not messages:
        typer.secho("No commits found between the supplied refs or not a git repository.", fg=typer.colors.YELLOW)
        raise typer.Exit(0)

    for msg in messages:
        typer.echo(msg)
    # Return all messages as a single joined string (for programmatic use)
    all_messages = "\n".join(messages)
    if not _copy_to_clipboard(all_messages, "📋 Commit messages copied to clipboard!"):
        typer.echo("📋 Commit messages:\n" + all_messages)
        typer.echo("❌ Failed to copy to clipboard\n")


@app.command(help=f"Print short commit hashes ({SHORT_HASH_LENGTH} chars) between two commits (inclusive of range), excluding merge commits")
def hashes_between(
    commit1: Optional[str] = typer.Argument(None, help="First commit ref (hash, branch, tag). If not provided, uses merge-base with main branch."),
    commit2: Optional[str] = typer.Argument(None, help="Second commit ref (hash, branch, tag). Defaults to HEAD if not provided."),
):
    """Print short commit hashes between commit1 and commit2, excluding merge commits.

    If commit2 is not specified, defaults to HEAD.
    If neither commit1 nor commit2 are specified, obtains the commit range 
    using the same logic as gdiff (without arguments) - from merge-base with main branch to HEAD.

    Tries the range `commit1..commit2` first. If that yields no results (or errors),
    it will try the reverse `commit2..commit1` so the command is forgiving about
    the order of arguments.

    Merge commits are automatically excluded from the output.
    Returns short hashes (first {SHORT_HASH_LENGTH} characters) for better readability.
    """
    def _run_log_hashes(rng: str) -> List[str]:
        try:
            proc = _run(["git", "log", "--no-merges", "--pretty=format:%H", rng], check=False)
            out = (proc.stdout or "").strip()
            # Truncate each hash to SHORT_HASH_LENGTH characters
            return [l[:SHORT_HASH_LENGTH] for l in out.splitlines() if l.strip()]
        except Exception:
            return []

    # Handle optional parameters
    if commit1 is None and commit2 is None:
        # Use same logic as gdiff without arguments - get range from merge-base to HEAD
        def_branch = _git_main_branch() or "main"
        mb = _git_merge_base(def_branch)
        if mb:
            commit1 = mb
            commit2 = "HEAD"
            typer.secho(f"🔍 Using merge-base range: {commit1}..{commit2}", fg=typer.colors.CYAN)
        else:
            commit1 = def_branch
            commit2 = "HEAD"
            typer.secho(f"🔍 No merge-base found. Using: {commit1}..{commit2}", fg=typer.colors.CYAN)
    elif commit2 is None:
        # Default commit2 to HEAD if not specified
        commit2 = "HEAD"
        typer.secho(f"🔍 Using range: {commit1}..{commit2}", fg=typer.colors.CYAN)

    # try commit1..commit2 first
    rng = f"{commit1}..{commit2}"
    hashes = _run_log_hashes(rng)
    if not hashes:
        # try reverse range
        rng = f"{commit2}..{commit1}"
        hashes = _run_log_hashes(rng)

    if not hashes:
        typer.secho("No commits found between the supplied refs or not a git repository.", fg=typer.colors.YELLOW)
        raise typer.Exit(0)

    for hash_val in hashes:
        typer.echo(hash_val)
    # Return all hashes as a single joined string (for programmatic use)
    all_hashes = "\n".join(hashes)
    if not _copy_to_clipboard(all_hashes, "📋 Commit hashes copied to clipboard!"):
        typer.echo("📋 Commit hashes:\n" + all_hashes)
        typer.echo("❌ Failed to copy to clipboard\n")


@app.command(help="Squash commits between two refs (inclusive) into a single commit with a summarized message")
def squash_commits(
    commit1: str = typer.Argument(..., help="Older commit ref (start of range)") ,
    commit2: str = typer.Argument(..., help="Newer commit ref (end of range; must be HEAD for automatic squash)"),
    backup: bool = typer.Option(True, "--no-backup/--backup", help="Create a backup branch before rewriting history"),
    preview: bool = typer.Option(False, "--preview", help="Show planned summary and git commands without executing"),
) -> None:
    """Squash commits from commit1..commit2 (inclusive) into a single commit.

    For safety the command only performs the automated soft-reset + commit when
    `commit2` is HEAD. If `commit2` is not HEAD this helper will print guidance
    for an interactive rebase instead.
    """
    # helper to collect messages
    def _collect_messages(rng: str) -> List[str]:
        try:
            proc = _run(["git", "log", "--pretty=format:%s", rng], check=False)
            out = (proc.stdout or "").strip()
            return [l for l in out.splitlines() if l.strip()]
        except Exception:
            return []

    # verify git repo
    try:
        _run(["git", "rev-parse", "--git-dir"], check=True)
    except Exception:
        typer.secho("❌ Not a git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Determine if commit2 equals HEAD
    try:
        proc = _run(["git", "rev-parse", "--verify", "HEAD"], check=False)
        head_sha = (proc.stdout or "").strip()
        proc2 = _run(["git", "rev-parse", "--verify", commit2], check=False)
        commit2_sha = (proc2.stdout or "").strip()
    except Exception:
        typer.secho("❌ Failed to resolve commits. Ensure refs exist.", fg=typer.colors.RED)
        raise typer.Exit(1)

    messages = _collect_messages(f"{commit1}..{commit2}") or _collect_messages(f"{commit2}..{commit1}")
    typer.secho("📋 Found commit messages:\n", fg=typer.colors.CYAN)
    for msg in messages:
        typer.echo(f" - {msg}")
    if not messages:
        typer.secho("No commits found between the supplied refs.", fg=typer.colors.YELLOW)
        raise typer.Exit(0)

    # Build a summarized message using LLM if available, else join subjects
    summary = ", ".join(messages)

    typer.secho("📋 Planned squash summary:\n", fg=typer.colors.CYAN)
    typer.echo(summary)

    if preview:
        typer.secho("🔎 Preview mode: no git operations will be run.", fg=typer.colors.YELLOW)
        typer.echo("Planned commands:")
        if backup:
            typer.echo(f"  git branch backup/squash-{_nowstamp()}")
        # If commit2 is HEAD, we can soft-reset to commit1^ and commit
        if commit2_sha == head_sha:
            typer.echo(f"  git reset --soft {commit1}^")
            typer.echo("  git commit -m '<summary from above>'")
        else:
            typer.echo("  # commit2 is not HEAD; consider: git rebase -i <commit1>^ and squash manually")
        raise typer.Exit(0)

    # Create backup branch
    if backup:
        bk = f"backup-squash-{_nowstamp()}"
        try:
            _run(["git", "branch", bk])
            typer.secho(f"✅ Backup branch created: {bk}", fg=typer.colors.GREEN)
        except Exception:
            typer.secho("⚠️ Failed to create backup branch; aborting to avoid data loss.", fg=typer.colors.RED)
            raise typer.Exit(1)

    # If commit2 is HEAD, perform soft-reset and commit
    if commit2_sha == head_sha:
        try:
            # Reset soft to just before commit1 so all changes are staged
            _run(["git", "reset", "--soft", f"{commit1}^"])
            # Commit with the summarized message
            _run(["git", "commit", "-m", summary])
            typer.secho("✅ Commits squashed into a single commit.", fg=typer.colors.GREEN)
        except Exception as exc:
            typer.secho(f"❌ Failed to perform squash operation: {exc}", fg=typer.colors.RED)
            typer.secho("Your backup branch preserves the previous history.", fg=typer.colors.YELLOW)
            raise typer.Exit(1)
    else:
        typer.secho("⚠️ Automatic squash only supported when the end ref is HEAD.", fg=typer.colors.YELLOW)
        typer.secho("Suggested manual steps:", fg=typer.colors.CYAN)
        typer.echo(f"  1. git rebase -i {commit1}^   # mark commits to squash")
        typer.echo("  2. edit commit message to the summary printed above")
        typer.echo("A backup branch has been created to preserve current history.")
        raise typer.Exit(0)

@app.command(help="Show git diff in various modes and copy output to clipboard (gdiff) - excludes AGENTS.md")
def gdiff(args: List[str] = typer.Argument(None, help="Arguments forwarded to git diff")) -> None:
    """Mimic the shell `gdiff` helper with these modes:
      - gdiff <ref>                # compare working tree with <ref>
      - gdiff <a> <b>              # compare a ↔ b
      - gdiff <commit> <files...>  # compare commit with specific files
      - gdiff                      # compare with repo main branch

    AGENTS.md is automatically excluded from all diffs.
    The diff is written to ~/tmp/tools/gdiff-<ts>.patch, copied to clipboard on macOS
    (pbcopy), and opened in $EDITOR (falls back to vi).
    """
    items = args or []

    # Determine default branch if needed
    def_branch = _git_main_branch() or "main"

    # Build git diff command depending on args - always exclude AGENTS.md
    if len(items) == 1:
        typer.secho(f"🔍 Comparing working tree with: {items[0]} (excluding AGENTS.md)", fg=typer.colors.CYAN)
        cmd = ["git", "diff", items[0], "--", ".", ":(exclude)AGENTS.md"]
    elif len(items) == 2:
        typer.secho(f"🔍 Comparing: {items[0]} ↔ {items[1]} (excluding AGENTS.md)", fg=typer.colors.CYAN)
        cmd = ["git", "diff", items[0], items[1], "--", ".", ":(exclude)AGENTS.md"]
    elif len(items) >= 3:
        commit = items[0]
        files = items[1:]
        # For specific files, only exclude AGENTS.md if it's not explicitly requested
        if "AGENTS.md" not in files:
            typer.secho(f"🔍 Comparing: {commit} with specific files: {' '.join(files)} (excluding AGENTS.md)", fg=typer.colors.CYAN)
            cmd = ["git", "diff", commit, "--", *files, ":(exclude)AGENTS.md"]
        else:
            typer.secho(f"🔍 Comparing: {commit} with specific files: {' '.join(files)}", fg=typer.colors.CYAN)
            cmd = ["git", "diff", commit, "--", *files]
    else:
        # Prefer showing changes since the common ancestor with the main branch
        mb = _git_merge_base(def_branch)
        if mb:
            # use the merge-base..HEAD range which is what the user requested
            typer.secho(f"🔍 No arguments provided. Comparing merge-base {mb}..HEAD (excluding AGENTS.md)", fg=typer.colors.CYAN)
            cmd = ["git", "diff", f"{mb}..HEAD", "--", ".", ":(exclude)AGENTS.md"]
        else:
            typer.secho(f"🔍 No merge-base found. Falling back to comparing against default branch: {def_branch} (excluding AGENTS.md)", fg=typer.colors.CYAN)
            cmd = ["git", "diff", def_branch, "--", ".", ":(exclude)AGENTS.md"]

    # Run git diff and capture output
    try:
        proc = _run(cmd, check=False)
        diff_text = proc.stdout or ""
    except Exception:
        typer.secho("❌ git diff failed or not a repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Ensure tmp directory exists and write file; include current branch in filename
    branch_clean = _get_git_branch()
    filename = f"gdiff-{branch_clean}-{_nowstamp()}.patch"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)

    outpath = outdir / filename
    outpath.write_text(diff_text, encoding="utf-8")

    # Copy to clipboard on macOS if pbcopy present
    if not _copy_to_clipboard(diff_text, "📋 Diff output copied to clipboard!"):
        typer.echo("📋 Diff output saved to: " + str(outpath))

    _open_in_editor(outpath, syntax_on=True)


@app.command(help="Show git diff --stat for commits or working tree (gs)")
def gs(args: List[str] = typer.Argument(None, help="Arguments forwarded: [commit_early] [commit_late]")) -> None:
    """Show `git diff --stat` in three modes:
      - gs <commit>           # working tree vs commit
      - gs <a> <b>            # diff stat between a and b
      - gs                    # diff stat vs repo main
    """
    items = args or []

    # Use the same diff-building logic but ensure --stat is included
    if len(items) >= 1:
        # Build command normally and insert --stat after 'git' 'diff'
        cmd, msg = _build_git_diff_cmd_and_msg(items, exclude_agents=False)
        if cmd[:2] == ["git", "diff"]:
            cmd = ["git", "diff", "--stat"] + cmd[2:]
        typer.secho(msg, fg=typer.colors.CYAN)
    else:
        # no args: prefer merge-base..HEAD via helper and add --stat
        cmd, msg = _build_git_diff_cmd_and_msg(items, exclude_agents=False)
        if cmd[:2] == ["git", "diff"]:
            cmd = ["git", "diff", "--stat"] + cmd[2:]
        typer.secho(msg, fg=typer.colors.CYAN)

    try:
        proc = _run(cmd, check=False)
        output = proc.stdout or ""
    except Exception:
        typer.secho("❌ git diff --stat failed or not a repository.", fg=typer.colors.RED)
        raise typer.Exit(1)

    branch_clean = _get_git_branch()
    filename = f"gs-{branch_clean}-{_nowstamp()}.txt"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / filename
    outpath.write_text(output, encoding="utf-8")

    _open_in_editor(outpath, syntax_on=True)


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

    typer.secho(f"🚀 Starting 'gnb' for new branch: {branch}", fg=typer.colors.CYAN)

    # If branch exists locally, delete it
    try:
        exists = _run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], check=False).returncode == 0
    except Exception:
        exists = False

    if exists:
        typer.secho(f"🗑️ Detected existing local branch '{branch}' — deleting...", fg=typer.colors.YELLOW)
        try:
            _run(["git", "branch", "-D", branch])
            typer.secho(f"✅ Deleted local branch '{branch}'", fg=typer.colors.GREEN)
        except Exception:
            typer.secho(f"❌ Failed to delete branch '{branch}'. Aborting.", fg=typer.colors.RED)
            raise typer.Exit(1)

    # Create and switch to new branch
    typer.secho(f"🌱 Creating and switching to branch '{branch}'...", fg=typer.colors.CYAN)
    try:
        _run(["git", "checkout", "-b", branch])
        typer.secho(f"✅ Now on branch '{branch}'", fg=typer.colors.GREEN)
    except Exception:
        typer.secho(f"❌ Failed to create branch '{branch}'. Aborting.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Checkout AGENTS.md from dev, add and commit
    typer.secho("📥 Attempting to checkout AGENTS.md from 'dev' (if present)...", fg=typer.colors.CYAN)
    try:
        _run(["git", "commit", "--allow-empty", "-m", "UNPICK START"])
        typer.secho("📄 UNPICK START", fg=typer.colors.GREEN)
        _run(["git", "checkout", "dev", "--", "AGENTS.md"]) 
        typer.secho("📄 AGENTS.md checked out from 'dev'", fg=typer.colors.GREEN)
        try:
            # Add empty commit with "UNPICK START" message before the AGENTS.md commit
            _run(["git", "add", "AGENTS.md"])
            _run(["git", "commit", "-m", "UNPICK added AGENTS.md"])
            typer.secho("✅ AGENTS.md added and committed.", fg=typer.colors.GREEN)
        except subprocess.CalledProcessError:
            typer.secho("⚠️ No changes to commit for AGENTS.md (or commit failed).", fg=typer.colors.YELLOW)
    except subprocess.CalledProcessError:
        typer.secho("⚠️ AGENTS.md not present in 'dev' or checkout failed; skipping.", fg=typer.colors.YELLOW)
    except Exception:
        # non-fatal: some repos may not have AGENTS.md
        typer.secho("⚠️ Unexpected error while handling AGENTS.md; continuing.", fg=typer.colors.YELLOW)

    typer.secho(f"🎉 Finished 'gnb' — branch '{branch}' is ready.", fg=typer.colors.GREEN)


@app.command(help="Run repository-specific rust clippy script and open output (rust_clippy)")
def rust_clippy() -> None:
    """Run `ci/scripts/rust_clippy.sh` if present and open the captured output in $EDITOR.

    Mirrors the shell helper which runs the CI script and pipes output to `vi -`.
    """
    script = Path("ci/scripts/rust_clippy.sh")
    if script.exists() and os.access(script, os.X_OK):
        typer.secho("👋 running datafusion rust_clippy script...", fg=typer.colors.CYAN)
        try:
            typer.echo("🔁 Executing script, this may take a while...")
            proc = _run([str(script)], check=False)
            output = proc.stdout or ""
            typer.secho("💾 Capturing script output...", fg=typer.colors.CYAN)
            filename = f"rust_clippy-{_nowstamp()}.txt"
            outdir = _get_output_dir(filename)
            outdir.mkdir(parents=True, exist_ok=True)
            outpath = outdir / filename
            outpath.write_text(output, encoding="utf-8")
            typer.secho(f"✅ Wrote output to: {outpath}", fg=typer.colors.GREEN)
            typer.echo("🖥️ Opening output in editor...")
            _open_in_editor(outpath)
            typer.secho("✅ rust_clippy completed.", fg=typer.colors.GREEN)
        except Exception as exc:
            typer.secho(f"❌ Failed running rust_clippy script: {exc}", fg=typer.colors.RED)
            raise typer.Exit(1)
    else:
        typer.secho("⚠️ ci/scripts/rust_clippy.sh not found or not executable. Skipping.", fg=typer.colors.YELLOW)


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
    branch_clean = _get_git_branch()
    filename = f"ccheck-{branch_clean}-{_nowstamp()}.txt"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / filename
    outpath.write_text(content, encoding="utf-8")
    typer.secho(f"✅ Wrote cargo check output to: {outpath}", fg=typer.colors.GREEN)
    typer.echo("🖥️ Opening output in editor...")
    _open_in_editor(outpath)
    typer.secho("✅ ccheck finished.", fg=typer.colors.GREEN)


@app.command(help="Run cargo run with optional head/tail and verbosity (crun)", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def crun(
    ctx: typer.Context,
    args: Optional[List[str]] = typer.Argument(None, help="Arguments passed to cargo run; use '--' to separate"),
    head: Optional[int] = typer.Option(None, "-h", help="Show only first N lines"),
    tail: Optional[int] = typer.Option(None, "-t", help="Show only last N lines"),
    verbose: bool = typer.Option(False, "-v", help="Run in verbose mode"),
) -> None:
    """Run `cargo run` (quiet by default), pass arguments, and show output (optionally head/tail).

    Use -v to enable non-quiet mode. Use args after '--' in shell to forward to cargo.
    """
    # Combine explicit positional args with any extra args from the context so flags
    # like --example are forwarded to cargo run.
    items: List[str] = list(args or [])
    extra = list(getattr(ctx, "args", []) or [])
    cmd = ["cargo", "run"]
    if not verbose:
        cmd.append("-q")
    cmd.extend(items + extra)

    typer.secho(f"🔧 Assembled command: {' '.join(cmd)}", fg=typer.colors.CYAN)
    try:
        typer.echo("🔁 Running cargo run...")
        proc = _run(cmd, check=False)
        out = proc.stdout or ""
        typer.secho("💾 Captured cargo output.", fg=typer.colors.CYAN)
    except Exception as exc:
        typer.secho(f"❌ Failed to run cargo run (is cargo installed?): {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    lines = out.splitlines()
    if head is not None and head > 0:
        lines = lines[:head]
    if tail is not None and tail > 0:
        lines = lines[-tail:]

    content = "\n".join(lines)
    branch_clean = _get_git_branch()
    filename = f"crun-{branch_clean}-{_nowstamp()}.txt"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / filename
    outpath.write_text(content, encoding="utf-8")
    typer.secho(f"✅ Wrote cargo output to: {outpath}", fg=typer.colors.GREEN)
    typer.echo("🖥️ Opening output in editor...")
    _open_in_editor(outpath)
    typer.secho("✅ crun finished.", fg=typer.colors.GREEN)


@app.command(help="Run cargo test with optional head/tail and verbosity (ctest)", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def ctest(
    ctx: typer.Context,
    head: Optional[int] = typer.Option(None, "-h", help="Show only first N lines"),
    tail: Optional[int] = typer.Option(None, "-t", help="Show only last N lines"),
    verbose: bool = typer.Option(False, "-v", help="Run in verbose mode"),
    args: Optional[List[str]] = typer.Argument(None, help="Arguments passed to cargo test; use '--' to separate"),
) -> None:
    """Run `cargo test` (quiet by default), pass arguments, and show output (optionally head/tail).

    Mirrors the shell helper: -v disables -q, -h/-t show head/tail lines. Non-verbose opens output in $EDITOR via a tmp file.
    """
    items = list(args or [])
    extra = list(getattr(ctx, "args", []) or [])

    cmd = ["cargo", "test"]
    if not verbose:
        cmd.append("-q")
    cmd.extend(items + extra)

    typer.secho(f"🔧 Assembled command: {' '.join(cmd)}", fg=typer.colors.CYAN)
    try:
        typer.echo("🔁 Running cargo test...")
        # Capture both stdout and stderr so the tmp file includes all output (equivalent to shell `2>&1`).
        proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.stdout or ""
        typer.secho("💾 Captured cargo test output (stdout+stderr).", fg=typer.colors.CYAN)
    except Exception as exc:
        typer.secho(f"❌ Failed to run cargo test (is cargo installed?): {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    lines = out.splitlines()
    if head is not None and head > 0:
        lines = lines[:head]
    if tail is not None and tail > 0:
        lines = lines[-tail:]

    content = "\n".join(lines)

    if verbose:
        # print to stdout for interactive consumption
        typer.echo(content)
        return

    branch_clean = _get_git_branch()
    args_string = "_".join(re.sub(r"[^A-Za-z0-9]+", "-", arg.replace(" ", "_")) for arg in (items + extra))[:40]
    filename = f"ctest-{branch_clean}_{args_string}_{_nowstamp()}.txt"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / filename
    outpath.write_text(content, encoding="utf-8")
    typer.secho(f"✅ Wrote cargo test output to: {outpath}", fg=typer.colors.GREEN)
    typer.echo("🖥️ Opening output in editor...")
    _open_in_editor(outpath)
    typer.secho("✅ ctest finished.", fg=typer.colors.GREEN)


@app.command(help="Run make with target, parse go failures, and open in vi (vmake)")
def vmake(
    target: str = typer.Argument("test-unit", help="Make target to run (default: test-unit)")
) -> None:
    """Run `make <target>`, pipe output through parser.py parse-go-failures, and open in vi.
    
    Equivalent to: make <target> 2>&1 | python parser.py parse-go-failures | vi -
    """
    parser_path = "/Users/kosiew/GitHub/python-scripts/parser.py"
    
    typer.secho(f"🔧 Running make {target} and parsing failures...", fg=typer.colors.CYAN)
    
    try:
        # Run make command and capture output
        make_proc = subprocess.run(
            ["make", target], 
            check=False, 
            text=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT
        )
        make_output = make_proc.stdout or ""
        
        typer.secho("📝 Parsing go failures...", fg=typer.colors.CYAN)
        
        # Run parser on the make output
        parser_proc = subprocess.run(
            ["python", parser_path, "parse-go-failures"],
            input=make_output,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        parsed_output = parser_proc.stdout or ""
        
        if parser_proc.returncode != 0:
            typer.secho(f"⚠️ Parser had issues: {parser_proc.stderr}", fg=typer.colors.YELLOW)
        
        typer.secho("🖥️ Opening parsed output in vi...", fg=typer.colors.GREEN)

        # Open the parsed output in vi using stdin
        vi_proc = subprocess.run(
            ["mvim", "-"],
            input=parsed_output,
            text=True,
            check=False
        )

        if vi_proc.returncode == 0:
            typer.secho("✅ vmake finished.", fg=typer.colors.GREEN)
        else:
            typer.secho("⚠️ vi exited with non-zero status.", fg=typer.colors.YELLOW)

    except FileNotFoundError as exc:
        typer.secho(f"❌ Command not found: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)
    except Exception as exc:
        typer.secho(f"❌ Failed to run vmake: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)


@app.command(help="Run arbitrary shell command, capture stdout+stderr and open in editor (rpipe)", context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
def rpipe(
    ctx: typer.Context,
    cmd: List[str] = typer.Argument(..., help="Command and args to run; pass as separate tokens or quoted string"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open the output file with"),
    verbose: bool = typer.Option(False, "-v", help="If set, print output to stdout instead of opening editor")
) -> None:
    """Run an arbitrary shell command, capture stdout+stderr (2>&1), and open the result in the editor.

    Example: rpipe maturin develop --uv  -> runs `maturin develop --uv 2>&1` and opens in $EDITOR via tmp file
    Supports passing extra args via the CLI context (mirrors ctest behavior).
    """
    # Build command: combine explicit cmd tokens and any extra args captured by Typer's ctx
    extra = list(getattr(ctx, "args", []) or [])
    full_cmd = list(cmd) + extra

    typer.secho(f"🔧 Running command: {' '.join(full_cmd)}", fg=typer.colors.CYAN)
    try:
        proc = subprocess.run(full_cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.stdout or ""
        typer.secho("💾 Captured command output (stdout+stderr).", fg=typer.colors.CYAN)
    except Exception as exc:
        typer.secho(f"❌ Failed to run command: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    if verbose:
        typer.echo(out)
        return

    # Write output to a tools tmp file and open in editor
    branch_clean = _get_git_branch() or "local"
    # Use the first command token as a filename prefix (sanitized)
    cmd_prefix = (full_cmd[0] if full_cmd else "rpipe").replace('/', '_')
    # sanitize non-alphanumeric to hyphens and truncate
    cmd_prefix = re.sub(r"[^A-Za-z0-9]+", "-", cmd_prefix).strip("-")[:40] or "rpipe"
    filename = f"{cmd_prefix}-{branch_clean}-{_nowstamp()}.txt"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / filename
    outpath.write_text(out, encoding="utf-8")

    typer.secho(f"✅ Wrote command output to: {outpath}", fg=typer.colors.GREEN)
    typer.echo("🖥️ Opening output in editor...")
    _open_in_editor(outpath, editor=editor)
    typer.secho(f"✅ {cmd_prefix} finished.", fg=typer.colors.GREEN)


@app.command(name="encode_and_copy")
def encode_and_copy_cmd(
    text: str = typer.Argument(..., help="Text to base64-encode and copy to clipboard")
):
    """Base64-encode the given text and copy to the macOS clipboard (pbcopy)."""
    import base64

    encoded = base64.b64encode(text.encode()).decode()
    if not _copy_to_clipboard(encoded, "Encoded message copied to clipboard.", 
                             "Failed to copy to clipboard; printing encoded text:"):
        # Non-macOS fallback or copy failure: print encoded value
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

        typer.secho(f"🔁 Preparing to copy chatmodes to: {target}", fg=typer.colors.CYAN)
        target.mkdir(parents=True, exist_ok=True)

        md_files = list(source.glob("*.md")) if source.exists() else []
        if not md_files:
            typer.secho(f"⚠️ No .md files found in source: {source}", fg=typer.colors.YELLOW)
            raise typer.Exit(1)

        typer.secho(f"📦 Found {len(md_files)} .md file(s) to copy.", fg=typer.colors.CYAN)
        for f in md_files:
            dest = target / f.name
            try:
                if preserve:
                    shutil.copy2(str(f), str(dest))
                else:
                    # previous behavior: copy content
                    dest.write_bytes(f.read_bytes())
                typer.echo(f"  ✅ {f.name} -> {dest}")
            except Exception as exc:
                typer.secho(f"  ⚠️ Failed to copy {f.name}: {exc}", fg=typer.colors.YELLOW)

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

    # Delete local branch
    typer.secho(f"🗑️ Deleting local branch: {branch}", fg=typer.colors.CYAN)
    try:
        _run(["git", "branch", "-d", branch])
        typer.secho(f"✅ Local branch '{branch}' deleted.", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ Failed to delete local branch '{branch}': {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Delete remote branch
    typer.secho(f"📤 Deleting remote branch: origin/{branch}", fg=typer.colors.CYAN)
    try:
        _run(["git", "push", "origin", "--delete", branch])
        typer.secho(f"✅ Remote branch 'origin/{branch}' deleted.", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ Failed to delete remote branch 'origin/{branch}': {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho(f"🎉 Deleted branch '{branch}' locally and on origin.", fg=typer.colors.GREEN)


@app.command(help="Show files changed compared to a branch (gdn)")
def gdn(branch: Optional[str] = typer.Argument(None, help="Branch to compare against (defaults to repo main)")) -> None:
    """Run `git diff --name-only <branch>` and open the list in $EDITOR (falls back to vi).

    If branch is omitted, attempt to detect the repo's main branch.
    """
    # If a branch was provided, ask the helper to compare, else prefer merge-base..HEAD
    items: List[str] = []
    if branch:
        items = [branch]
    # Build command but ensure AGENTS.md is NOT excluded
    cmd, msg = _build_git_diff_cmd_and_msg(items, exclude_agents=False)
    typer.secho(msg, fg=typer.colors.CYAN)

    try:
        typer.echo("🔁 Running git diff --name-only...")
        # Replace 'git diff' with 'git diff --name-only' while preserving range/paths
        if cmd[:2] == ["git", "diff"]:
            cmd2 = ["git", "diff", "--name-only"] + cmd[2:]
        else:
            cmd2 = cmd
        proc = _run(cmd2)
        output = proc.stdout or ""
        typer.secho("💾 Captured git diff output.", fg=typer.colors.CYAN)
    except Exception as exc:
        typer.secho(f"❌ git diff failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Write to a temporary file and open in editor
    current_branch = _get_git_branch()
    # b_display: use provided branch if present else detect main branch name
    b_display = branch if branch else (_git_main_branch() or "main")
    filename = f"gdn-{b_display}-{current_branch}-{_nowstamp()}.txt"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / filename
    outpath.write_text(output, encoding="utf-8")
    typer.secho(f"✅ Wrote git diff list to: {outpath}", fg=typer.colors.GREEN)
    typer.echo("🖥️ Opening output in editor...")
    _open_in_editor(outpath)


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


@app.command(help="Review branch workflow: diff vs main (excluding AGENTS.md), revert, and force push")
def greview_branch() -> None:
    """Execute the review branch workflow:
    
    1. Get diff vs main (excluding AGENTS.md) and copy to clipboard
    2. Run grevdiff to reverse apply the diff
    3. Commit with message "revert branch UNPICK"
    4. Revert the last commit
    5. Force push with lease
    6. Copy commit hash to clipboard
    
    AGENTS.md is retained but excluded from the diff to avoid including it in the review.
    """
    # Step 1: Get diff vs main (excluding AGENTS.md) and copy to clipboard
    typer.secho("🔍 Getting diff vs main (excluding AGENTS.md)...", fg=typer.colors.CYAN)
    try:
        items: List[str] = []
        cmd, msg = _build_git_diff_cmd_and_msg(items)
        typer.secho("🔍 Getting diff for review...", fg=typer.colors.CYAN)
        typer.secho(msg, fg=typer.colors.CYAN)
        diff_text = _git_diff_text(items)
        
        # Copy to clipboard on macOS
        if not _copy_to_clipboard(diff_text, "📋 Diff (excluding AGENTS.md) copied to clipboard"):
            typer.secho("📋 Diff generated (clipboard copy not available)", fg=typer.colors.GREEN)
            
    except Exception as exc:
        typer.secho(f"❌ Failed to get diff: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 2: Run grevdiff
    typer.secho("↩️ Running grevdiff...", fg=typer.colors.CYAN)
    try:
        grevdiff()
        typer.secho("✅ grevdiff completed", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ grevdiff failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 3: Commit revert with gacommit
    typer.secho("📝 Committing revert...", fg=typer.colors.CYAN)
    try:
        gacommit(["UNPICK changes to review"])
        typer.secho("✅ Committed revert", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to commit revert: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 4: Git revert HEAD
    typer.secho("🔄 Reverting HEAD commit...", fg=typer.colors.CYAN)
    try:
        _run(["git", "revert", "--no-edit", "HEAD"])
        typer.secho("✅ Reverted HEAD commit", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to revert: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 5: Force push with lease
    typer.secho("🚀 Force pushing with lease...", fg=typer.colors.CYAN)
    try:
        _run(["git", "push", "--force-with-lease"])
        typer.secho("✅ Force pushed with lease", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to force push: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 6: Copy commit hash
    typer.secho("📋 Copying commit hash...", fg=typer.colors.CYAN)
    try:
        gcopyhash()
        typer.secho("✅ Commit hash copied", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to copy hash: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("🎉 Review branch workflow completed successfully! Codex Ask, use ggreviewpr snippet", fg=typer.colors.GREEN, bold=True)


@app.command(help="Review PR workflow: wait for confirmation, apply diff, commit, push, and copy hash")
def greview_pr() -> None:
    """Execute the review PR workflow:
    
    1. Pause and wait for confirmation that PR diff has been copied
    2. Run gappdiff to apply the patch from clipboard
    3. Commit with message "CHANGES to review" using gacommit
    4. Push changes to remote
    5. Copy commit hash to clipboard
    """
    # Step 1: Wait for confirmation that PR diff has been copied
    typer.secho("📋 Please copy the PR diff to your clipboard first.", fg=typer.colors.YELLOW, bold=True)
    typer.secho("💡 Tip: You can use the browser to copy the diff from GitHub PR page.", fg=typer.colors.CYAN)
    
    if not typer.confirm("👉 Have you copied the PR diff to clipboard?", default=False):
        typer.secho("❌ Cancelled: Please copy the PR diff first.", fg=typer.colors.RED)
        raise typer.Exit(0)

    # Step 2: Run gappdiff
    typer.secho("📥 Applying patch from clipboard...", fg=typer.colors.CYAN)
    try:
        gappdiff(dry_run=False)
        typer.secho("✅ Patch applied successfully", fg=typer.colors.GREEN)
    except typer.Exit as exc:
        # gappdiff uses typer.Exit to signal success/failure
        if exc.exit_code == 0:
            typer.secho("✅ Patch applied successfully", fg=typer.colors.GREEN)
        else:
            typer.secho(f"❌ Failed to apply patch (exit code {exc.exit_code})", fg=typer.colors.RED)
            raise typer.Exit(1)
    except Exception as exc:
        typer.secho(f"❌ Failed to apply patch: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Check if there are actually changes to commit
    typer.secho("🔍 Checking for changes to commit...", fg=typer.colors.CYAN)
    try:
        staged_changes = _run(["git", "diff", "--cached", "--name-only"]).stdout.strip()
        if not staged_changes:
            typer.secho("⚠️ No changes to commit. The patch may have already been applied or resulted in no net changes.", fg=typer.colors.YELLOW)
            typer.secho("✅ Workflow completed (no commit needed).", fg=typer.colors.GREEN)
            return
        else:
            typer.secho(f"✅ Found changes to commit: {len(staged_changes.splitlines())} file(s)", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to check staged changes: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 3: Commit with gacommit
    typer.secho("📝 Committing changes...", fg=typer.colors.CYAN)
    try:
        gacommit(["CHANGES to review"])
        typer.secho("✅ Changes committed", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to commit changes: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 4: Git push
    typer.secho("🚀 Pushing changes to remote...", fg=typer.colors.CYAN)
    try:
        _run(["git", "push"])
        typer.secho("✅ Changes pushed to remote", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to push changes: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Step 5: Copy commit hash
    typer.secho("📋 Copying commit hash...", fg=typer.colors.CYAN)
    try:
        gcopyhash()
        typer.secho("✅ Commit hash copied", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to copy hash: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.secho("🎉 Review PR workflow completed successfully!. Now go to Codex Ask, use ggreviewpr snippet", fg=typer.colors.GREEN, bold=True)


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
    typer.secho(f"🚀 Starting gsquash: {c1}..{c2} -> {to or '(current)'}", fg=typer.colors.CYAN)
    # Basic validations
    try:
        _run(["git", "rev-parse", "--git-dir"])
    except Exception:
        typer.secho("❌ Not a git repo.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("🔍 Verifying commits exist...")
    # verify commits exist
    if _run(["git", "rev-parse", "--verify", c1], check=False).returncode != 0:
        typer.secho(f"❌ Commit {c1} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)
    if _run(["git", "rev-parse", "--verify", c2], check=False).returncode != 0:
        typer.secho(f"❌ Commit {c2} not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("🔗 Checking ancestor relationship...")
    # ensure c1 is ancestor of c2
    if _run(["git", "merge-base", "--is-ancestor", c1, c2], check=False).returncode != 0:
        typer.secho(f"❌ {c1} is not an ancestor of {c2}.", fg=typer.colors.RED)
        raise typer.Exit(1)

    orig_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    target_branch = to or orig_branch

    typer.echo("🧹 Ensuring working tree and index are clean...")
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
            typer.secho(f"✅ Created temp branch {tmp_branch}", fg=typer.colors.GREEN)
        except Exception:
            typer.secho("❌ Failed to switch to temp branch.", fg=typer.colors.RED)
            raise typer.Exit(1)
    else:
        tmp_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        typer.secho(f"ℹ️  Using current branch as temp: {tmp_branch}", fg=typer.colors.CYAN)

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
    typer.echo("⚙️ Staging range into index (reset --soft)...")
    try:
        _run(["git", "reset", "--soft", f"{c1}^"])
        typer.secho("✅ Range staged.", fg=typer.colors.GREEN)
    except Exception:
        typer.secho("❌ reset --soft failed.", fg=typer.colors.RED)
        _run(["git", "switch", orig_branch], check=False)
        raise typer.Exit(1)

    # Commit
    commit_msg = message or f"chore: squash {c1}..{c2}"
    typer.echo("📝 Creating squashed commit...")
    try:
        _run(["git", "commit", "-m", commit_msg])
        typer.secho("✅ Squashed commit created.", fg=typer.colors.GREEN)
    except Exception:
        typer.secho("❌ Commit failed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    squashed_sha = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    typer.secho(f"✅ Created squashed commit: {squashed_sha}", fg=typer.colors.GREEN)

    # apply back to target branch
    typer.echo(f"🔁 Applying squashed commit to target branch: {target_branch}")
    if _run(["git", "show-ref", "--verify", f"refs/heads/{target_branch}"], check=False).returncode != 0:
        typer.secho(f"❌ Target branch '{target_branch}' not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Does target contain c2?
    if _run(["git", "merge-base", "--is-ancestor", c2, f"refs/heads/{target_branch}"], check=False).returncode == 0:
        # Target contains c2
        _cur_target_sha = _run(["git", "rev-parse", target_branch]).stdout.strip()
        if _cur_target_sha == sha_c2:
            typer.secho(f"🔁 Moving {target_branch} to squashed commit (replacing {c2})…", fg=typer.colors.CYAN)
            _run(["git", "switch", target_branch])
            _run(["git", "reset", "--hard", squashed_sha])
            typer.secho(f"✅ {target_branch} reset to {squashed_sha}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"🪄 Rebasing commits after {c2} on top of squashed commit…", fg=typer.colors.CYAN)
            _run(["git", "switch", target_branch])
            try:
                _run(["git", "rebase", "--onto", squashed_sha, c2])
                typer.secho("✅ Rebase onto squashed commit succeeded.", fg=typer.colors.GREEN)
            except Exception:
                typer.secho("❌ Rebase failed.", fg=typer.colors.RED)
                raise typer.Exit(1)
    else:
        # Target doesn't contain c2 → cherry-pick the squashed change
        typer.secho(f"ℹ️  {target_branch} doesn’t contain {c2}; cherry-picking squashed commit…", fg=typer.colors.CYAN)
        _run(["git", "switch", target_branch])
        try:
            _run(["git", "cherry-pick", squashed_sha])
            typer.secho("✅ Cherry-pick succeeded.", fg=typer.colors.GREEN)
        except Exception:
            # If cherry-pick produces no changes, create empty commit with same message
            if _run(["git", "diff", "--cached", "--quiet"], check=False).returncode == 0 and _run(["git", "diff", "--quiet"], check=False).returncode == 0:
                typer.secho("⚠️ Cherry-pick produced no changes. Creating an empty commit to preserve history.", fg=typer.colors.YELLOW)
                # Get original message
                orig_msg = _run(["git", "log", "-1", "--pretty=%B", squashed_sha]).stdout.strip()
                _run(["git", "commit", "--allow-empty", "-m", orig_msg])
                typer.secho("✅ Empty commit created.", fg=typer.colors.GREEN)
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
                typer.secho("✅ Force-push completed.", fg=typer.colors.GREEN)
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
    # Handle Typer ArgumentInfo objects that can be passed when called programmatically
    if hasattr(message, '__class__') and 'ArgumentInfo' in str(type(message)):
        msg = None  # Treat ArgumentInfo as no message provided
    else:
        msg = message
    if not msg:
        typer.echo("🧠 Generating commit message from staged changes...")
        try:
            staged = _run(["git", "diff", "--staged"]).stdout
        except Exception:
            staged = ""

        if staged.strip():
            generated = _llm(["-s", "Generate a clear, conventional commit message for these staged changes"], staged)
            msg = _unwrap_fenced(generated).strip()

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
        gcommit_cmd(" ".join(args))
    else:
        gcommit_cmd()


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
    typer.secho("🔍 Retrieving short HEAD commit hash...", fg=typer.colors.CYAN)
    try:
        short_hash = _run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
        typer.secho(f"✅ Found hash: {short_hash}", fg=typer.colors.GREEN)
    except Exception:
        typer.secho("❌ Not a git repo or failed to get HEAD hash.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not _copy_to_clipboard(short_hash, f"✅ Short commit hash copied to clipboard: {short_hash}",
                             "⚠️ Failed to copy to clipboard; falling back to printing."):
        # fallback: print to stdout
        typer.echo(short_hash)


@app.command(help="Load ~/tmp/reviewpr-<pr-number>.md, replace {hash} with short HEAD hash, and copy to clipboard")
def reviewpr(pr_number: str = typer.Argument(..., help="PR number, e.g. 43197")) -> None:
    """Load reviewpr file, substitute {hash}, and copy to clipboard (or print)."""
    # Use the shared helper to load and fill template; do not call gcopyhash here.
    filled = _load_and_fill_template("reviewpr", pr_number, copy_hash=False)

    # Try to copy to clipboard using shared helper; fallback to printing
    if _copy_text_to_clipboard(filled, label="reviewpr content", pr_number=pr_number):
        return
    typer.echo(filled)


def _get_template_from_clipboard_or_stdin(prefix: str, pr_number: str) -> str:
    """Prompt the user to copy a template to the clipboard and read it.

    Returns the template text read from the macOS clipboard (pbpaste) or from stdin.
    Raises typer.Exit(1) if the user cancels or no content is found.
    """
    typer.secho(f"📋 Please copy the '{prefix}' template for PR {pr_number} to your clipboard.", fg=typer.colors.YELLOW, bold=True)
    typer.secho("💡 Tip: copy the template from your browser or template file and then confirm below.", fg=typer.colors.CYAN)
    if not typer.confirm("👉 Have you copied the template to clipboard?", default=False):
        typer.secho("❌ Cancelled: Template not provided.", fg=typer.colors.RED)
        raise typer.Exit(1)

    text: str = ""
    # Try to read from macOS clipboard (pbpaste). Fallback to reading stdin.
    if _is_macos_with_pbcopy():  # pbcopy implies pbpaste availability
        text = _read_from_clipboard()
        if text:
            # attempt to persist the clipboard content so subsequent runs find the file
            try:
                p = Path.home() / "tmp" / f"{prefix}-{pr_number}.md"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text, encoding="utf-8")
                typer.secho(f"✅ Saved template to: {p}", fg=typer.colors.GREEN)
            except Exception:
                typer.secho("⚠️ Failed to save template to file; continuing with clipboard content.", fg=typer.colors.YELLOW)
        else:
            typer.secho("⚠️ Failed to read from clipboard; please paste the template below and finish with Ctrl-D.", fg=typer.colors.YELLOW)
            try:
                typer.echo("Paste template now, then press Ctrl-D:")
                text = sys.stdin.read()
            except Exception:
                text = ""
    else:
        # Non-macOS fallback: prompt user to paste template into stdin
        typer.secho("⚠️ Clipboard read not supported on this platform; please paste the template and press Ctrl-D.", fg=typer.colors.YELLOW)
        try:
            typer.echo("Paste template now, then press Ctrl-D:")
            text = sys.stdin.read()
        except Exception:
            text = ""

    if not text:
        typer.secho("❌ No template content found in clipboard/stdin.", fg=typer.colors.RED)
        raise typer.Exit(1)

    return text


def _load_and_fill_template(prefix: str, pr_number: str, copy_hash: bool = False) -> str:
    """Helper to load ~/tmp/<prefix>-<pr_number>.md, replace {hash} with the
    short HEAD commit hash, optionally copy the short hash to the clipboard
    (via gcopyhash()), and return the filled text.

    prefix: 'reviewpr' or 'prwhy' etc.
    """
    p = Path.home() / "tmp" / f"{prefix}-{pr_number}.md"

    text: Optional[str] = None
    if not p.exists():
        # Prompt the user to copy the template and read it from clipboard or stdin
        text = _get_template_from_clipboard_or_stdin(prefix, pr_number)
    else:
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as exc:
            typer.secho(f"❌ Failed to read file {p}: {exc}", fg=typer.colors.RED)
            raise typer.Exit(1)

    try:
        short_hash = _run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    except Exception:
        short_hash = ""

    filled = text.replace("{hash}", short_hash)

    # If template contains {START}, attempt to resolve it to the first commit
    # after the merge-base which does NOT contain the string 'UNPICK' in
    # its commit message. Truncate the returned sha to the same length as
    # `short_hash` (fall back to SHORT_HASH_LENGTH when short_hash is empty).
    if "{START}" in text:
        # Use extracted helper to resolve the truncated start sha (defaults preserve previous behavior)
        start_short = _resolve_start_short(short_hash, "UNPICK", False)
        if start_short:
            filled = filled.replace("{START}", start_short)

    if copy_hash:
        # Try to invoke the local function to copy the short hash, fall back to pbcopy
        try:
            gcopyhash()
        except Exception:
            _copy_to_clipboard(short_hash or "", success_msg="", error_msg="")

    return filled


def _copy_text_to_clipboard(text: str, label: str = "content", pr_number: Optional[str] = None) -> bool:
    """Copy text to macOS clipboard using pbcopy. Returns True if copied.

    label is used for user-friendly messages (e.g., 'prwhy content').
    pr_number, if provided, is shown in the success message.
    """
    if pr_number:
        success_msg = f"📋 {label} content copied to clipboard for PR {pr_number}"
    else:
        success_msg = f"📋 {label} content copied to clipboard"
    
    error_msg = "⚠️ Failed to copy to clipboard; printing output instead."
    
    return _copy_to_clipboard(text, success_msg, error_msg)


@app.command(help="Load ~/tmp/prwhy-<pr-number>.md, replace {hash} with short HEAD hash, call gcopyhash(), and copy to clipboard")
def prwhy(pr_number: str = typer.Argument(..., help="PR number, e.g. 43197")) -> None:
    """Load prwhy file, substitute {hash}, call gcopyhash to copy the short hash,
    and copy the filled content to clipboard (or print)."""
    filled = _load_and_fill_template("prwhy", pr_number, copy_hash=True)

    # Try to copy to clipboard using shared helper; fallback to printing
    if _copy_text_to_clipboard(filled, label="prwhy content", pr_number=pr_number):
        return
    typer.echo(filled)


@app.command(help="Load ~/tmp/prrespond-<pr-number>.md, replace {hash} with short HEAD hash, call gcopyhash(), and copy to clipboard")
def prrespond(pr_number: str = typer.Argument(..., help="PR number, e.g. 43197")) -> None:
    """Load prrespond file, substitute {hash}, call gcopyhash to copy the short hash,
    and copy the filled content to clipboard (or print).
    """
    filled = _load_and_fill_template("prrespond", pr_number, copy_hash=True)

    # Try to copy to clipboard using shared helper; fallback to printing
    if _copy_text_to_clipboard(filled, label="prrespond content", pr_number=pr_number):
        return
    typer.echo(filled)


@app.command(help="Copy current branch name to clipboard (gcopybranch)")
def gcopybranch() -> None:
    """Copy the current branch name to macOS clipboard (pbcopy) or print it.
    """
    typer.secho("🔍 Retrieving current branch name...", fg=typer.colors.CYAN)
    try:
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        typer.secho(f"✅ Current branch: {branch}", fg=typer.colors.GREEN)
    except Exception:
        typer.secho("❌ Not a git repo or failed to get branch name.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not _copy_to_clipboard(branch, f"✅ Current branch name copied to clipboard: {branch}",
                             "⚠️ Failed to copy to clipboard; falling back to printing."):
        typer.echo(branch)


def _git_require_repo_or_exit() -> None:
    try:
        _run(["git", "rev-parse", "--git-dir"])  
    except Exception:
        typer.secho("❌ Not a git repository.", fg=typer.colors.RED)
        raise typer.Exit(1)


def _git_commit_count() -> int:
    try:
        return int((_run(["git", "rev-list", "--count", "HEAD"], check=False).stdout or "0").strip())
    except Exception:
        return 0


def _ensure_clean_index_or_exit() -> None:
    if _run(["git", "diff", "--quiet"], check=False).returncode != 0 or _run(["git", "diff", "--cached", "--quiet"], check=False).returncode != 0:
        typer.secho("❌ Working tree or index not clean. Commit or stash changes first.", fg=typer.colors.RED)
        raise typer.Exit(1)


def _get_head_and_prev() -> tuple[str, str]:
    sha_head = _run(["git", "rev-parse", "HEAD"]).stdout.strip()
    sha_prev = _run(["git", "rev-parse", "HEAD~1"]).stdout.strip()
    return sha_head, sha_prev


def _get_commit_message(sha: str) -> str:
    return _run(["git", "log", "-1", "--pretty=%B", sha]).stdout or ""


def _create_branch(branch: str) -> None:
    _run(["git", "branch", branch])


def _checkout_new_branch_at(branch: str, ref: str) -> None:
    _run(["git", "checkout", "-b", branch, ref])


def _cherry_pick_no_commit(sha: str) -> None:
    _run(["git", "cherry-pick", "--no-commit", sha])


def _commit_with_message(message: str) -> None:
    _run(["git", "commit", "-m", message])


def _abort_cherry_pick_safe() -> None:
    _run(["git", "cherry-pick", "--abort"], check=False)


def _reset_branch_hard(branch: str, target: str) -> None:
    _run(["git", "checkout", branch])
    _run(["git", "reset", "--hard", target])


def _delete_branch(branch: str) -> None:
    _run(["git", "branch", "-D", branch], check=False)


@app.command(help="Swap messages of the last two commits (swapmsgs)")
def swapmsgs(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show planned actions without changing history"),
    keep_backup: bool = typer.Option(False, "--keep-backup/--no-keep-backup", help="Keep a backup branch at HEAD before rewriting"),
) -> None:
    """Orchestrate swapping the messages of the last two commits using small helpers."""
    _git_require_repo_or_exit()

    if _git_commit_count() < 2:
        typer.secho("❌ Need at least two commits to swap messages.", fg=typer.colors.RED)
        raise typer.Exit(1)

    _ensure_clean_index_or_exit()

    sha_head, sha_prev = _get_head_and_prev()
    msg_head = _get_commit_message(sha_head)
    msg_prev = _get_commit_message(sha_prev)

    cur_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    backup_branch = f"swapmsgs-backup-{_nowstamp()}"
    tmp_branch = f"swapmsgs-tmp-{_nowstamp()}"

    typer.secho(f"🔍 Preparing to swap messages on branch: {cur_branch}", fg=typer.colors.CYAN)
    typer.secho(f"   commits: {sha_prev} (older), {sha_head} (HEAD)")

    if dry_run:
        typer.echo("Planned steps:")
        typer.echo(f"  - Create backup branch: {backup_branch} at HEAD")
        typer.echo(f"  - Create temporary branch {tmp_branch} at HEAD~2")
        typer.echo(f"  - Cherry-pick --no-commit {sha_prev} and commit with message from {sha_head}")
        typer.echo(f"  - Cherry-pick --no-commit {sha_head} and commit with message from {sha_prev}")
        typer.echo(f"  - Reset {cur_branch} to {tmp_branch} and delete {tmp_branch}")
        raise typer.Exit(0)

    try:
        _create_branch(backup_branch)
        typer.secho(f"💾 Backup branch created: {backup_branch}", fg=typer.colors.GREEN)
    except Exception as exc:
        typer.secho(f"❌ Failed to create backup branch: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        _checkout_new_branch_at(tmp_branch, "HEAD~2")
        _cherry_pick_no_commit(sha_prev)
        _commit_with_message(msg_head)
        _cherry_pick_no_commit(sha_head)
        _commit_with_message(msg_prev)
    except Exception as exc:
        typer.secho(f"❌ Failed while creating swapped commits: {exc}", fg=typer.colors.RED)
        _abort_cherry_pick_safe()
        try:
            _run(["git", "checkout", cur_branch], check=False)
        except Exception:
            pass
        typer.secho(f"👉 Your original branch is preserved on backup: {backup_branch}", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    try:
        _reset_branch_hard(cur_branch, tmp_branch)
    except Exception as exc:
        typer.secho(f"❌ Failed to update branch {cur_branch}: {exc}", fg=typer.colors.RED)
        typer.secho(f"👉 Your original branch is preserved on backup: {backup_branch}", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    _delete_branch(tmp_branch)

    if keep_backup:
        typer.secho(f"✅ Swapped messages. Backup branch left at: {backup_branch}", fg=typer.colors.GREEN)
    else:
        _delete_branch(backup_branch)
        typer.secho("✅ Swapped messages. Backup branch removed.", fg=typer.colors.GREEN)



def _handle_apply_failure(proc: subprocess.CompletedProcess, patch_path: Path) -> None:
    """Handle patch application failure with detailed diagnostics and suggestions.
    
    Args:
        proc: The completed git apply process
        patch_path: Path to the patch file
        
    Raises:
        typer.Exit: Always exits with code 1 to indicate failure
    """
    # Get repository root for manual apply suggestion
    try:
        root = _run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    except Exception:
        root = "."
    
    # Nothing staged — report failure and show stderr
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    typer.secho("❌ Apply failed.", fg=typer.colors.RED)
    typer.secho(f"   Return code: {proc.returncode}", fg=typer.colors.RED)
    
    if stderr:
        typer.secho("   Git stderr:", fg=typer.colors.RED)
        for line in stderr.splitlines():
            typer.secho(f"   {line}", fg=typer.colors.RED)
    
    if stdout:
        typer.secho("   Git stdout:", fg=typer.colors.RED)
        for line in stdout.splitlines():
            typer.secho(f"   {line}", fg=typer.colors.RED)
    
    # Show current repo state for debugging
    try:
        status_proc = _run(["git", "status", "--porcelain"], check=False)
        if status_proc.stdout and status_proc.stdout.strip():
            typer.secho("   Current repo status:", fg=typer.colors.CYAN)
            for line in status_proc.stdout.strip().splitlines()[:10]:  # Limit to 10 lines
                typer.secho(f"   {line}", fg=typer.colors.CYAN)
            if len(status_proc.stdout.strip().splitlines()) > 10:
                typer.secho("   ... (truncated)", fg=typer.colors.CYAN)
        else:
            typer.secho("   Repository is clean (no uncommitted changes)", fg=typer.colors.GREEN)
    except Exception:
        pass  # Don't fail if we can't get status
            
    # Check for common issues and provide helpful suggestions
    if "does not exist in index" in stderr:
        typer.secho("   💡 This might be a new file. Try: git add . && git apply --3way", fg=typer.colors.CYAN)
    elif "patch does not apply" in stderr:
        typer.secho("   💡 Patch conflicts detected. Check file contents and resolve manually.", fg=typer.colors.CYAN)
    elif "already exists in working directory" in stderr:
        typer.secho("   💡 File already exists. Check if changes were already applied.", fg=typer.colors.CYAN)
        
    typer.secho(f"   Patch file: {patch_path}", fg=typer.colors.YELLOW)
    typer.secho(f"   Try manual: (cd \"{root}\" && git apply --3way --reject \"{patch_path}\")", fg=typer.colors.YELLOW)
    typer.secho(f"   📁 Patch saved to: {patch_path}", fg=typer.colors.CYAN)
    raise typer.Exit(1)


def _apply_patch(patch_path: Path) -> None:
    """Apply the patch and handle success/failure scenarios.
    
    Args:
        patch_path: Path to the patch file
        
    Raises:
        typer.Exit: With code 0 if patch applies successfully, 1 if it fails
    """
    typer.secho("", fg=typer.colors.WHITE)  # Add spacing
    typer.secho("📥 Applying with --3way…", fg=typer.colors.CYAN)
    proc = _run(["git", "apply", "--3way", "--index", "--verbose", str(patch_path)], check=False)
    
    # git apply may exit non-zero but still stage changes when using --3way;
    # check for staged changes as the real indicator of success.
    if proc.returncode == 0:
        typer.secho("🎉 Applied. Changes are staged.", fg=typer.colors.GREEN)
        # Show what was applied
        stdout = (proc.stdout or "").strip()
        if stdout:
            typer.secho("   Applied changes:", fg=typer.colors.GREEN)
            for line in stdout.splitlines()[:5]:  # Show first 5 lines
                typer.secho(f"   {line}", fg=typer.colors.GREEN)
            if len(stdout.splitlines()) > 5:
                typer.secho("   ... (use 'git status' to see all changes)", fg=typer.colors.GREEN)
        typer.secho(f"   📁 Patch saved to: {patch_path}", fg=typer.colors.CYAN)
        raise typer.Exit(0)
    else:
        # However, sometimes git apply exits non-zero but has applied hunks and
        # written .git/rebase-apply or similar; inspect staged state to be sure.
        # Check if index has changes (i.e., git diff --cached is non-empty)
        cached = _run(["git", "diff", "--cached", "--name-only"], check=False)
        if (cached.stdout or "").strip():
            typer.secho("⚠️ git apply exited non-zero but changes are staged.", fg=typer.colors.YELLOW)
            typer.secho("🎉 Applied. Changes are staged.", fg=typer.colors.GREEN)
            typer.secho(f"   📁 Patch saved to: {patch_path}", fg=typer.colors.CYAN)
            raise typer.Exit(0)
        
        # If we reach here, the apply failed
        _handle_apply_failure(proc, patch_path)


def _run_dry_run_check(patch_path: Path, root: str) -> None:
    """Run a dry-run check to see if the patch would apply cleanly.
    
    Args:
        patch_path: Path to the patch file
        root: Git repository root directory
        
    Raises:
        typer.Exit: With code 0 if patch would apply cleanly, 1 if it would fail
    """
    typer.secho("🧪 Dry-run: checking with --3way…", fg=typer.colors.CYAN)
    proc = _run(["git", "apply", "--3way", "--index", "--check", str(patch_path)], check=False)
    if proc.returncode == 0:
        typer.secho("✅ Patch would apply cleanly.", fg=typer.colors.GREEN)
        typer.secho(f"   📁 Patch saved to: {patch_path}", fg=typer.colors.CYAN)
        raise typer.Exit(0)
    else:
        # Provide git's stderr for debugging when available
        stderr = (proc.stderr or "").strip()
        typer.secho("❌ Patch check failed.", fg=typer.colors.RED)
        typer.secho(f"   Return code: {proc.returncode}", fg=typer.colors.RED)
        if stderr:
            typer.secho("   Git stderr:", fg=typer.colors.RED)
            for line in stderr.splitlines():
                typer.secho(f"   {line}", fg=typer.colors.RED)
        typer.secho(f"   Patch file: {patch_path}", fg=typer.colors.YELLOW)
        typer.secho(f"   Try manual: (cd \"{root}\" && git apply --3way --reject \"{patch_path}\")", fg=typer.colors.YELLOW)
        # Keep the patch file for debugging
        typer.secho(f"   📁 Patch saved to: {patch_path}", fg=typer.colors.CYAN)
        raise typer.Exit(1)


def _show_patch_preview(patch_text: str) -> None:
    """Display a preview of the patch content (first 20 lines).
    
    Args:
        patch_text: The patch content to preview
    """
    typer.secho("📋 Patch preview (first 20 lines):", fg=typer.colors.CYAN)
    for ln in patch_text.splitlines()[:20]:
        typer.echo(ln)


def _create_patch_file(patch_text: str) -> Path:
    """Create a timestamped patch file and write the patch content to it.
    
    Args:
        patch_text: The normalized patch content to write
        
    Returns:
        Path: Path to the created patch file
    """
    # Create timestamped filename and use ~/tmp/tools directory
    branch_clean = _get_git_branch()
    filename = f"gappdiff-{branch_clean}-{_nowstamp()}.patch"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    patch_path = outdir / filename
    
    patch_path.write_text(patch_text, encoding="utf-8")
    
    return patch_path


def _normalize_patch_text(patch_text: str) -> str:
    """Normalize patch text by handling CRLF and ensuring proper trailing newline.
    
    Args:
        patch_text: Raw patch content
        
    Returns:
        str: Normalized patch text with proper line endings
    """
    # Normalize CRLF and ensure the patch ends with a single trailing newline
    # Some git apply flows expect a trailing blank line; make it explicit.
    patch_text = patch_text.replace("\r\n", "\n").replace("\r", "\n")
    
    if not patch_text.endswith("\n"):
        patch_text += "\n"
        
    return patch_text


def _filter_patch_content(clip: str) -> str:
    """Filter clipboard content to extract patch data.
    
    Removes fenced code blocks and everything before the first 'diff --git' line.
    
    Args:
        clip: Raw clipboard content
        
    Returns:
        str: Filtered patch content
        
    Raises:
        typer.Exit: If no valid patch is found (no 'diff --git')
    """
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
    
    if not patch_text.strip():
        typer.secho("❌ Clipboard doesn't contain a valid patch (no 'diff --git').", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    return patch_text


def _read_clipboard_content() -> str:
    """Read clipboard content using pbpaste and validate it's not empty.
    
    Returns:
        str: The clipboard content
        
    Raises:
        typer.Exit: If clipboard is empty or pbpaste fails
    """
    try:
        proc = _run(["pbpaste"], check=False)
        clip = proc.stdout or ""
    except Exception:
        clip = ""

    if not clip:
        typer.secho("❌ Clipboard empty or pbpaste failed.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    return clip

@app.command(help="Apply a patch from the clipboard (handles fenced code blocks) (gappdiff)")
def gappdiff(dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Check whether patch would apply without applying")) -> None:
    """Read clipboard (macOS pbpaste), strip code fences and non-patch text, save to ~/tmp/tools with timestamp,
    and apply with `git apply --3way --index`. Use --dry-run to only check with --3way --check.

    This simplified version contains the full flow in one function and no longer calls a separate
    _gappdiff_core helper. It still relies on the existing small helpers in the module:
    _which, _read_clipboard_content, _filter_patch_content, _normalize_patch_text,
    _create_patch_file, _run, _show_patch_preview, _run_dry_run_check, and _apply_patch.
    """
    # Platform / dependency checks
    _ensure_macos_with_pbpaste()

    # Read clipboard (try helper first, fallback to pbpaste subprocess)
    clip = _read_clipboard_content()
    if not clip:
        try:
            proc = _run(["pbpaste"], check=False)
            clip = proc.stdout or ""
        except Exception:
            clip = ""

    if not clip:
        typer.secho("❌ Clipboard empty or pbpaste failed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Filter / normalize patch text
    # _filter_patch_content should handle fenced-code removal and selecting from first 'diff --git'.
    patch_text = _filter_patch_content(clip)
    patch_text = _normalize_patch_text(patch_text)

    if not patch_text.strip():
        typer.secho("❌ Clipboard doesn’t contain a valid patch (no 'diff --git').", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Ensure single trailing newline (some git apply flows expect it)
    if not patch_text.endswith("\n"):
        patch_text += "\n"

    # Create the patch file (helper returns a pathlib.Path-like object)
    patch_path = _create_patch_file(patch_text)

    # Determine repo root
    try:
        root = _run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    except Exception:
        typer.secho("❌ Repo root not found; ensure you're inside a git repo.", fg=typer.colors.RED)
        raise typer.Exit(1)

    # Show a preview to the user
    _show_patch_preview(patch_text)

    # Dry-run vs apply
    if dry_run:
        typer.secho("", fg=typer.colors.WHITE)  # spacing for readability
        _run_dry_run_check(patch_path, root)
    else:
        _apply_patch(patch_path)


@app.command(help="Reverse-apply a patch saved in the clipboard to revert changes (grevdiff)")
def grevdiff() -> None:
    """Save clipboard to rev.patch, run `git apply -R rev.patch`, then remove the file.

    Mirrors the shell `grevdiff` helper. Requires macOS pbpaste.
    """
    _ensure_macos_with_pbpaste()

    typer.secho("📋 Saving clipboard contents to rev.patch...", fg=typer.colors.CYAN)
    content = _read_from_clipboard()

    if not content:
        typer.secho("❌ Failed to read clipboard or clipboard empty.", fg=typer.colors.RED)
        raise typer.Exit(1)

    rev_path = Path.cwd() / "rev.patch"
    
    if not content.endswith("\n"):
        content += "\n"
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
    msg = _unwrap_fenced(msg or "").strip()

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

    # Parse porcelain output to extract file paths and handle renames
    files: List[str] = []
    for ln in out.splitlines():
        if not ln.strip():
            continue
        # rename lines may include '->' with old and new paths
        if "->" in ln:
            newpath = ln.split("->")[-1].strip()
            files.append(newpath)
        else:
            parts = ln.split()
            if len(parts) >= 2:
                files.append(parts[1])

    # Process each file with gfilecommit
    for f in files:
        try:
            gfilecommit(f)
        except Exception:
            typer.secho(f"⚠️ Failed to process {f}; continuing.", fg=typer.colors.YELLOW)

    typer.secho("✅ Done! All files have been committed individually.", fg=typer.colors.GREEN)
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

    filename = f"gadded-{_nowstamp()}.txt"
    outdir = _get_output_dir(filename)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / filename
    outpath.write_text(content, encoding="utf-8")

    _open_in_editor(outpath)


@app.command(help="""Rebase commits onto upstream branch with Signed-off-by signatures.

WHAT 'gsign main' DOES: Takes all commits from your current branch that are NOT in 'main', rebases them onto main's tip, and adds 'Signed-off-by' to each commit.

UPSTREAM BRANCH: The base branch you want to rebase onto (e.g., 'main', 'develop'). Git finds commits in your branch but NOT in upstream, then replays them on top.

EXAMPLES: 
  gsign main → Rebase current branch onto main with signatures
  gsign main..HEAD → Same as above (explicit range)  
  gsign upstream/main --autosquash → Rebase onto upstream/main with auto-squashing""")
def gsign(
    upstream_or_range: str = typer.Argument(..., help="Upstream branch or range (e.g. 'main' or 'main..HEAD' or 'abc123..def456')"),
    autosquash: bool = typer.Option(False, "--autosquash", help="Pass --autosquash to git rebase to automatically fixup/squash commits marked with fixup!/squash!"),
    rebase_merges: bool = typer.Option(False, "--rebase-merges", help="Pass --rebase-merges to preserve merge commits during the rebase"),
) -> None:
    """Rebase commits with Signed-off-by and add missing signatures.

    WHAT DOES 'gsign main' DO?
    ==========================
    Running 'gsign main' will:
    1. Take all commits from your current branch that are NOT in 'main'
    2. Rebase them onto the tip of 'main' 
    3. Add 'Signed-off-by: Your Name <your@email.com>' to each commit message
    4. This effectively replays your commits on top of main with signatures

    WHAT IS AN UPSTREAM BRANCH?
    ===========================
    An "upstream" branch is the base branch you want to rebase onto. It's typically:
    - 'main' or 'master': The main development branch
    - 'develop': A development integration branch
    - Any other branch you want to base your work on

    When you specify 'main' as upstream, git finds all commits that are in your
    current branch but NOT in main, then replays them on top of main's latest commit.

    EXAMPLES:
    =========
    gsign main
        → Rebase current branch onto 'main', add signatures to all commits
        → Equivalent to: git rebase --signoff main

    gsign main..HEAD
        → Same as above (explicitly specifying the range)

    gsign feature-branch..my-branch --autosquash
        → Rebase commits from feature-branch to my-branch, with auto-squashing

    gsign upstream/main --rebase-merges
        → Rebase onto upstream/main, preserving any merge commits

    REQUIREMENTS:
    =============
    - Must be in a git repository
    - Working tree and index must be clean (no uncommitted changes)
    - No rebase already in progress
    """

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

    # Determine upstream and branch from input
    upstream = ""
    branch = ""
    if ".." in upstream_or_range:
        upstream, branch = upstream_or_range.split("..", 1)
        if not branch:
            branch = "HEAD"
    else:
        upstream = upstream_or_range
        branch = "HEAD"

    try:
        cur_branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    except Exception:
        cur_branch = "HEAD"

    typer.secho(f"🔧 Rebase {branch} onto {upstream} with --signoff {('and --autosquash' if autosquash else '')}{(' and --rebase-merges' if rebase_merges else '')}...", fg=typer.colors.CYAN)
    typer.secho(f"   Current branch: {cur_branch}", fg=typer.colors.CYAN)

    # Build command
    cmd = ["git", "rebase", "--signoff"]
    if autosquash:
        cmd.append("--autosquash")
    if rebase_merges:
        cmd.append("--rebase-merges")
    
    # Add upstream
    cmd.append(upstream)
    
    # Only add branch if it's not HEAD and different from current branch
    # This prevents detached HEAD state when rebasing the current branch
    if branch != "HEAD" and branch != cur_branch:
        cmd.append(branch)

    try:
        _run(cmd)
    except subprocess.CalledProcessError as exc:
        typer.secho(f"❌ git rebase failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)

@app.command(name="chezcrypt")
def chezcrypt_cmd(dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be encrypted without running chezmoi"),
                 targets: list[str] = typer.Argument(..., help="One or more target directories to encrypt")) -> None:
    """Encrypt all files in the given directories using `chezmoi add --encrypt`.

    For each provided directory, runs `find <dir> -type f -exec chezmoi add --encrypt {}`.
    
    Note: the sequence "\\;" contains a backslash. Keep this as a literal
    backslash+semicolon in the docstring to match the shell `find -exec` syntax.
    The backslash is escaped here so Python won't emit a SyntaxWarning about
    an invalid escape sequence.
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
        typer.secho("🔄 Running: chezmoi re-add", fg=typer.colors.CYAN)
        _run(["chezmoi", "re-add"])
        typer.secho("✅ chezmoi re-add completed", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError:
        typer.secho("❌ chezmoi re-add failed.", fg=typer.colors.RED)
        raise typer.Exit(1)

    if not chez_repo.exists():
        typer.secho(f"❌ Failed to access chezmoi repo: {chez_repo}", fg=typer.colors.RED)
        raise typer.Exit(1)

    # change working dir to chez_repo
    cwd = Path.cwd()
    try:
        typer.secho(f"📁 Changing directory to: {chez_repo}", fg=typer.colors.CYAN)
        os.chdir(chez_repo)

        # check for changes (untracked/modified or staged)
        typer.secho("🔎 Checking for changes in chezmoi repo...", fg=typer.colors.CYAN)
        diff_ret = subprocess.run(["git", "diff", "--quiet"]).returncode
        staged_ret = subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode

        if diff_ret == 0 and staged_ret == 0:
            typer.secho("🔍 No changes to commit.", fg=typer.colors.YELLOW)
            return

        typer.secho("➕ Staging changes (git add .)", fg=typer.colors.CYAN)
        _run(["git", "add", "."])

        # simple commit with message
        msg = f"chezmoi: re-add {datetime.now().strftime('%Y-%m-%d_%H:%M')}"
        typer.secho(f"✍️  Committing changes with message: {msg}", fg=typer.colors.CYAN)
        try:
            _run(["git", "commit", "-m", msg])
            typer.secho("✅ Commit created", fg=typer.colors.GREEN)
        except subprocess.CalledProcessError:
            # commit may fail if nothing to commit
            typer.secho("❌ git commit failed.", fg=typer.colors.RED)
            raise typer.Exit(1)

        typer.secho("📤 Pushing changes to remote (git push)", fg=typer.colors.CYAN)
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
            if _is_macos_with_pbcopy():  # pbcopy implies pbpaste availability
                # Use pbpaste to populate both files sequentially (user may have split content manually)
                # First read current clipboard once into f1, then prompt for a second paste into f2.
                clipboard_content = _read_from_clipboard()
                f1.write(clipboard_content.encode())

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

        if not _copy_to_clipboard(out, "📋 Extracted content copied to clipboard!"):
            typer.echo(out)
    except Exception as exc:
        typer.secho(f"❌ Failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1)
    # end of cdiff_cmd


@app.command(help="Add a well-thought-out comment to a GitHub issue")
def icomment(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Add a well-thought-out comment to a GitHub issue.
    
    This command extracts the issue context and generates a thoughtful comment
    that provides a new and helpful perspective, ideally grounded in the code
    or project direction. The comment is constructive and specific.
    """
    prompt = (
        "Add a well-thought-out comment to the issue. It should provide a new and helpful "
        "perspective, ideally grounded in the code or project direction. Keep it constructive and specific."
    )
    
    # Reuse the existing issue_to_file functionality
    issue_to_file(url=url, prompt=prompt, prefix="icomment", no_open=no_open, editor=editor)


@app.command(help="Respond to the latest unanswered questions directed at @kosiew")
def irespond(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Respond to the latest unanswered questions directed at @kosiew.
    
    This command extracts the issue context and generates thoughtful, detailed,
    and technically sound arguments to move the discussion forward. The response
    is respectful and concise.
    """
    prompt = (
        "Respond to the latest unanswered questions directed at @kosiew. Provide thoughtful, "
        "detailed, and technically sound arguments to move the discussion forward. Be respectful and concise."
    )
    
    # Reuse the existing issue_to_file functionality
    issue_to_file(url=url, prompt=prompt, prefix="irespond", no_open=no_open, editor=editor)


@app.command(help="Summarize the issue with headings, bullet points, and diagrams")
def isum(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Summarize the issue with headings, bullet points, and add diagrams if they help clarify the concepts.
    
    This command extracts the issue context and generates a comprehensive summary
    with clear structure and visual aids when appropriate.
    """
    prompt = (
        "Summarize the issue with headings, bullet points, and add diagrams if they help clarify the concepts."
    )
    
    # Reuse the existing issue_to_file functionality
    issue_to_file(url=url, prompt=prompt, prefix="isum", no_open=no_open, editor=editor)


@app.command(help="Summarize GitHub issue from clipboard with headings, bullet points, and diagrams")
def isum_clip(
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Summarize GitHub issue from clipboard with headings, bullet points, and add diagrams if they help clarify the concepts.
    
    This command reads the issue content from the clipboard and generates a comprehensive summary
    with clear structure and visual aids when appropriate.
    """
    prompt = (
        "Summarize the issue with headings, bullet points, and add diagrams if they help clarify the concepts."
    )
    
    # Reuse the existing clipboard_to_file functionality
    clipboard_to_file(prompt=prompt, prefix="isum_clip", no_open=no_open, editor=editor)


@app.command(help="Deep analysis of GitHub issue with investigation approaches and solutions")
def ideep(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
    local_md: str = typer.Option(IDEEP_MD, "--local-md", help="Local template filename next to alias.py"),
):
    """
    Deep analysis of a GitHub issue from a senior developer perspective.
    
    This command extracts the issue context and provides thoughtful analysis including:
    - Investigation approaches
    - Multiple solution approaches
    - Ranking by feasibility and effectiveness
    - Clear rationale for rankings
    """
    
    # Prefer a local template file (next to alias.py) like ictriage/icask
    issue_id = _extract_id(url)
    ts = _nowstamp()

    tpl_text = _read_local_template(local_md)
    if tpl_text is None:
        typer.secho(f"❌ Template '{local_md}' not found next to alias.py. Please create {local_md}.", fg=typer.colors.RED)
        raise typer.Exit(2)

    # Ensure llm is available for generating deep analysis
    if not _which("llm"):
        typer.secho("❌ 'llm' not found in PATH. ideep requires 'llm' to generate the analysis.", fg=typer.colors.RED)
        raise typer.Exit(1)

    try:
        typer.secho("🧠 Generating concise summary of the issue...", fg=typer.colors.CYAN)
    except Exception:
        pass

    summary_text = _gen_summary_from_issue(url)
    if not summary_text:
        summary_text = "(Summary could not be auto-generated. Replace with 3–6 concise bullets.)"

    # Still generate full deep analysis via LLM for completeness (optional), but the template will receive the concise summary.
    try:
        typer.secho("🧠 Generating deep analysis using LLM (also saved to template as supplemental content)...", fg=typer.colors.CYAN)
    except Exception:
        pass

    # Pass the concise summary into the template as ${summary}
    _render_and_write(issue_id=issue_id, url=url, prefix="ideep", tpl_text=tpl_text, summary_text=summary_text, ts=ts, no_open=no_open, editor=editor)


@app.command(help="Generate specific instructions for AI coding agents (Codex) to implement solutions")
def icodex(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Generate specific, executable instructions for AI coding agents (like Codex) to implement solutions.
    
    This command analyzes GitHub issues and provides detailed, actionable guidance for AI agents,
    including multiple solution approaches for features and direct implementation steps for bugs.
    """
    prompt = (
        "You are a **senior open-source contributor and software engineer**. Given a GitHub issue, follow the instructions based on its type:\n"
        "---\n"
        "### **A. Feature or Improvement Request**\n"
        "1. **Analyze** the issue and produce **multiple distinct solution approaches**.\n"
        "2. For **each approach**, include:\n"
        "   * **Title & Summary** – A short, clear description of the strategy.\n"
        "   * **Agent Instructions** – Specific, executable steps for an AI coding agent (e.g., Codex) to implement the solution, including:\n"
        "     * Identifying the files, directories, or modules to review.\n"
        "     * How to evaluate extending existing modules vs. creating new ones.\n"
        "     * Step-by-step implementation actions.\n"
        "3. **Ranking** – Order the approaches by **feasibility** and **effectiveness**.\n"
        "4. **Formatting Requirements**:\n"
        "   * Use a **Heading** for each approach.\n"
        "   * Use **bullet points** or **code blocks** for agent instructions.\n"
        "   * End with a **final ranked list** of approaches.\n"
        "5. **Do not** include generic investigation steps or commentary—only concrete, actionable guidance.\n"
        "---\n"
        "### **B. Bug Report**\n"
        "Produce **direct instructions** for an AI coding agent (e.g., Codex) to:\n"
        "1. **Confirm the bug** by:\n"
        "   * Creating a **script or test** in the relevant file to reproduce the issue.\n"
        "2. **Investigate** by:\n"
        "   * Identifying the root cause.\n"
        "3. **Fix** by:\n"
        "   * Modifying the relevant code sections to resolve the root cause.\n"
        "4. Focus solely on **specific, executable actions**—exclude vague steps or general debugging tips."
    )
    
    # Warn that this command is deprecated / not used anymore
    try:
        typer.secho("⚠️ 'icodex' is deprecated and not used anymore. Consider using updated workflows.", fg=typer.colors.YELLOW)
    except Exception:
        pass

    # Reuse the existing issue_to_file functionality
    issue_to_file(url=url, prompt=prompt, prefix="icodex", no_open=no_open, editor=editor)


@app.command(help="Generate strategic review for GitHub issue and associated commit changes")
def iprfb(
    issue: str = typer.Argument(..., help="GitHub issue URL or issue summary text"),
    commit_hash: str = typer.Argument(..., help="Commit hash to review"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Generate strategic review for a GitHub issue and associated commit changes.
    
    This command can work in two modes:
    - URL mode: Provide a GitHub issue URL to fetch and summarize the issue
    - Summary mode: Provide pre-written issue summary text
    
    The review focuses on consistency, redundancy, and effectiveness of the changes.
    """
    # Warn that this command is deprecated / not used anymore
    try:
        typer.secho("⚠️ 'iprfb' is deprecated and not used anymore. Consider using updated workflows.", fg=typer.colors.YELLOW)
    except Exception:
        pass

    # Determine if first argument is a URL or summary text
    is_url = issue.startswith(("http://", "https://"))
    
    # Generate short title for filename
    short_title = "issue-review"
    if _which("llm"):
        try:
            title_prompt = "Condense this into a 6–10 word review title (no punctuation). If it's a URL, derive the title from the issue context."
            proc = _run(["llm", "-s", title_prompt], input=issue)
            if proc.stdout.strip():
                short_title = proc.stdout.strip()
        except Exception:
            pass
    
    # Fallback title generation if llm failed
    if short_title == "issue-review":
        import re
        sanitized = re.sub(r"https?://", "", issue)
        sanitized = re.sub(r"[^\w\s-]", "", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        short_title = sanitized[:60] if sanitized else "issue-review"
    
    # Build the appropriate summary step and prefilled content
    if is_url:
        summary_step = f"1. **Summarize** the issue clearly and concisely (source: {issue})."
        prefilled_summary = ""
    else:
        summary_step = "1. **Use the provided issue summary** (do not re-summarize):"
        # Format the summary with proper indentation
        indented_summary = "\n".join(f"> {line}" for line in issue.split("\n"))
        prefilled_summary = f"\n\n**Issue Summary (provided):**\n\n{indented_summary}\n"
    
    # Compose the full prompt
    prompt = f"""**Role:** You are a **senior open-source contributor and software engineer**.

**Task:** Given a GitHub issue and the associated codebase, produce a strategic and actionable review by following these steps:

{summary_step}
2. **Review the changes introduced in commit: {commit_hash}**
3. **Provide constructive and actionable feedback**, focusing on:

- **Consistency** — Are the changes aligned with the repository's coding conventions and structure?
- **Redundancy** — Do the changes introduce any code duplication that could be avoided or refactored?
- **Effectiveness** — Do the changes fully and appropriately address the described issue?

Conclusion:
- Approve
- Approve with Suggestions (list specific follow-up actions)
- Request Changes (list specific blocking issues)

{prefilled_summary}"""
    
    # Handle execution based on mode
    if is_url:
        # URL mode: use issue_to_file functionality
        prefix = f"iprfb:{short_title}"
        issue_to_file(url=issue, prompt=prompt, prefix=prefix, no_open=no_open, editor=editor)
    else:
        # Summary mode: direct LLM execution or output
        if not _which("llm"):
            typer.secho("❌ 'llm' not found in PATH. Outputting prompt instead:", fg=typer.colors.RED)
            typer.echo(prompt)
            return
        
        try:
            proc = _run(["llm"], input=prompt)
            typer.echo(proc.stdout)
        except Exception as exc:
            typer.secho(f"❌ Failed to run llm: {exc}", fg=typer.colors.RED)
            typer.secho("Outputting prompt instead:", fg=typer.colors.YELLOW)
            typer.echo(prompt)


@app.command(help="Generate strategic instructions using a provided template and write to icask file")
def icask(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    comment: str = typer.Argument("", help="Optional reviewer comment to incorporate"),
    prefix: str = typer.Option("icask", "--prefix", "-p", help="Filename prefix"),
    local_md: str = typer.Option(ICASK_MD, "--local-md", help="Local template filename next to alias.py"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Create a concise ${summary} and substitute into the provided template, then save to the same
    auto-generated filename used by `icask`.
    """
    issue_id = _extract_id(url)
    ts = _nowstamp()

    # Generate concise summary (fallback text provided if LLM isn't available)
    summary_text = _gen_summary_from_issue(url)
    if not summary_text:
        summary_text = "(Summary could not be auto-generated. Replace with 3–6 concise bullets: problem, scope, impact, constraints.)"

    # Rephrase optional reviewer comment and incorporate if present
    rephrased = ""
    if comment.strip():
        if _which("llm"):
            try:
                rephrase_prompt = "Rephrase this reviewer note in 1–2 concise, professional sentences. Keep key constraints; avoid first person; do not quote verbatim."
                proc = _run(["llm", "-s", rephrase_prompt], input=comment)
                rephrased = proc.stdout.strip() if proc.stdout.strip() else comment
            except Exception:
                rephrased = comment
        else:
            rephrased = comment

    if rephrased:
        # Prepend reviewer note to the summary to make it visible in generated output
        summary_text = f"Reviewer note: {rephrased}\n\n{summary_text}"

    tpl_text = _read_local_template(local_md)
    if tpl_text is None:
        typer.secho(f"❌ Template '{local_md}' not found next to alias.py. Please create {local_md}.", fg=typer.colors.RED)
        raise typer.Exit(2)

    _render_and_write(issue_id=issue_id, url=url, prefix=prefix, tpl_text=tpl_text, summary_text=summary_text, ts=ts, no_open=no_open, editor=editor)


@app.command(help="Generate a structured triage file using a provided template and write to ictriage file")
def ictriage(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    prefix: str = typer.Option("ictriage", "--prefix", "-p", help="Filename prefix"),
    local_md: str = typer.Option(ICTRIAGE_MD, "--local-md", help="Local template filename next to alias.py"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Create a triage document by generating a concise ${summary} and substituting into the
    provided template (or local ictriage.md), then save to the autogenerated ictriage file.
    """
    issue_id = _extract_id(url)
    ts = _nowstamp()

    summary_text = _gen_summary_from_issue(url)
    if not summary_text:
        summary_text = "(Summary could not be auto-generated. Replace with 3–6 concise bullets: problem, scope, impact, constraints.)"

    tpl_text = _read_local_template(local_md)
    if tpl_text is None:
        typer.secho(f"❌ Template '{local_md}' not found next to alias.py. Please create {local_md}.", fg=typer.colors.RED)
        raise typer.Exit(2)

    _render_and_write(issue_id=issue_id, url=url, prefix=prefix, tpl_text=tpl_text, summary_text=summary_text, ts=ts, no_open=no_open, editor=editor)




@app.command(help="Ask a specific question about a GitHub issue")
def iask(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    question: str = typer.Argument(..., help="Question to ask about the issue"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Ask a specific question about a GitHub issue.
    
    This command allows you to pose any question about a GitHub issue and get
    an AI-generated response based on the issue context and codebase.
    """
    # For iask, the question itself is the prompt - no additional formatting needed
    # This preserves the original behavior where the user's question is passed directly
    issue_to_file(url=url, prompt=question, prefix="iask", no_open=no_open, editor=editor)


@app.command(help="Reflect on GitHub issue with analysis of key aspects and relationships")
def imuse(
    url: str = typer.Argument(..., help="GitHub issue/PR URL"),
    no_open: bool = typer.Option(False, "--no-open", help="Do not open the file in $EDITOR"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to open file"),
):
    """
    Reflect on a GitHub issue with analysis of key aspects and relationships.
    
    This command extracts the issue context and provides thoughtful reflection using
    clear headings, bullet points, and illustrative diagrams to explore the issue's
    various aspects and their interconnections.
    """
    prompt = (
        "Reflect on this issue using clear headings, bullet points and illustrative diagrams "
        "to explore key aspects and relationships."
    )
    
    # Reuse the existing issue_to_file functionality
    issue_to_file(url=url, prompt=prompt, prefix="imuse", no_open=no_open, editor=editor)


@app.command(name="cleantmp")
def cleantmp_cmd(
    days: int = typer.Option(30, "--days", "-d", help="Delete files older than this many days"),
    pattern: Optional[str] = typer.Option(None, "--pattern", "-p", help="Optional regex pattern to match filenames to delete")
) -> None:
    """Clean ~/tmp directory by removing old files and empty directories.
    
    This function:
    1. Deletes files older than the specified number of days (default: 30)
    2. Removes empty directories (excluding vim_swap and pycache)
    3. Provides feedback on the cleanup process
    """
    import time
    
    tmp_dir = Path.home() / "tmp"
    
    if not tmp_dir.exists():
        typer.secho(f"📁 ~/tmp directory doesn't exist, nothing to clean.", fg=typer.colors.YELLOW)
        return
    
    typer.secho("🧹 Cleaning ~/tmp...", fg=typer.colors.CYAN)
    typer.secho(f"🗑️  Deleting files older than {days} days...", fg=typer.colors.CYAN)
    
    # Calculate cutoff time (days ago from now)
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    
    # Coerce Typer OptionInfo (or other non-str values) to None when called
    # programmatically so we don't pass a non-string to re.compile.
    if pattern is not None and not isinstance(pattern, str):
        try:
            # Typer sometimes passes an OptionInfo object when invoked programmatically;
            # fall back to treating it as no pattern.
            from typer.models import OptionInfo  # type: ignore
            if isinstance(pattern, OptionInfo):
                pattern = None
        except Exception:
            # Generic fallback: if it's not a str, treat as None
            pattern = None

    # Use reusable helper to remove files
    files_deleted = find_and_remove_old_files("tmp", days=days, pattern=pattern)
    typer.secho(f"📄 Deleted {files_deleted} old files", fg=typer.colors.GREEN)
    
    # Delete empty directories (excluding vim_swap and pycache)
    typer.secho("📂 Deleting empty folders (excluding vim_swap, tools and pycache)...", fg=typer.colors.CYAN)
    
    dirs_deleted = 0
    # Walk directories in reverse order (deepest first) to handle nested empty dirs
    for dir_path in sorted(tmp_dir.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if dir_path.is_dir() and dir_path != tmp_dir:
            # Skip excluded directories
            if dir_path.name in ("vim_swap", "tools", "pycache", "__pycache__"):
                continue
            
            try:
                # Check if directory is empty
                if not any(dir_path.iterdir()):
                    typer.echo(f"Deleting empty dir: {dir_path}")
                    dir_path.rmdir()
                    dirs_deleted += 1
            except (OSError, PermissionError) as e:
                typer.secho(f"⚠️  Could not delete {dir_path}: {e}", fg=typer.colors.YELLOW)
    
    typer.secho(f"📁 Deleted {dirs_deleted} empty directories", fg=typer.colors.GREEN)
    typer.secho("✅ Cleanup complete!", fg=typer.colors.GREEN)




@app.command(name="clean_old_zcompdump")
def clean_old_zcompdump_cmd() -> None:
    """Remove old ~/.zcompdump* files, keeping the current ~/.zcompdump.

    Mirrors the shell helper: finds files matching ~/.zcompdump* and removes any that are not
    the current ~/.zcompdump file, then prints a summary.
    """
    # Use the reusable helper to remove older .zcompdump* files in the home dir
    removed = find_and_remove_old_files(".", days=7, pattern=r"^\.zcompdump", recurse=False)
    if removed > 0:
        typer.secho(f"🗑️  Cleaned up {removed} old zcompdump file(s)!", fg=typer.colors.GREEN)


@app.command(name="weekly_tmp_cleaner")
def weekly_tmp_cleaner_cmd() -> None:
    """Check if it's time to run weekly tmp cleanup and execute if needed.
    
    This function uses cron-like scheduling to run cleanup every Monday at 7:00 AM.
    It maintains a timestamp file to track the last run and only executes when due.
    """
    # Delegate scheduling to the reusable helper which will create its own stamp
    # file derived from the cron expression.
    schedule_and_run("0 7 * * 1", _run_cleantmp_and_notify)


@app.command(name="daily_prefixed_cleaner")
def daily_prefixed_cleaner_cmd() -> None:
    """Schedule and run daily cleanup for files matching configured prefixes.

    Uses `schedule_and_run` to run `_run_prefixed_cleanup_and_notify` every day
    at 07:00 and maintain its own stamp file.
    """

    # Cron expression for every day at 07:00
    schedule_and_run("0 7 * * *", _run_prefixed_cleanup_and_notify)


@app.command(name="weekly_zcompdump_cleaner")
def weekly_zcompdump_cleaner_cmd() -> None:
    """Schedule and run weekly cleanup for old .zcompdump files.

    Uses `schedule_and_run` to run `clean_old_zcompdump_cmd` every Monday at 07:00.
    """
    cache_dir = Path.home() / ".cache"
    cache_dir.mkdir(exist_ok=True)

    # Cron expression for Monday at 07:00
    schedule_and_run("0 7 * * 1", clean_old_zcompdump_cmd, cache_dir=cache_dir)


def _run_cleantmp_and_notify() -> None:
    """Run cleantmp and show macOS notification."""
    # Run the cleantmp function directly
    cleantmp_cmd(days=30)
    
    # Show macOS notification
    try:
        _notify_macos("Old files and empty folders cleaned from ~/tmp ✅", title="Weekly Cleanup")
    except Exception as e:
        typer.secho(f"⚠️  Could not show notification: {e}", fg=typer.colors.YELLOW)


def _run_prefixed_cleanup_and_notify(prefixes: List[str] = ["gdiff-", "gdn-", "gs-", "ctest-", "crun-", "maturin-"]) -> None:
    """Clean files whose names begin with any of `prefixes` older than 1 days and notify macOS.

    Args:
        prefixes: optional list of filename prefixes (e.g. ['gdiff', 'gdn', 'ctest']).
                  If omitted, defaults to ['gdiff', 'gdn', 'ctest'].

    This reuses `cleantmp_cmd` with a filename regex constructed from `prefixes`.
    """
    # Make a shallow copy to avoid accidental mutation of the default list
    prefixes = list(prefixes) if prefixes is not None else ["gdiff", "gdn", "ctest"]
    DAYS = 1
    # Build a safe regex that matches names starting with any of the prefixes.
    # Escape each prefix to avoid regex metacharacters causing surprises.
    try:
        safe_parts = [re.escape(p) for p in prefixes if p]
        if not safe_parts:
            # nothing to do
            return
        pattern = r"^(?:" + "|".join(safe_parts) + ")"
    except Exception:
        pattern = r"^(?:gdiff|gdn|ctest)"

    # Clean files whose names start with the given prefixes older than 2 days
    try:
        cleantmp_cmd(days=DAYS, pattern=pattern)
    except Exception as e:
        typer.secho(f"⚠️  cleanup failed for prefixes={prefixes}: {e}", fg=typer.colors.YELLOW)
        raise

    # Notify the user on macOS (best-effort)
    try:
        joined = ",".join(prefixes)
        day_message = "1 day" if DAYS == 1 else f"{DAYS} days"
        _notify_macos(f"Cleaned {joined} files older than {day_message} ✅", title="Cleanup")
    except Exception as e:
        typer.secho(f"⚠️  Could not show notification: {e}", fg=typer.colors.YELLOW)


def _notify_macos(message: str, title: str = "Notification") -> None:
    """Show a macOS notification using osascript.

    This is a tiny helper to centralize macOS notification logic so it can be
    reused elsewhere in `alias.py`.
    """
    try:
        # Use the lightweight _run helper to execute osascript; allow failures silently
        _run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], check=False)
    except Exception:
        # swallowing errors is intentional here; callers may log or surface if needed
        pass


def _parse_cron_field(field: str, min_val: int, max_val: int) -> set[int]:
    """Parse a single cron field and return a set of matching values.
    
    Supports:
    - '*' for all values
    - Single numbers (e.g., '5')
    - Comma-separated lists (e.g., '1,3,5')
    - Ranges (e.g., '1-5')
    """
    vals = set()
    
    if field == "*":
        vals.update(range(min_val, max_val + 1))
        return vals
    
    for part in field.split(","):
        part = part.strip()
        if "-" in part and not part.startswith("-"):
            # Range like "1-5"
            a, b = part.split("-", 1)
            vals.update(range(int(a), int(b) + 1))
        else:
            vals.add(int(part))
    return vals





def schedule_and_run(cron_expr: str, task: Callable[[], None], *, cache_dir: Optional[Path] = None) -> None:
    """Schedule wrapper that uses `cron_expr` to decide whether to run `task`.

    - Creates a stamp file under cache_dir derived from the cron expression.
    - Computes the most recent scheduled epoch for `cron_expr`.
    - If the task is due (not recorded as run at that scheduled epoch) it runs
      `task()` inside the `_stamp_on_success` context manager which writes the
      stamp only if the task completes without raising.

    Args:
        cron_expr: a 5-field cron string (minute hour day month weekday)
        task: a zero-argument callable to execute when scheduled
        cache_dir: optional Path to hold the stamp file; defaults to ~/.cache
    """
    import time
    from datetime import datetime

    if cache_dir is None:
        cache_dir = Path.home() / ".cache"
    cache_dir.mkdir(exist_ok=True)

    # Use a deterministic stamp filename derived from the cron expression
    # and the task identity to avoid collisions when multiple different
    # tasks share the same cron expression.
    def _task_safe_name(t: Callable[[], None]) -> str:
        """Produce a short, filesystem-safe name for the task.

        Prefer the callable's __name__ when available, otherwise fall back to
        the repr. Strip non-alphanumeric characters and replace them with
        hyphens to keep filenames safe.
        """
        name = getattr(t, "__name__", None) or repr(t)
        # keep letters, numbers, dot, underscore and replace others with '-'
        cleaned = re.sub(r"[^A-Za-z0-9._-]", "-", name)
        # collapse repeated hyphens
        cleaned = re.sub(r"-+", "-", cleaned).strip("-")
        # limit length to avoid overly long filenames
        return cleaned[:64] or "task"

    safe_name = "cron_" + "_".join(cron_expr.split())
    task_name = _task_safe_name(task)
    stamp_file = cache_dir / f".{safe_name}_{task_name}_last_run"

    now_dt = datetime.now()
    now_epoch = int(time.time())

    scheduled_epoch = _get_last_scheduled_epoch(cron_expr, now_dt=now_dt, now_epoch=now_epoch)
    if scheduled_epoch is None:
        return

    # Read last run (best-effort)
    try:
        if stamp_file.exists():
            last_run = int(stamp_file.read_text().strip())
        else:
            last_run = 0
    except (ValueError, OSError):
        last_run = 0

    # If due, run inside stamp-on-success so stamp only updates on success
    if now_epoch >= scheduled_epoch and last_run < scheduled_epoch:
        with _stamp_on_success(stamp_file, scheduled_epoch):
            task()


def _get_last_scheduled_epoch(cron_expr: str, *, now_dt: Optional[datetime] = None, now_epoch: Optional[int] = None) -> Optional[int]:
    """Return the most recent scheduled epoch (<= now) for `cron_expr`, or None if none found.

    Uses the same evaluation as `_is_cron_schedule_due` but returns the scheduled epoch so callers
    can take action (and stamp) using that precise time.
    """
    from datetime import datetime, timedelta
    import time as _time

    if now_dt is None:
        now_dt = datetime.now()
    if now_epoch is None:
        now_epoch = int(_time.time())

    parts = cron_expr.split()
    if len(parts) != 5:
        raise ValueError("cron_expr must have 5 fields: minute hour day month weekday")

    minute_field, hour_field, day_field, month_field, weekday_field = parts

    minutes = _parse_cron_field(minute_field, 0, 59)
    hours = _parse_cron_field(hour_field, 0, 23)
    days = _parse_cron_field(day_field, 1, 31)
    months = _parse_cron_field(month_field, 1, 12)
    weekdays = _parse_cron_field(weekday_field, 0, 6)  # Monday=0

    candidate = now_dt.replace(second=0, microsecond=0)
    for days_back in range(0, 8):
        day_candidate = candidate - timedelta(days=days_back)
        if day_candidate.month not in months:
            continue
        if day_candidate.day not in days:
            continue
        if day_candidate.weekday() not in weekdays:
            continue

        if days_back == 0:
            hr_list = sorted([h for h in hours if h <= day_candidate.hour], reverse=True)
            for h in hr_list:
                min_list = sorted([m for m in minutes if (h < day_candidate.hour and True) or m <= day_candidate.minute], reverse=True)
                for m in min_list:
                    scheduled = day_candidate.replace(hour=h, minute=m, second=0, microsecond=0)
                    scheduled_epoch = int(scheduled.timestamp())
                    if scheduled_epoch <= now_epoch:
                        return scheduled_epoch
            continue
        else:
            h = max(hours)
            m = max(minutes)
            scheduled = day_candidate.replace(hour=h, minute=m, second=0, microsecond=0)
            scheduled_epoch = int(scheduled.timestamp())
            return scheduled_epoch

    return None


from contextlib import contextmanager


@contextmanager
def _stamp_on_success(stamp_file: Path, epoch: int):
    """Context manager that writes `epoch` to `stamp_file` if the block succeeds.

    If the block raises, the stamp is not updated.
    """
    try:
        yield
    except Exception:
        # re-raise, do not stamp
        raise
    else:
        try:
            stamp_file.write_text(str(epoch))
        except Exception:
            # best-effort: ignore write failures
            pass


if __name__ == "__main__":
    app()