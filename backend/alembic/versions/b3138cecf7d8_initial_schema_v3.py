"""initial_schema_v3

Revision ID: b3138cecf7d8
Revises: 
Create Date: 2026-04-29 19:45:31.505483

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b3138cecf7d8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Criar 'user' SEM FK de company_id (evita dependência circular)
    op.create_table('user',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)

    # 2. Criar 'company' COM FK para user.id (user já existe)
    op.create_table('company',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('document', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('created_by', sa.String(length=100), nullable=True),
    sa.Column('updated_by', sa.String(length=100), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # 3. Adicionar FK company_id em user COM ON DELETE SET NULL
    op.create_foreign_key('fk_user_company_id', 'user', 'company', ['company_id'], ['id'], ondelete='SET NULL')

    op.create_table('business',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('document', sa.String(length=20), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('created_by', sa.String(length=100), nullable=True),
    sa.Column('updated_by', sa.String(length=100), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('product',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('company_id', sa.Integer(), nullable=False),
    sa.Column('sku', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('ncm', sa.String(length=20), nullable=True),
    sa.Column('cost_price', sa.Numeric(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['company_id'], ['company.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('uploads',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('upload_type', sa.String(length=50), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('original_filename', sa.String(length=255), nullable=False),
    sa.Column('file_path', sa.String(length=500), nullable=False),
    sa.Column('parquet_path', sa.String(length=500), nullable=True),
    sa.Column('processing_status', sa.String(length=50), nullable=False),
    sa.Column('rows_processed', sa.Integer(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('metrics_json', sa.Text(), nullable=True),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_uploads_upload_type'), 'uploads', ['upload_type'], unique=False)
    op.create_index(op.f('ix_uploads_user_id'), 'uploads', ['user_id'], unique=False)
    op.create_table('account',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('business_id', sa.Integer(), nullable=True),
    sa.Column('marketplace_id', sa.BigInteger(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('access_token', sa.Text(), nullable=True),
    sa.Column('refresh_token', sa.Text(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('created_by', sa.String(length=100), nullable=True),
    sa.Column('updated_by', sa.String(length=100), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['business_id'], ['business.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('account_address',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.Text(), nullable=True),
    sa.Column('logradouro', sa.Text(), nullable=False),
    sa.Column('numero', sa.Text(), nullable=False),
    sa.Column('complemento', sa.Text(), nullable=True),
    sa.Column('bairro', sa.Text(), nullable=True),
    sa.Column('cidade', sa.Text(), nullable=False),
    sa.Column('estado', sa.CHAR(length=2), nullable=False),
    sa.Column('cep', sa.Text(), nullable=True),
    sa.Column('principal', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('external_order_id', sa.String(length=50), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Text(), nullable=True),
    sa.Column('data_criacao', sa.DateTime(), nullable=True),
    sa.Column('valor', sa.Numeric(), nullable=True),
    sa.Column('pago', sa.Numeric(), nullable=True),
    sa.Column('receita_produtos', sa.Numeric(), nullable=True),
    sa.Column('acrescimo_parcelamento', sa.Numeric(), nullable=True),
    sa.Column('tarifa_venda', sa.Numeric(), nullable=True),
    sa.Column('parcelas', sa.Integer(), nullable=True),
    sa.Column('valor_parcela', sa.Numeric(), nullable=True),
    sa.Column('total_refund', sa.Numeric(), nullable=True),
    sa.Column('rebate_meli', sa.Numeric(), nullable=True),
    sa.Column('receita_envio', sa.Numeric(), nullable=True),
    sa.Column('tarifa_envio', sa.Numeric(), nullable=True),
    sa.Column('custo_envio_declarado', sa.Numeric(), nullable=True, server_default=sa.text('0')),
    sa.Column('custo_diferenca_peso', sa.Numeric(), nullable=True, server_default=sa.text('0')),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('created_by', sa.String(length=100), nullable=True),
    sa.Column('updated_by', sa.String(length=100), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('billing',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('order_id', sa.BigInteger(), nullable=True),
    sa.Column('doc_tipo', sa.Text(), nullable=True),
    sa.Column('doc_numero', sa.Text(), nullable=True),
    sa.Column('razao_social', sa.Text(), nullable=True),
    sa.Column('ie', sa.Text(), nullable=True),
    sa.Column('cep', sa.Text(), nullable=True),
    sa.Column('logradouro', sa.Text(), nullable=True),
    sa.Column('numero', sa.Text(), nullable=True),
    sa.Column('complemento', sa.Text(), nullable=True),
    sa.Column('bairro', sa.Text(), nullable=True),
    sa.Column('cidade', sa.Text(), nullable=True),
    sa.Column('estado', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('items_order',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('sku', sa.Text(), nullable=True),
    sa.Column('titulo', sa.String(length=255), nullable=False),
    sa.Column('quantidade', sa.Integer(), nullable=False),
    sa.Column('preco_unitario', sa.Numeric(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('created_by', sa.String(length=100), nullable=True),
    sa.Column('updated_by', sa.String(length=100), nullable=True),
    sa.Column('deleted_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('shipping',
    sa.Column('id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('order_id', sa.BigInteger(), nullable=True),
    sa.Column('receiver_name', sa.Text(), nullable=True),
    sa.Column('cep', sa.Text(), nullable=True),
    sa.Column('logradouro', sa.Text(), nullable=True),
    sa.Column('numero', sa.Text(), nullable=True),
    sa.Column('complemento', sa.Text(), nullable=True),
    sa.Column('bairro', sa.Text(), nullable=True),
    sa.Column('cidade', sa.Text(), nullable=True),
    sa.Column('estado', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

    # Views
    op.execute("""
        CREATE OR REPLACE VIEW v_accounts_ativas AS
        SELECT * FROM account
        WHERE status = 'active'
          AND deleted_at IS NULL
    """)
    op.execute("""
        CREATE OR REPLACE VIEW v_business_ativos AS
        SELECT * FROM business
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_business_ativos")
    op.execute("DROP VIEW IF EXISTS v_accounts_ativas")
    op.drop_constraint('fk_user_company_id', 'user', type_='foreignkey')
    op.drop_table('shipping')
    op.drop_table('items_order')
    op.drop_table('billing')
    op.drop_table('orders')
    op.drop_table('account_address')
    op.drop_table('account')
    op.drop_index(op.f('ix_uploads_user_id'), table_name='uploads')
    op.drop_index(op.f('ix_uploads_upload_type'), table_name='uploads')
    op.drop_table('uploads')
    op.drop_table('product')
    op.drop_table('business')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('company')
    op.drop_table('user')