#!/bin/bash
git checkout --orphan clean-main
git add .
git commit -m "feat: improve history sidebar and cleanup secrets"
git push origin clean-main:main --force 2>&1 | tee push_output_clean.log
git checkout main
