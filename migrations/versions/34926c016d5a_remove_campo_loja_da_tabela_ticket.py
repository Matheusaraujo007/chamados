"""Remove campo loja da tabela ticket

Revision ID: 34926c016d5a
Revises: 5f7010aacbbd
Create Date: 2025-07-04 13:47:58.077804

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '34926c016d5a'
down_revision = '5f7010aacbbd'
branch_labels = None
depends_on = None


def upgrade():
    # ### comandos auto-gerados pelo Alembic - ajuste necessário ###
    with op.batch_alter_table('ticket', schema=None) as batch_op:
        # Alteração da coluna 'setor' para não ser nula
        batch_op.alter_column('setor',
               existing_type=sa.VARCHAR(length=100),
               nullable=False)
        
        # Alteração da coluna 'prioridade' para o novo tipo e para não ser nula
        batch_op.alter_column('prioridade',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.String(length=20),
               nullable=False)
        
        # Remover a coluna 'loja'
        batch_op.drop_column('loja')

    # ### fim dos comandos Alembic ###


def downgrade():
    # ### comandos auto-gerados pelo Alembic - ajuste necessário ###
    with op.batch_alter_table('ticket', schema=None) as batch_op:
        # Adicionar a coluna 'loja' de volta à tabela
        batch_op.add_column(sa.Column('loja', sa.VARCHAR(length=100), nullable=False))
        
        # Alterar novamente as colunas 'prioridade' e 'setor' para os tipos anteriores
        batch_op.alter_column('prioridade',
               existing_type=sa.String(length=20),
               type_=sa.VARCHAR(length=50),
               nullable=True)
        
        batch_op.alter_column('setor',
               existing_type=sa.VARCHAR(length=100),
               nullable=True)

    # ### fim dos comandos Alembic ###
