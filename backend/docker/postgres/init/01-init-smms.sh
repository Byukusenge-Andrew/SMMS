#!/bin/bash
set -e

# This script runs when the PostgreSQL container is first created
echo "Initializing SMMS PostgreSQL database..."

# Create additional databases if needed
# createdb -U postgres smms_test

# Set up any initial data or configurations
echo "PostgreSQL initialization complete for SMMS!"
