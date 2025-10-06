from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
# Revision identifiers
revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bloomberg_messages",
        # sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("eventId", sa.String(), nullable=False, unique=True),
        sa.Column("roomId", sa.String(), nullable=False),
        sa.Column("originalMessage", sa.Text(), nullable=False),

        sa.Column("trader_uuid", sa.String(), nullable=False),
        sa.Column("trader_legalEntityShortName", sa.String(), nullable=True),
        sa.Column("trader_alias", sa.String(), nullable=True),

        sa.Column("original_llm_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("current_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),

        sa.Column("is_edited", sa.Boolean(), server_default="false"),
        sa.Column("messageStatus", sa.String(), server_default="received", nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("isTarget", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_table(
        "instruments",
        sa.Column("tradeableId", sa.String(), primary_key=True, index=True),
        sa.Column("expiryDate", sa.Date(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("contractId", sa.String(), nullable=False),
        sa.Column("strategyDisplayName", sa.String(), nullable=False),
        sa.Column("refInstrument", sa.String(), nullable=True),
        sa.Column("refPrice", sa.Float(), nullable=True),
    )
    # --- users ---
    op.create_table(
        'users',
        sa.Column('uuid', sa.String, primary_key=True, index=True),
        sa.Column('shortName', sa.String, nullable=True),
        sa.Column('userName', sa.String, nullable=True),
        sa.Column('alias', sa.String, nullable=True),
        sa.Column('tpPostingID', sa.String, nullable=True),
        sa.Column('tpUserUID', sa.String, nullable=True),
        sa.Column('tpDdeskUID', sa.String, nullable=True),
        sa.Column('legalEntity', sa.String, nullable=True),
        sa.Column('legalEntityShortName', sa.String, nullable=True),
        sa.Column('role', sa.String, nullable=True),
        sa.Column('firmId', sa.String, nullable=True),
    )

    # --- orders ---
    op.create_table(
        "orders",
        sa.Column("orderId", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("createdAt", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("lastUpdated", sa.DateTime(timezone=True), onupdate=sa.func.now()),

        sa.Column("eventId", sa.String(), nullable=False),
        sa.Column("linkedOrderID", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("expiryDate", sa.String(), nullable=False),
        sa.Column("strategyID", sa.String(), nullable=True),
        sa.Column("contractId", sa.String(), nullable=False),
        sa.Column("side", sa.String(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("basis", sa.Float(), nullable=False),

        sa.Column("orderStatus", sa.String(), server_default="active"),
        sa.Column("orderStatusHistory", postgresql.JSON(astext_type=sa.Text()), server_default="[]"),

        sa.Column("traderUuid", sa.String(), nullable=False),
        sa.Column("traderLegalEntityShortName", sa.String(), nullable=True),
        sa.Column("traderAlias", sa.String(), nullable=True),

        sa.Column("refPrice", sa.Float(), nullable=True),

        sa.Column("reminderEnabled", sa.Boolean(), server_default="false"),
        sa.Column("reminderCount", sa.Integer(), server_default="0"),
        sa.Column("nextReminderDue", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lastReminderSent", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminderHistory", postgresql.JSON(astext_type=sa.Text()), server_default="[]"),
        sa.Column("isTarget", sa.Boolean(), server_default="false"),
        sa.Column("targetPrice", sa.String(), nullable=True),

    )


    # # --- efp_run ---
    # op.create_table(
    #     'efp_run',
    #     sa.Column('id', sa.Integer, primary_key=True),
    #     sa.Column('index_name', sa.String(20), nullable=False),
    #     sa.Column('bid', sa.Float, nullable=True),
    #     sa.Column('offer', sa.Float, nullable=True),
    #     sa.Column('cash_ref', sa.Float, nullable=True),
    #     sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    #     sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    # )
    # op.create_index('ix_efp_run_index_name', 'efp_run', ['index_name'])

    # # --- recap ---
    # op.create_table(
    #     'recap',
    #     sa.Column('id', sa.Integer, primary_key=True),
    #     sa.Column('index_name', sa.String(20), nullable=False),
    #     sa.Column('price', sa.Float, nullable=False),
    #     sa.Column('lots', sa.Integer, nullable=False),
    #     sa.Column('cash_ref', sa.Float, nullable=True),
    #     sa.Column('recap_text', sa.Text, nullable=False),
    #     sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    # )

    # # --- cash_level ---
    # op.create_table(
    #     'cash_level',
    #     sa.Column('id', sa.Integer, primary_key=True),
    #     sa.Column('index_name', sa.String(20), nullable=False),
    #     sa.Column('level', sa.Float, nullable=False),
    #     sa.Column('as_of', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    # )
    # op.create_index('ix_cash_level_index_name', 'cash_level', ['index_name'])

    # # --- daily_close ---
    # op.create_table(
    #     'daily_close',
    #     sa.Column('id', sa.Integer, primary_key=True),
    #     sa.Column('index_name', sa.String(20), nullable=False),
    #     sa.Column('level', sa.Float, nullable=False),
    #     sa.Column('as_of_date', sa.Date, nullable=False),
    # )

    # # --- blotter_trades ---
    # op.create_table(
    #     'blotter_trades',
    #     sa.Column('id', sa.Integer, primary_key=True, index=True),
    #     sa.Column('side', sa.String, nullable=False),
    #     sa.Column('index_name', sa.String, nullable=False),
    #     sa.Column('qty', sa.Integer, nullable=False),
    #     sa.Column('avg_price', sa.Float, nullable=False),
    #     sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    # )


def downgrade():
    # op.drop_table('blotter_trades')
    # op.drop_table('daily_close')
    # op.drop_index('ix_cash_level_index_name', table_name='cash_level')
    # op.drop_table('cash_level')
    # op.drop_table('recap')
    # op.drop_index('ix_efp_run_index_name', table_name='efp_run')
    # op.drop_table('efp_run')
    op.drop_table('orders')
    op.drop_table('users')
    op.drop_table("instruments")
    op.drop_table("bloomberg_messages")