"""Unique constraints on dependency data

Revision ID: 8
Revises: 7
Create Date: 2023-02-27 16:55:32.016934

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '10'
down_revision = '9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    #UniqueConstraint("repo_id","dep_name", name="deps-insert-unique")
    op.create_unique_constraint('deps-libyear-insert-unique', 'repo_deps_libyear', ['repo_id', 'name', 'data_collection_date'], schema='augur_data')
    op.create_unique_constraint('deps-insert-unique', 'repo_dependencies', ['repo_id', 'dep_name','data_collection_date'], schema='augur_data')
    op.create_unique_constraint('deps-scorecard-insert-unique', 'repo_deps_scorecard', ['repo_id', 'name'], schema='augur_data')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('deps-libyear-insert-unique', 'repo_deps_libyear', schema='augur_data', type_='unique')
    op.drop_constraint('deps-insert-unique', 'repo_dependencies',schema='augur_data', type_='unique')
    op.drop_constraint('deps-scorecard-insert-unique', 'repo_deps_scorecard', schema='augur_data', type_='unique')
    # ### end Alembic commands ###
