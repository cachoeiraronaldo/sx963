#!/bin/bash

# Instala libmagic
apt-get update && apt-get install -y libmagic1

# Continua com o build padrão do Vercel
pip install --target=. --upgrade -r requirements.txt