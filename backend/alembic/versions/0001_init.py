from alembic import op
import sqlalchemy as sa

revision = '0001_init'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('efp_run',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('index_name', sa.String(20), nullable=False),
        sa.Column('bid', sa.Float, nullable=True),
        sa.Column('offer', sa.Float, nullable=True),
        sa.Column('cash_ref', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_efp_run_index_name', 'efp_run', ['index_name'])

    op.create_table('recap',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('index_name', sa.String(20), nullable=False),
        sa.Column('price', sa.Float, nullable=False),
        sa.Column('lots', sa.Integer, nullable=False),
        sa.Column('cash_ref', sa.Float, nullable=True),
        sa.Column('recap_text', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )

    op.create_table('cash_level',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('index_name', sa.String(20), nullable=False),
        sa.Column('level', sa.Float, nullable=False),
        sa.Column('as_of', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'))
    )
    op.create_index('ix_cash_level_index_name', 'cash_level', ['index_name'])

    op.create_table('daily_close',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('index_name', sa.String(20), nullable=False),
        sa.Column('level', sa.Float, nullable=False),
        sa.Column('as_of_date', sa.Date, nullable=False)
    )


def downgrade():
    op.drop_table('daily_close')
    op.drop_index('ix_cash_level_index_name', table_name='cash_level')
    op.drop_table('cash_level')
    op.drop_table('recap')
    op.drop_index('ix_efp_run_index_name', table_name='efp_run')
    op.drop_table('efp_run')
