#!/bin/bash
git reset HEAD~3
git add index.html README.md quick_test.py task.md walkthrough.md
git commit -m "feat: improve history sidebar and cleanup secrets"
git push origin main --force 2>&1 | tee push_output_final.log
