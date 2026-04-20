"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("list_type", sa.String(32), nullable=False, server_default="recurrent"),
        sa.Column("country", sa.String(4), nullable=False, server_default="AR"),
        sa.Column("currency", sa.String(4), nullable=False, server_default="ARS"),
        sa.Column("budget", sa.Numeric(12, 2), nullable=True),
        sa.Column("monitoring_frequency", sa.String(16), nullable=False, server_default="daily"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shopping_lists_user_id", "shopping_lists", ["user_id"])

    op.create_table(
        "product_canonicals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("category", sa.String(128), nullable=False),
        sa.Column("base_unit", sa.String(8), nullable=False),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "shopping_list_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("list_id", sa.String(36), sa.ForeignKey("shopping_lists.id"), nullable=False),
        sa.Column("canonical_product_id", sa.String(36),
                  sa.ForeignKey("product_canonicals.id"), nullable=True),
        sa.Column("original_text", sa.Text, nullable=False),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("preferred_brand", sa.String(128), nullable=True),
        sa.Column("excluded_brands", postgresql.JSONB, nullable=True),
        sa.Column("desired_presentation", sa.String(128), nullable=True),
        sa.Column("desired_quantity", sa.Integer, nullable=False, server_default="1"),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("priority", sa.String(16), nullable=False, server_default="medium"),
        sa.Column("allowed_stores", postgresql.JSONB, nullable=True),
        sa.Column("excluded_stores", postgresql.JSONB, nullable=True),
        sa.Column("allow_equivalents", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("allow_bulk", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shopping_list_items_list_id", "shopping_list_items", ["list_id"])

    op.create_table(
        "offer_observations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("shopping_list_items.id"), nullable=True),
        sa.Column("canonical_product_id", sa.String(36),
                  sa.ForeignKey("product_canonicals.id"), nullable=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("retailer", sa.String(128), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="supermarket"),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("external_sku", sa.String(128), nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("detected_brand", sa.String(128), nullable=True),
        sa.Column("detected_category", sa.String(128), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("original_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(4), nullable=False, server_default="ARS"),
        sa.Column("in_stock", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("shipping_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("promo_description", sa.Text, nullable=True),
        sa.Column("installments", postgresql.JSONB, nullable=True),
        sa.Column("seller", sa.String(255), nullable=True),
        sa.Column("raw_attributes", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("image_url", sa.Text, nullable=True),
        sa.Column("parsed_quantity", sa.Numeric(12, 4), nullable=True),
        sa.Column("parsed_unit", sa.String(16), nullable=True),
        sa.Column("parsed_pack_size", sa.Integer, nullable=True),
        sa.Column("total_quantity", sa.Numeric(12, 4), nullable=True),
        sa.Column("normalized_unit", sa.String(8), nullable=True),
        sa.Column("price_per_base_unit", sa.Numeric(14, 4), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("matching_score", sa.Float, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
    )
    op.create_index("ix_offer_observations_item_id", "offer_observations", ["item_id"])
    op.create_index("ix_offer_observations_source", "offer_observations", ["source"])
    op.create_index("ix_offer_observations_captured_at", "offer_observations", ["captured_at"])

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("shopping_list_items.id"), nullable=False),
        sa.Column("rule_type", sa.String(32), nullable=False),
        sa.Column("threshold_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("threshold_unit", sa.String(8), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "alert_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(36), sa.ForeignKey("alert_rules.id"), nullable=False),
        sa.Column("offer_id", sa.String(36), sa.ForeignKey("offer_observations.id"), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("acknowledged", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("alert_events")
    op.drop_table("alert_rules")
    op.drop_table("offer_observations")
    op.drop_table("shopping_list_items")
    op.drop_table("product_canonicals")
    op.drop_table("shopping_lists")
    op.drop_table("users")
