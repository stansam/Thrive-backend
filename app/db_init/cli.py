"""
Flask CLI Commands for Database Management
Run with: flask db-init, flask db-reset, etc.
"""

import click
from flask import current_app
from flask.cli import with_appcontext
from app.db_init import init_database, clear_database
from app.db_init.init_db import reset_database


@click.group()
def db_commands():
    """Database management commands"""
    pass


@db_commands.command('init')
@click.option('--no-sample-data', is_flag=True, help='Skip creating sample data')
@with_appcontext
def init_db_command(no_sample_data):
    """Initialize the database with tables and optional sample data"""
    try:
        with_sample_data = not no_sample_data
        init_database(with_sample_data=with_sample_data)
        click.echo('✅ Database initialized successfully!')
    except Exception as e:
        click.echo(f'❌ Error initializing database: {str(e)}', err=True)
        raise


@db_commands.command('reset')
@click.confirmation_option(prompt='⚠️  This will delete all data. Are you sure?')
@with_appcontext
def reset_db_command():
    """Reset the database (drop all tables and recreate with sample data)"""
    try:
        reset_database()
        click.echo('✅ Database reset successfully!')
    except Exception as e:
        click.echo(f'❌ Error resetting database: {str(e)}', err=True)
        raise


@db_commands.command('clear')
@click.confirmation_option(prompt='⚠️  This will delete all tables. Are you sure?')
@with_appcontext
def clear_db_command():
    """Clear all database tables"""
    try:
        clear_database()
        click.echo('✅ Database cleared successfully!')
    except Exception as e:
        click.echo(f'❌ Error clearing database: {str(e)}', err=True)
        raise


def register_commands(app):
    """Register CLI commands with the Flask app"""
    app.cli.add_command(db_commands, name='db-manage')
