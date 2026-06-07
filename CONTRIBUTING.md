# Contributing to WarmGrid

Thanks for your interest in contributing. Here's how to get started.

## Local Setup

Follow the [Quick Start](README.md#quick-start-local) in the README to get the app running locally.

## Making Changes

1. Fork the repo and create a branch: `git checkout -b fix/your-fix-name`
2. Make your changes
3. Test that the backend starts: `uvicorn main:app --reload`
4. Test that the frontend builds: `npm run build`
5. Open a pull request

## Code Style

- **Python:** Follow PEP 8. Keep functions focused and async where possible.
- **React:** Functional components only. Keep components small and reusable.
- **No new dependencies** without a good reason — keep the stack lean.

## Reporting Bugs

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) template. Include backend logs and browser console errors.

## Questions

Open a GitHub Discussion or Issue with the `question` label.
