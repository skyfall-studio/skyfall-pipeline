#!/bin/bash
# SKYFALL Pipeline v3.0 – Structure Auto Generator
# Creates full skeleton directories & template files

REPO=~/skyfall-dev/pipeline

echo "==========================================="
echo " SKYFALL PIPELINE v3.0 STRUCTURE GENERATOR "
echo " Target: $REPO"
echo "==========================================="

cd $REPO || { echo "❌ repo not found"; exit 1; }

echo "📁 Creating directories..."

# Core modules
mkdir -p core/api
mkdir -p core/io
mkdir -p core/env
mkdir -p core/publish/schema
mkdir -p core/utils
mkdir -p core/log

# Application hooks
mkdir -p apps/nuke
mkdir -p apps/resolve
mkdir -p apps/blender
mkdir -p apps/maya

# Tools
mkdir -p tools

# Services
mkdir -p services

# Config
mkdir -p config/ocio
mkdir -p config/luts
mkdir -p config/menu_templates

# Templates
mkdir -p templates/nuke
mkdir -p templates/publish
mkdir -p templates/delivery

# Install scripts
mkdir -p install

echo "📝 Creating placeholder template files..."

# Core files
echo "# SKYFALL Core API Module (v3.0)" > core/api/README.md
echo "# SKYFALL I/O Utilities (v3.0)" > core/io/README.md
echo "# SKYFALL Pipeline Environment Loaders (v3.0)" > core/env/README.md
echo "# Publish Schema Root" > core/publish/schema/README.md
echo "# Shared Utilities" > core/utils/README.md
echo "# Logging utilities" > core/log/README.md

# Apps
echo "# Nuke Integration (menu.py, hooks)" > apps/nuke/README.md
echo "# Resolve Integration" > apps/resolve/README.md
echo "# Blender Integration" > apps/blender/README.md
echo "# Maya Integration" > apps/maya/README.md

# Tools
echo "# Artist Tools (setup_shots, ingest, publish)" > tools/README.md

# Services
echo "# Background Services (kitsu sync, ingest watcher)" > services/README.md

# Config
echo "# OCIO configs for Shows" > config/ocio/README.md
echo "# LUT files" > config/luts/README.md
echo "# Nuke menu templates" > config/menu_templates/README.md

# Templates
echo "# Nuke script templates" > templates/nuke/README.md
echo "# Publish templates" > templates/publish/README.md
echo "# Delivery templates" > templates/delivery/README.md

# Install
echo "# Installation Scripts" > install/README.md

echo "==========================================="
echo " 🎉 SKYFALL Pipeline v3.0 structure created "
echo " Now run:"
echo ""
echo "   git add ."
echo "   git commit -m \"Add v3.0 pipeline skeleton structure\""
echo "   git push"
echo ""
echo "==========================================="
