"""Initial migration for Qwen Code database schema.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-09-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('project_path', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False, default=0),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata', sqlite.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sqlite_autoincrement=False
    )
    op.create_index(op.f('ix_sessions_id'), 'sessions', ['id'])
    op.create_index(op.f('ix_sessions_project_path'), 'sessions', ['project_path'])
    op.create_index(op.f('ix_sessions_is_active'), 'sessions', ['is_active'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('metadata', sqlite.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sqlite_autoincrement=True
    )
    op.create_index(op.f('ix_messages_id'), 'messages', ['id'])
    op.create_index(op.f('ix_messages_session_id'), 'messages', ['session_id'])
    op.create_index(op.f('ix_messages_timestamp'), 'messages', ['timestamp'])
    
    # Create session_stats table
    op.create_table(
        'session_stats',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('total_messages', sa.Integer(), nullable=False, default=0),
        sa.Column('total_tokens', sa.Integer(), nullable=False, default=0),
        sa.Column('user_messages', sa.Integer(), nullable=False, default=0),
        sa.Column('assistant_messages', sa.Integer(), nullable=False, default=0),
        sa.Column('average_response_time', sa.Float(), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id')
    )
    
    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.CheckConstraint("type IN ('string', 'integer', 'float', 'boolean', 'json')", name='ck_user_preferences_type'),
        sa.PrimaryKeyConstraint('key')
    )
    
    # Create auth_tokens table with encrypted fields
    op.create_table(
        'auth_tokens',
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('provider')
    )
    
    # Create project_analysis table
    op.create_table(
        'project_analysis',
        sa.Column('project_path', sa.String(), nullable=False),
        sa.Column('total_files', sa.Integer(), nullable=True),
        sa.Column('total_lines', sa.Integer(), nullable=True),
        sa.Column('languages', sqlite.JSON(), nullable=True),
        sa.Column('dependencies', sqlite.JSON(), nullable=True),
        sa.Column('structure', sqlite.JSON(), nullable=True),
        sa.Column('last_analyzed', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('analysis_version', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('project_path')
    )
    
    # Create file_metadata table
    op.create_table(
        'file_metadata',
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('project_path', sa.String(), nullable=True),
        sa.Column('file_type', sa.String(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('lines_count', sa.Integer(), nullable=True),
        sa.Column('last_modified', sa.DateTime(), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.Column('analysis_data', sqlite.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['project_path'], ['project_analysis.project_path'], ),
        sa.PrimaryKeyConstraint('file_path')
    )
    op.create_index(op.f('ix_file_metadata_project_path'), 'file_metadata', ['project_path'])
    op.create_index(op.f('ix_file_metadata_file_type'), 'file_metadata', ['file_type'])
    
    # Create usage_stats table
    op.create_table(
        'usage_stats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_data', sqlite.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sqlite_autoincrement=True
    )
    op.create_index(op.f('ix_usage_stats_id'), 'usage_stats', ['id'])
    op.create_index(op.f('ix_usage_stats_event_type'), 'usage_stats', ['event_type'])
    op.create_index(op.f('ix_usage_stats_timestamp'), 'usage_stats', ['timestamp'])
    
    # Create api_usage table
    op.create_table(
        'api_usage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_estimate', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sqlite_autoincrement=True
    )
    op.create_index(op.f('ix_api_usage_id'), 'api_usage', ['id'])
    op.create_index(op.f('ix_api_usage_provider'), 'api_usage', ['provider'])
    op.create_index(op.f('ix_api_usage_timestamp'), 'api_usage', ['timestamp'])
    
    # Create additional performance indexes
    op.create_index('ix_messages_session_timestamp', 'messages', ['session_id', 'timestamp'])
    op.create_index('ix_sessions_project_active', 'sessions', ['project_path', 'is_active'])
    op.create_index('ix_file_metadata_project_type', 'file_metadata', ['project_path', 'file_type'])
    op.create_index('ix_usage_stats_type_timestamp', 'usage_stats', ['event_type', 'timestamp'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_usage_stats_type_timestamp', table_name='usage_stats')
    op.drop_index(op.f('ix_usage_stats_timestamp'), table_name='usage_stats')
    op.drop_index(op.f('ix_usage_stats_event_type'), table_name='usage_stats')
    op.drop_index(op.f('ix_usage_stats_id'), table_name='usage_stats')
    op.drop_table('usage_stats')
    
    op.drop_index(op.f('ix_api_usage_timestamp'), table_name='api_usage')
    op.drop_index(op.f('ix_api_usage_provider'), table_name='api_usage')
    op.drop_index(op.f('ix_api_usage_id'), table_name='api_usage')
    op.drop_table('api_usage')
    
    op.drop_index(op.f('ix_file_metadata_project_type'), table_name='file_metadata')
    op.drop_index(op.f('ix_file_metadata_file_type'), table_name='file_metadata')
    op.drop_index(op.f('ix_file_metadata_project_path'), table_name='file_metadata')
    op.drop_table('file_metadata')
    
    op.drop_table('project_analysis')
    op.drop_table('auth_tokens')
    op.drop_table('user_preferences')
    op.drop_table('session_stats')
    
    op.drop_index(op.f('ix_messages_timestamp'), table_name='messages')
    op.drop_index(op.f('ix_messages_session_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_id'), table_name='messages')
    op.drop_table('messages')
    
    op.drop_index(op.f('ix_sessions_is_active'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_project_path'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_id'), table_name='sessions')
    op.drop_table('sessions')