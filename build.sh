#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala as dependências do sistema para o WeasyPrint
apt-get update && apt-get install -y libpango1.0-0 libpangoft2-1.0-0

# Instala as dependências do Python
pip install -r requirements.txt