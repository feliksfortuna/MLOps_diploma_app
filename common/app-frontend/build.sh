#!/bin/bash

echo "Building MLOps version..."
NEXT_PUBLIC_DEPLOYMENT_TYPE=mlops bun run build
mv .next .next-mlops

echo "Building DevOps version..."
NEXT_PUBLIC_DEPLOYMENT_TYPE=devops bun run build
mv .next .next-devops

echo "Builds completed successfully!"