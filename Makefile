.PHONY: hooks serve

hooks: ## Install the pre-commit guard that keeps data out of the repository
	chmod +x scripts/check_commit.sh
	ln -sf ../../scripts/check_commit.sh .git/hooks/pre-commit

serve: ## Serve the map pages on http://127.0.0.1:8765
	cd flows && python3 -m http.server 8765 --bind 127.0.0.1
