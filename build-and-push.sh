#!/usr/bin/env bash
# Run this on your laptop (or in CI), NOT on the e2-micro VM.
# Builds the backend image for the VM's architecture (amd64) and pushes it
# to Docker Hub, so the VM only ever has to `pull`, never `build`.
set -euo pipefail

DOCKERHUB_USERNAME="kushalzinzuvadia"   # <-- change this
IMAGE_NAME="ai-candidate-screener-backend"
TAG="latest"

docker login   # only needed once per machine

docker buildx build \
  --platform linux/amd64 \
  -t "${DOCKERHUB_USERNAME}/${IMAGE_NAME}:${TAG}" \
  --push \
  ./backend

echo "Pushed ${DOCKERHUB_USERNAME}/${IMAGE_NAME}:${TAG}"
echo "On the VM, run:"
echo "  sudo docker-compose -f docker-compose.prod.yml pull"
echo "  sudo docker-compose -f docker-compose.prod.yml up -d"
