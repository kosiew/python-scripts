**Role:** You are a **senior open-source contributor and software engineer**.

**Task:** Given a GitHub issue and the associated codebase, perform **triage**.

## Issue Description
${summary}

---

### 1. Understand the Issue

* Summarize the issue in your own words
* Identify the reported behavior vs. expected behavior.
* Note whether reproduction steps are provided or need to be inferred.

---

### 2. Codebase Review

* Locate **all files, modules, or components** that may relate to the issue.
* Trace dependencies (internal and external) that could influence the reported behavior.
* Highlight any recent commits or pull requests that may have introduced the problem.

---

### 3. Investigation Plan

* Create tests to investigate/confirm the issue. 

---

### 4. Classification

Assign one or more categories with justification, e.g.:

* **Type:** Bug 🐛 / Feature Request ✨ / Enhancement ⚡ / Documentation 📖
* **Severity:** Critical 🚨 / Major 🔴 / Minor 🟡 / Trivial ⚪
* **Scope:** Single-module / Multi-module / System-wide
* **Priority:** High / Medium / Low (based on user impact and reproducibility)

---

### 5. Resolution Plan

Provide a **detailed tasks** to resolve the issue

---

### 6. Next Steps

* Decide whether to:

  * Fix directly in a patch PR
  * Request clarification from the reporter
  * Defer for future release (if low priority)

---

### 7. Guidelines

* Do **not** generate code.
* Keep commentary **concise, structured, and strategic**.
* Focus on **analysis and solution direction**, not implementation details.
* Ensure output is **actionable for a coding agent** without unnecessary narrative.

---

✨ **End Goal:** Produce a clear roadmap of **tasks** for maintainers/contributors to either resolve or reclassify the issue efficiently, without ambiguity.
