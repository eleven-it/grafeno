"""
Script de seed para cargar datos demo.
Crea una lista de ejemplo con items y ofertas de múltiples fuentes.

Uso:
  python seeds/demo.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.infrastructure.database import SessionLocal, create_all_tables
from app.services import list_service, item_service, offer_service, alert_service
from app.connectors.mock import MockConnector


def run():
    create_all_tables()
    db = SessionLocal()

    try:
        # Usuario demo
        user = list_service.get_or_create_demo_user(db)
        print(f"Usuario: {user.email} ({user.id})")

        # Lista 1: Super semanal
        lst = list_service.create_list(db, user.id, {
            "name": "Super semanal",
            "description": "Compras habituales del supermercado",
            "list_type": "recurrent",
            "country": "AR",
            "currency": "ARS",
            "monitoring_frequency": "daily",
        })
        print(f"\nLista creada: {lst.name} ({lst.id})")

        # Items
        items_data = [
            {
                "original_text": "leche entera 1L",
                "category": "leche",
                "preferred_brand": "La Serenísima",
                "desired_quantity": 3,
                "priority": "high",
                "allow_equivalents": True,
                "allow_bulk": True,
            },
            {
                "original_text": "detergente 750ml",
                "category": "detergente",
                "desired_quantity": 1,
                "priority": "medium",
                "allow_equivalents": True,
            },
            {
                "original_text": "arroz largo fino 1kg",
                "category": "arroz",
                "desired_quantity": 2,
                "priority": "medium",
            },
        ]

        created_items = []
        for item_data in items_data:
            item = item_service.create_item(db, lst.id, item_data)
            created_items.append(item)
            print(f"  Item: {item.original_text} ({item.id})")

        # Lista 2: Materiales de obra
        lst2 = list_service.create_list(db, user.id, {
            "name": "Materiales de obra",
            "description": "Pintura y materiales para remodelación",
            "list_type": "project",
            "country": "AR",
            "currency": "ARS",
        })
        paint_item = item_service.create_item(db, lst2.id, {
            "original_text": "pintura látex interior blanco 4L",
            "category": "pintura",
            "desired_quantity": 4,
            "priority": "high",
            "allow_bulk": True,
        })
        print(f"\nLista 2: {lst2.name} ({lst2.id})")
        print(f"  Item: {paint_item.original_text} ({paint_item.id})")

        # Cargar ofertas desde mock connector
        connector = MockConnector()
        all_offers = connector.get_all()

        # Asignar item_id según categoría
        category_to_item = {
            "leche": created_items[0].id,
            "detergente": created_items[1].id,
            "arroz": created_items[2].id,
            "pintura": paint_item.id,
        }

        imported = 0
        for raw_offer in all_offers:
            offer_dict = raw_offer.to_dict()
            cat = offer_dict.get("detected_category")
            if cat in category_to_item:
                offer_dict["item_id"] = category_to_item[cat]
            offer_service.import_offer(db, offer_dict)
            imported += 1

        print(f"\nOfertas importadas: {imported}")

        # Alertas de ejemplo
        alert_service.create_rule(db, created_items[0].id, {
            "rule_type": "price_below",
            "threshold_value": 900,
            "threshold_unit": "ARS",
        })
        alert_service.create_rule(db, created_items[0].id, {
            "rule_type": "unit_price_below",
            "threshold_value": 1000,
            "threshold_unit": "ARS",
        })
        print("\nReglas de alerta creadas")

        print("\n" + "="*50)
        print("SEED COMPLETADO")
        print(f"Lista principal: {lst.id}")
        print(f"Items de leche: {created_items[0].id}")
        print(f"Lista de obra: {lst2.id}")
        print("\nEjemplos de endpoints:")
        print(f"  GET /lists/{lst.id}/items")
        print(f"  GET /items/{created_items[0].id}/unit-economics")
        print(f"  GET /items/{created_items[0].id}/recommendation")
        print(f"  GET /lists/{lst.id}/best-cart")

    finally:
        db.close()


if __name__ == "__main__":
    run()
