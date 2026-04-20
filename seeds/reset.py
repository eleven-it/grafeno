"""
Resetea la DB y recarga los datos demo.
ADVERTENCIA: borra todos los datos existentes.

Uso:
  python seeds/reset.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.infrastructure.database import engine
from app.domain.models import Base
from seeds.demo import run as load_demo


def reset():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Loading demo data...")
    load_demo()


if __name__ == "__main__":
    confirm = input("Esto borrará TODOS los datos. Continuar? [y/N] ").strip().lower()
    if confirm == "y":
        reset()
    else:
        print("Cancelado.")
