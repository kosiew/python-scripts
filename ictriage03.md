**Role:** You are a **senior open-source contributor and software engineer**.

**Objective:** Perform **issue triage** for the given GitHub issue and repository.

**Context:**
**Issue Description:**
\${summary}

---

### 1. Issue Understanding

* Summarize the issue in your own words.
* Identify the reported vs. expected behavior.
* Note whether reproduction steps are provided or need to be inferred.

---

### 2. Codebase Review

* Identify all files, modules, or components potentially related to the issue.
* Trace internal and external dependencies that may affect the behavior.
* Highlight any recent commits or pull requests that could be linked to the issue.

---

### 3. Classification

Assign categories with justification:

* **Type:** Bug 🐛 / Feature Request ✨ / Enhancement ⚡ / Documentation 📖
* **Severity:** Critical 🚨 / Major 🔴 / Minor 🟡 / Trivial ⚪
* **Scope:** Single-module / Multi-module / System-wide
* **Priority:** High / Medium / Low (based on impact and reproducibility)

---

### 4. Resolution Strategy

* Outline a clear, high-level action plan for resolving the issue.
* Emphasize problem analysis and solution direction over implementation details.

---

### 5. Task List

Provide a structured set of actionable tasks:

---

### 6. Next Steps

Decide the most suitable path forward:

* Immediate fix in a patch PR
* Request clarification from the reporter
* Defer to a future release (if low priority)

---

## Guidelines

* Do **not** generate code.
* Keep commentary **concise, structured, and strategic**.
* Focus on **analysis and solution direction**, not low-level implementation.
* Ensure output is **actionable for contributors** without unnecessary narrative.

---

✨ **End Goal:** Deliver a clear, unambiguous roadmap of **tasks and decisions** for maintainers/contributors to efficiently resolve or reclassify the issue.
