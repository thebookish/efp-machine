from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
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
        'orders',
        sa.Column('orderId', sa.String, primary_key=True, index=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('eventId', sa.String, nullable=True),
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('timestamp', sa.String, nullable=True),
        sa.Column('sender_uuid', sa.String, nullable=True),
        sa.Column('requester_uuid', sa.String, nullable=True),
        sa.Column('expiryDate', sa.String, nullable=True),
        sa.Column('strategyID', sa.String, nullable=True),
        sa.Column('contractId', sa.String, nullable=True),
        sa.Column('orderType', sa.String, nullable=True),
        # sa.Column('orderID', sa.String, nullable=True),
        sa.Column('state', sa.String, nullable=True),
        sa.Column('buySell', sa.String, nullable=True),
        sa.Column('price', sa.Float, nullable=True),
        sa.Column('basis', sa.Float, nullable=True),
        sa.Column('linkedOrderID', sa.String, nullable=True),
        sa.Column('refInstrument', sa.String, nullable=True),
        sa.Column('refPrice', sa.Float, nullable=True),
        sa.Column('alias', sa.String, nullable=True),
        sa.Column('legalEntityShortName', sa.String, nullable=True),
        sa.Column('tpUserUidTrader', sa.String, nullable=True),
        sa.Column('tpPostingIdRequester', sa.String, nullable=True),
        sa.Column('uuidRequester', sa.String, nullable=True),
        sa.Column('response', sa.Text, nullable=True),
        sa.Column('timestamp', sa.DateTime, nullable=True),
    )

    # --- efp_run ---
    op.create_table(
        'efp_run',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('index_name', sa.String(20), nullable=False),
        sa.Column('bid', sa.Float, nullable=True),
        sa.Column('offer', sa.Float, nullable=True),
        sa.Column('cash_ref', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_efp_run_index_name', 'efp_run', ['index_name'])

    # --- recap ---
    op.create_table(
        'recap',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('index_name', sa.String(20), nullable=False),
        sa.Column('price', sa.Float, nullable=False),
        sa.Column('lots', sa.Integer, nullable=False),
        sa.Column('cash_ref', sa.Float, nullable=True),
        sa.Column('recap_text', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # --- cash_level ---
    op.create_table(
        'cash_level',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('index_name', sa.String(20), nullable=False),
        sa.Column('level', sa.Float, nullable=False),
        sa.Column('as_of', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('ix_cash_level_index_name', 'cash_level', ['index_name'])

    # --- daily_close ---
    op.create_table(
        'daily_close',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('index_name', sa.String(20), nullable=False),
        sa.Column('level', sa.Float, nullable=False),
        sa.Column('as_of_date', sa.Date, nullable=False),
    )

    # --- blotter_trades ---
    op.create_table(
        'blotter_trades',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('side', sa.String, nullable=False),
        sa.Column('index_name', sa.String, nullable=False),
        sa.Column('qty', sa.Integer, nullable=False),
        sa.Column('avg_price', sa.Float, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )


def downgrade():
    op.drop_table('blotter_trades')
    op.drop_table('daily_close')
    op.drop_index('ix_cash_level_index_name', table_name='cash_level')
    op.drop_table('cash_level')
    op.drop_table('recap')
    op.drop_index('ix_efp_run_index_name', table_name='efp_run')
    op.drop_table('efp_run')
    op.drop_table('orders')
    op.drop_table('users')