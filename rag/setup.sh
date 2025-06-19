#!/bin/bash
# Setup script for RAG Solution on Linux/Mac

echo "Installing dependencies..."
poetry install

echo
echo "Creating .env file if it doesn't exist..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please update it with your OpenAI API key."
else
    echo ".env file already exists."
fi

echo
echo "Setup complete!"
echo
echo "To run the application:"
echo "poetry run python src/main.py"
echo
echo "For more information, see USAGE.md"
