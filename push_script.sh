#!/bin/bash
git add .
git commit -m "fix: add redundant history buttons in cards for guaranteed visibility"
git push origin main 2>&1 | tee push_output.log
