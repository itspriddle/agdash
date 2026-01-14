# AGDash Makefile

HOST = hoth.priddle.network
REMOTE_DIR = /opt/agdash
USER = priddle
SSH = ssh $(USER)@$(HOST)
RSYNC = rsync -avz --delete --exclude='.git' --exclude='__pycache__' --exclude='.venv' --exclude='*.pyc' --exclude='*.png' --exclude='.envrc'

.PHONY: deploy setup logs run status restart stop ssh clean

deploy:
	@echo "Deploying to $(HOST)..."
	$(RSYNC) ./ $(USER)@$(HOST):$(REMOTE_DIR)/
	$(SSH) "cd $(REMOTE_DIR) && ~/.local/bin/uv sync --extra nanopi"
	$(SSH) "sudo systemctl restart agdash"
	@echo "Done."

setup:
	@echo "Setting up $(HOST)..."
	$(SSH) "sudo apt update && sudo apt install -y python3-dev i2c-tools"
	$(SSH) "command -v uv || curl -LsSf https://astral.sh/uv/install.sh | sh"
	$(SSH) "sudo mkdir -p $(REMOTE_DIR) && sudo chown $(USER):$(USER) $(REMOTE_DIR)"
	$(RSYNC) ./ $(USER)@$(HOST):$(REMOTE_DIR)/
	$(SSH) "cd $(REMOTE_DIR) && ~/.local/bin/uv sync --extra nanopi"
	$(SSH) "sudo systemctl stop agdash 2>/dev/null || true"
	scp agdash.service $(USER)@$(HOST):/tmp/agdash.service
	$(SSH) "sudo mv /tmp/agdash.service /etc/systemd/system/"
	$(SSH) "sudo systemctl daemon-reload"
	$(SSH) "sudo systemctl enable agdash"
	$(SSH) "sudo systemctl start agdash"
	@echo "Done."

logs:
	$(SSH) "journalctl -u agdash -f"

status:
	$(SSH) "sudo systemctl status agdash"

restart:
	$(SSH) "sudo systemctl restart agdash"

stop:
	$(SSH) "sudo systemctl stop agdash"

ssh:
	$(SSH)

run:
	uv run python -m agdash.main

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .venv *.png 2>/dev/null || true
